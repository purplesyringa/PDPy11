import os


whitespace = "\n\r\t "
punctuation = ",!@#%^&*()[]\\{}|/~`'\";:?<>.+-="

class EndOfParsingError(Exception):
	pass
class InvalidError(Exception):
	pass

class Parser:
	def __init__(self, code):
		self.code = code
		self.pos = 0
		self.decimal = False

	def parse(self):
		try:
			while True:
				for cmd in self.parseCommand():
					yield cmd
		except EndOfParsingError:
			pass

	def parseCommand(self, labels=[]):
		literal = self.needLiteral(maybe=True)

		# First, handle metacommands (directives)
		if literal == "ORG":
			yield self.handleLink(), labels
			return
		elif literal == "DB":
			yield self.handleByte(), labels
			return
		elif literal == "DW":
			yield self.handleWord(), labels
			return
		elif literal == "END":
			yield None, labels
			raise EndOfParsingError()
		elif literal == "DS":
			yield self.handleBlkb(), labels
			return
		elif literal == "ALIGN":
			yield self.handleAlign(), labels
			return
		elif literal == "MAKE_RAW":
			yield self.handleMakeRaw(), labels
			return
		elif literal == "MAKE_BK0010_ROM":
			yield self.handleMakeBin(), labels
			return
		elif literal == "CONVERT1251TOKOI8R":
			yield self.handleConvert1251toKOI8R(), labels
			return
		elif literal == "DECIMALNUMBERS":
			yield self.handleDecimalNumbers(), labels
			return
		elif literal == "INSERT_FILE":
			yield self.handleInsertFile(), labels
			return

		# Maybe it's a metacommand that starts with a dot?
		if literal is None and self.needPunct(".", maybe=True):
			literal = self.needLiteral()

			if literal == "LINK" or literal == "LA":
				yield self.handleLink(), labels
				return
			elif literal == "INCLUDE":
				yield self.handleInclude(), labels
				return
			elif literal == "RAW_INCLUDE":
				yield self.handleInclude(raw=True), labels
				return
			elif literal == "PDP11":
				yield self.handlePdp11(), labels
				return
			elif literal == "I8080":
				yield self.handleI8080(), labels
				return
			elif literal == "SYNTAX":
				yield self.handleSyntax(), labels
				return
			elif literal == "DB" or literal == "BYTE":
				yield self.handleByte(), labels
				return
			elif literal == "DW" or literal == "WORD":
				yield self.handleWord(), labels
				return
			elif literal == "END":
				yield None, labels
				raise EndOfParsingError()
			elif literal == "DS" or literal == "BLKB":
				yield self.handleBlkb(), labels
				return
			elif literal == "BLKW":
				yield self.handleBlkw(), labels
				return
			elif literal == "EVEN":
				yield self.handleEven(), labels
				return
			elif literal == "ASCII":
				yield self.handleAscii(term=""), labels
				return
			elif literal == "ASCIZ":
				yield self.handleAscii(term="\x00"), labels
				return
			else:
				raise InvalidError("Expected .COMMAND, got '.{}'".format(literal))

		if literal is None:
			raise InvalidError("Expected COMMAND, LABEL: or .COMMAND")

		# It is either a command or a label
		if self.needPunct(":", maybe=True):
			# It's a label
			for cmd in self.parseCommand(labels=labels + [literal]):
				yield cmd
			return

		# It's a command
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
						if literal == "":
							raise InvalidError("Expected literal, got '{}'".format(self.code[self.pos]))
						return literal
				except IndexError:
					# End
					if literal == "":
						raise InvalidError("Expected literal, got EOF")
					return literal

				if self.code[self.pos].upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_$":
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
		elif isinstance(err, EndOfParsingError):
			# It doesn't make sense to parse further
			raise err
		elif isinstance(err, InvalidError):
			# Could not parse token as ...
			if self.maybe:
				self.parser.pos = self.pos
				return True
			else:
				raise err
		else:
			# Some weird bug
			raise err