from __future__ import print_function
import sys
import os
from .deferred import Deferred
from .turbowav import encodeTurboWav
from .wav import encodeWav

def encodeBinRawSavWav(output_format, args, raw, link_address):
	if output_format == "bin":
		raw = [
			link_address & 0xFF,
			link_address >> 8,
			len(raw) & 0xFF,
			len(raw) >> 8
		] + raw
	elif output_format == "sav":
		final_address = args[0] if len(args) >= 1 else link_address + len(raw)
		block_start = link_address // 512
		block_end = (final_address + 511) // 512
		raw = [0] * 32 + [
			link_address & 0xFF,
			link_address >> 8,
			0o1000 & 0xFF,
			0o1000 >> 8,
			0,
			0,
			0,
			0,
			final_address & 0xFF,
			final_address >> 8
		] + [0] * 198 + [
			sum(((block_start <= ((7 - j) + i * 8) < block_end) << j for j in range(8)))
			for i in range(16)
		] + [0] * 256 + raw
	elif output_format.startswith("turbo-wav:"):
		bk_filename = output_format[len("turbo-wav:"):]
		raw = encodeTurboWav(link_address, bk_filename, raw)
	elif output_format.startswith("wav:"):
		bk_filename = output_format[len("wav:"):]
		raw = encodeWav(link_address, bk_filename, raw)

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


def encodeKoi8(string):
	if sys.version_info[0] == 2:
		return string.decode("utf8").encode("koi8-r")
	else:
		return string.encode("koi8-r")


def octal(n):
	# Compatible with Python 2 and Python 3
	return oct(int(n))[1:].replace("o", "")



def open_device(name, mode="r"):
	if name == "~speaker":
		# A special file-like object
		class Speaker:
			def __init__(self):
				self.audio = b""
			def write(self, bytes):
				self.audio += bytes
			def close(self):
				# Yeah, we have to make it crossplatform
				if sys.platform == "win32":
					import winsound
					winsound.PlaySound(self.audio, winsound.SND_MEMORY)
				elif sys.platform.startswith("linux"):
					def f(n):
						return ord(n) if isinstance(n, str) else n
					sample_rate = 0
					sample_rate |= f(self.audio[24])
					sample_rate |= f(self.audio[25]) << 8
					sample_rate |= f(self.audio[26]) << 16
					sample_rate |= f(self.audio[27]) << 24
					raw = self.audio[44:]

					try:
						os.stat("/dev/dsp")
						# Worked, using OSS
						import ossaudiodev
						with ossaudiodev.open("w") as audio:
							audio.setfmt(ossaudiodev.AFMT_U8)
							audio.channels(1)
							audio.speed(sample_rate)
							audio.write(raw)
					except IOError:
						# Didn't work, using PulseAudio
						import ctypes
						import struct
						class Spec(ctypes.Structure):
							_fields_ = (
								("format", ctypes.c_int),
								("rate", ctypes.c_uint32),
								("channels", ctypes.c_uint8)
							)
						spec = Spec(0, sample_rate, 1)
						pa = ctypes.cdll.LoadLibrary("libpulse-simple.so.0")
						s = pa.pa_simple_new(None, "PDPy11", 1, None, "PDPy11", ctypes.byref(spec), None, None, None)
						pa.pa_simple_write(s, raw, len(raw), None)
						pa.pa_simple_drain(s)
						pa.pa_simple_free(s)
				elif sys.platform == "darwin":
					import subprocess
					import tempfile
					path = tempfile.mktemp()
					with open(path, "w") as f:
						f.write(self.audio)
					subprocess.Popen(["afplay", "-q", "1", path]).wait()
					os.unlink(path)
			def __enter__(self):
				return self
			def __exit__(self, err_cls, err, traceback):
				self.close()
				return False
		return Speaker()
	else:
		return open(name, mode)


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
