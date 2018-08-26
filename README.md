# PDPy11

PDPy11 is a compiler for PDP-11, written in Python.

License: MIT

## Requirements

- Python 2.7 or later, or Python 3.5 (may work on earlier versions)
- No Python modules required
- Any platform (Windows, Mac OS, Linux)

## Docs

You can check the full docs as [docs.md](docs.md).

## TL;DR aka tutorial

### Compiling to .bin

1. Create `test.mac` file with the following content:

```
MOV #2, R1
```

2. Run `python -m pdpy11 path-to/test.mac`

This will generate `test.bin` file with the following content:

```
001000 ; the file is loaded from address 1000 -- the default address
000004 ; 4 bytes, or 2 words -- the size of the resulting code
012701 ; MOV (PC)+, R1
000002 ; .WORD 2
```

The header (4 bytes) is called ".bin header", sometimes "binary header".

To remove ".bin header", run `python -m pdpy11 path-to/test.mac --raw`.

### Syntax

Standard PDP-11 assembler syntax is used, i.e.:

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