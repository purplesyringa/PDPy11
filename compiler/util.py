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