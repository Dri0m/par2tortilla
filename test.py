import os
import subprocess
import unittest
from pathlib import Path

from click.testing import CliRunner

import par2tortilla
from constants import DEFAULT_PARITY_FILE_COUNT, DEFAULT_BLOCK_COUNT, DEFAULT_REDUNDANCY
from utils import corrupt_file, par2create, glob_files

CWD = None
TEST_FILE_SIZE = 2 ** 20


class Context:
    def __init__(self, parity_file_count: int = DEFAULT_PARITY_FILE_COUNT, redundancy: int = DEFAULT_REDUNDANCY,
                 block_count: int = DEFAULT_BLOCK_COUNT):
        self.cwd = None
        self.test_directories = ["a1/a2/",
                                 "b1/b2/",
                                 "b1/b2/b3/b4/"]
        self.test_files = ["f0.bin",
                           "a1/f1.bin",
                           "a1/f2.bin",
                           "a1/a2/f3.bin",
                           "a1/a2/f4.bin",
                           "b1/b2/f5.bin"]

        self.globbed_files = None

        self.parity_file_count = parity_file_count
        self.redundancy = redundancy
        self.block_count = block_count

    def create_test_data(self):
        for directory_chain in self.test_directories:
            print(f"creating directory chain '{directory_chain}'...")
            Path(directory_chain).mkdir(parents=True, exist_ok=True)

        for file_name in self.test_files:
            print(f"creating file '{file_name}'...")
            with open(file_name, "wb") as f:
                f.write(os.urandom(TEST_FILE_SIZE))

        self.globbed_files = glob_files("./")

    def create_parity_for_test_data(self):
        for file_name in self.globbed_files:
            par2create(file_name, self.parity_file_count, self.redundancy, self.block_count)

    def verify_parity_for_test_data(self, expect_damage: bool, repair_possible: bool):
        for file_name in self.globbed_files:
            par2verify_test(file_name, expect_damage, repair_possible)

    def corrupt_test_data(self, corruption_percent: float):
        """Corrupt files from start to corruption_percent."""

        for file_name in self.globbed_files:
            corrupt_file(file_name, corruption_percent)

    def corrupt_parity_data(self, corruption_percent: float):
        """Corrupt files from start to corruption_percent. TODO works only with nice and even parity block counts and vol sizes."""

        parity_files = []

        parity_blocks = int(self.block_count * (self.redundancy / 100))
        block_digits = len(str(self.block_count)) - 1

        for file_name in self.globbed_files:
            parity_files.append(f"{file_name}.par2")
            block_counter = 0
            vol_block_count = int(parity_blocks / self.parity_file_count)
            for i in range(self.parity_file_count):
                parity_files.append(
                    f"{file_name}.vol{str(block_counter).zfill(block_digits)}+{str(vol_block_count).zfill(block_digits)}.par2")
                block_counter += vol_block_count

        for file_name in parity_files:
            corrupt_file(file_name, corruption_percent)


def par2verify_test(file: str, expect_damage: bool, repair_possible: bool):
    print(f"verifying file '{file}'...")
    process = subprocess.Popen(["par2", "v", file],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    assert stderr == b"", f"some stderr happened: {stderr}"
    print(stdout)

    if expect_damage:
        assert b"Repair is required" in stdout, "file should be damaged but message not found"

        if repair_possible:
            assert b"Repair is possible" in stdout, "repair should be possible but message not found"
        else:
            assert b"Repair is not possible" in stdout, "repair should not be possible but message not found"


class TestsPar2Baseline(unittest.TestCase):
    """Some basic tests testing almost only the behavior of par2."""

    def setUp(self):
        self.context = Context()

    def test_no_damage(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            self.context.create_parity_for_test_data()
            self.context.verify_parity_for_test_data(expect_damage=False, repair_possible=True)

    def test_repairable_damage(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context = Context(redundancy=10)
            self.context.create_test_data()
            self.context.create_parity_for_test_data()
            self.context.corrupt_test_data(5)
            self.context.verify_parity_for_test_data(expect_damage=True, repair_possible=True)

    def test_repairable_damage_edge(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context = Context(redundancy=10)
            self.context.create_test_data()
            self.context.create_parity_for_test_data()
            self.context.corrupt_test_data(10)
            self.context.verify_parity_for_test_data(expect_damage=True, repair_possible=True)

    def test_unrepairable_damage(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context = Context(redundancy=10)
            self.context.create_test_data()
            self.context.create_parity_for_test_data()
            self.context.corrupt_test_data(10.1)
            self.context.verify_parity_for_test_data(expect_damage=True, repair_possible=False)

    def test_repairable_damage_corrupt_par_files(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context = Context(redundancy=10)
            self.context.create_test_data()
            self.context.create_parity_for_test_data()
            self.context.corrupt_test_data(5)
            self.context.corrupt_parity_data(30)
            self.context.verify_parity_for_test_data(expect_damage=True, repair_possible=True)

    def test_unrepairable_damage_corrupt_par_files(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context = Context(redundancy=10)
            self.context.create_test_data()
            self.context.create_parity_for_test_data()
            self.context.corrupt_test_data(5)
            self.context.corrupt_parity_data(51)
            self.context.verify_parity_for_test_data(expect_damage=True, repair_possible=False)


class TestsPar2TortillaRun(unittest.TestCase):

    def setUp(self):
        self.context = Context()

    def test_read_only(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "./"])
            assert result.exit_code == 0
            assert f"Data files with parity: 0" in result.output
            assert f"Data files without parity: {len(self.context.test_files)}" in result.output
            assert f"PAR2 files: 0" in result.output
            assert f"PAR2 files without data files: 0" in result.output
            assert f"Data file backups (?) created by par2repair: 0" in result.output

    def test_create_basic(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "--create", "./"])
            assert result.exit_code == 0

            result = runner.invoke(par2tortilla.main, ["run", "./"])
            assert result.exit_code == 0
            assert f"Data files with parity: {len(self.context.test_files)}" in result.output
            assert f"Data files without parity: 0" in result.output
            assert f"PAR2 files: {len(self.context.test_files) * (self.context.parity_file_count + 1)}" in result.output
            assert f"PAR2 files without data files: 0" in result.output
            assert f"Data file backups (?) created by par2repair: 0" in result.output

    def test_create_delete_file(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "--create", "./"])
            assert result.exit_code == 0

            Path(self.context.test_files[0]).unlink()

            result = runner.invoke(par2tortilla.main, ["run", "./"])
            assert result.exit_code == 0
            assert f"Data files with parity: {len(self.context.test_files) - 1}" in result.output
            assert f"Data files without parity: 0" in result.output
            assert f"PAR2 files: {len(self.context.test_files) * (self.context.parity_file_count + 1)}" in result.output
            assert f"PAR2 files without data files: {self.context.parity_file_count + 1}" in result.output
            assert f"Data file backups (?) created by par2repair: 0" in result.output

    def test_create_no_files(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(par2tortilla.main, ["run", "--create", "./"])
            assert result.exit_code == 0
            assert f"No files without parity found." in result.output

    def test_verify_no_files(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(par2tortilla.main, ["run", "--verify", "./"])
            assert result.exit_code == 0
            assert f"No files with parity found." in result.output

    def test_verify_no_files_with_parity(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "--verify", "./"])
            assert result.exit_code == 0
            assert f"No files with parity found." in result.output

    def test_verify_basic(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "--create", "./"])
            assert result.exit_code == 0

            result = runner.invoke(par2tortilla.main, ["run", "--verify", "./"])
            assert result.exit_code == 0
            assert f"Files that are OK: {len(self.context.test_files)}" in result.output
            assert f"Files that are damaged but repairable: 0" in result.output
            assert f"Files that are damaged and unrepairable: 0" in result.output

    def test_verify_repairable(self):
        self.context = Context(redundancy=10)
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "--create", "./"])
            assert result.exit_code == 0

            self.context.corrupt_test_data(5)

            result = runner.invoke(par2tortilla.main, ["run", "--verify", "./"])
            assert result.exit_code == 0
            assert f"Files that are OK: 0" in result.output
            assert f"Files that are damaged but repairable: {len(self.context.test_files)}" in result.output
            assert f"Files that are damaged and unrepairable: 0" in result.output

    def test_verify_fubar(self):
        self.context = Context(redundancy=10)
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "--create", "./"])
            assert result.exit_code == 0

            self.context.corrupt_test_data(15)

            result = runner.invoke(par2tortilla.main, ["run", "--verify", "./"])
            assert result.exit_code == 0
            assert f"Files that are OK: 0" in result.output
            assert f"Files that are damaged but repairable: 0" in result.output
            assert f"Files that are damaged and unrepairable: {len(self.context.test_files)}" in result.output

    def test_repair_without_verify(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(par2tortilla.main, ["run", "--repair", "./"])
            assert result.exit_code == 1
            assert f"Cannot use --repair without --verify!" in result.output

    def test_repair_basic(self):
        self.context = Context(redundancy=10)
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "--create", "./"])
            assert result.exit_code == 0

            self.context.corrupt_test_data(5)

            result = runner.invoke(par2tortilla.main, ["run", "--verify", "--repair", "./"])
            assert result.exit_code == 0
            assert f"Repaired {len(self.context.test_files)}/{len(self.context.test_files)} files." in result.output

            result = runner.invoke(par2tortilla.main, ["run", "--verify", "./"])
            assert result.exit_code == 0
            assert f"Files that are OK: {len(self.context.test_files)}" in result.output
            assert f"Files that are damaged but repairable: 0" in result.output
            assert f"Files that are damaged and unrepairable: 0" in result.output

            result = runner.invoke(par2tortilla.main, ["run", "./"])
            assert result.exit_code == 0
            assert f"Data files with parity: {len(self.context.test_files)}" in result.output
            assert f"Data files without parity: 0" in result.output
            assert f"PAR2 files: {len(self.context.test_files) * (self.context.parity_file_count + 1)}" in result.output
            assert f"PAR2 files without data files: 0" in result.output
            assert f"Data file backups (?) created by par2repair: {len(self.context.test_files)}" in result.output

    def test_repair_check_backups(self):
        self.context = Context(redundancy=10)
        runner = CliRunner()
        with runner.isolated_filesystem():
            self.context.create_test_data()
            result = runner.invoke(par2tortilla.main, ["run", "--create", "./"])
            assert result.exit_code == 0

            self.context.corrupt_test_data(5)

            result = runner.invoke(par2tortilla.main, ["run", "--verify", "--repair", "./"])
            assert result.exit_code == 0

            result = runner.invoke(par2tortilla.main, ["run", "./"])
            assert result.exit_code == 0
            assert f"Data files with parity: {len(self.context.test_files)}" in result.output
            assert f"Data files without parity: 0" in result.output
            assert f"PAR2 files: {len(self.context.test_files) * (self.context.parity_file_count + 1)}" in result.output
            assert f"PAR2 files without data files: 0" in result.output
            assert f"Data file backups (?) created by par2repair: {len(self.context.test_files)}" in result.output


if __name__ == "__main__":
    unittest.main()
