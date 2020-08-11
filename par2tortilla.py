import multiprocessing
import re
from functools import partial

import click

from constants import DEFAULT_PARITY_FILE_COUNT, DEFAULT_REDUNDANCY, DEFAULT_BLOCK_COUNT, FileStatus
from utils import glob_files, par2create, par2verify, par2repair


@click.group()
# @click.argument('command', type=click.Choice(['run', 'split-directories', 'merge-directories']), nargs=1)
def main():
    """A tool that runs `par2` recursively on each and every file in a specified directory."""
    pass


@main.command()
@click.option("--create/--no-create", "create", default=False, show_default=True,
              help="Create PAR2 parities for files that do not have them.")
@click.option("--verify/--no-verify", "verify", default=False, show_default=True, help="Verify files that have PAR2 parities.")
@click.option("--repair/--no-repair", "repair", default=False, show_default=True,
              help="Repair damaged files, assuming they have PAR2 parities.")
@click.option("--parity-file-count", "parity_file_count", default=DEFAULT_PARITY_FILE_COUNT, show_default=True,
              help="PAR2 file count. Uniform size.")
@click.option("--redundancy", "redundancy", default=DEFAULT_REDUNDANCY, show_default=True, help="PAR2 redundancy.")
@click.option("--block-count", "block_count", default=DEFAULT_BLOCK_COUNT, show_default=True, help="PAR2 block count.")
@click.option("-p", "--processes", "processes", default=2, show_default=True, help="Process files simultaneously.")
@click.argument("directory", type=click.Path())
def run(create, verify, repair, parity_file_count, redundancy, block_count, processes, directory):
    if repair and not verify:
        click.echo("Cannot use --repair without --verify!")
        exit(1)

    all_files: set = glob_files(directory)

    data_files = set(filter(lambda s: not s.endswith(".par2"), all_files))
    parity_files = set(filter(lambda s: s.endswith(".par2"), all_files))

    files_without_parity = set()
    for file_name in data_files:
        assumed_parity_name = file_name + ".par2"
        if assumed_parity_name not in parity_files:
            files_without_parity.add(file_name)

    files_with_parity: set = data_files.difference(files_without_parity)

    parity_without_files = set()
    vol_regex = re.compile(r"^.*\.vol\d+\+\d+\.par2$")
    for file_name in parity_files:
        if vol_regex.match(file_name):
            assumed_data_file = ".".join(file_name.split(".")[:-2])
        else:
            assumed_data_file = ".".join(file_name.split(".")[:-1])
        if assumed_data_file not in data_files:
            parity_without_files.add(file_name)

    numeric_extension_regex = re.compile(r".*\.\d+")
    numeric_extension_files = set(filter(lambda s: numeric_extension_regex.match(s), data_files))

    potential_backup_files = set()
    for file_name in numeric_extension_files:
        assumed_data_file = ".".join(file_name.split(".")[:-1])
        if assumed_data_file in data_files:
            potential_backup_files.add(file_name)
            files_without_parity.remove(file_name)

    if not create and not verify:
        click.echo(f"Data files with parity: {len(files_with_parity)}")
        click.echo(f"Data files without parity: {len(files_without_parity)}")
        click.echo(f"PAR2 files: {len(parity_files)}")
        click.echo(f"PAR2 files without data files: {len(parity_without_files)}")
        click.echo(f"Data file backups (?) created by par2repair: {len(potential_backup_files)}")
        click.echo("Nothing was asked, nothing to do.")
        exit(0)

    if create:
        if len(files_without_parity) == 0:
            click.echo("No files without parity found.")

        click.echo("Creating parities...")
        mp_par2create = partial(par2create, parity_file_count=parity_file_count, redundancy=redundancy, block_count=block_count)
        multiprocessing.Pool(processes).map(mp_par2create, files_without_parity, len(files_without_parity) // processes + 1)

    if verify:
        if len(files_with_parity) == 0:
            click.echo("No files with parity found.")
        else:

            files_ok = set()
            files_repairable = set()
            files_fubar = set()

            click.echo("Verifying files...")
            for file_name, result in multiprocessing.Pool(processes).map(par2verify, files_with_parity,
                                                                         len(files_with_parity) // processes + 1):
                if result == FileStatus.OK:
                    files_ok.add(file_name)
                elif result == FileStatus.REPAIRABLE:
                    files_repairable.add(file_name)
                elif result == FileStatus.FUBAR:
                    files_fubar.add(file_name)

            click.echo(f"Files that are OK: {len(files_ok)}")
            click.echo(f"Files that are damaged but repairable: {len(files_repairable)}")
            click.echo(f"Files that are damaged and unrepairable: {len(files_fubar)}")

            if repair:
                click.echo("Repairing files...")
                repair_counter = 0
                for result in multiprocessing.Pool(processes).map(par2repair, files_repairable, len(files_repairable) // processes + 1):
                    if result == FileStatus.REPAIRED:
                        repair_counter += 1
                click.echo(f"Repaired {repair_counter}/{len(files_repairable)} files.")


@main.command()
@click.argument('directory', type=click.Path())
@click.argument('par2-directory', type=click.Path())
def split_directories():
    raise NotImplementedError()  # TODO


@main.command()
@click.argument('directory', type=click.Path())
@click.argument('par2-directory', type=click.Path())
def merge_directories():
    raise NotImplementedError()  # TODO


if __name__ == "__main__":
    main()
