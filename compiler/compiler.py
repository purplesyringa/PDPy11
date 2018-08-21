import os
from .parser import Parser, EndOfParsingError
from .deferred import Deferred
from . import commands

class CompilerError(Exception):
	pass

class Compiler:
	def __init__(self, syntax="py11", link=0o1000, file_list=[], project=None):
		self.syntax = syntax
		self.link_address = link
		self.file_list = file_list
		self.project = project
		self.labels = {}
		self.PC = link
		self.build = []
		self.writes = []

	def addFile(self, file):
		# Resolve file path
		if file.startswith("/") or file[1:3] == ":\\":
			# Absolute
			pass
		else:
			# Relative
			file = os.path.join(os.getcwd(), file)

		with open(file) as f:
			code = f.read()

		self.compileFile(file, code)


	def compileFile(self, file, code):
		parser = Parser(code, syntax=self.syntax)

		for (command, arg), labels in parser.parse():
			for label in labels:
				if label in self.labels:
					raise CompilerError("Redefinition of label {}".format(label))

				self.labels[label] = self.PC

			if command == ".LINK":
				self.PC = arg
			elif command == ".INCLUDE":
				raise NotImplementedError(".INCLUDE and .RAW_INCLUDE are not implemented yet")
			elif command == ".PDP11":
				pass
			elif command == ".I8080":
				raise CompilerError("PY11 cannot compile 8080 programs")
			elif command == ".SYNTAX":
				pass
			elif command == ".BYTE":
				self.writeByte(arg)
			elif command == ".WORD":
				self.writeWord(arg)
			elif command == ".END":
				break
			elif command == ".BLKB":
				bytes_ = Deferred.Repeat(arg, 0)
				self.writeBytes(bytes_)
			elif command == ".BLKW":
				words = Deferred.Repeat(arg, 0)
				self.writeWords(words)
			elif command == ".EVEN":
				self.writeBytes(
					Deferred.If(
						lambda: self.PC % 2 == 0,
						[],
						[0]
					)
				)
			elif command == ".ALIGN":
				self.writeBytes(
					Deferred.If(
						lambda: self.PC % arg == 0,
						[],
						Deferred.Repeat(
							arg - self.PC % arg,
							0
						)
					)
				)
			elif command == ".ASCII":
				self.writeBytes(
					Deferred(arg)
						.then(lambda string: [ord(char) for char in string])
				)
			elif command == ".MAKE_RAW":
				self.build.append(("raw", arg))
			elif command == ".MAKE_BIN":
				self.build.append(("bin", arg))
			elif command == ".CONVERT1251TOKOI8R":
				pass
			elif command == ".DECIMALNUMBERS":
				pass
			elif command == ".INSERT_FILE":
				with open(arg) as f:
					self.writeBytes([ord(char) for char in f.read()])
			else:
				print(command, arg, labels)




	def writeByte(self, byte):
		byte = (Deferred(byte)
			.then(lambda byte: (
				Deferred.Raise(CompilerError("Byte {} is too big".format(byte)))
				if byte >= 256 else 0
			))
			.then(lambda byte: (
				Deferred.Raise(CompilerError("Byte {} is too small".format(byte)))
				if byte < -256 else 0
			))
			.then(lambda byte: byte + 256 if byte < 0 else byte)
		)

		self.writes.append((self.PC, byte))
		self.PC = self.PC + 1

	def writeWord(self, word):
		word = (Deferred(word)
			.then(lambda word: (
				Deferred.Raise(CompilerError("Word {} is too big".format(word)))
				if word >= 65536 else 0
			))
			.then(lambda word: (
				Deferred.Raise(CompilerError("Word {} is too small".format(word)))
				if word < -65536 else 0
			))
			.then(lambda word: word + 65536 if word < 0 else word)
		)

		self.writes.append((self.PC, word & 0xFF))
		self.writes.append((self.PC + 1, word >> 8))
		self.PC = self.PC + 2

	def writeBytes(self, bytes_):
		self.writes.append(bytes_)
	def writeWords(self, words):
		self.writes.append(words)