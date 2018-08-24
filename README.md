# PDPy11

PDPy11 is a compiler for PDP-11, written in Python.

License: MIT

## Requirements

- Python 2.7 or later, or Python 3.5 (may work on earlier versions)
- No Python modules required
- Any platform (Windows, Mac OS, Linux)

## Docs

### Syntax

Standard PDP-11 syntax is supported. For example:

```
MOV #1, R0
MOV R0, @#1000
MOV 1000, @#2000
```

Strings can be surrounded by `"`, `'` or `/`.

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
- local (e.g. `1` or `0`). Currently, labels like `1$` are not supported

In addition to these 2 label types, meta-label `.` is supported, pointing to the beginning of current command, e.g.:

```
MOV #100, R0
SOB R0, . ; SOB 100 times and then continue
BR .-2 ; branch to SOB
```

### Command line usage

To compile a single file, use `pdpy11 filename.mac` syntax. The result will be outputted to `filename.bin`, with `.bin` header.

To compile a single file in raw mode (without `.bin` header), use `pdpy11 filename.mac --raw` syntax. The result will be outputted to `filename`.

To set output filename, use: `pdpy11 filename.mac -o output`. It will be outputted to `output`, no matter whether `--raw` or `--bin` are passed.

To set output format, both CLI arguments and meta-commands can be used.

If at least one meta-command is used inside file (`make_bk0010_rom` = `--bin` or `make_raw` = `--raw`) is used, the result won't be outputted to `filename` or `filename.bin`. To force it as well as `make_bk0010_rom` and `make_raw`, add `--bin` or `--raw` CLI argument.

To set link address if it's not mentioned in `.mac` file, use `--link N` argument. It has less priority than `.LINK` or `.LA` or `ORG`.

To set global syntax (see `.SYNTAX` meta-command), use `--syntax {pdp11asm/pdpy11}`.

To set label/constant, use `-Da=N` syntax (same as `a = N`) or `-Da=/N/` (same as `a = /N/`).

For `--project` argument, see *Project mode*.


### Meta-commands

#### `ORG addr` / `.LINK addr` / `.LA addr`

Default: `1000`.

Set PC to `addr`, and output to `.bin` (or `.raw`) data since `addr`.

Example:

```
.LINK 1000
MOV #1, @#A
A:  .WORD 0
```

If the program is loaded and executed from `1000`, `A` will be equal to `1006`, and if it's loaded from `2000`, `A` will still be equal to `1006`, because the `.LINK` address was not changed to `2000`.

If a file containing `.LINK` (or `ORG` / `.LA`) is included, `.` is not changed, but the file is linked like a separate file from `addr`.

Example:

**main.mac**

```
.LINK 1000
.WORD 1
.WORD 2
.WORD 3
.INCLUDE "inc.mac"
```

**inc.mac**

```
.LINK 2000
A: .WORD A
```

**Output:** (`.bin` from 1000)

```
000001 000002 000003 002000
```

#### `.INCLUDE /filename/` / `.RAW_INCLUDE filename`

In `pdpy11` mode, the commands work the same way. In `pdp11asm` compatibility mode, `.INCLUDE` works like `.INCLUDE + .END`, and `.RAW_INCLUDE` works correctly.

Example:

**main.mac**

```
.SYNTAX pdpy11 ; disable compatibility mode
.INCLUDE "test.mac"
.RAW_INCLUDE test.mac
```

**test.mac**

```
.WORD 1
```

**Output:**

```
000001 000001
```

See also: `.EXTERN`

#### `.PDP11`

For compatibility with `pdp11asm`. Ignored.

#### `.i8080`

For compatibility with `pdp11asm`. Raises syntax error, as PDPy11 doesn't support Intel 8080.

#### `.SYNTAX pdp11asm` / `.SYNTAX pdpy11`

Default: `pdp11asm`

Enables (`pdp11asm`) or disables (`pdpy11`) pdp11asm compatibility mode, including `.INCLUDE` and other commands.

#### `.DB n` / `.BYTE n` / `DB n`

Write byte `n` to output.

#### `.DW n` / `.WORD n` / `DW n`

Write word (2 bytes) `n` to output.

#### `.END` / `END`

Stop compiling file. Works like EOF. Inside `.REPEAT`, works like `continue` in Python / C / JavaScript / whatever-language-you-know.

#### `.DS n` / `.BLKB n` / `DS n`

Output `n` zero bytes.

#### `.BLKW n`

Output `n` zero words (= `n * 2` bytes)

#### `.EVEN`

If current `PC` is odd (e.g. after `.ASCII`), increment it.

#### `ALIGN n`

If current `PC` is not divisible by `n`, ceil it up.

#### `.ASCII /string/`

Output `string`.

#### `.ASCIZ /string/`

Output `string`, and then zero byte.

#### `make_raw [/filename/]`

Output resulting file (since link address) to `filename`, or to compilable-file-without-mac-extension if filename is not passed.

#### `make_bk0010_rom [/filename/]`

Output resulting file (since link address) with binary header to `filename`, or to compilable-file-without-mac-extension + `.bin` if filename is not passed.

#### `convert1251toKOI8R boolean`

For compatibility with pdp11asm. Ignored.

#### `decimalnumbers boolean`

Default: `OFF`.

If `OFF`, number without radix is octal. If `ON`, number without radix is decimal.

Example:

```
decimalnumbers OFF
.WORD 10 ; 8.
decimalnumbers ON
.WORD 10 ; 10.
```

#### `insert_file /filename/`

Include `filename` directly to output.

#### `.REPEAT count { commands }`

Repeat `commands` exactly `count` times.

#### `.EXTERN NONE` / `.EXTERN ALL` / `.EXTERN label[, ...]`

Default: `NONE`;

Sets what labels are visible in other files.

`NONE` means that any labels inside current file are visible in current file only, and they can be registered in other files.

Example:

**a.mac**

```
.EXTERN NONE
VAR = 1
.WORD VAR
.INCLUDE "b.mac"
.WORD VAR
```

**b.mac**

```
.EXTERN NONE
VAR = 2
.WORD VAR
```

**Output:**

```
000001 000002 000001
```

`ALL` is the same as mentioning all the labels defined in current file.

Example:

**a.mac**

```
.EXTERN LABEL_A
LABEL_A = 1
LABEL_B = 2
.WORD LABEL_A, LABEL_B
.INCLUDE "b.mac"
.WORD LABEL_A, LABEL_B
```

**b.mac**

```
LABEL_B = 3
.WORD LABEL_A, LABEL_B
```

**Output:**

```
000001 000002 000001 000003 000001 000002
```


### Project mode

PDPy11 can compile projects. Use `--project directory` CLI argument for this. PDPy11 will compile `directory/main.mac` file. However, there are some differences from using `pdpy11 directory/main.mac`:

- `ORG` / `.LINK` / `.LA` directives are ignored.
- `.INCLUDE` and `.RAW_INCLUDE` can include directories, which means to include all `.mac` files inside the directory (except files mentioned in `.pdpy11ignore`).

#### `.pdpy11ignore`

This file has syntax similar to `.gitignore`. It sets what files to ignore when including directories.

Example:

```
filename.mac ; Ignore all files called filename.mac
a/* ; Ignore files in "a" directory and "whatever/a" directory
/a ; Ignore files in "a" directory only
test.mac/ ; Ignore everything inside "test.mac" directory and "whatever/test.mac" directory, but not "test.mac" file or "whatever/test.mac" file
```


## Features

Any kind of label/constant relations are supported. For example:

```
A = B + 100
B = 200 + C
C = L2 - L1

L1: .BLKW 100
L2:
```

Some compilers won't compile this file (like my old fork of `pdp11asm`), but PDPy11 will evaluate it.