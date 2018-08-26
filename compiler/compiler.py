from __future__ import print_function
import os
import sys
from .parser import Parser, EndOfParsingError
from .deferred import Deferred
from . import commands
from . import util
from .expression import Expression, ExpressionEvaluateError

class CompilerError(Exception):
	pass

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

	def define(self, name, value):
		value_text = "\"{}\"".format(value) if isinstance(value, str) else value

		if name.upper() in self.global_labels:
			self.err({
				"file": "CLI",
				"line": 1,
				"column": 1,
				"text": "-D{}={}".format(name, value_text)
			}, "Redefinition of label {}".format(name))

		self.global_labels[name.upper()] = value

	def buildProject(self):
		# Add all files inside project directory that have
		# make_raw or make_bk0010_rom directive
		to_make = set()
		for file in self.file_list:
			# Read file
			with open(file) as f:
				code = f.read()

			# Parse it
			print("Parsing", file)
			parser = Parser(file, code, syntax=self.syntax)

			for (command, arg), labels in parser.parse():
				if command == ".MAKE_RAW" or command == ".MAKE_BIN":
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
			for ext, name in self.build:
				try:
					link_address = Deferred(self.link_address, int)(self)
					print("    Output: {} ({} format) from {}".format(name, ext, util.octal(link_address)))
				except:
					print("    Output: {} ({} format) from {}".format(name, ext, repr(self.link_address)))

				self.all_build.append((ext, name, self.writes, self.link_address))

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

		with open(file) as f:
			code = f.read()

		try:
			self.compileFile(file, code)
		except CompilerError as e:
			print(e)
			raise SystemExit(1)

	def resolve(self, from_, file):
		# Resolve file path
		if file.startswith("/") or file[1:3] == ":\\":
			# Absolute
			return file
		else:
			# Relative
			return os.path.join(os.path.dirname(from_), file)

	def link(self):
		try:
			for label in self.labels:
				Deferred(self.labels[label], int)(self)

			if self.project is not None:
				all_build = []
				for ext, file, writes, link_address in self.all_build:
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
					all_build.append((ext, file, array[link_address:], link_address))

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
				return self.build
		except (ExpressionEvaluateError, CompilerError) as e:
			print(e)
			raise SystemExit(1)

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
			if self.project is not None:
				if self.include_root == parser.file:
					self.PC = arg
					self.linkPC = arg
					self.link_address = arg
				else:
					print("    {}: linking from {}, output address may differ".format(parser.file, repr(arg)))
					self.linkPC = arg
			else:
				self.PC = arg
				self.linkPC = arg
				self.link_address = arg
		elif command == ".INCLUDE":
			self.include(arg, parser.file)
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
			self.writeBytes(
				Deferred(arg, str)
					.then(lambda string: [ord(char) for char in string], list)
			)
		elif command == ".MAKE_RAW":
			if parser.file == self.include_root:
				if arg is None:
					arg = parser.file
					if arg.endswith(".mac"):
						arg = arg[:-4]
				self.build.append(("raw", arg))
		elif command == ".MAKE_BIN":
			if parser.file == self.include_root:
				if arg is None:
					arg = parser.file
					if arg.endswith(".mac"):
						arg = arg[:-4]
					arg += ".bin"
				self.build.append(("bin", arg))
		elif command == ".CONVERT1251TOKOI8R":
			pass
		elif command == ".DECIMALNUMBERS":
			pass
		elif command == ".INSERT_FILE":
			with open(self.resolve(arg, os.path.dirname(parser.file)), "rb") as f:
				if sys.version_info[0] == 2:
					# Python 2
					self.writeBytes([ord(char) for char in f.read()])
				else:
					# Python 3
					self.writeBytes([char for char in f.read()])
		elif command == ".EQU":
			name, value = arg
			self.defineLabel(parser.file, name, value, coords)
		elif command == ".REPEAT":
			count, repeat_commands = arg
			count = Deferred(count, int)
			try:
				count = count(self)
			except ExpressionEvaluateError as e:
				self.err(
					coords,
					"Error while evaluating .REPEAT count:\n" +
					"(notice: count must be known at the time of its usage)\n" +
					"\n" +
					str(e)
				)

			for _ in range(count):
				for (command, arg), labels in repeat_commands:
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
		else:
			# It's a simple command
			if command in commands.zero_arg_commands:
				self.writeWord(commands.zero_arg_commands[command], coords)
			elif command in commands.one_arg_commands:
				self.writeWord(
					commands.one_arg_commands[command] |
					self.encodeArg(arg[0]),
					coords
				)
			elif command in commands.jmp_commands:
				offset = arg[0] - self.linkPC - 2
				offset = (Deferred(offset, int)
					.then(lambda offset: (
						self.err(coords, "Unaligned branch: {} bytes".format(util.octal(offset)))
						if offset % 2 == 1
						else offset // 2
					), int)
					.then(lambda offset: (
						self.err(coords, "Too far branch: {} words".format(util.octal(offset)))
						if offset < -128 or offset > 127
						else offset
					), int)
				)

				self.writeWord(
					commands.jmp_commands[command] |
					util.int8ToUint8(offset),
					coords
				)
			elif command in commands.imm_arg_commands:
				max_imm_value = commands.imm_arg_commands[command][1]

				value = (Deferred(arg[0], int)
					.then(lambda value: (
						self.err(coords, "Too big immediate value: {}".format(util.octal(value)))
						if value > max_imm_value
						else value
					), int)
					.then(lambda value: (
						self.err(coords, "Negative immediate value: {}".format(util.octal(value)))
						if value < 0
						else value
					), int)
				)

				self.writeWord(commands.imm_arg_commands[command][0] | (value // 2), coords)
			elif command in commands.two_arg_commands:
				self.writeWord(
					commands.two_arg_commands[command] |
					(self.encodeArg(arg[0]) << 6) |
					self.encodeArg(arg[1]),
					coords
				)
			elif command in commands.reg_commands:
				self.writeWord(
					commands.reg_commands[command] |
					(self.encodeRegister(arg[0]) << 6) |
					self.encodeArg(arg[1]),
					coords
				)
			elif command == "RTS":
				self.writeWord(
					0o000200 | self.encodeRegister(arg[0]),
					coords
				)
			elif command == "SOB":
				offset = self.linkPC + 2 - arg[1]
				offset = (Deferred(offset, int)
					.then(lambda offset: (
						self.err(coords, "Unaligned SOB: {} bytes".format(util.octal(offset)))
						if offset % 2 == 1
						else offset // 2
					), int)
					.then(lambda offset: (
						self.err(coords, "Too far SOB: {} words".format(util.octal(offset)))
						if offset < 0 or offset > 63
						else offset
					), int)
				)

				self.writeWord(
					0o077000 |
					(self.encodeRegister(arg[0]) << 6) |
					offset,
					coords
				)
			else:
				self.err(coords, "Unknown command {}".format(command))

			for arg1 in arg:
				if isinstance(arg1, tuple):
					_, additional = arg1
				elif isinstance(arg1, (int, Expression)):
					additional = arg1
				else:
					additional = None

				if additional is not None:
					if getattr(additional, "isOffset", False):
						additional = additional - self.linkPC - 2

					self.writeWord(additional, coords)


	def include(self, path, file):
		old_PC = self.PC
		old_linkPC = self.linkPC

		self.addFile(path, relative_to=file)

		include_length = self.PC - old_PC
		self.linkPC = old_linkPC + include_length



	def writeByte(self, byte, coords=None):
		byte = (Deferred(byte, int)
			.then(lambda byte: (
				self.err(coords, "Byte {} is too big".format(util.octal(byte)))
				if byte >= 256 else byte
			), int)
			.then(lambda byte: (
				self.err(coords, "Byte {} is too small".format(util.octal(byte)))
				if byte < -256 else byte
			), int)
			.then(lambda byte: byte + 256 if byte < 0 else byte, int)
		)

		self.writes.append((self.PC, byte))
		self.PC = self.PC + 1
		self.linkPC = self.linkPC + 1

	def writeWord(self, word, coords=None):
		word = (Deferred(word, int)
			.then(lambda word: (
				self.err(coords, "Word {} is too big".format(util.octal(word)))
				if word >= 65536 else word
			), int)
			.then(lambda word: (
				self.err(coords, "Word {} is too small".format(util.octal(word)))
				if word < -65536 else word
			), int)
			.then(lambda word: word + 65536 if word < 0 else word, int)
		)

		self.writes.append((self.PC, word & 0xFF))
		self.writes.append((self.PC + 1, word >> 8))
		self.PC = self.PC + 2
		self.linkPC = self.linkPC + 2

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
		if reg == "SP":
			return 6
		elif reg == "PC":
			return 7
		else:
			return ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7").index(reg)
	def encodeAddr(self, addr):
		return ("Rn", "(Rn)", "(Rn)+", "@(Rn)+", "-(Rn)", "@-(Rn)", "N(Rn)", "@N(Rn)").index(addr)

	def encodeArg(self, arg):
		(reg, addr), _ = arg
		return (self.encodeAddr(addr) << 3) | self.encodeRegister(reg)


	def err(self, coords, text):
		raise CompilerError(
			"{}\n  at file {file} (line {line}, column {column})\n\n{text}".format(
				text,
				file=coords["file"],
				line=coords["line"], column=coords["column"],
				text=coords["text"]
			)
		)


	def resolve(self, file, relative_to):
		# Resolve file path
		if file.startswith("/") or file[1:3] == ":\\":
			# Absolute
			return file
		else:
			# Relative
			return os.path.join(relative_to, file)

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
				if label.endswith(":{}".format(name)):
					self.err(
						coords,
						("Redefinition of global label {} with local " +
						"label defined in {}").format(name, label.rsplit(":", 1)[0])
					)

			# Check that there is no file where such global label is
			# defined.
			if name in self.labels:
				self.err(
					coords,
					"Redefinition of global label {}".format(name)
				)

			self.labels[name] = value
		else:
			# Check that there is no file where such global label is
			# defined.
			if name in self.labels:
				self.err(
					coords,
					("Redefinition of global label {} with local " +
					"label defined in {}").format(name, file_id)
				)

			self.labels["{}:{}".format(file_id, name)] = value