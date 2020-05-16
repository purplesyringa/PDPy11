# PDPy11

PDPy11 is a compiler for PDP-11, written in Python.

License: MIT

## Requirements

- Python 2.7 or later, or Python 3.5 (may work on earlier versions)
- No Python modules required
- Any platform (Windows, Mac OS, Linux)

## Installation

### Via git

```
$ git clone https://github.com/imachug/pdpy11
```

### Via GitHub UI

Press green `Clone or download` button (it's above file list), press `Download ZIP` and extract the archive.

## Docs

You can check the full docs as [docs.md](docs.md).

Read how to use Sublime Text build system and syntax highlighting [here](sublime/README.md).

## TL;DR aka tutorial

### Compiling single file to .bin

1. Create `test.mac` file with the following content:

```
MOV #2, R1
```

2. `cd` to the directory that contains `pdpy11` (e.g. if you used `git clone`, don't run `cd pdpy11` afterwards)

3. Run `python -m pdpy11 path-to/test.mac`

This will generate `test.bin` file with the following content:

```
001000 ; the file is loaded from address 1000 -- the default address
000004 ; 4 bytes, or 2 words -- the size of the resulting code
012701 ; MOV (PC)+, R1
000002 ; .WORD 2
```

The header (4 bytes) is called ".bin header", sometimes "binary header".

To remove ".bin header", run `python -m pdpy11 path-to/test.mac --raw`, or add `make_raw` meta-command to the end of the file.

If you want to use `.sav` format, run `python -m pdpy11 path-to/test.mac --sav` (or use `make_sav` meta-command):

For example:

```
MOV #2, R1
make_raw
```

```
MOV #2, R1
make_sav
```

For debugging, you can enable `.lst` file generation by using `python -m pdpy11 path-to/test.mac --lst`. Here's an example:

```
.LINK 3000
HELLO = 2 + 2
WORLD: MOV #HELLO, R0
```

```
path-to/test.mac
000004 HELLO
003000 WORLD
```

### Syntax

Standard PDP-11 assembler syntax is used, i.e.:

Strings can be surrounded by `"`, `'` or `/`. Literal strings can be joined together: `"A" "B"` is the same as `"AB"`. `<n>` syntax can be used to put a raw character, e.g.: `"A"<12>"B"` inserts a newline between `"A"` and `"B"`.

Registers: `R0..R7`, with `SP = R6` and `PC = R7`.

Supported commands:

- `HALT`, `WAIT`, `RTI`, `BPT`, `IOT`, `RESET`, `RTT`, `START` (code 12), `STEP` (code 16), `NOP` (code 240), `CLC`, `CLV`, `CLZ`, `CLN`, `CCC`, `SEC`, `SEV`, `SEZ`, `SEN`, `SCC`, `RET`
- `JMP`, `CALL` (as alias to `JSR PC`), `SWAB`, `CLR(B)`, `COM(B)`, `INC(B)`, `DEC(B)`, `NEG(B)`, `ADC(B)`, `SBC(B)`, `TST(B)`, `ROR(B)`, `ROL(B)`, `ASR(B)`, `ASL(B)`, `SXT`, `MTPS`, `MFPS`
- `BR`, `BNE`, `BEQ`, `BGE`, `BLT`, `BGT`, `BLE`, `BPL`, `BMI`, `BVC`, `BHIS`, `BCC`, `BLO`, `BCS`, `BLOS`
- `EMT`, `TRAP`, `MARK`
- `MOV(B)`, `CMP(B)`, `BIT(B)`, `BIC(B)`, `BIS(B)`, `ADD`
- `JSR`, `XOR`
- `SOB`, `RTS`

2 label types are supported:

- global (e.g. `ABACABA`, `TEST`)
- local (e.g. `1` or `0`). Labels like `1$` (i.e. digit + anything) are supported as well

In addition to these 2 label types, meta-label `.` is supported, pointing to the beginning of current command, e.g.:

```
MOV #100, R0
SOB R0, . ; SOB 100 times and then continue
BR .-2 ; branch to SOB
```

### Some useful macrocommands

To compile ("link") the program from another address (e.g. 0o3000), not the default 0o1000, use `.LINK 3000` macrocommand.

---

To enable `pdp11asm` compatibility mode (NOT RECOMMENDED!), use `.SYNTAX pdp11asm` macrocommand.

---

To store a byte, use `.BYTE n`. To store a word, use `.WORD n`. To store N zero bytes, use `.BLKB n`. To store N zero words, use `.BLKW n`.

---

To insert a string, use `.ASCII` or `.ASCIZ = .ASCII + .BYTE 0`.

---

To set a variable, use: `A = 7` or `A EQU 7`. Then you can use *A* instead of *7*.

Example:

```
A = 7
.WORD A
MOV #A, R0
```

---

To insert another file, use `insert_file "path-to-file"` if it's a binary file or `.INCLUDE "path-to-file.mac"` if it's an assembler file. Notice: in `pdp11asm` compatibility mode, `.INCLUDE` works like `.INCLUDE + .END` (i.e. no code after `.INCLUDE` is compiled). To fix this, 1. don't use compatibility mode, or 2. use `.RAW_INCLUDE path-to-file.mac` (without quotes!).

Notice: if you define labels (or variables) inside included files, they're not visible in the main program. Add `.EXTERN ALL` line to the beginning of included file to "export" all labels that are defined in the included file to the main program and all other included files, for example:

**main.mac**

```
.INCLUDE "constants.mac"
MOV #1, @#SOME_REGISTER1
.INCLUDE "a.mac"
```

**a.mac**

```
MOV #2, @#SOME_REGISTER2
```

**constants.mac**

```
.EXTERN ALL ; same as .EXTERN SOME_REGISTER1, SOME_REGISTER2
SOME_REGISTER1 = 177714
SOME_REGISTER2 = 177716
```

If you want to include `constants.mac` twice (e.g. you're going to include it in every file that uses the registers, to show that it's a dependency), use:

**constants.mac**

```
.ONCE ; never compile code below twice, which would result in "redefinition of label" error
.EXTERN ALL ; same as .EXTERN SOME_REGISTER1, SOME_REGISTER2
SOME_REGISTER1 = 177714
SOME_REGISTER2 = 177716
```

Check [docs.md](docs.md) for more `.INCLUDE` / `.EXTERN` / `.ONCE` usecases.

---

To repeat some code a few times, use:

```
.REPEAT 10 {
    .WORD 0
}
```

The above is the same as `.BLKW 10`. You can use any commands or macrocommands inside `.REPEAT`.


### Project mode

It's quite possible that you're making a big project -- otherwise, it doesn't make sense to use such a big tool as `pdpy11`. `pdpy11` has a special mode for projects.

1. Create directory `TestProject`.

2. Create `test.mac` file inside `TestProject` with the following content:

```
MOV #2, R1
make_bin
```

3. Run `python -m pdpy11 --project TestProject`.

This will generate `TestProject/test.bin` file with the same content as we got in *Compiling single file to .bin* section.

Notice that we've used `make_bin`, but we didn't add `--bin` or `--raw` CLI argument. In a large project, you may have several outputs -- e.g., if you're making an OS, you may have a *bootloader* (< 512 bytes) and *os* (the kernel itself, the stuff *bootloader* loads). So you have to manually set which files should be compiled to `.bin` or `.raw` -- they are called "include roots".

---

An interesting point is that all external labels are shared between all "include roots". For example:

**bootloader.mac**

```
.EXTERN OS_LINK
OS_LINK = 100000

; load os
MOV #OS_LINK, R0
...
CALL @#160004

; startup
JMP @#OS_STARTUP

make_raw
```

**os.mac**

```
.EXTERN OS_STARTUP

.LINK OS_LINK

.WORD 0 ; some options for the processor macrocode,
.WORD 1 ; or some other constants that must be exactly
.WORD 2 ; at OS_LINK

OS_STARTUP: ; the code to be executed when the kernel is loaded
...

make_bin
```

The above project, when compiled, will result in two files: `bootloader` and `os.bin`, with `OS_LINK` and `OS_STARTUP` labels shared between them and all other `.mac` files.

---

Some other useful things added by project mode:

- `.INCLUDE` now works on directories: it includes all `.mac` files inside the directory.
- You can use `.pdpy11ignore` to set what files aren't included when `.INCLUDE` is called on directory and what files aren't checked for `make_raw` and `make_bin` (i.e. which files can't be "include roots").
- You can run `.INCLUDE` on files that have `.LINK`. This is the same as compiling the included file in raw mode and embedding the raw content to current file, like with `insert_file`.
