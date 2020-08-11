import glob
import os
import subprocess
from pathlib import Path
from typing import Tuple

from constants import FileStatus


def rmdir(directory):
    directory = Path(directory)
    for item in directory.iterdir():
        if item.is_dir():
            rmdir(item)
        else:
            item.unlink()
    directory.rmdir()


def corrupt_file(file_name: str, corruption_percent: float):
    print(f"reading '{file_name}'...")
    with open(file_name, "rb+") as f:
        data = bytearray(f.read())
        write_stop = int(len(data) * (corruption_percent / 100))

        print(f"corrupting first {write_stop} bytes...")
        write_data = os.urandom(write_stop)
        for i in range(write_stop):
            data[i] = write_data[i]

        print(f"writing '{file_name}'...")
        f.seek(0)
        f.write(data)
        f.truncate()


def par2create(file: str, parity_file_count: int, redundancy: int, block_count: int):
    print(f"creating par2 parity for '{file}'...")
    process = subprocess.Popen(
        ["par2", "c", "-q", "-u", f"-n{parity_file_count}", f"-r{redundancy}", f"-b{block_count}", file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    assert stderr == b"", f"ERROR '{file}' - {stderr}"  # TODO handle


def par2verify(file: str) -> Tuple[str, FileStatus]:
    print(f"verifying file '{file}'...")
    process = subprocess.Popen(["par2", "v", "-q", file],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    assert stderr == b"", f"ERROR '{file}' - {stderr}"  # TODO handle

    if b"All files are correct, repair is not required" in stdout:
        return file, FileStatus.OK

    if b"Repair is required" in stdout:
        if b"Repair is possible" in stdout:
            return file, FileStatus.REPAIRABLE
        if b"Repair is not possible" in stdout:
            return file, FileStatus.FUBAR

    print(stdout)
    raise Exception(f"ERROR '{file}' - Unexpected par2 output ^^^.")


def par2repair(file: str) -> FileStatus:
    print(f"repairing file '{file}'...")
    process = subprocess.Popen(["par2", "r", "-q", file],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    assert stderr == b"", f"ERROR '{file}' - {stderr}"  # TODO handle

    if b"Repair complete" in stdout:
        return FileStatus.REPAIRED

    print(stdout)
    raise Exception(f"ERROR '{file}' - Unexpected par2 output ^^^.")


def glob_files(directory: str) -> set:
    if not Path(directory).exists():
        raise FileNotFoundError(directory)
    if not Path(directory).is_dir():
        raise NotADirectoryError(directory)
    return {str(Path(f)) for f in glob.glob(directory + "/**", recursive=True) if Path(f).is_file()}
