zero_arg_commands = {
	"HALT":   0o000000,
	"WAIT":   0o000001,
	"RTI":    0o000002,
	"BPT":    0o000003,
	"IOT":    0o000004,
	"RESET":  0o000005,
	"RTT":    0o000006,
	"START":  0o000012,
	"STEP":   0o000016,
	"NOP":    0o000240,
	"CLC":    0o000241,
	"CLV":    0o000242,
	"CLZ":    0o000244,
	"CLN":    0o000250,
	"CCC":    0o000257,
	"SEC":    0o000261,
	"SEV":    0o000262,
	"SEZ":    0o000264,
	"SEN":    0o000270,
	"SCC":    0o000277,
	"RET":    0o000207 # RTS PC
}

one_arg_commands = {
	"JMP":    0o000100,
	"CALL":   0o004700, # JSR PC
	"SWAB":   0o000300,
	"CLR":    0o005000,
	"CLRB":   0o105000,
	"COM":    0o005100,
	"COMB":   0o105100,
	"INC":    0o005200,
	"INCB":   0o105200,
	"DEC":    0o005300,
	"DECB":   0o105300,
	"NEG":    0o005400,
	"NEGB":   0o105400,
	"ADC":    0o005500,
	"ADCB":   0o105500,
	"SBC":    0o005600,
	"SBCB":   0o105600,
	"TST":    0o005700,
	"TSTB":   0o105700,
	"ROR":    0o006000,
	"RORB":   0o106000,
	"ROL":    0o006100,
	"ROLB":   0o106100,
	"ASR":    0o006200,
	"ASRB":   0o106200,
	"ASL":    0o006300,
	"ASLB":   0o106300,
	"SXT":    0o006700,
	"MTPS":   0o106400,
	"MFPS":   0o106700
}

jmp_commands = {
	"BR":     0o000400,
	"BNE":    0o001000,
	"BEQ":    0o001400,
	"BGE":    0o002000,
	"BLT":    0o002400,
	"BGT":    0o003000,
	"BLE":    0o003400,
	"BPL":    0o100000,
	"BMI":    0o100400,
	"BHI":    0o101000,
	"BVS":    0o102000,
	"BVC":    0o102400,
	"BHIS":   0o103000,
	"BCC":    0o103000,
	"BLO":    0o103400,
	"BCS":    0o103400,
	"BLOS":   0o101400
}

imm_arg_commands = {
	"EMT":    (0o104000, 0o377),
	"TRAP":   (0o104400, 0o377),
	"MARK":   (0o006400, 0o77)
}

two_arg_commands = {
	"MOV":    0o010000,
	"CMP":    0o020000,
	"BIT":    0o030000,
	"BIC":    0o040000,
	"BIS":    0o050000,
	"ADD":    0o060000,
	"MOVB":   0o110000,
	"CMPB":   0o120000,
	"BITB":   0o130000,
	"BICB":   0o140000,
	"BISB":   0o150000,
	"SUB":    0o160000
}

reg_commands = {
	"JSR":    0o004000,
	"XOR":    0o074000
}