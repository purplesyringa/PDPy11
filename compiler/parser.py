import os


whitespace = "\n\r\t "
punctuation = ",!@#$%^&*()[]\\{}|/~`'\";:?<>._+-="

class EndOfParsingError(Exception):
	pass
class InvalidError(Exception):
	pass

class Parser:
	def __init__(self, code):
		self.code = code
		self.pos = 0
		self.decimal = False

	def parseCommand(self):
		literal = self.needLiteral(maybe=True)

		# First, handle metacommands (directives)
		if literal == "ORG":
			return self.handleLink()
		elif literal == "DB":
			return self.handleByte()
		elif literal == "DW":
			return self.handleWord()
		elif literal == "END":
			raise EndOfParsingError()
		elif literal == "DS":
			return self.handleBlkb()
		elif literal == "ALIGN":
			return self.handleAlign()
		elif literal == "MAKE_RAW":
			return self.handleMakeRaw()
		elif literal == "MAKE_BK0010_ROM":
			return self.handleMakeBin()
		elif literal == "CONVERT1251TOKOI8R":
			return self.handleConvert1251toKOI8R()
		elif literal == "DECIMALNUMBERS":
			return self.handleDecimalNumbers()
		elif literal == "INSERT_FILE":
			return self.handleInsertFile()

		# Maybe it's a metacommand that starts with a dot?
		if literal is None and self.needPunct(".", maybe=True):
			literal = self.needLiteral()

			if literal == "LINK" or literal == "LA":
				return self.handleLink()
			elif literal == "INCLUDE":
				return self.handleInclude()
			elif literal == "RAW_INCLUDE":
				return self.handleInclude(raw=True)
			elif literal == "PDP11":
				return self.handlePdp11()
			elif literal == "I8080":
				return self.handleI8080()
			elif literal == "SYNTAX":
				return self.handleSyntax()
			elif literal == "DB" or literal == "BYTE":
				return self.handleByte()
			elif literal == "DW" or literal == "WORD":
				return self.handleWord()
			elif literal == "END":
				raise EndOfParsingError()
			elif literal == "DS" or literal == "BLKB":
				return self.handleBlkb()
			elif literal == "BLKW":
				return self.handleBlkw()
			elif literal == "EVEN":
				return self.handleEven()
			elif literal == "ASCII":
				return self.handleAscii(term="")
			elif literal == "ASCIZ":
				return self.handleAscii(term="\x00")
			else:
				raise InvalidError("Expected .COMMAND, got '.{}'".format(literal))

		# Otherwise, it's a simple command
		if literal is None:
			raise InvalidError("Expected literal or .COMMAND")

		print("simple command", literal)



	def handleLink(self):
		# ORG / .LINK / .LA
		return ".LINK", self.needInteger()

	def handleInclude(self, raw):
		# .INCLUDE / .RAW_INCLUDE
		if raw:
			return ".INCLUDE", self.needRaw()
		else:
			return ".INCLUDE", self.needString()

	def handlePdp11(self):
		return ".PDP11", None

	def handleI8080(self):
		return ".I8080", None

	def handleSyntax(self):
		return ".SYNTAX", self.needLiteral().lower()

	def handleByte(self):
		# .DB / .BYTE / DB
		return ".BYTE", self.needInteger()

	def handleWord(self):
		# .DW / .WORD / DW
		return ".WORD", self.needInteger()

	def handleEnd(self):
		return ".END", None

	def handleBlkb(self):
		# .DS / .BLKB / DS
		return ".BLKB", self.needInteger()

	def handleBlkw(self):
		# .BLKW
		return ".BLKW", self.needInteger()

	def handleEven(self):
		# .EVEN
		return ".EVEN", None

	def handleAlign(self):
		# ALIGN
		return ".ALIGN", self.needInteger()

	def handleAscii(self, term=""):
		# .ASCII/.ASCIZ
		return ".ASCII", self.needString() + term

	def handleMakeRaw(self):
		return ".MAKE_RAW", self.needString(maybe=True)

	def handleMakeBin(self):
		return ".MAKE_BIN", self.needString(maybe=True)

	def handleConvert1251toKOI8R(self):
		return ".CONVERT1251TOKOI8R", self.needBool()

	def handleDecimalNumbers(self):
		self.decimal = self.needBool()
		return ".DECIMALNUMBERS", self.decimal

	def handleInsertFile(self):
		return ".INSERT_FILE", self.needString()


	def needLiteral(self, maybe=False):
		# Parse literal, starting with self.pos, and seek to
		# its end. Return the literal in upper case.

		with Transaction(self, maybe=maybe):
			# Skip whitespace
			try:
				while self.code[self.pos] in whitespace:
					self.pos += 1
			except IndexError:
				raise InvalidError("Expected literal, got EOF")

			literal = ""

			while True:
				try:
					if self.code[self.pos] in whitespace + punctuation:
						# Punctuation or whitespace
						return literal
				except IndexError:
					# End
					return literal

				if self.code[self.pos].upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
					literal += self.code[self.pos].upper()
					self.pos += 1
				elif self.code[self.pos] in "0123456789" and literal != "":
					literal += self.code[self.pos].upper()
					self.pos += 1
				else:
					raise InvalidError("Expected literal, got '{}'".format(self.code[self.pos]))


	def needPunct(self, char, maybe=False):
		with Transaction(self, maybe=maybe):
			# Skip whitespace
			try:
				while self.code[self.pos] in whitespace:
					self.pos += 1
			except IndexError:
				raise InvalidError("Expected literal, got EOF")

			if self.code[self.pos] == char:
				self.pos += 1
				return char
			else:
				raise InvalidError("Expected '{}', got '{}'".format(char, self.code[self.pos]))


	def needInteger(self, maybe=False):
		# Parse integer, starting with self.pos, and seek to
		# its end. Return the integer in 'int' type.

		with Transaction(self, maybe=maybe):
			# Skip whitespace
			try:
				while self.code[self.pos] in whitespace:
					self.pos += 1
			except IndexError:
				raise InvalidError("Expected integer, got EOF")

			integer = ""
			radix = None

			while True:
				if self.code[self.pos] == ".":
					# Decimal
					if integer == "":
						raise InvalidError("Expected integer, got '.'")
					else:
						if radix is None:
							radix = 10
							break
						else:
							raise InvalidError("Two (or more) radix specifiers")
				elif self.code[self.pos] in "hH":
					# Hexadimical
					if radix is None:
						radix = 16
						break
					else:
						raise InvalidError("Two (or more) radix specifiers")
				elif self.code[self.pos] in "dD":
					# Decimal
					if radix is None:
						radix = 10
						break
					else:
						raise InvalidError("Two (or more) radix specifiers")
				elif self.code[self.pos] in "bB":
					# Binary
					if radix is None:
						radix = 2
						break
					else:
						raise InvalidError("Two (or more) radix specifiers")
				elif self.code[self.pos] in "oO":
					# Octal
					if radix is None:
						radix = 8
						break
					else:
						raise InvalidError("Two (or more) radix specifiers")
				elif self.code[self.pos] in "xX" and integer == "0":
					# Hexadimical
					if radix is None:
						radix = 16
						break
					else:
						raise InvalidError("Two (or more) radix specifiers")
				elif self.code[self.pos] in "bB" and integer == "0":
					# Binary
					if radix is None:
						radix = 2
						break
					else:
						raise InvalidError("Two (or more) radix specifiers")
				elif self.code[self.pos] in "oO" and integer == "0":
					# Octal
					if radix is None:
						radix = 8
						break
					else:
						raise InvalidError("Two (or more) radix specifiers")


				try:
					if self.code[self.pos] in whitespace + punctuation:
						# Punctuation or whitespace
						break
				except IndexError:
					# End
					break

				if self.code[self.pos].upper() in "0123456789ABCDEF":
					integer += self.code[self.pos].upper()
					self.pos += 1
				else:
					raise InvalidError("Expected integer, got '{}'".format(self.code[self.pos]))

			if radix is None:
				radix = 10 if self.decimal else 8

			return int(integer, radix)


	def needRaw(self):
		# Return string till the end of the string (trimmed)

		with Transaction(self, maybe=False):
			string = ""

			while True:
				try:
					if self.code[self.pos] in "\r\n":
						# EOL
						return string.strip()
				except IndexError:
					# EOF
					return string.strip()

				string += self.code[self.pos]
				self.pos += 1


	def needString(self, maybe=False):
		# Return string between " and ", or / and /

		with Transaction(self, maybe=maybe):
			# Skip whitespace
			try:
				while self.code[self.pos] in whitespace:
					self.pos += 1
			except IndexError:
				raise InvalidError("Expected string, got EOF")

			punct = ""
			if self.code[self.pos] in "\"/":
				punct = self.code[self.pos]
				self.pos += 1
			else:
				raise InvalidError("Expected string, got '{}'".format(self.code[self.pos]))

			string = ""

			while True:
				try:
					if self.code[self.pos] == "\\":
						# Escape character
						self.pos += 1

						if self.code[self.pos] in "nN":
							self.pos += 1
							string += "\n"
						elif self.code[self.pos] in "rR":
							self.pos += 1
							string += "\r"
						elif self.code[self.pos] in "tT":
							self.pos += 1
							string += "\t"
						elif self.code[self.pos] in "sS":
							self.pos += 1
							string += " "
						elif self.code[self.pos] in "xX":
							self.pos += 1
							num = self.code[self.pos]
							self.pos += 1
							num += self.code[self.pos]
							self.pos += 1
							string += chr(int(num, 16))
						elif self.code[self.pos] in "\\\"/":
							self.pos += 1
							string += self.code[self.pos]
						else:
							raise InvalidError("Expected \\n, \\r, \\t, \\s, \\\\, \\\", \\/ or \\xNN, got '\\{}'".format(self.code[self.pos]))
					elif self.code[self.pos] == punct:
						# EOS
						self.pos += 1
						return string
					else:
						string += self.code[self.pos]
						self.pos += 1
				except IndexError:
					# EOF
					raise InvalidError("Expected string, got EOF")


	def needBool(self, maybe=False):
		# Handle ON, OFF, TRUE, FALSE, YES, NO

		with Transaction(self, maybe=maybe):
			# Skip whitespace
			try:
				while self.code[self.pos] in whitespace:
					self.pos += 1
			except IndexError:
				raise InvalidError("Expected boolean, got EOF")

			lit = self.needLiteral(maybe=True)
			if lit in ("ON", "TRUE", "YES"):
				return True
			elif lit in ("OFF", "FALSE", "NO"):
				return False
			elif lit is not None:
				raise InvalidError("Expected boolean, got '{}'".format(lit))
			else:
				try:
					raise InvalidError("Expected boolean, got '{}'".format(self.code[self.pos]))
				except IndexError:
					raise InvalidError("Expected boolean, got EOF")


class Transaction:
	def __init__(self, parser, maybe=False):
		self.parser = parser
		self.maybe = maybe

	def __enter__(self):
		self.pos = self.parser.pos
	def __exit__(self, err_cls, err, traceback):
		if err_cls is None:
			# Success
			pass
		elif isinstance(err_cls, EndOfParsingError):
			# It doesn't make sense to parse further
			raise err
		elif isinstance(err_cls, InvalidError):
			# Could not parse token as ...
			maybe
			if self.maybe:
				return
			else:
				raise err
		else:
			# Some weird bug
			raise err