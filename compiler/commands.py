zero_arg_commands = {
	"HALT": 0,
	"WAIT": 1,
	"RTI": 2,
	"BPT": 3,
	"IOT": 4,
	"RESET": 5,
	"RTT": 6,
	"START": 0o12,
	"STEP": 0o16,
	"NOP": 0o240,
	"CLC": 0o241,
	"CLV": 0o242,
	"CLZ": 0o244,
	"CLN": 0o250,
	"CCC": 0o257,
	"SEC": 0o261,
	"SEV": 0o262,
	"SEZ": 0o264,
	"SEN": 0o270,
	"SCC": 0o277,
	"RET": 0o207 # RTS PC
}

one_arg_commands = {
	"JMP": 0o0001,
	"CALL": 0o0047, # JSR PC
	"SWAB": 0o0003,
	"CLR": 0o0050,
	"CLRB": 0o1050,
	"COM": 0o0051,
	"COMB": 0o1051,
	"INC": 0o0052,
	"INCB": 0o1052,
	"DEC": 0o0053,
	"DECB": 0o1053,
	"NEG": 0o0054,
	"NEGB": 0o1054,
	"ADC": 0o0055,
	"ADCB": 0o1055,
	"SBC": 0o0056,
	"SBCB": 0o1056,
	"TST": 0o0057,
	"TSTB": 0o1057,
	"ROR": 0o0060,
	"RORB": 0o1060,
	"ROL": 0o0061,
	"ROLB": 0o1061,
	"ASR": 0o0062,
	"ASRB": 0o1062,
	"ASL": 0o0063,
	"ASLB": 0o1063,
	"SXT": 0o0067,
	"MTPS": 0o1064,
	"MFPS": 0o1067
}

jmp_commands = {
	"BR": 0o0004,
	"BNE": 0o0010,
	"BEQ": 0o0014,
	"BGE": 0o0020,
	"BLT": 0o0024,
	"BGT": 0o0030,
	"BLE": 0o0034,
	"BPL": 0o1000,
	"BMI": 0o1004,
	"BHI": 0o1010,
	"BVS": 0o1020,
	"BVC": 0o1024,
	"BHI": 0o1030,
	"BCC": 0o1030,
	"BLO": 0o1034,
	"BCS": 0o1034,
	"BLOS": 0o1014
}

imm_arg_commands = {
	"EMT": (0o104000, 0o377),
	"TRAP": (0o104400, 0o377),
	"MARK": (0o006400, 0o77)
}

two_arg_commands = {
	"MOV": 0o010000,
	"CMP": 0o020000,
	"BIT": 0o030000,
	"BIC": 0o040000,
	"BIS": 0o050000,
	"ADD": 0o060000,
	"MOVB": 0o110000,
	"CMPB": 0o120000,
	"BITB": 0o130000,
	"BICB": 0o140000,
	"BISB": 0o150000,
	"SUB": 0o160000
}

reg_commands = {
	"JSR": 0o004000,
	"XOR": 0o074000
}