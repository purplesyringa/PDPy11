from __future__ import print_function
import os
import sys
import string
import random
from collections import defaultdict
from .parser import Parser, EndOfParsingError
from .deferred import Deferred
from .commands import commands
from . import util
from .util import raiseCompilerError, A, R, D, I, R0, R1, R2, R3, R4, R5, SP, PC
from .expression import Expression

class Compiler(object):
	def __init__(self, syntax="pdpy11", link=0o1000, file_list=[], project=None):
		self.syntax = syntax
		self.link_address = link
		self.file_list = file_list
		self.project = project
		self.global_labels = {}
		self.labels = self.global_labels
		self.PC = link
		self.linkPC = link
		self.all_build = []
		self.build = []
		self.writes = []
		self.extern_labels = False
		self.included_before = set()
		self.last_static_alloc = Expression("MEMORY", "STATIC_ALLOC", 0, 0)

	def define(self, name, value):
		value_text = "\"{str}\"".format(str=value) if isinstance(value, str) else value

		if name.upper() in self.global_labels:
			self.err({
				"file": "CLI",
				"line": 1,
				"column": 1,
				"text": "-D{name}={value}".format(name=name, value=value_text)
			}, "Duplicate label {label}".format(label=name))

		self.global_labels[name.upper()] = value

	def generateLst(self):
		by_files = defaultdict(lambda: [])
		for label in self.labels:
			# Convert string like this: "A: B: C: D: E:F: G: H: I: J"
			# To this: file "A: B: C: D: E", label "F: G: H: I: J"

			parts = label.split(": ")
			label_parts = []
			file_parts = []
			for i in range(len(parts) - 1, -1, -1):
				part = parts[i]
				splitted = part.rsplit(":", 1)
				label_parts.append(splitted[-1])
				if len(splitted) > 1:
					file_parts.append(splitted[0])
					break
			file_name = ": ".join(parts[:i] + file_parts)
			label_name = ": ".join(label_parts[::-1])

			if not file_name:
				# Global label
				continue
			elif ": " in label_name:
				# Local label
				continue
			elif label_name.startswith("."):
				# . simulation
				continue

			# Collect labels per file
			label_value = Deferred(self.labels[label], int)(self)
			by_files[file_name].append((label_value, label_name))

		# Output
		for file_name, labels in by_files.items():
			yield file_name
			for value, name in sorted(labels):
				text_value = util.octal(value)
				# Pad to 6 chars
				text_value = "0" * (6 - len(text_value)) + text_value
				yield "{value} {name}".format(value=text_value, name=name)
			yield ""

	def buildProject(self):
		# Add all files inside project directory that have
		# make_raw or make_bk0010_rom directive
		to_make = set()
		for file in self.file_list:
			# Read file
			with open(file, "r") as f:
				code = f.read()

			# Parse it
			print("Parsing", file)
			parser = Parser(file, code, syntax=self.syntax)

			for (command, arg), labels in parser.parse():
				if command in (
					".MAKE_RAW", ".MAKE_BIN", ".MAKE_SAV", ".MAKE_TURBO_WAV", ".MAKE_WAV"
				):
					to_make.add(file)

		# All these files are separate project roots,
		# just with common extern labels
		for file in to_make:
			# By default, build file from 1000
			self.link_address = 0o1000
			self.PC = self.link_address
			self.linkPC = self.link_address

			# No writes, no build
			self.writes = []
			self.build = []

			# Compile file
			print("Compiling", file, "as include root")
			file = self.resolve(file, os.getcwd())
			self.include_root = file
			self.addFile(file)

			# Save all writes
			for ext, name, args in self.build:
				try:
					link_address = Deferred(self.link_address, int)(self)
					print("    Output: {name} ({ext} format) from {link}".format(name=name, ext=ext, link=util.octal(link_address)))
				except:
					print("    Output: {name} ({ext} format) from {link}".format(name=name, ext=ext, link=repr(self.link_address)))

				self.all_build.append((ext, name, args, self.writes, self.link_address))

		print("Linking")
		return self.link()



	def addFile(self, file, relative_to=None):
		if relative_to is None:
			relative_to = os.getcwd()
		else:
			relative_to = os.path.dirname(relative_to)

		file = self.resolve(file, relative_to)

		if os.path.isdir(file):
			for subfile in self.file_list:
				if subfile.startswith(file + os.sep):
					self.addFile(subfile, relative_to=self.project)
			return

		with open(file, "r") as f:
			code = f.read()

		self.compileFile(file, code)

	def resolve(self, file, base):
		# Resolve file path
		if file.startswith("/") or file[1:3] == ":\\":
			# Absolute
			return file
		else:
			# Relative
			return os.path.abspath(os.path.join(base, file))

	def link(self):
		for label in self.labels:
			Deferred(self.labels[label], int)(self)

		if self.project is not None:
			all_build = []
			for ext, file, args, writes, link_address in self.all_build:
				array = []
				for addr, value in writes:
					value = Deferred(value, any)(self)

					if not isinstance(value, list):
						value = [value]

					addr = Deferred(addr, int)(self)
					for i, value1 in enumerate(value):
						if addr + i >= len(array):
							array += [0] * (addr + i - len(array) + 1)
						array[addr + i] = value1

				link_address = Deferred(link_address, int)(self)
				all_build.append((ext, file, tuple(Deferred(arg)(self) for arg in args), array[link_address:], link_address))

			return all_build
		else:
			array = []
			for addr, value in self.writes:
				value = Deferred(value, any)(self)

				if not isinstance(value, list):
					value = [value]

				addr = Deferred(addr, int)(self)
				for i, value1 in enumerate(value):
					if addr + i >= len(array):
						array += [0] * (addr + i - len(array) + 1)
					array[addr + i] = value1

			self.link_address = Deferred(self.link_address, int)(self)
			self.output = array[self.link_address:]
			return [(ext, name, tuple(Deferred(arg)(self) for arg in args)) for ext, name, args in self.build]

	def compileFile(self, file, code):
		parser = Parser(file, code, syntax=self.syntax)

		extern_labels = self.extern_labels

		self.extern_labels = False # .EXTERN NONE
		try:
			for (command, arg), labels in parser.parse():
				try:
					self.handleCommand(parser, command, arg, labels)
				except EOFError:
					break
		finally:
			self.extern_labels = extern_labels


	def handleCommand(self, parser, command, arg, labels):
		coords = parser.getCurrentCommandCoords()

		for label in labels:
			self.defineLabel(parser.file, label, self.linkPC, coords)

		if command is None:
			return
		elif command == ".LINK":
			if self.include_root == parser.file:
				self.PC = arg
				self.linkPC = arg
				self.link_address = arg
			else:
				print("    {name}: linking from {link}, output address may differ".format(name=parser.file, link=util.octal(arg)))
				self.linkPC = arg
		elif command == ".INCLUDE":
			self.include(arg, parser.file, coords)
		elif command == ".PDP11":
			pass
		elif command == ".I8080":
			self.err(coords, "PDPY11 cannot compile 8080 programs")
		elif command == ".SYNTAX":
			pass
		elif command == ".BYTE":
			for byte in arg:
				self.writeByte(byte, coords)
		elif command == ".WORD":
			for word in arg:
				self.writeWord(word, coords)
		elif command == ".DWORD":
			for dword in arg:
				self.writeDword(dword, coords)
		elif command == ".END":
			raise EOFError()
		elif command == ".BLKB":
			bytes_ = Deferred.Repeat(arg, 0)
			self.writeBytes(bytes_)
		elif command == ".BLKW":
			words = Deferred.Repeat(arg * 2, 0)
			self.writeBytes(words)
		elif command == ".EVEN":
			self.writeBytes(
				Deferred.If(
					self.linkPC % 2 == 0,
					[],
					[0]
				)
			)
		elif command == ".ALIGN":
			self.writeBytes(
				Deferred.If(
					self.linkPC % arg == 0,
					[],
					Deferred.Repeat(
						arg - self.linkPC % arg,
						0
					)
				)
			)
		elif command == ".ASCII":
			def stringToCharlist(string):
				try:
					bts = util.encodeKoi8(string)
				except UnicodeEncodeError:
					self.err(
						coords,
						"Cannot encode string to KOI8-R"
					)
				if sys.version_info[0] == 2:
					bts = map(ord, bts)
				return list(bts)

			self.writeBytes(
				Deferred(arg, str)
					.then(stringToCharlist, list)
			)
		elif command == ".MAKE_RAW":
			if parser.file == self.include_root:
				if arg is None:
					arg = parser.file
					if arg.lower().endswith(".mac"):
						arg = arg[:-4]
				else:
					arg = os.path.join(os.path.dirname(parser.file), arg)
				self.build.append(("raw", arg, ()))
		elif command == ".MAKE_BIN":
			if parser.file == self.include_root:
				if arg is None:
					arg = parser.file
					if arg.lower().endswith(".mac"):
						arg = arg[:-4]
					arg += ".bin"
				else:
					arg = os.path.join(os.path.dirname(parser.file), arg)
				self.build.append(("bin", arg, ()))
		elif command == ".MAKE_SAV":
			if parser.file == self.include_root:
				filename, final_address = arg
				if filename is None:
					filename = parser.file
					if filename.lower().endswith(".mac"):
						filename = filename[:-4]
					filename += ".sav"
				else:
					filename = os.path.join(os.path.dirname(parser.file), filename)
				self.build.append(("sav", filename, (final_address,) if final_address is not None else ()))
		elif command == ".MAKE_TURBO_WAV" or command == ".MAKE_WAV":
			if parser.file == self.include_root:
				real_filename, bk_filename = arg
				if real_filename is None:
					real_filename = parser.file
					if real_filename.lower().endswith(".mac"):
						real_filename = real_filename[:-4]
					real_filename += ".wav"
				else:
					real_filename = os.path.join(os.path.dirname(parser.file), real_filename)
				if bk_filename is None:
					bk_filename = os.path.basename(real_filename)
					if bk_filename.endswith(".wav"):
						bk_filename = bk_filename[:-4]
				format = "turbo-wav" if command == ".MAKE_TURBO_WAV" else "wav"
				self.build.append((format, real_filename, (bk_filename,)))
		elif command == ".CONVERT1251TOKOI8R":
			pass
		elif command == ".DECIMALNUMBERS":
			pass
		elif command == ".INSERT_FILE":
			try:
				with open(self.resolve(arg, os.path.dirname(parser.file)), "rb") as f:
					if sys.version_info[0] == 2:
						# Python 2
						self.writeBytes([ord(char) for char in f.read()])
					else:
						# Python 3
						self.writeBytes([char for char in f.read()])
			except IOError as e:
				self.err(
					coords,
					"Error inserting {file} (relative to {relative})".format(
						file=arg, relative=parser.file
					)
				)
		elif command == ".EQU":
			name, value = arg
			self.defineLabel(parser.file, name, value, coords)
		elif command == ".REPEAT":
			count, repeat_commands = arg
			count = Deferred(count, int)(self)

			local_labels = []
			for _, labels in repeat_commands:
				for name in labels:
					if ": " not in name:
						self.err(
							coords,
							"Cannot define global label {name} inside .REPEAT".format(name=name)
						)
				local_labels += labels

			repeat_id = "".join([random.choice(string.ascii_lowercase) for _ in range(8)])

			for idx in range(count):
				label_suffix = ": .REPEAT({id})[{idx}]".format(id=repeat_id, idx=idx)
				for (command, arg), labels in repeat_commands:
					arg = self.mapLabels(lambda label: label + label_suffix if label in local_labels else label, arg)
					labels = [label + label_suffix for label in labels]
					try:
						self.handleCommand(parser, command, arg, labels)
					except EOFError:
						break
		elif command == ".EXTERN":
			is_all = False
			is_none = False
			label_list = []
			for part in arg:
				if part == "ALL":
					is_all = True
				elif part == "NONE":
					is_none = True
				else:
					label_list.append(part)

			if is_all and is_none:
				self.err(coords, ".EXTERN ALL and .EXTERN NONE cannot be used together")
			elif is_all and len(label_list) > 0:
				self.err(coords, ".EXTERN ALL and .EXTERN LABEL cannot be used together")
			elif is_none and len(label_list) > 0:
				self.err(coords, ".EXTERN NONE and .EXTERN LABEL cannot be used together")

			if is_all:
				self.extern_labels = True
			elif is_none:
				self.extern_labels = False
			else:
				self.extern_labels = label_list
		elif command == ".ONCE":
			if parser.file in self.included_before:
				raise EOFError()
			else:
				self.included_before.add(parser.file)
		elif callable(commands[command][1]):
			# Metacommand
			for sub_command, sub_arg in commands[command][1](*arg):
				self.handleCommand(parser, sub_command, sub_arg, [])
		else:
			# It's a simple command
			if arg == ():
				self.writeWord(commands[command][1], coords)
			elif len(arg) == 1 and isinstance(arg[0], A):
				self.writeWord(
					commands[command][1] |
					self.encodeArg(arg[0]),
					coords
				)
			elif len(arg) == 1 and isinstance(arg[0], D):
				def unalignedBranch(offset):
					if offset % 2 == 1:
						self.err(coords, "Unaligned branch: {len} bytes".format(len=util.octal(offset)))
					else:
						return offset // 2
				def farBranch(offset):
					if offset < -128 or offset > 127:
						self.err(coords, "Too far branch: {len} words".format(len=util.octal(offset)))
					else:
						return offset

				offset = arg[0].addr - self.linkPC - 2
				offset = (Deferred(offset, int)
					.then(unalignedBranch, int)
					.then(farBranch, int)
				)

				self.writeWord(
					commands[command][1] |
					util.int8ToUint8(offset),
					coords
				)
			elif len(arg) == 1 and isinstance(arg[0], I):
				max_imm_value = commands[command][1]

				def bigImmediateValue(value):
					if value > max_imm_value:
						self.err(coords, "Too big immediate value: {value}".format(value=util.octal(value)))
					else:
						return value
				def negativeImmediateValue(value):
					if value < 0:
						self.err(coords, "Negative immediate value: {value}".format(value=util.octal(value)))
					else:
						return value

				value = (Deferred(arg[0].value, int)
					.then(bigImmediateValue, int)
					.then(negativeImmediateValue, int)
				)

				self.writeWord(commands[command][1] | value, coords)
				return
			elif len(arg) == 1 and isinstance(arg[0], R):
				self.writeWord(
					commands[command][1] | self.encodeRegister(arg[0]),
					coords
				)
			elif len(arg) == 2 and isinstance(arg[0], A) and isinstance(arg[1], A):
				self.writeWord(
					commands[command][1] |
					(self.encodeArg(arg[0]) << 6) |
					self.encodeArg(arg[1]),
					coords
				)
			elif len(arg) == 2 and isinstance(arg[0], R) and isinstance(arg[1], A):
				self.writeWord(
					commands[command][1] |
					(self.encodeRegister(arg[0]) << 6) |
					self.encodeArg(arg[1]),
					coords
				)
			elif len(arg) == 2 and isinstance(arg[0], A) and isinstance(arg[1], R):
				self.writeWord(
					commands[command][1] |
					(self.encodeRegister(arg[1]) << 6) |
					self.encodeArg(arg[0]),
					coords
				)
			elif len(arg) == 2 and isinstance(arg[0], R) and isinstance(arg[1], D):
				def unaligned(offset):
					if offset % 2 == 1:
						self.err(coords, "Unaligned {command}: {len} bytes".format(command=command, len=util.octal(offset)))
					else:
						return offset // 2
				def far(offset):
					if offset < 0 or offset > 63:
						self.err(coords, "Too far {command}: {len} words".format(command=command, len=util.octal(offset)))
					else:
						return offset

				offset = self.linkPC + 2 - arg[1].addr
				offset = (Deferred(offset, int)
					.then(unaligned, int)
					.then(far, int)
				)

				self.writeWord(
					commands[command][1] |
					(self.encodeRegister(arg[0]) << 6) |
					offset,
					coords
				)
			else:
				self.err(coords, "Unknown command {command}".format(command=command))

			for arg1 in arg:
				if isinstance(arg1, A) and arg1.imm is not None:
					additional = arg1.imm
					if getattr(additional, "isOffset", False):
						additional = additional - self.linkPC - 2

					self.writeWord(additional, coords)


	def include(self, path, file, coords):
		old_PC = self.PC
		old_linkPC = self.linkPC

		try:
			self.addFile(path, relative_to=file)
		except IOError:
			self.err(
				coords,
				"Error including {file} (relative to {relative})".format(
					file=path, relative=file
				)
			)

		include_length = self.PC - old_PC
		self.linkPC = old_linkPC + include_length



	def writeByte(self, byte, coords=None):
		def valueToByte(byte):
			if byte >= 256:
				self.err(coords, "Byte {byte} is too big".format(byte=util.octal(byte)))
			elif byte < -256:
				self.err(coords, "Byte {byte} is too small".format(byte=util.octal(byte)))
			elif byte < 0:
				return byte + 256
			else:
				return byte

		byte = Deferred(byte, int).then(valueToByte, int)

		self.writes.append((self.PC, byte))
		self.PC = self.PC + 1
		self.linkPC = self.linkPC + 1

	def writeWord(self, word, coords=None):
		def valueToWord(word):
			if word >= 65536:
				self.err(coords, "Word {word} is too big".format(word=util.octal(word)))
			elif word < -65536:
				self.err(coords, "Word {word} is too small".format(word=util.octal(word)))
			elif word < 0:
				return word + 65536
			else:
				return word

		word = Deferred(word, int).then(valueToWord, int)

		self.writes.append((self.PC, word & 0xFF))
		self.writes.append((self.PC + 1, word >> 8))
		self.PC = self.PC + 2
		self.linkPC = self.linkPC + 2

	def writeDword(self, dword, coords=None):
		def valueToDword(dword):
			if dword >= 0x100000000:
				self.err(coords, "Double word {dword} is too big".format(dword=util.octal(dword)))
			elif dword < -0x100000000:
				self.err(coords, "Double word {dword} is too small".format(dword=util.octal(dword)))
			elif dword < 0:
				return dword + 0x100000000
			else:
				return dword

		dword = Deferred(dword, int).then(valueToDword, int)

		self.writes.append((self.PC, (dword >> 16) & 0xFF))
		self.writes.append((self.PC + 1, dword >> 24))
		self.writes.append((self.PC + 2, dword & 0xFF))
		self.writes.append((self.PC + 3, (dword >> 8) & 0xFF))
		self.PC = self.PC + 4
		self.linkPC = self.linkPC + 4

	def writeBytes(self, bytes_):
		self.writes.append((self.PC, bytes_))
		self.PC = self.PC + Deferred(bytes_, list).then(len, int)
		self.linkPC = self.linkPC + Deferred(bytes_, list).then(len, int)

	def writeWords(self, words):
		def wordsToBytes(words):
			bytes_ = []
			for word in words:
				bytes_.append(word & 0xFF)
				bytes_.append(word >> 8)
			return bytes_
		self.writeBytes(Deferred(words).then(wordsToBytes))


	def encodeRegister(self, reg):
		if reg is SP:
			return 6
		elif reg is PC:
			return 7
		else:
			return (R0, R1, R2, R3, R4, R5).index(reg)
	def encodeAddr(self, addr):
		return ("Rn", "(Rn)", "(Rn)+", "@(Rn)+", "-(Rn)", "@-(Rn)", "N(Rn)", "@N(Rn)").index(addr)

	def encodeArg(self, arg):
		return (self.encodeAddr(arg.mode) << 3) | self.encodeRegister(arg.reg)


	def err(self, coords, text):
		raiseCompilerError(text, coords)


	def defineLabel(self, file_id, name, value, coords):
		extern = False
		if self.extern_labels is True:
			# .EXTERN ALL
			extern = True
		elif self.extern_labels is False:
			# .EXTERN NONE
			extern = False
		else:
			extern = name in self.extern_labels

		if extern:
			# Check that there is no file where such local label is
			# defined.
			for label in self.labels:
				if label.endswith(":{name}".format(name=name)):
					self.err(
						coords,
						("Duplicate global label {name} with local " +
						"label defined in {file_id}").format(name=name, file_id=label.rsplit(":", 1)[0])
					)

			# Check that there is no file where such global label is
			# defined.
			if name in self.labels:
				self.err(
					coords,
					"Duplicate global label {name}".format(name=name)
				)

			self.labels[name] = value
		else:
			# Check that there is no file where such global label is
			# defined.
			if name in self.labels:
				self.err(
					coords,
					("Duplicate global label {name} with local " +
					"label defined in {file_id}").format(name=name, file_id=file_id)
				)

		# Check that such local label is not defined in this file.
		local_name = "{file_id}:{name}".format(file_id=file_id, name=name)
		if local_name in self.labels:
			self.err(
				coords,
				"Duplicate local label {name}".format(name=name)
			)

		self.labels[local_name] = value

	def static_alloc(self, byte_length):
		address = self.last_static_alloc
		self.last_static_alloc = self.last_static_alloc + byte_length
		return address

	def mapLabels(self, f, obj):
		if isinstance(obj, list):
			return [self.mapLabels(f, x) for x in obj]
		elif isinstance(obj, tuple):
			return tuple([self.mapLabels(f, x) for x in obj])
		elif isinstance(obj, A):
			return A(obj.reg, obj.mode, self.mapLabels(f, obj.imm))
		elif isinstance(obj, D):
			return D(self.mapLabels(f, obj.addr))
		elif isinstance(obj, I):
			return I(self.mapLabels(f, obj.value))
		elif isinstance(obj, Expression.Get):
			return obj.map(f)
		elif isinstance(obj, Deferred):
			return obj.map(lambda x: self.mapLabels(f, x))
		else:
			return obj