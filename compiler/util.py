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