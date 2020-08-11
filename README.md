# par2tortilla
It's a python3 tool that runs `par2cmdline` recursively on each and every file in a specified directory. It expects you to have `par2` command available.

I intend to use this tool to enhance long-living collections of *small* files with protection against random corruptions in situations where better solutions (ZFS) are unavailable or too costly. A `restic` repo comes to mind.

## Usage

`python par2tortilla.py run --help`

```
Usage: par2tortilla.py run [OPTIONS] DIRECTORY

Options:
  --create / --no-create       Create PAR2 parities for files that do not have
                               them.  [default: False]
  --verify / --no-verify       Verify files that have PAR2 parities.
                               [default: False]
  --repair / --no-repair       Repair damaged files, assuming they have PAR2
                               parities.  [default: False]
  --parity-file-count INTEGER  PAR2 file count. Uniform size.  [default: 1]
  --redundancy INTEGER         PAR2 redundancy.  [default: 10]
  --block-count INTEGER        PAR2 block count.  [default: 500]
  -p, --processes INTEGER      Process files simultaneously.  [default: 2]
  --help                       Show this message and exit.
```


## Consider not using it just yet
- If `par2cmdline` throws error, it's not handled properly by this tool. That shouldn't eat your data though.
- No way to actually list files of certain state (damaged, unrepairable etc.)
- `par2` files are stored along the data. This is something I personally want, but I plan to implement option to store them in a separate location. 
- No way to clean up backups left after `repair`
- No way to clean up orphaned `par2` files.
- Tests cover only happy paths.
- Note that `par2cmdline` is already multithreaded, running this tool with large `-p` value on large files might needlessly overload your machine.

## Examples
Let's have a directory `../test/` with 4 files.  
`python par2tortilla.py run ../test/`
```text
Data files with parity: 0
Data files without parity: 4
PAR2 files: 0
PAR2 files without data files: 0
Data file backups (?) created by par2repair: 0
Nothing was asked, nothing to do.
```

Let's create the parity files. `python par2tortilla.py run --create ../test/`
```text
Creating parities...
creating par2 parity for '..\test\008ec90ccddd8f7e53a8205471c8dd803f84f17997ef94e0eed9f9e5d7c48887'...
creating par2 parity for '..\test\00c4e284c723cae7c057e47f63e313848a59d313be69f47bfee830acf9db1c1c'...
creating par2 parity for '..\test\006f19fd1a0dc96b58bf701d01b0707fb37e4bbb1a651cb998482f803210170f'...
creating par2 parity for '..\test\006809060d2af1515c52b6f90b76f60434c843dd64d065f21f72699f4469f699'...
```

And then verify. `python par2tortilla.py run --verify ../test/`
```text
Verifying files...
verifying file '..\test\00c4e284c723cae7c057e47f63e313848a59d313be69f47bfee830acf9db1c1c'...
verifying file '..\test\006f19fd1a0dc96b58bf701d01b0707fb37e4bbb1a651cb998482f803210170f'...
verifying file '..\test\006809060d2af1515c52b6f90b76f60434c843dd64d065f21f72699f4469f699'...
verifying file '..\test\008ec90ccddd8f7e53a8205471c8dd803f84f17997ef94e0eed9f9e5d7c48887'...
Files that are OK: 4
Files that are damaged but repairable: 0
Files that are damaged and unrepairable: 0
```

Let's delete a file. `python par2tortilla.py run --verify ../test/`
```text
Verifying files...
verifying file '..\test\008ec90ccddd8f7e53a8205471c8dd803f84f17997ef94e0eed9f9e5d7c48887'...
verifying file '..\test\00c4e284c723cae7c057e47f63e313848a59d313be69f47bfee830acf9db1c1c'...
verifying file '..\test\006f19fd1a0dc96b58bf701d01b0707fb37e4bbb1a651cb998482f803210170f'...
Files that are OK: 3
Files that are damaged but repairable: 0
Files that are damaged and unrepairable: 0
```

Suspicious... `python par2tortilla.py run ../test/`
```text
Data files with parity: 3
Data files without parity: 0
PAR2 files: 8
PAR2 files without data files: 2 <------------------ here
Data file backups (?) created by par2repair: 0
Nothing was asked, nothing to do.
```

Well, at least you know about it.

Let's damage a file. `python .\par2tortilla.py run --verify ..\test\`
```text
Verifying files...
verifying file '..\test\006f19fd1a0dc96b58bf701d01b0707fb37e4bbb1a651cb998482f803210170f'...
verifying file '..\test\008ec90ccddd8f7e53a8205471c8dd803f84f17997ef94e0eed9f9e5d7c48887'...
verifying file '..\test\00c4e284c723cae7c057e47f63e313848a59d313be69f47bfee830acf9db1c1c'...
Files that are OK: 2
Files that are damaged but repairable: 1
Files that are damaged and unrepairable: 0
```

Let's repair it. `python .\par2tortilla.py run --verify --repair ..\test\`
```text
Verifying files...
verifying file '..\test\008ec90ccddd8f7e53a8205471c8dd803f84f17997ef94e0eed9f9e5d7c48887'...
verifying file '..\test\00c4e284c723cae7c057e47f63e313848a59d313be69f47bfee830acf9db1c1c'...
verifying file '..\test\006f19fd1a0dc96b58bf701d01b0707fb37e4bbb1a651cb998482f803210170f'...
Files that are OK: 2
Files that are damaged but repairable: 1
Files that are damaged and unrepairable: 0
Repairing files...
repairing file '..\test\006f19fd1a0dc96b58bf701d01b0707fb37e4bbb1a651cb998482f803210170f'...
Repaired 1/1 files.
```

The end. `python par2tortilla.py run ../test/`
```text
Data files with parity: 3
Data files without parity: 0
PAR2 files: 8
PAR2 files without data files: 2
Data file backups (?) created by par2repair: 1
Nothing was asked, nothing to do.
```