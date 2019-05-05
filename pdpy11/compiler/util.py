from __future__ import print_function
import sys
from .deferred import Deferred
from .turbowav import encodeTurboWav

def encodeBinRawSavWav(output_format, raw, link_address):
	if output_format == "bin":
		raw = [
			link_address & 0xFF,
			link_address >> 8,
			len(raw) & 0xFF,
			len(raw) >> 8
		] + raw
	elif output_format == "sav":
		raw = [0] * 32 + [
			link_address & 0xFF,
			link_address >> 8,
			0o1000 & 0xFF,
			0o1000 >> 8,
			0,
			0,
			0,
			0,
			(link_address + len(raw)) & 0xFF,
			(link_address + len(raw)) >> 8
		] + [0] * 214 + [0] * (link_address - 256) + raw
	elif output_format.startswith("turbo-wav:"):
		bk_filename = output_format[len("turbo-wav:"):]
		raw = encodeTurboWav(link_address, bk_filename, raw)

	if sys.version_info[0] == 2:
		# Python 2
		return "".join([chr(char) for char in raw])
	else:
		# Python 3
		return bytes(raw)


def int8ToUint8(int8):
	if isinstance(int8, Deferred):
		return Deferred.If(
			int8 < 0,
			int8 + 256,
			int8
		)
	else:
		if int8 < 0:
			return int8 + 256
		else:
			return int8



def octal(n):
	# Compatible with Python 2 and Python 3
	return oct(int(n))[1:].replace("o", "")


error_mode_sublime = False

def raiseSyntaxError(file, line, column, stack=[], error=None):
	if error_mode_sublime:
		print("{file}:::{line}:::{column}:::{error}".format(
			file=file,
			line=line,
			column=column,
			error=error
		))
	else:
		print("Syntax error")
		if error is not None:
			print(error)
		print("  at file", file, "(line {line}, column {column})".format(line=line, column=column))
		for stage in stack:
			print("  at", stage)
	raise SystemExit(1)

def raiseCompilerError(text, coords):
	if error_mode_sublime:
		print("{file}:::{line}:::{column}:::{error}".format(
			file=coords["file"],
			line=coords["line"],
			column=coords["column"],
			error=text
		))
	else:
		print(text)
		print("  at file {file} (line {line}, column {column})".format(
			file=coords["file"],
			line=coords["line"],
			column=coords["column"]
		))
		print()
		print(coords["text"])
	raise SystemExit(1)

def raiseExpressionEvaluateError(file, line, column, text):
	if error_mode_sublime:
		print("{file}:::{line}:::{column}:::{error}".format(
			file=file,
			line=line,
			column=column,
			error=text
		))
	else:
		print(text)
		print("  at file {file} (line {line}, column {column})".format(
			file=file,
			line=line,
			column=column
		))
	raise SystemExit(1)

def setErrorMode(sublime=True):
	global error_mode_sublime
	error_mode_sublime = sublime



class A(object):
	def __init__(self, reg, mode, imm=None):
		self.reg = reg
		self.mode = mode
		self.imm = imm
	def __str__(self):
		return self.mode.replace("Rn", str(self.reg)).replace("N", "({imm!r})".format(imm=self.imm))
	def __repr__(self):
		return str(self)
class D(object):
	def __init__(self, addr):
		self.addr = addr
	def __str__(self):
		return "D({addr!r})".format(addr=self.addr)
	def __repr__(self):
		return str(self)
class I(object):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return "I({value!r})".format(value=self.value)
	def __repr__(self):
		return str(self)
class R(object):
	cache = {}
	def __new__(cls, *names):
		for name in names:
			if name in cls.cache:
				inst = cls.cache[name]
				break
		else:
			inst = object.__new__(cls)
		for name in names:
			cls.cache[name] = inst
		return inst
	def __init__(self, *names):
		self.name = names[0]
	def __str__(self):
		return self.name
	def __repr__(self):
		return str(self)
# Generate all registers
R0, R1, R2, R3, R4, R5 = R("R0"), R("R1"), R("R2"), R("R3"), R("R4"), R("R5")
R6, R7 = R("SP", "R6"), R("PC", "R7")
SP, PC = R6, R7