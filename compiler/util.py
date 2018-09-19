from __future__ import print_function
import sys
from .deferred import Deferred

def encodeBinRaw(isBin, raw, link_address):
	if isBin:
		header = [
			link_address & 0xFF,
			link_address >> 8,
			len(raw) & 0xFF,
			len(raw) >> 8
		]
	else:
		header = []

	if sys.version_info[0] == 2:
		# Python 2
		return "".join([chr(char) for char in header + raw])
	else:
		# Python 3
		return bytes(header + raw)


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