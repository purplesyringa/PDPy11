import os
import sys
from .compiler import Compiler
from .compiler.util import encodeBinRaw

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
	print("""py11 --project dir              Compile & link file dir/main.mac (see Project   """)
	print("""                                mode)                                           """)
	print()
	print("""--link n                        Link file/project from 0oN (default -- 0o1000)  """)
	print()
	print("""--syntax pdp11asm               (default) Use pdp11asm bugs/features: @M is same""")
	print("""                                as @M(PC) (M is not resolved to M-.), make_raw  """)
	print("""                                directive, .INCLUDE is same as .INCLUDE .END    """)
	print("""--syntax py11                   Use PY11 features, fix pdp11asm bugs            """)
	print()
	print("Directives:")
	print("""ORG n / .LINK n / .LA n         Link file from N (replaces --link). Ignored in  """)
	print("""                                project mode.                                   """)
	print(""".INCLUDE "filename" /           Compile file "filename", then return to current """)
	print(""".RAW_INCLUDE filename           file. Embed "filename" to current binary file,  """)
	print("""                                and link it from ".".                           """)
	print("""                                In "pdp11asm" mode, .INCLUDE is same as .INCLUDE""")
	print("""                                .END, and .RAW_INCLUDE is same as .INCLUDE.     """)
	print("""                                In "py11" mode, they work the same way, only    """)
	print("""                                syntax differs.                                 """)
	print(""".PDP11                          Ignored                                         """)
	print(""".i8080                          Emits syntax error                              """)
	print(""".SYNTAX {pdp11asm/py11}         Change syntax locally, for 1 file               """)
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
	print("""                                filename is ignored. Ignored in project mode.   """)
	print("""make_bk0010_rom ["..."]         Same as --bin. If string is passed, this is the """)
	print("""                                resulting filename. However, if -o is passed,   """)
	print("""                                filename is ignored. Ignored in project mode.   """)
	print("""convert1251toKOI8R {ON|OFF}     Ignored                                         """)
	print("""decimalnumbers {ON|OFF}         If ON, N is the same as N., and you must use    """)
	print("""                                0oN or 0N or No for octal. This does not affect """)
	print("""                                --link and other CLI arguments.                 """)
	print("""insert_file "filename"          Insert raw file "filename" to .                 """)
	print()
	print("Project mode")
	print("""In project mode, most directives, such as ORG, .LINK, .LA, make_raw and         """)
	print("""make_bk0010_rom are ignored, and only arguments from command line are used.     """)
	print(""".py11ignore file is checked, and all files (and directories -- this file has    """)
	print("""syntax that's similar to .gitignore) are not compiled or linked.                """)
	print("""The file to be compiled is main.mac -- it can include other files via .INCLUDE  """)
	print("""or .RAW_INCLUDE. Moreover, these directives support passing directories now --  """)
	print("""this includes all .mac files inside, not specified in .py11ignore.              """)

	raise SystemExit(0)


# Parse CLI arguments
isBin = None
files = []
output = None
syntax = "pdp11asm"
link = "1000"
project = None

args = sys.argv[1:]
while len(args):
	arg = args.pop(0)

	if arg == "--bin":
		isBin = True
	elif arg == "--raw":
		isBin = False
	elif arg == "--project":
		if project is not None:
			print("Only 1 project may be linked")
			raise SystemExit(1)

		project = args.pop(0)
	elif arg == "-o":
		output = args.pop(0)
	elif arg == "--link":
		link = args.pop(0)
	elif arg == "--syntax":
		syntax = args.pop(0)
	else:
		files.append(arg)

if len(files) == 0 and project is None:
	print("No files passed")
	raise SystemExit(1)
elif len(files) != 0 and project is not None:
	print("Either a project or file list may be passed, not both")
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

if project is not None:
	if isBin is None:
		isBin = True

output_noext = output
if output is None:
	if project is not None:
		output = project
		output_noext = output

		# Add extension
		if isBin:
			output += ".bin"
		else:
			output += ".raw"
	else:
		output = files[0][0]
		if output.endswith(".mac"):
			output = output[:-4]
		output_noext = output

file_list = []

if project is not None:
	files.append(os.path.join(project, "main.mac"))

	# Get py11ignore
	py11ignore = []
	try:
		with open(os.path.join(project, ".py11ignore")) as f:
			for line in f.read().split("\n"):
				# Replace directory separators
				line = line.replace("/", os.sep)
				line = line.replace("\\", os.sep)

				isRoot = line.startswith(os.sep)
				isDir = line.endswith(os.sep)

				# Split
				line = line.split(os.sep)

				# Remove empty parts
				line = [part for part in line if part != ""]

				# Join back
				line = os.sep.join(line)

				# Save
				py11ignore.append((line, isRoot, isDir))
	except FileNotFoundError:
		pass

	# Get file list
	for dirName, _, fileNames in os.walk(project):
		for fileName in fileNames:
			file = os.path.join(dirName, fileName)

			for line, isRoot, isDir in py11ignore:
				if file == line:
					# Full match
					if not isDir:
						break
				elif file.startswith(line + os.sep):
					# Prefix match
					break
				elif file.endswith(os.sep + line):
					# Suffix match
					if not isRoot:
						break
				elif os.sep + line + os.sep in file:
					# Substring match
					if not isRoot:
						break
			else:
				# No match -- not in py11ignore
				if file.endswith(".mac"):
					file_list.append(file)


compiler = Compiler(syntax=syntax, link=link, file_list=file_list, project=project)
for file in files:
	compiler.addFile(file)

out_files = compiler.link()

if project is None:
	# Single file mode
	for ext, file in out_files:
		if file is None:
			file = output_noext + "." + ext

		with open(file, "wb") as f:
			f.write(encodeBinRaw(ext == "bin", compiler))

if len(out_files) == 0 or project is not None:
	# Project mode / no out file
	output_stream = open(output, "wb")
	output_stream.write(encodeBinRaw(isBin, compiler))