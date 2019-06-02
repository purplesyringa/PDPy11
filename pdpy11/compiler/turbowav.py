from .wav import u16, H, HS, L, _encodeWav

ONE = [H, H, H, L, L]
ZERO = [H, L, L]
SYNC = [HS, HS, HS, L, L, L] * 1024 + [HS] * 12 + [L] * 12
PAUSE = [L, L, L, L]
EOF = [HS] * 3 + [L] * 3 + [HS] * 3 + [L] * 3

def _encodeRaw(data):
	raw_data = []
	for byte in data:
		for _ in range(8):
			bit = byte & 1
			byte >>= 1
			raw_data += ONE if bit == 1 else ZERO
	return raw_data

def encodeTurboWav(link_address, bk_filename, raw):
	wav_data = []

	# Sync
	wav_data += SYNC
	# Header
	header = u16(link_address)
	header += u16(len(raw))
	header += [ord(x) for x in bk_filename.ljust(16)[:16]]
	wav_data += _encodeRaw(header)
	# Pause
	wav_data += PAUSE
	# File data
	wav_data += _encodeRaw(raw)
	# A small pause
	wav_data += PAUSE
	# Checksum
	checksum = 0
	for c in raw:
		checksum += c
		checksum += checksum >> 16
		checksum &= 2 ** 16 - 1
	wav_data += _encodeRaw(u16(checksum))
	# EOF
	wav_data += EOF

	return _encodeWav(wav_data, 40000)