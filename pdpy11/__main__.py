from __future__ import print_function
import os
import sys
from .compiler import Compiler
from .compiler.util import encodeBinRawSavWav, setErrorMode, open_device

if len(sys.argv) < 2:
	print("PDPy11 Compiler")
	print("(c) 2018 Ivanq")
	print()
	print("Usage:")
	print("""pdpy11 file.mac                 Compile file.mac to file.bin                    """)
	print("""pdpy11 file.mac --bin           Compile file.mac to file.bin, replaces          """)
	print("""                                make_raw / make_bk0010_rom / make_bin /         """)
	print("""                                make_sav / make_turbo_wav / make_wav            """)
	print("""pdpy11 file.mac --sav           Compile file.mac to file.sav, replaces          """)
	print("""                                make_raw / make_bk0010_rom / make_bin /         """)
	print("""                                make_sav / make_turbo_wav / make_wav            """)
	print("""pdpy11 file.mac --turbo-wav     Compile file.mac to file.wav, replaces          """)
	print("""                                make_raw / make_bk0010_rom / make_bin /         """)
	print("""                                make_sav / make_turbo_wav / make_wav            """)
	print("""pdpy11 file.mac --wav           Compile file.mac to file.wav, replaces          """)
	print("""                                make_raw / make_bk0010_rom / make_bin /         """)
	print("""                                make_sav / make_turbo_wav / make_wav            """)
	print("""pdpy11 file.mac --raw           Compile file.mac to file, without bin header    """)
	print("""pdpy11 a b c                    Compile & link files a, b and c to a.bin        """)
	print("""pdpy11 a b c -o proj --raw      Compile & link files a, b and c to proj (w/o bin""")
	print("""                                header)                                         """)
	print("""pdpy11 a b c -o proj            Compile & link files a, b and c to proj.bin (w/ """)
	print("""                                bin header)                                     """)
	print("""pdpy11 --project dir            Compile & link file dir/main.mac (see Project   """)
	print("""                                mode)                                           """)
	print()
	print("""pdpy11 file.mac --lst           Generate listing file "file.lst"                """)
	print()
	print("""--link n                        Link file/project from 0oN (default -- 0o1000)  """)
	print()
	print("""--syntax pdp11asm               Use pdp11asm bugs/features: @M is same as @M(PC)""")
	print("""                                (M is not resolved to M-.), .INCLUDE is same as """)
	print("""                                .INCLUDE .END                                   """)
	print("""--syntax pdpy11                 (default) Use PDPy11 features, fix pdp11asm     """)
	print("""                                bugs. This is the recommended mode for all new  """)
	print("""                                projects.                                       """)
	print("""-Dname=value                    Set global label <name> to integer <value>      """)
	print("""                                (parsed using assembler rules)                  """)
	print("""-Dname="value" or               Set global label <name> to string <value>       """)
	print("""-Dname='value' or                                                               """)
	print("""-Dname=/value/                                                                  """)
	print()
	print("""--sublime                       Output errors in Sublime-compatible format. This""")
	print("""                                allows Sublime to show errors inline.           """)
	print()
	print("Directives:")
	print("""ORG n / .LINK n / .LA n         Link file from N (replaces --link). However, if """)
	print("""                                an included file contains .LINK, the included   """)
	print("""                                file will be linked from N, but written to ".". """)
	print(""".INCLUDE "filename" /           Compile file "filename", then return to current """)
	print(""".RAW_INCLUDE filename           file. Embed "filename" to current binary file,  """)
	print("""                                and link it from ".".                           """)
	print("""                                In "pdp11asm" mode, .INCLUDE is same as .INCLUDE""")
	print("""                                .END, and .RAW_INCLUDE is same as .INCLUDE.     """)
	print("""                                In "pdpy11" mode, they work the same way, only  """)
	print("""                                syntax differs.                                 """)
	print("""                                Technically, this is the same as directly       """)
	print("""                                inserting the included file's source code to    """)
	print("""                                current file, with only .EXTERNal labels being  """)
	print("""                                visible to other files. This also means that    """)
	print("""                                including a file that has ".EXTERN" twice is    """)
	print("""                                not a good idea -- an error will be raised, as  """)
	print("""                                labels are redefined. Use ".ONCE" to fix this.  """)
	print(""".PDP11                          Ignored                                         """)
	print(""".i8080                          Emits syntax error                              """)
	print(""".SYNTAX {pdp11asm/pdpy11}       Change syntax locally, for 1 file               """)
	print(""".DB n / .BYTE n / DB n          Emits byte N                                    """)
	print(""".DW n / .WORD n / DW n          Emits word N                                    """)
	print(""".END / END                      Same as EOF; inside .REPEAT block works like    """)
	print("""                                'continue' operator                             """)
	print(""".DS n / .BLKB n / DS n          Emits N zero bytes                              """)
	print(""".BLKW n                         Emits N zero words (N * 2 bytes)                """)
	print(""".EVEN                           If . points to an odd address, emit 1 zero byte """)
	print("""ALIGN n                         Align . by n, ceiling if n is not a divisor of  """)
	print("""                                ".".                                            """)
	print(""".ASCII "..."                    Emits string                                    """)
	print(""".ASCII "..." <12> "..."         Emits a string, then a newline, then a string   """)
	print(""".ASCIZ "..."                    Emits string, plus zero byte                    """)
	print("""make_raw ["..."]                Same as --raw. If string is passed, this is the """)
	print("""                                resulting filename.                             """)
	print("""make_bk0010_rom ["..."] /       Same as --bin. If string is passed, this is the """)
	print("""make_bin ["..."]                resulting filename.                             """)
	print("""make_sav ["..."[, ...]]         Same as --sav. If string is passed, this is the """)
	print("""                                resulting filename. If an additional argument   """)
	print("""                                is passed, it is the final address used by the  """)
	print("""                                program.                                        """)
	print("""make_turbo_wav ["..."[, "..."]] Same as --turbo-wav. If a string is passed, this""")
	print("""                                is the resulting filename. If two strings are   """)
	print("""                                passed, the first one is the real filename and  """)
	print("""                                the second one is BK filename.                  """)
	print("""make_wav ["..."[, "..."]]       Same as --wav. If a string is passed, this is   """)
	print("""                                the resulting filename. If two strings are      """)
	print("""                                passed, the first one is the real filename and  """)
	print("""                                the second one is BK filename.                  """)
	print("""convert1251toKOI8R {ON|OFF}     Ignored                                         """)
	print("""decimalnumbers {ON|OFF}         If ON, N is the same as N., and you must use    """)
	print("""                                0oN or 0N or No for octal. This does not affect """)
	print("""                                --link and other CLI arguments.                 """)
	print("""insert_file "filename"          Insert raw file "filename" to .                 """)
	print(""".REPEAT count { code }          Repeat code inside .REPEAT block <count> times  """)
	print(""".EXTERN NONE /                  Sets which labels are visible in other files.   """)
	print(""".EXTERN ALL /                   "NONE" means all global labels are visible in   """)
	print(""".EXTERN label1[, label2[, ...]] current file, but not others. "ALL" is the same """)
	print("""                                as mentioning all the labels defined in current """)
	print("""                                file. See also: Project mode.                   """)
	print(""".ONCE                           Makes current file includable only once -- if it""")
	print("""                                was included before, it works like ".END".      """)
	print()
	print("Project mode")
	print("""PDPy11 can compile projects. Use `--project directory` CLI argument for this.   """)
	print("""PDPy11 will compile all files (except the ones mentioned in `.pdpy11ignore` --  """)
	print("""see below) containing `make_raw`, `make_bk0010_rom`, `make_bin`, `make_sav`,    """)
	print("""`make_turbo_wav` or `make_wav` directive. Such files are called "include roots".""")
	print()
	print("""In project mode, `.INCLUDE` and `.RAW_INCLUDE` can include directories, which   """)
	print("""means to include all `.mac` files inside the directory (except files mentioned  """)
	print("""in `.pdpy11ignore`).                                                            """)
	print()
	print(".pdpy11ignore")
	print("""This file has syntax similar to `.gitignore`. It sets what files to ignore when """)
	print("""including directories.                                                          """)
	print("""Example:                                                                        """)
	print("""filename.mac    ; Ignore all files called filename.mac                          """)
	print("""a/*             ; Ignore files in "a" directory and "whatever/a" directory      """)
	print("""/a              ; Ignore files in "a" directory only                            """)
	print("""test.mac/       ; Ignore everything inside "test.mac" directory and             """)
	print("""                ; whatever/test.mac" directory, but not "test.mac" file or      """)
	print("""                ; "whatever/test.mac" file                                      """)

	raise SystemExit(0)


# Parse CLI arguments
output_format = None
files = []
output = None
syntax = "pdpy11"
link = "1000"
project = None
defines = []
do_lst = False

args = sys.argv[1:]
while len(args):
	arg = args.pop(0)

	if arg == "--bin":
		output_format = "bin"
	elif arg == "--sav":
		output_format = "sav"
	elif arg == "--raw":
		output_format = "raw"
	elif arg == "--turbo-wav":
		output_format = "turbo-wav"
	elif arg == "--wav":
		output_format = "wav"
	elif arg == "--lst":
		do_lst = True
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
	elif arg.startswith("--syntax="):
		syntax = arg.replace("--syntax=", "")
	elif arg == "--sublime":
		setErrorMode(sublime=True)
	elif arg[:2] == "-D":
		name, value = arg[2:].split("=", 1)
		str_punct = ("\"", "'", "/")
		if value == "":
			pass
		elif value[0] == value[-1] and value[0] in str_punct:
			# String
			defines.append((name, value[1:-1]))
		else:
			# Integer
			if value[:2] in ("0x", "0X"):
				value = int(value[2:], 16)
			elif value[-1] == ".":
				value = int(value[:-1], 10)
			else:
				value = int(value, 8)
			defines.append((name, value))
	else:
		files.append(arg)

if len(files) == 0 and project is None:
	print("No files passed")
	raise SystemExit(1)
elif len(files) != 0 and project is not None:
	print("Either a project or file list may be passed, not both")
	raise SystemExit(1)
elif syntax not in ("pdp11asm", "pdpy11"):
	print("Invalid syntax (expected 'pdp11asm' or 'pdpy11', got '{}')".format(syntax))
	raise SystemExit(1)

if link[:2] in ("0x", "0X"):
	link = int(link[2:], 16)
elif link[-1] == ".":
	link = int(link[:-1], 10)
else:
	link = int(link, 8)

output_noext = output
if output is None:
	if project is not None:
		output = project
		output_noext = output

		# Add extension
		if output_format is None or output_format == "bin":
			output += ".bin"
		elif output_format == "sav":
			output += ".sav"
		elif output_format == "turbo-wav" or output_format == "wav":
			output += ".wav"
		else:
			output += ".raw"
	else:
		output = files[0]
		if output.endswith(".mac"):
			output = output[:-4]
		output_noext = output

		# Add extension
		if output_format is None or output_format == "bin":
			output += ".bin"
		elif output_format == "sav":
			output += ".sav"
		elif output_format == "turbo-wav" or output_format == "wav":
			output += ".wav"

file_list = []

if project is not None:
	# Get pdpy11ignore
	pdpy11ignore = []
	try:
		with open(os.path.join(project, ".pdpy11ignore")) as f:
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
				pdpy11ignore.append((line, isRoot, isDir))
	except IOError:
		pass

	# Get file list
	for dirName, _, fileNames in os.walk(project):
		for fileName in fileNames:
			file = os.path.join(dirName, fileName)

			for line, isRoot, isDir in pdpy11ignore:
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
				# No match -- not in pdpy11ignore
				if file.endswith(".mac"):
					file = os.path.join(os.getcwd(), file)
					file_list.append(file)


compiler = Compiler(syntax=syntax, link=link, file_list=file_list, project=project)
for name, value in defines:
	compiler.define(name, value)

if project is not None:
	# Project mode
	lstname = project
	for ext, file, args, output, link_address in compiler.buildProject():
		with open_device(file, "wb") as f:
			f.write(encodeBinRawSavWav(ext, args, output, link_address))
else:
	# Single file mode
	lstname = files[0]
	if lstname.endswith(".mac"):
		lstname = lstname[:-4]
	for file in files:
		compiler.include_root = os.path.abspath(file)
		compiler.addFile(file)

	out_files = compiler.link()

	for ext, file, args in out_files:
		with open_device(file, "wb") as f:
			f.write(encodeBinRawSavWav(ext, args, compiler.output, compiler.link_address))

	if len(out_files) == 0:
		# No output file
		with open_device(output, "wb") as f:
			f.write(encodeBinRawSavWav(output_format or "bin", (), compiler.output, compiler.link_address))

if do_lst:
	with open(lstname + ".lst", "w") as f:
		for line in compiler.generateLst():
			f.write(line + "\n")