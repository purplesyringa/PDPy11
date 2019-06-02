def u16(n):
	return [n & 255, n >> 8]

H, HS, L = 208, 200, 48
ONE = [HS, HS, L, L] + [H] * 4 + [L] * 4
ZERO = [HS, HS, L, L] + [H] * 2 + [L] * 2
SYNC = [HS, HS, L, L] * 4096 + [HS] * 8 + [L] * 8 + [H] * 4 + [L] * 4 + [HS, HS, L, L] * 10 + [HS] * 8 + [L] * 8 + [H] * 4 + [L] * 4
PAUSE = [HS, HS, L, L] * 10 + [HS] * 8 + [L] * 8 + [H] * 4 + [L] * 4
EOF = [HS, HS, L, L] * 200

def _encodeRaw(data):
	raw_data = []
	for byte in data:
		for _ in range(8):
			bit = byte & 1
			byte >>= 1
			raw_data += ONE if bit == 1 else ZERO
	return raw_data

def _encodeWav(data, sample_rate):
	total_size = 36 + len(data)
	return [
		82, 73, 70, 70,               # "RIFF"
		total_size & 0xFF,            # chunk size
		(total_size >> 8) & 0xFF,
		(total_size >> 16) & 0xFF,
		(total_size >> 24) & 0xFF,
		87, 65, 86, 69,               # "WAVE"
		102, 109, 116, 32,            # "fmt "
		16, 0, 0, 0,                  # sub chunk 1 size (always 16)
		1, 0,                         # PCM format
		1, 0,                         # channel count
		sample_rate & 0xFF,           # sample rate in samples
		(sample_rate >> 8) & 0xFF,
		(sample_rate >> 16) & 0xFF,
		(sample_rate >> 24) & 0xFF,
		sample_rate & 0xFF,           # sample rate in bytes
		(sample_rate >> 8) & 0xFF,
		(sample_rate >> 16) & 0xFF,
		(sample_rate >> 24) & 0xFF,
		1, 0,                         # block align
		8, 0,                         # sound depth (8 bits)
		100, 97, 116, 97,             # "data" in ASCII
		len(data) & 0xFF,             # size of 1st subchunk
		(len(data) >> 8) & 0xFF,
		(len(data) >> 16) & 0xFF,
		(len(data) >> 24) & 0xFF
	] + data

def encodeWav(link_address, bk_filename, raw):
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
	# Checksum
	checksum = 0
	for c in raw:
		checksum += c
		checksum += checksum >> 16
		checksum &= 2 ** 16 - 1
	wav_data += _encodeRaw(u16(checksum))
	# EOF
	wav_data += EOF

	return _encodeWav(wav_data, 21428)