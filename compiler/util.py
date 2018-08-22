from .deferred import Deferred

def encodeBinRaw(isBin, compiler):
	raw = compiler.output
	if isBin:
		return bytes([
			compiler.link_address & 0xFF,
			compiler.link_address >> 8,
			len(raw) & 0xFF,
			len(raw) >> 8
		]) + raw
	else:
		return raw


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
	return oct(int(n)).replace("0o", "")