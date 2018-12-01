from .util import R, A, D, I, SP


commands = {
	# Zero arguments
	"HALT":   ((    ), 0o000000),
	"WAIT":   ((    ), 0o000001),
	"RTI":    ((    ), 0o000002),
	"BPT":    ((    ), 0o000003),
	"IOT":    ((    ), 0o000004),
	"RESET":  ((    ), 0o000005),
	"RTT":    ((    ), 0o000006),
	"START":  ((    ), 0o000012),
	"STEP":   ((    ), 0o000016),
	"NOP":    ((    ), 0o000240),
	"CLC":    ((    ), 0o000241),
	"CLV":    ((    ), 0o000242),
	"CLZ":    ((    ), 0o000244),
	"CLN":    ((    ), 0o000250),
	"CCC":    ((    ), 0o000257),
	"SEC":    ((    ), 0o000261),
	"SEV":    ((    ), 0o000262),
	"SEZ":    ((    ), 0o000264),
	"SEN":    ((    ), 0o000270),
	"SCC":    ((    ), 0o000277),
	"RET":    ((    ), 0o000207), # RTS PC

	# One argument
	"JMP":    ((A,  ), 0o000100),
	"CALL":   ((A,  ), 0o004700), # JSR PC
	"SWAB":   ((A,  ), 0o000300),
	"CLR":    ((A,  ), 0o005000),
	"CLRB":   ((A,  ), 0o105000),
	"COM":    ((A,  ), 0o005100),
	"COMB":   ((A,  ), 0o105100),
	"INC":    ((A,  ), 0o005200),
	"INCB":   ((A,  ), 0o105200),
	"DEC":    ((A,  ), 0o005300),
	"DECB":   ((A,  ), 0o105300),
	"NEG":    ((A,  ), 0o005400),
	"NEGB":   ((A,  ), 0o105400),
	"ADC":    ((A,  ), 0o005500),
	"ADCB":   ((A,  ), 0o105500),
	"SBC":    ((A,  ), 0o005600),
	"SBCB":   ((A,  ), 0o105600),
	"TST":    ((A,  ), 0o005700),
	"TSTB":   ((A,  ), 0o105700),
	"ROR":    ((A,  ), 0o006000),
	"RORB":   ((A,  ), 0o106000),
	"ROL":    ((A,  ), 0o006100),
	"ROLB":   ((A,  ), 0o106100),
	"ASR":    ((A,  ), 0o006200),
	"ASRB":   ((A,  ), 0o106200),
	"ASL":    ((A,  ), 0o006300),
	"ASLB":   ((A,  ), 0o106300),
	"SXT":    ((A,  ), 0o006700),
	"MTPS":   ((A,  ), 0o106400),
	"MFPS":   ((A,  ), 0o106700),

	# Branch commands
	"BR":     ((D,  ), 0o000400),
	"BNE":    ((D,  ), 0o001000),
	"BEQ":    ((D,  ), 0o001400),
	"BGE":    ((D,  ), 0o002000),
	"BLT":    ((D,  ), 0o002400),
	"BGT":    ((D,  ), 0o003000),
	"BLE":    ((D,  ), 0o003400),
	"BPL":    ((D,  ), 0o100000),
	"BMI":    ((D,  ), 0o100400),
	"BHI":    ((D,  ), 0o101000),
	"BVS":    ((D,  ), 0o102400),
	"BVC":    ((D,  ), 0o102000),
	"BHIS":   ((D,  ), 0o103000),
	"BCC":    ((D,  ), 0o103000),
	"BLO":    ((D,  ), 0o103400),
	"BCS":    ((D,  ), 0o103400),
	"BLOS":   ((D,  ), 0o101400),

	# Immediate arguments
	"EMT":    ((I,  ), 0o104000, 0o377),
	"TRAP":   ((I,  ), 0o104400, 0o377),
	"MARK":   ((I,  ), 0o006400, 0o77 ),

	# Two arguments
	"MOV":    ((A, A), 0o010000),
	"CMP":    ((A, A), 0o020000),
	"BIT":    ((A, A), 0o030000),
	"BIC":    ((A, A), 0o040000),
	"BIS":    ((A, A), 0o050000),
	"ADD":    ((A, A), 0o060000),
	"MOVB":   ((A, A), 0o110000),
	"CMPB":   ((A, A), 0o120000),
	"BITB":   ((A, A), 0o130000),
	"BICB":   ((A, A), 0o140000),
	"BISB":   ((A, A), 0o150000),
	"SUB":    ((A, A), 0o160000),

	# Register and argument
	"JSR":    ((R, A), 0o004000),
	"MUL":    ((A, R), 0o070000),
	"DIV":    ((A, R), 0o071000),
	"ASH":    ((A, R), 0o072000),
	"ASHC":   ((A, R), 0o073000),
	"XOR":    ((R, A), 0o074000),

	# Misc
	"RTS":    ((R,  ), 0o000200),
	"SOB":    ((R, D), 0o077000)
}

def PUSH(a):
	yield "MOV", (a, A(SP, "-(Rn)"))
commands["PUSH"] = ((A,  ), PUSH)

def POP(a):
	yield "MOV", (A(SP, "(Rn)+"), a)
commands["POP"] = ((A,  ), POP)