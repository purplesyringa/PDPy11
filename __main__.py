import sys
#from .compiler import Compiler

if len(sys.argv) < 2:
	print("PY11 Compiler")
	print("(c) 2018 Ivanq")
	print()
	print("Usage:")
	print("""py11 file.mac                   Compile file.mac to file.bin                    """)
	print("""py11 file.mac --bin             Compile file.mac to file.bin, replaces          """)
	print("""                                make_raw / make_bk0010_rom                      """)
	print("""py11 file.mac --raw             Compile file.mac to file, without bin header    """)
	print("""py11 a b c                      Compile & link files a, b and c to a.bin        """)
	print("""py11 a b c -o proj --raw        Compile & link files a, b and c to proj (w/o bin""")
	print("""                                header)                                         """)
	print("""py11 a b c -o proj              Compile & link files a, b and c to proj.bin (w/ """)
	print("""                                bin header)                                     """)
	print("""py11 --project dir              Compile & link all files inside dir/, not       """)
	print("""                                mentioned in .py11ignore, to dir.bin            """)
	print()
	print("""--link n                        Link file/project from 0oN (default -- 0o1000)  """)
	print()
	print("""--syntax pdp11asm               (default) Use pdp11asm bugs/features: @M is same""")
	print("""                                as @M(PC) (M is not resolved to M-.), make_raw  """)
	print("""                                directive, .INCLUDE is same as .INCLUDE .END    """)
	print("""--syntax py11                   Use PY11 features, fix pdp11asm bugs            """)
	print()
	print("Directives:")
	print("""ORG n / .LINK n / .LA n         Link file from N (replaces --link)              """)
	print(""".INCLUDE "filename" /           Compile file "filename", then return to current """)
	print(""".RAW_INCLUDE filename           file. Embed "filename" to current binary file,  """)
	print("""                                and link it from ".".                           """)
	print("""                                In "pdp11asm" mode, .INCLUDE is same as .INCLUDE""")
	print("""                                .END, and .RAW_INCLUDE is same as .INCLUDE.     """)
	print("""                                In "py11" mode, they work the same way, only    """)
	print("""                                syntax differs.                                 """)
	print(""".PDP11                          Ignored                                         """)
	print(""".i8080                          Emits syntax error                              """)
	print(""".DB n / .BYTE n / DB n          Emits byte N                                    """)
	print(""".DW n / .WORD n / DW n          Emits word N                                    """)
	print(""".END / END                      Same as EOF                                     """)
	print(""".DS n / .BLKB n / DS n          Emits N zero bytes                              """)
	print(""".BLKW n                         Emits N zero words (N * 2 bytes)                """)
	print(""".EVEN                           If . points to an odd address, emit 1 zero byte """)
	print("""ALIGN n                         Align . by n, ceiling if n is not a divisor of  """)
	print("""                                ".".                                            """)
	print(""".ASCII "..."                    Emits string                                    """)
	print(""".ASCIZ "..."                    Emits string, plus zero byte                    """)
	print("""make_raw ["..."]                Same as --raw. If string is passed, this is the """)
	print("""                                resulting filename. However, if -o is passed,   """)
	print("""                                filename is ignored.                            """)
	print("""make_bk0010_rom ["..."]         Same as --bin. If string is passed, this is the """)
	print("""                                resulting filename. However, if -o is passed,   """)
	print("""                                filename is ignored.                            """)
	print("""convert1251toKOI8R {ON|OFF}     Ignored                                         """)
	print("""decimalnumbers {ON|OFF}         If ON, N is the same as N., and you must use    """)
	print("""                                0oN or 0N or No for octal. This does not affect """)
	print("""                                --link and other CLI arguments.                 """)
	print("""insert_file "filename" [, start Insert raw file "filename" to ., omitting       """)
	print("""[, size] ]                      start bytes from the beginning of "filename"    """)
	print("""                                and, if size is passed, trimming to at most     """)
	print("""                                size bytes.                                     """)

	raise SystemExit(0)


# Parse CLI arguments
isBin = None
files = []
output = None
syntax = "pdp11asm"
link = "1000"

args = sys.argv[1:]
while len(args):
	arg = args.pop(0)

	if arg == "--bin":
		isBin = True
	elif arg == "--raw":
		isBin = False
	elif arg == "--project":
		files.append((args.pop(0), True))
	elif arg == "-o":
		output = args.pop(0)
	elif arg == "--link":
		link = args.pop(0)
	elif arg == "--syntax":
		syntax = args.pop(0)
	else:
		files.append((arg, False))

if len(files) == 0:
	print("No files passed")
	raise SystemExit(1)
elif syntax not in ("pdp11asm", "py11"):
	print("Invalid syntax (expected 'pdp11asm' or 'py11', got '{}')".format(syntax))
	raise SystemExit(1)

if link[:2] in ("0x", "0X"):
	link = int(link[2:], 16)
elif link[:2] in ("0d", "0D"):
	link = int(link[2:], 10)
elif link[-1] in ("h", "H"):
	link = int(link[:-1], 16)
elif link[-1] in ("d", "D", "."):
	link = int(link[:-1], 10)
else:
	link = int(link, 8)

if output is None:
	output = files[0][0]
	if output.endswith(".mac"):
		output = output[:-4]

print(files, output, syntax, link)