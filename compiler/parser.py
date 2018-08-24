from __future__ import print_function
import os
from . import commands
from .expression import Expression


whitespace = "\n\r\t "
punctuation = ",!@#%^&*()[]\\{}|/~`'\";:?<>.+-="
registers = ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "SP", "PC")

class EndOfParsingError(Exception):
	pass
class InvalidError(Exception):
	pass

class Parser(object):
	last_mark = 0

	def __init__(self, file, code, syntax):
		self.code = code
		self.pos = 0
		self.file = file
		self.decimal = False
		self.syntax = syntax
		self.last_label = ""
		self.stage_stack = []
		self.last_error_stages = []

	def parse(self):
		try:
			while True:
				for cmd in self.parseCommand():
					yield cmd
		except EndOfParsingError:
			pass
		except InvalidError as e:
			# Position to line/col
			line = len(self.code[:self.pos].split("\n"))
			try:
				last_lf = self.code[:self.pos].rindex("\n")
			except ValueError:
				last_lf = 0
			col = self.pos - last_lf

			print("Syntax error")
			print(e)
			print("  at file", self.file, "(line {}, column {})".format(line, col))
			for stage in self.last_error_stages:
				if stage is not None:
					print("  at", stage)
			raise SystemExit(1)

	def parseCommand(self, labels=None):
		if labels is None:
			labels = []

		if self.isEOF():
			yield (None, None), labels
			raise EndOfParsingError()

		self.current_labels = labels

		self.skipWhitespace()
		self.cmd_start = self.pos

		with Transaction(self, maybe=False, stage="command") as t:
			pos = self.pos
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
				yield (None, None), labels
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
				with Transaction(self, maybe=False, stage=".COMMAND") as t:
					literal = self.needLiteral()

					if literal == "LINK" or literal == "LA":
						yield self.handleLink(), labels
						return
					elif literal == "INCLUDE":
						yield self.handleInclude(), labels
						if self.syntax == "pdp11asm":
							raise EndOfParsingError()
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
						yield (None, None), labels
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
					elif literal == "REPEAT":
						yield self.handleRepeat(), labels
						return
					else:
						raise InvalidError("Expected .COMMAND, got '.{}'".format(literal))

			if literal is None:
				# Maybe integer label?
				label = self.needInteger()
				self.needPunct(":")

				# It's a label
				label = "{}@{}".format(self.last_label, label)
				t.exit()
				for cmd in self.parseCommand(labels=labels + [label]):
					yield cmd
				return


			# It is either a command or a label, or EQU
			if self.needPunct(":", maybe=True):
				# It's a label
				self.last_label = literal
				t.exit()
				for cmd in self.parseCommand(labels=labels + [literal]):
					yield cmd
				return
			elif self.needPunct("=", maybe=True):
				# EQU
				expr = self.needExpression()
				yield (".EQU", (literal, expr)), labels
				return

			with Transaction(self, maybe=True) as t:
				if self.needLiteral() == "EQU":
					t.noRollback()

					with Transaction(self, maybe=False, stage="EQU") as t:
						expr = self.needExpression()
						yield (".EQU", (literal, expr)), labels
						return
				else:
					raise InvalidError("Rollback")

			# It's a command
			self.pos = pos
			yield self.handleCommand(), labels

	def mark(self):
		label = ".{}".format(Parser.last_mark)
		self.current_labels.append(label)
		Parser.last_mark += 1
		return Expression(label)



	def handleLink(self):
		# ORG / .LINK / .LA
		with Transaction(self, maybe=False, stage=".LINK"):
			return ".LINK", self.needExpression()

	def handleInclude(self, raw=False):
		# .INCLUDE / .RAW_INCLUDE
		with Transaction(self, maybe=False, stage=".INCLUDE"):
			if raw:
				return ".INCLUDE", self.needRaw()
			else:
				return ".INCLUDE", self.needString()

	def handlePdp11(self):
		return ".PDP11", None

	def handleI8080(self):
		return ".I8080", None

	def handleSyntax(self):
		# .SYNTAX
		with Transaction(self, maybe=False, stage=".SYNTAX"):
			syntax = self.needLiteral().lower()
			self.syntax = syntax
			return ".SYNTAX", syntax

	def handleByte(self):
		# .DB / .BYTE / DB
		with Transaction(self, maybe=False, stage=".BYTE"):
			values = [self.needExpression()]
			while self.needPunct(",", maybe=True):
				values.append(self.needExpression())
			return ".BYTE", values

	def handleWord(self):
		# .DW / .WORD / DW
		with Transaction(self, maybe=False, stage=".WORD"):
			values = [self.needExpression()]
			while self.needPunct(",", maybe=True):
				values.append(self.needExpression())
			return ".WORD", values

	def handleEnd(self):
		return ".END", None

	def handleBlkb(self):
		# .DS / .BLKB / DS
		with Transaction(self, maybe=False, stage=".BLKB"):
			return ".BLKB", self.needExpression()

	def handleBlkw(self):
		# .BLKW
		with Transaction(self, maybe=False, stage=".BLKW"):
			return ".BLKW", self.needExpression()

	def handleEven(self):
		# .EVEN
		return ".EVEN", None

	def handleAlign(self):
		# ALIGN
		with Transaction(self, maybe=False, stage=".ALIGN"):
			return ".ALIGN", self.needExpression()

	def handleAscii(self, term=""):
		# .ASCII/.ASCIZ
		with Transaction(self, maybe=False, stage=".ASCII / .ASCIZ"):
			return ".ASCII", self.needString() + term

	def handleMakeRaw(self):
		with Transaction(self, maybe=False, stage=".MAKE_RAW"):
			return ".MAKE_RAW", self.needString(maybe=True)

	def handleMakeBin(self):
		with Transaction(self, maybe=False, stage=".MAKE_BIN"):
			return ".MAKE_BIN", self.needString(maybe=True)

	def handleConvert1251toKOI8R(self):
		with Transaction(self, maybe=False, stage=".CONVERT1251TOKOI8R"):
			return ".CONVERT1251TOKOI8R", self.needBool()

	def handleDecimalNumbers(self):
		with Transaction(self, maybe=False, stage=".DECIMALNUMBERS"):
			self.decimal = self.needBool()
			return ".DECIMALNUMBERS", self.decimal

	def handleInsertFile(self):
		with Transaction(self, maybe=False, stage=".INSERT_FILE"):
			return ".INSERT_FILE", self.needString()

	def handleRepeat(self):
		with Transaction(self, maybe=False, stage=".REPEAT"):
			count = self.needExpression()

			self.needPunct("{")
			commands = []
			cmd_start = self.cmd_start
			while True:
				if self.needPunct("}", maybe=True):
					self.cmd_start = cmd_start
					return ".REPEAT", (count, commands)
				else:
					for cmd in self.parseCommand():
						commands.append(cmd)

	def handleCommand(self):
		self.skipWhitespace()

		with Transaction(self, maybe=False, stage="compilable command") as t:
			command_name = self.needLiteral()

			if command_name in commands.zero_arg_commands:
				# No arguments expected
				return command_name, ()
			elif command_name in commands.one_arg_commands:
				# Need exactly 1 argument
				arg = self.needArgument()
				return command_name, (arg,)
			elif command_name in commands.jmp_commands:
				# Need 1 label, or relative address
				expr = self.needExpression(isLabel=True)
				return command_name, (expr,)
			elif command_name in commands.imm_arg_commands:
				# Need 1 expression
				expr = self.needExpression()
				return command_name, (expr,)
			elif command_name in commands.two_arg_commands:
				# Need exactly 2 arguments
				arg1 = self.needArgument()
				self.needPunct(",")
				arg2 = self.needArgument()
				return command_name, (arg1, arg2)
			elif command_name in commands.reg_commands:
				# Need register & argument
				reg1 = self.needRegister()
				self.needPunct(",")
				arg2 = self.needArgument()
				return command_name, (reg1, arg2)
			elif command_name == "RTS":
				# Need register
				reg = self.needRegister()
				return command_name, (reg,)
			elif command_name == "SOB":
				# Need register & relative address (or label)
				reg1 = self.needRegister()
				self.needPunct(",")
				arg2 = self.needExpression(isLabel=True)
				return command_name, (reg1, arg2)
			else:
				raise InvalidError(
					"Expected command name, got '{}'".format(command_name)
				)


	def needArgument(self, maybe=False):
		# Parse Rn, (Rn) (as well as @Rn), (Rn)+, -(Rn), @(Rn)+, @-(Rn),
		# expression(Rn), @expression(Rn), and PC shortcuts: #expression,
		# @#expression, @expression and expression.

		with Transaction(self, maybe=maybe, stage="argument") as t:
			if self.needPunct("(", maybe=True):
				# (Rn) or (Rn)+
				t.noRollback()
				reg = self.needRegister()
				self.needPunct(")")

				if self.needPunct("+", maybe=True):
					# (Rn)+
					return (reg, "(Rn)+"), None
				else:
					# (Rn)
					return (reg, "(Rn)"), None
			elif self.needPunct("@", maybe=True):
				# @Rn, @(Rn)+, @-(Rn), @expression(Rn), @(Rn), @#expression or
				# @expression

				if self.needPunct("#", maybe=True):
					# @#expression = @(PC)+
					t.noRollback()
					expr = self.needExpression()
					return ("PC", "@(Rn)+"), expr
				elif self.needPunct("(", maybe=True):
					# @(Rn)+ or @(Rn)
					t.noRollback()
					reg = self.needRegister()
					self.needPunct(")")
					if self.needPunct("+", maybe=True):
						# @(Rn)+
						return (reg, "@(Rn)+"), None
					else:
						# @0(Rn)
						return (reg, "@N(Rn)"), Expression(0)
				elif self.needPunct("-", maybe=True):
					# @-(Rn)
					t.noRollback()
					self.needPunct("(")
					reg = self.needRegister()
					self.needPunct(")")
					return (reg, "@-(Rn)"), None

				reg = self.needRegister(maybe=True)
				if reg is not None:
					# @Rn = (Rn)
					return (reg, "(Rn)"), None
				else:
					# @expression(Rn) or @expression
					t.noRollback()
					expr = self.needExpression()

					if self.needPunct("(", maybe=True):
						# @expression(Rn)
						t.noRollback()
						reg = self.needRegister()
						self.needPunct(")")
						return (reg, "@N(Rn)"), expr
					else:
						# @expression
						if self.syntax == "pdp11asm":
							# PDP11Asm bug
							return ("PC", "@N(Rn)"), expr
						else:
							return ("PC", "@N(Rn)"), Expression.asOffset(expr)
			else:
				# Rn, -(Rn), expression(Rn), expression or #expression
				if self.needPunct("-", maybe=True):
					# -(Rn)
					t.noRollback()
					self.needPunct("(")
					reg = self.needRegister()
					self.needPunct(")")
					return (reg, "-(Rn)"), None
				elif self.needPunct("#", maybe=True):
					# #expression = (PC)+
					t.noRollback()
					expr = self.needExpression()
					return ("PC", "(Rn)+"), expr
				else:
					# Rn, expression(Rn) or expression
					reg = self.needRegister(maybe=True)
					if reg is not None:
						# Rn
						return (reg, "Rn"), None
					else:
						# expression(Rn) or expression
						t.noRollback()
						expr = self.needExpression()
						if self.needPunct("(", maybe=True):
							# expression(Rn)
							t.noRollback()
							reg = self.needRegister()
							self.needPunct(")")
							return (reg, "N(Rn)"), expr
						else:
							# expression = expression - ...(PC)
							return ("PC", "N(Rn)"), Expression.asOffset(expr)


	def needRegister(self, maybe=False):
		with Transaction(self, maybe=maybe, stage="register"):
			literal = self.needLiteral()
			if literal in registers:
				return literal
			else:
				raise InvalidError(
					"Expected register, got '{}'".format(literal)
				)


	def needExpression(self, isLabel=False, maybe=False):
		with Transaction(self, maybe=maybe, stage="expression") as t:
			if self.syntax == "pdp11asm":
				value = self.needValue(isLabel=isLabel)

				t.noRollback()

				while True:
					if self.needPunct("+", maybe=True):
						t.noRollback()
						value += self.needValue(isLabel=isLabel)
					elif self.needPunct("-", maybe=True):
						t.noRollback()
						value -= self.needValue(isLabel=isLabel)
					elif self.needPunct("*", maybe=True):
						t.noRollback()
						value *= self.needValue(isLabel=isLabel)
					elif self.needPunct("/", maybe=True):
						t.noRollback()
						value //= self.needValue(isLabel=isLabel)
					else:
						break

				value.isOffset = False
				return value
			else:
				raise NotImplementedError(
					"PDPY11 expression syntax is not implemented yet"
				)


	def needValue(self, isLabel=False, maybe=False):
		with Transaction(self, maybe=maybe, stage="value") as t:
			# Char (or two)
			string = self.needString(maybe=True)

			if string is not None:
				t.noRollback()
				if len(string) == 0:
					raise InvalidError(
						"#'string': expected 1 or 2 chars, got 0"
					)
				elif len(string) == 1:
					return Expression(ord(string[0]))
				elif len(string) == 2:
					a = ord(string[0])
					b = ord(string[1])
					if a >= 256 or b >= 256:
						raise InvalidError(
							"Cannot fit two UTF characters in 1 word: " +
							"'{}'".format(string)
						)
					return Expression(a | (b << 8))
				else:
					raise InvalidError(
						"Cannot fit {} characters in 1 word: '{}'".format(
							len(string), string
						)
					)

			# Integer
			integer = self.needInteger(maybe=True)
			if integer is not None:
				# Label?
				if isLabel:
					return Expression("{}@{}".format(self.last_label, integer))
				else:
					return Expression(integer)

			# . (dot)
			if self.needPunct(".", maybe=True):
				return self.mark()

			# Label
			label = self.needLiteral(maybe=True)
			if label is None:
				raise InvalidError("Expected integer, string, . (dot) or label")
			return Expression(label)



	def needLiteral(self, maybe=False):
		# Parse literal, starting with self.pos, and seek to
		# its end. Return the literal in upper case.

		with Transaction(self, maybe=maybe, stage="literal"):
			# Skip whitespace
			self.skipWhitespace()

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
		with Transaction(self, maybe=maybe, stage="sign '{}'".format(char)):
			# Skip whitespace
			self.skipWhitespace()

			if self.code[self.pos] == char:
				self.pos += 1
				return char
			else:
				raise InvalidError("Expected '{}', got '{}'".format(char, self.code[self.pos]))

	def needChar(self, char, maybe=False):
		with Transaction(self, maybe=maybe, stage="character '{}'".format(char)):
			try:
				if self.code[self.pos].upper() == char:
					self.pos += 1
					return char
				else:
					raise InvalidError("Expected '{}', got '{}'".format(char, self.code[self.pos]))
			except IndexError:
				raise InvalidError("Expected '{}', got EOF".format(char))


	def needInteger(self, maybe=False):
		# Parse integer, starting with self.pos, and seek to
		# its end. Return the integer in 'int' type.

		with Transaction(self, maybe=maybe, stage="integer") as t:
			# Skip whitespace
			self.skipWhitespace()

			integer = ""
			radix = None

			if self.needChar("+", maybe=True):
				integer = "+"
			elif self.needChar("-", maybe=True):
				integer = "-"

			while True:
				if self.needChar(".", maybe=True):
					# Decimal
					if integer == "":
						raise InvalidError("Expected integer, got '.'")
					elif radix is None:
						radix = 10
						break
					else:
						t.noRollback()
						raise InvalidError("Two (or more) radix specifiers")
				elif self.needChar("B", maybe=True):
					# Binary
					if integer != "0":
						raise InvalidError("Expected integer, got '{}b'".format(integer))
					else:
						if radix is None:
							radix = 2
							t.noRollback()
						else:
							t.noRollback()
							raise InvalidError("Two (or more) radix specifiers")
				elif self.needChar("O", maybe=True):
					# Octal
					if integer != "0":
						raise InvalidError("Expected integer, got '{}o'".format(integer))
					else:
						if radix is None:
							radix = 8
							t.noRollback()
						else:
							t.noRollback()
							raise InvalidError("Two (or more) radix specifiers")
				elif self.needChar("X", maybe=True):
					# Hexadimical
					if integer != "0":
						raise InvalidError("Expected integer, got '{}x'".format(integer))
					elif radix is None:
						radix = 16
						t.noRollback()
					else:
						t.noRollback()
						raise InvalidError("Two (or more) radix specifiers")
				else:
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

			try:
				return int(integer, radix)
			except ValueError:
				raise InvalidError("Expected integer, got '{}' (radix {})".format(integer, radix))


	def needRaw(self):
		# Return string till the end of the string (trimmed)

		with Transaction(self, maybe=False, stage="raw string (terminated by EOL)"):
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

		with Transaction(self, maybe=maybe, stage="string") as t:
			# Skip whitespace
			self.skipWhitespace()

			punct = ""
			if self.code[self.pos] in "\"'/":
				punct = self.code[self.pos]
				self.pos += 1
				t.noRollback()
			else:
				raise InvalidError("Expected string, got '{}'".format(self.code[self.pos]))

			string = ""

			while True:
				try:
					#if self.code[self.pos] == "\\":
					#	# Escape character
					#	self.pos += 1
					#
					#	if self.code[self.pos] in "nN":
					#		self.pos += 1
					#		string += "\n"
					#	elif self.code[self.pos] in "rR":
					#		self.pos += 1
					#		string += "\r"
					#	elif self.code[self.pos] in "tT":
					#		self.pos += 1
					#		string += "\t"
					#	elif self.code[self.pos] in "sS":
					#		self.pos += 1
					#		string += " "
					#	elif self.code[self.pos] in "xX":
					#		self.pos += 1
					#		num = self.code[self.pos]
					#		self.pos += 1
					#		num += self.code[self.pos]
					#		self.pos += 1
					#		string += chr(int(num, 16))
					#	elif self.code[self.pos] in "\\\"/":
					#		self.pos += 1
					#		string += self.code[self.pos]
					#	else:
					#		raise InvalidError("Expected \\n, \\r, \\t, \\s, \\\\, \\\", \\/ or \\xNN, got '\\{}'".format(self.code[self.pos]))
					if self.code[self.pos] == punct:
						# EOS
						self.pos += 1
						return string
					else:
						string += self.code[self.pos]
						self.pos += 1
				except IndexError:
					# EOF
					with Transaction(self, maybe=False):
						raise InvalidError("Expected string terminator, got EOF")


	def needBool(self, maybe=False):
		# Handle ON, OFF, TRUE, FALSE, YES, NO

		with Transaction(self, maybe=maybe, stage="boolean"):
			# Skip whitespace
			self.skipWhitespace()

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

	def isEOF(self):
		pos = self.pos

		# Skip whitespace
		try:
			self.skipWhitespace()
		except InvalidError:
			return True

		self.pos = pos
		return False

	def skipWhitespace(self):
		try:
			skipped = True
			while skipped:
				skipped = False

				# Skip whitespace
				while self.code[self.pos] in whitespace:
					skipped = True
					self.pos += 1

				# Skip ; comment
				if self.code[self.pos] == ";":
					# Comment
					skipped = True
					while self.code[self.pos] != "\n":
						self.pos += 1

				# Skip // comment
				if self.code[self.pos:self.pos + 2] == "//":
					# Comment
					skipped = True
					while self.code[self.pos] != "\n":
						self.pos += 1
		except IndexError:
			raise InvalidError("Got EOF")


	def getCurrentCommandCoords(self):
		# Position to line/col
		line = len(self.code[:self.cmd_start].split("\n"))
		try:
			last_lf = self.code[:self.cmd_start].rindex("\n")
		except ValueError:
			last_lf = 0
		col = self.cmd_start - last_lf

		return {
			"file": self.file,
			"line": line,
			"column": col,
			"text": self.code[self.cmd_start:self.pos].strip()
		}


class Transaction(object):
	def __init__(self, parser, maybe=False, stage=None):
		self.parser = parser
		self.maybe = maybe
		self.stage = stage

	def __enter__(self):
		self.pos = self.parser.pos
		self.allow_rollback = True
		self.parser.stage_stack.append(self.stage)
		self.exitted = False
		return self
	def __exit__(self, err_cls, err, traceback):
		stack = self.parser.stage_stack[:]
		if not self.exitted:
			self.parser.stage_stack.pop()

		if err_cls is None:
			# Success
			return
		elif isinstance(err, EndOfParsingError):
			# It doesn't make sense to parse further
			return False
		elif isinstance(err, InvalidError):
			# Could not parse token as ...
			if self.parser.last_error_stages is None:
				# Rollback to the place from which we couldn't match
				self.parser.pos = self.pos
				self.parser.last_error_stages = stack

			if self.maybe and self.allow_rollback:
				self.parser.pos = self.pos
				self.parser.last_error_stages = None
				return True
			else:
				return False
		else:
			# Some weird bug
			return False

	def reraise(self, exception):
		self.parser.last_error_stages = self.parser.stage_stack[:]
		raise exception

	def noRollback(self):
		# If encounter InvalidError, always reraise it
		self.allow_rollback = False

	def exit(self):
		if not self.exitted:
			self.parser.stage_stack.pop()
		self.exitted = True