from __future__ import print_function
import os
import sys
from .commands import commands
from .deferred import Deferred
from .expression import Expression, StaticAlloc
import operator
from .util import raiseSyntaxError, encodeKoi8, A, R, D, I, PC


whitespace = "\n\r\t "
punctuation = ",!@#%^&*()[]\\{}|/~`'\";:?<>.+-="
registers = ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "SP", "PC")

operators = {}
for priority, (assoc, ops) in enumerate((
	("left",  (("|",  operator.or_   ),                                                     )),
	("left",  (("^",  operator.xor   ),                                                     )),
	("left",  (("&",  operator.and_  ),                                                     )),
	("left",  (("<<", operator.lshift), (">>", operator.rshift  )                           )),
	("left",  (("+",  operator.add   ), ("-",  operator.sub     )                           )),
	("left",  (("*",  operator.mul   ), ("/",  operator.floordiv), ("%",  operator.mod      )))
)):
	for char, op in ops:
		operators[char] = (priority, assoc, op)


class EndOfParsingError(Exception):
	pass
class InvalidError(Exception):
	pass

class Parser(object):
	last_mark = 0

	def __init__(self, file, code, syntax):
		self.code = code
		self.pos = 0
		self.cmd_start = 0
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

			stack = []
			for stage in self.last_error_stages:
				if stage is not None:
					stack.append(stage)
			raiseSyntaxError(self.file, line=line, column=col, stack=stack, error=e)

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
			elif literal in ("MAKE_BK0010_ROM", "MAKE_BIN"):
				yield self.handleMakeBin(), labels
				return
			elif literal == "MAKE_SAV":
				yield self.handleMakeSav(), labels
				return
			elif literal == "MAKE_TURBO_WAV":
				yield self.handleMakeTurboWav(), labels
				return
			elif literal == "MAKE_WAV":
				yield self.handleMakeWav(), labels
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
					elif literal == "DWORD":
						yield self.handleDword(), labels
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
					elif literal == "EXTERN":
						yield self.handleExtern(), labels
						return
					elif literal == "ONCE":
						yield self.handleOnce(), labels
						return
					else:
						raise InvalidError("Expected .COMMAND, got '.{command}'".format(command=literal))

			if literal is None:
				# Maybe integer label?
				label = self.needIntegerLabel()
				self.needPunct(":")

				# It's a label
				label = "{last_label}: {label}".format(last_label=self.last_label, label=label)
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
		label = ".{last_mark}".format(last_mark=Parser.last_mark)
		self.current_labels.append(label)
		Parser.last_mark += 1
		coords = self.getCurrentCommandCoords()
		return Expression(label, coords["file"], line=coords["line"], column=coords["column"])



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

	def handleDword(self):
		# .DWORD
		with Transaction(self, maybe=False, stage=".DWORD"):
			values = [self.needExpression()]
			while self.needPunct(",", maybe=True):
				values.append(self.needExpression())
			return ".DWORD", values

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

	def handleMakeSav(self):
		with Transaction(self, maybe=False, stage=".MAKE_SAV"):
			filename = self.needString(maybe=True)
			if filename is not None and self.needPunct(",", maybe=True):
				final_address = self.needExpression()
			else:
				final_address = None
			return ".MAKE_SAV", (filename, final_address)

	def handleMakeTurboWav(self):
		with Transaction(self, maybe=False, stage=".MAKE_TURBO_WAV"):
			real_filename = self.needString(maybe=True)
			if real_filename is not None and self.needPunct(",", maybe=True):
				bk_filename = self.needString()
			else:
				bk_filename = None
			return ".MAKE_TURBO_WAV", (real_filename, bk_filename)

	def handleMakeWav(self):
		with Transaction(self, maybe=False, stage=".MAKE_WAV"):
			real_filename = self.needString(maybe=True)
			if real_filename is not None and self.needPunct(",", maybe=True):
				bk_filename = self.needString()
			else:
				bk_filename = None
			return ".MAKE_WAV", (real_filename, bk_filename)

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

	def handleExtern(self):
		with Transaction(self, maybe=False, stage=".EXTERN"):
			extern = [self.needLiteral()]
			while self.needPunct(",", maybe=True):
				extern.append(self.needLiteral())

			return ".EXTERN", extern

	def handleOnce(self):
		return ".ONCE", None

	def handleCommand(self):
		self.skipWhitespace()

		with Transaction(self, maybe=False, stage="compilable command") as t:
			command_name = self.needLiteral()

			if command_name not in commands:
				raise InvalidError(
					"Expected command name, got '{command_name}'".format(command_name=command_name)
				)

			argtypes = commands[command_name][0]
			args = []
			for i, arg in enumerate(argtypes):
				if i != 0:
					self.needPunct(",")
				if arg is A:
					args.append(self.needArgument())
				elif arg is D:
					args.append(D(self.needExpression(isLabel=True)))
				elif arg is I:
					args.append(I(self.needExpression()))
				elif arg is R:
					args.append(self.needRegister())
			return command_name, tuple(args)


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
					return A(reg, "(Rn)+")
				else:
					# (Rn)
					return A(reg, "(Rn)")
			elif self.needPunct("@", maybe=True):
				# @Rn, @(Rn)+, @-(Rn), @expression(Rn), @(Rn), @#expression or
				# @expression

				expr = self.needExpression(maybe=True)
				if expr is not None:
					# @expression(Rn) or @expression
					t.noRollback()

					if self.needPunct("(", maybe=True):
						# @expression(Rn)
						t.noRollback()
						reg = self.needRegister()
						self.needPunct(")")
						return A(reg, "@N(Rn)", expr)
					else:
						# @expression
						if self.syntax == "pdp11asm":
							# PDP11Asm bug
							return A(PC, "@N(Rn)", expr)
						else:
							return A(PC, "@N(Rn)", Expression.asOffset(expr))
				elif self.needPunct("#", maybe=True):
					# @#expression = @(PC)+
					t.noRollback()
					expr = self.needExpression()
					return A(PC, "@(Rn)+", expr)
				elif self.needPunct("(", maybe=True):
					# @(Rn)+ or @(Rn)
					t.noRollback()
					reg = self.needRegister()
					self.needPunct(")")
					if self.needPunct("+", maybe=True):
						# @(Rn)+
						return A(reg, "@(Rn)+")
					else:
						# @0(Rn)
						coords = self.getCurrentCommandCoords()
						return A(reg, "@N(Rn)", Expression(
							0, self.file,
							line=coords["line"],
							column=coords["column"]
						))
				elif self.needPunct("-", maybe=True):
					# @-(Rn)
					t.noRollback()
					self.needPunct("(")
					reg = self.needRegister()
					self.needPunct(")")
					return A(reg, "@-(Rn)")
				else:
					# @Rn = (Rn)
					reg = self.needRegister()
					return A(reg, "(Rn)")
			else:
				# Rn, -(Rn), expression(Rn), expression or #expression
				expr = self.needExpression(maybe=True)
				if expr is not None:
					# expression(Rn) or expression
					t.noRollback()
					if self.needPunct("(", maybe=True):
						# expression(Rn)
						t.noRollback()
						reg = self.needRegister()
						self.needPunct(")")
						return A(reg, "N(Rn)", expr)
					else:
						# expression = expression - ...(PC)
						return A(PC, "N(Rn)", Expression.asOffset(expr))
				elif self.needPunct("-", maybe=True):
					# -(Rn)
					t.noRollback()
					self.needPunct("(")
					reg = self.needRegister()
					self.needPunct(")")
					return A(reg, "-(Rn)")
				elif self.needPunct("#", maybe=True):
					# #expression = (PC)+
					t.noRollback()
					expr = self.needExpression()
					return A(PC, "(Rn)+", expr)
				else:
					# Rn
					reg = self.needRegister()
					return A(reg, "Rn")


	def needRegister(self, maybe=False):
		with Transaction(self, maybe=maybe, stage="register"):
			literal = self.needLiteral(maybe=True)
			if not literal:
				raise InvalidError("Expected register")
			elif literal not in registers:
				raise InvalidError(
					"Expected register, got '{register}'".format(register=literal)
				)
			else:
				return R(literal)


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
				if isLabel:
					# First, analyze the expression. If it doesn't contain any
					# brackets, we treat the first integer as a label and
					# everything that follows as a number (Macro-11-compatible
					# mode). If there ARE brackets, we treat all integers as
					# numbers, and local labels must have a suffix of ":".

					has_brackets = False

					with Transaction(self, maybe=True):
						while True:
							if self.needPunct("(", maybe=True):
								has_brackets = True
								break

							# Try reading value
							self.needValue(isLabel=isLabel)

							# Get operator
							cur_char = self.needOperator(maybe=True)
							if cur_char is None:
								# Syntax error, handled later
								break
						raise InvalidError("Rollback")

					if has_brackets:
						# Labels must use ":" suffix
						isLabel = False



				def execute(char):
					_, _, op = operators[char]
					b = stack.pop()
					a = stack.pop()
					stack.append(op(a, b))

				stack = []
				op_stack = []

				while True:
					# Math opening bracket
					while self.needPunct("(", maybe=True):
						op_stack.append("(")

					# Really read value
					value = self.needValue(isLabel=isLabel)
					stack.append(value)
					if isinstance(value, Deferred):
						# Only the first label is treated as a label
						isLabel = False

					# Match closing bracket
					while "(" in op_stack and self.needPunct(")", maybe=True):
						while len(op_stack) > 0:
							top = op_stack.pop()
							if top == "(":
								break
							else:
								execute(top)
						else:
							raise InvalidError("Unmatched ')'")

					# Get operator
					cur_char = self.needOperator(maybe=True)
					if cur_char is None:
						break
					cur_priority, cur_assoc, cur_op = operators[cur_char]

					while len(op_stack) > 0:
						top_char = op_stack[-1]
						if top_char == "(":
							break
						top_priority, top_assoc, top_op = operators[top_char]

						if top_priority < cur_priority:
							# If stack top priority is less than new priority,
							# break
							break
						elif top_priority > cur_priority:
							# If stack top priority is more than new priority,
							# pop from stack top
							execute(op_stack.pop())
						else:
							# If stack top priority equals new priority, pop
							# from stack top if the operator is left-associative,
							# and break if it's right-associative
							if top_assoc == "left":
								execute(op_stack.pop())
							else:
								break

					# Push current operator onto stack
					op_stack.append(cur_char)

				while len(op_stack) > 0:
					top = op_stack.pop()
					if top == "(":
						raise InvalidError("Unmatched '('")
					else:
						execute(top)

				return stack.pop()


	def needOperator(self, maybe=False):
		with Transaction(self, maybe=maybe, stage="operator") as t:
			operator_list = sorted(operators.keys(), key=len, reverse=True)
			for operator in operator_list:
				if self.needPunct(operator, maybe=True):
					return operator
			raise InvalidError("Expected operator")

	def needValue(self, isLabel=False, maybe=False):
		with Transaction(self, maybe=maybe, stage="value") as t:
			# Char (or two)
			string = self.needString(maybe=True)
			coords = self.getCurrentCommandCoords()

			if string is not None:
				t.noRollback()
				try:
					bts = encodeKoi8(string)
				except UnicodeEncodeError:
					raise InvalidError(
						"#'string': cannot encode string to KOI8-R"
					)
				if len(bts) == 0:
					raise InvalidError(
						"#'string': expected 1 or 2 chars, got 0"
					)
				elif len(bts) == 1:
					return Expression(
						ord(bts[0]) if sys.version_info[0] == 2 else bts[0],
						coords["file"],
						line=coords["line"],
						column=coords["column"]
					)
				elif len(bts) == 2:
					a, b = map(ord, bts) if sys.version_info[0] == 2 else bts
					if a >= 256 or b >= 256:
						raise InvalidError(
							"Cannot fit two UTF characters in 1 word: " +
							"'{string}'".format(string=string)
						)
					return Expression(
						a | (b << 8),
						coords["file"],
						line=coords["line"],
						column=coords["column"]
					)
				else:
					raise InvalidError(
						("Cannot fit {len} characters in 1 word: " +
						"'{string}'").format(
							len=len(string), string=string
						)
					)

			# Integer / local label
			if isLabel:
				local_label = self.needIntegerLabel(maybe=True)
				if local_label is not None:
					return Expression(
						"{last_label}: {local_label}".format(last_label=self.last_label, local_label=local_label),
						coords["file"],
						line=coords["line"],
						column=coords["column"]
					)
			else:
				# Try to get an integer label. If it is an integer itself,
				# there must be a colon next to it to be handled as a label
				with Transaction(self, maybe=True):
					local_label = self.needIntegerLabel()
					# Handle raw integers (e.g. 123) which shouldn't be labels
					# by default, as well as 0x..., 0b... and 0o... labels which
					# are most likely meant to be integers
					if (
						local_label.isdigit() or
						local_label.lower().startswith("0x") or
						local_label.lower().startswith("0b") or
						local_label.lower().startswith("0o")
					):
						self.needPunct(":")
					return Expression(
						"{last_label}: {local_label}".format(last_label=self.last_label, local_label=local_label),
						coords["file"],
						line=coords["line"],
						column=coords["column"]
					)

			# Integer
			integer = self.needInteger(maybe=True)
			if integer is not None:
				return Expression(
					integer,
					coords["file"],
					line=coords["line"],
					column=coords["column"]
				)

			# . (dot)
			if self.needPunct(".", maybe=True):
				return self.mark()

			# STATIC_ALLOC[_BYTE]
			literal = self.needLiteral(maybe=True)
			if literal == "STATIC_ALLOC" or literal == "STATIC_ALLOC_BYTE":
				t.noRollback()
				with Transaction(self, maybe=False, stage=literal):
					self.needPunct("(")
					length = self.needExpression()
					self.needPunct(")")
					return StaticAlloc(length, literal == "STATIC_ALLOC_BYTE")

			# Label
			if literal is None or literal in registers:
				raise InvalidError("Expected integer, string, . (dot), label or STATIC_ALLOC[_BYTE]")
			return Expression(
				literal,
				coords["file"],
				line=coords["line"],
				column=coords["column"]
			)



	def needLiteral(self, maybe=False):
		# Parse literal, starting with self.pos, and seek to
		# its end. Return the literal in upper case.

		with Transaction(self, maybe=maybe, stage="literal"):
			# Skip whitespace
			self.skipWhitespace(allow_eof=False)

			literal = ""

			while True:
				try:
					if self.code[self.pos] in whitespace + punctuation:
						# Punctuation or whitespace
						if literal == "":
							raise InvalidError("Expected literal, got '{char}'".format(char=self.code[self.pos]))
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
					raise InvalidError("Expected literal, got '{char}'".format(char=self.code[self.pos]))


	def needPunct(self, char, maybe=False):
		with Transaction(self, maybe=maybe, stage="sign '{char}'".format(char=char)):
			# Skip whitespace
			self.skipWhitespace()

			if self.isEOF():
				raise InvalidError("Expected '{exp}', got EOF".format(exp=char))
			elif self.code[self.pos] == char:
				self.pos += 1
				return char
			else:
				raise InvalidError("Expected '{exp}', got '{char}'".format(exp=char, char=self.code[self.pos]))

	def needChar(self, char, maybe=False):
		with Transaction(self, maybe=maybe, stage="character '{char}'".format(char=char)):
			try:
				if self.code[self.pos].upper() == char:
					self.pos += 1
					return char
				else:
					raise InvalidError("Expected '{exp}', got '{char}'".format(exp=char, char=self.code[self.pos]))
			except IndexError:
				raise InvalidError("Expected '{char}', got EOF".format(char=char))


	def needIntegerLabel(self, maybe=False):
		with Transaction(self, maybe=maybe, stage="local label") as t:
			# Skip whitespace
			self.skipWhitespace()

			# Try to get digit
			label = ""
			try:
				if self.code[self.pos] in "0123456789":
					label += self.code[self.pos]
					self.pos += 1
				else:
					raise InvalidError("Expected digit, got '{char}'".format(char=self.code[self.pos]))
			except IndexError:
				raise InvalidError("Expected digit, got EOF")

			# Get all the literal left
			while True:
				try:
					if self.code[self.pos] in whitespace + punctuation:
						# Punctuation or whitespace
						break
				except IndexError:
					# End
					break

				if self.code[self.pos].upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_$0123456789":
					label += self.code[self.pos].upper()
					self.pos += 1
				else:
					raise InvalidError("Expected literal, got '{char}'".format(char=self.code[self.pos]))

			return label


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

				if radix is None:
					if self.needChar("B", maybe=True):
						# Binary
						if integer != "0":
							raise InvalidError("Expected integer, got '{int}b'".format(int=integer))
						else:
							radix = 2
							t.noRollback()
							continue
					elif self.needChar("O", maybe=True):
						# Octal
						if integer != "0":
							raise InvalidError("Expected integer, got '{int}o'".format(int=integer))
						else:
							radix = 8
							t.noRollback()
							continue
					elif self.needChar("X", maybe=True):
						# Hexadimical
						if integer != "0":
							raise InvalidError("Expected integer, got '{int}x'".format(int=integer))
						else:
							radix = 16
							t.noRollback()
							continue

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
					raise InvalidError("Expected integer, got '{char}'".format(char=self.code[self.pos]))

			if radix is None:
				radix = 10 if self.decimal else 8

			try:
				return int(integer, radix)
			except ValueError:
				raise InvalidError("Expected integer, got '{int}' (radix {radix})".format(int=integer, radix=radix))


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
			mapped_at_least_once = False
			string = ""

			while True:
				# Skip whitespace
				self.skipWhitespace()

				if self.needChar("<", maybe=True):
					# Raw code
					code = self.needInteger()
					string += chr(code)
					self.needChar(">")
					mapped_at_least_once = True
					continue

				if self.isEOF():
					if mapped_at_least_once:
						return string
					else:
						raise InvalidError("Expected string, got EOF")

				punct = ""
				if self.code[self.pos] in "\"'/":
					punct = self.code[self.pos]
					self.pos += 1
					t.noRollback()
				else:
					if mapped_at_least_once:
						return string
					else:
						raise InvalidError("Expected string, got '{char}'".format(char=self.code[self.pos]))

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
						#		raise InvalidError("Expected \\n, \\r, \\t, \\s, \\\\, \\\", \\/ or \\xNN, got '\\{escape}'".format(escape=self.code[self.pos]))
						if self.code[self.pos] == punct:
							# End of string
							self.pos += 1
							mapped_at_least_once = True
							break
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
				raise InvalidError("Expected boolean, got '{boolean}'".format(boolean=lit))
			else:
				try:
					raise InvalidError("Expected boolean, got '{boolean}'".format(boolean=self.code[self.pos]))
				except IndexError:
					raise InvalidError("Expected boolean, got EOF")

	def isEOF(self):
		pos = self.pos

		# Skip whitespace
		try:
			self.skipWhitespace(allow_eof=False)
		except InvalidError:
			return True

		self.pos = pos
		return False

	def skipWhitespace(self, allow_eof=True):
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
			if not allow_eof:
				raise InvalidError("Unexpected EOF")


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