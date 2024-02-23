import subprocess
import time

# this is an example code that increments $s0 from 1 to 10, then stores the value in memory
code = [
	"addi $s0, $zero, 1", # start from 1
	"addi $t0, $zero, 10", # stop at 10
	
	"beq $s0, $t0, 8", # if $s0 is 10, go to instruction 5 (current + (8/4)+1)
	"addi $s0, $s0, 1", # else increment by 1
	"j 2", # let's try now, go to instruction 2 (third line)
	"add $t0, $zero, $zero", # set $t0 to 0
	
	"sw $s0, 0($zero)" # stores the value in memory at location 0
]

regs = [0]*32 # set all registers to 0
pc = 0 # set current PC to 0
inst_memory = [] # contains istructions (1 instruction = 4 bytes)
data_memory = [0]*64 # memory of 64 bytes

regs_def = {
	"$zero":0,
	"$at":1,
	"$v0":2,
	"$v1":3,
	"$a0":4,
	"$a1":5,
	"$a2":6,
	"$a3":7,
	"$t0":8,
	"$t1":9,
	"$t2":10,
	"$t3":11,
	"$t4":12,
	"$t5":13,
	"$t6":14,
	"$t7":15,
	"$s0":16,
	"$s1":17,
	"$s2":18,
	"$s3":19,
	"$s4":20,
	"$s5":21,
	"$s6":22,
	"$s7":23,
	"$t8":24,
	"$t9":25,
	"$k0":26,
	"$k1":27,
	"$gp":28,
	"$sp":29,
	"$fp":30,
	"$ra":31
}
insts_def = {
	"and":"000000{0:05b}{1:05b}{2:05b}00000100100",
	"or":"000000{0:05b}{1:05b}{2:05b}00000100101",
	"add":"000000{0:05b}{1:05b}{2:05b}00000100000",
	"sub":"000000{0:05b}{1:05b}{2:05b}00000100010",
	"slt":"000000{0:05b}{1:05b}{2:05b}00000101010",
	
	"beq":"000100{0:05b}{1:05b}{2:016b}",
	"addi":"001000{0:05b}{1:05b}{2:016b}",
	"lw":"100011{0:05b}{1:05b}{2:016b}",
	"sw":"101011{0:05b}{1:05b}{2:016b}",
	
	"j":"000010{0:026b}",
}

# binary string to integer
def bin_to_int(string):
	return int(string, 2)

# formats human readable code instructions to binary strings
def mnem_to_bin(input):
	inst_parts = input.replace(',', ' ').replace('(', ' ').replace(')', ' ').split()

	operation = inst_parts[0]
	regs_imms = inst_parts[1:]
	
	regs_imms_int = []
	inst = insts_def[operation]
	if operation in ["addi", "beq"]:
		regs_imms_int = [
			regs_def[regs_imms[1]],
			regs_def[regs_imms[0]],
			int(regs_imms[2])
		]
	elif operation in ["and","or","add","sub","slt"]:
		regs_imms_int = [
			regs_def[regs_imms[1]],
			regs_def[regs_imms[2]],
			regs_def[regs_imms[0]]
		]
	elif operation in ["j"]:
		regs_imms_int = [
			int(regs_imms[0])
		]
	elif operation in ["lw","sw"]:
		regs_imms_int = [
			regs_def[regs_imms[2]],
			regs_def[regs_imms[0]],
			int(regs_imms[1])
		]
	
	inst = inst.format(*regs_imms_int)
	return inst

# adds instruction to memory (split by 8 bits)
def add_to_inst_memory(inst):
	inst_memory.append(inst[0:8])
	inst_memory.append(inst[8:16])
	inst_memory.append(inst[16:24])
	inst_memory.append(inst[24:32])

# control unit
def control(opcode):
	opcode_bin = format(opcode, '06b')
	r_format = not(int(opcode_bin[0])) and not(int(opcode_bin[1])) and not(int(opcode_bin[2])) and not(int(opcode_bin[3])) and not(int(opcode_bin[4])) and not(int(opcode_bin[5]))
	lw = int(opcode_bin[0]) and not(int(opcode_bin[1])) and not(int(opcode_bin[2])) and not(int(opcode_bin[3])) and int(opcode_bin[4]) and int(opcode_bin[5])
	sw = int(opcode_bin[0]) and not(int(opcode_bin[1])) and int(opcode_bin[2]) and not(int(opcode_bin[3])) and int(opcode_bin[4]) and int(opcode_bin[5])
	beq = not(int(opcode_bin[0])) and not(int(opcode_bin[1])) and not(int(opcode_bin[2])) and int(opcode_bin[3]) and not(int(opcode_bin[4])) and not(int(opcode_bin[5]))
	addi = not(int(opcode_bin[0])) and not(int(opcode_bin[1])) and int(opcode_bin[2]) and not(int(opcode_bin[3])) and not(int(opcode_bin[4])) and not(int(opcode_bin[5]))
	j = not(int(opcode_bin[0])) and not(int(opcode_bin[1])) and not(int(opcode_bin[2])) and not(int(opcode_bin[3])) and int(opcode_bin[4]) and not(int(opcode_bin[5]))

	regdst = int(r_format)
	regwrite = int(r_format or lw or addi)
	alusrc = int(lw or sw or addi)
	aluop1 = int(r_format)
	aluop0 = int(beq)
	branch = int(beq)
	memread = int(lw)
	memwrite = int(sw)
	memtoreg = int(lw)
	jump = int(j)

	return regdst, regwrite, alusrc, aluop1, aluop0, branch, memread, memwrite, memtoreg, jump

# alu control
def alu_control(aluop1, aluop0, funct):
	funct_bin = format(funct, '06b')
	op2 = int((aluop0 or aluop1) and int(funct_bin[4]))
	op1 = int(not(aluop1) or not(int(funct_bin[3])))
	op0 = int(aluop1 and (int(funct_bin[5]) or int(funct_bin[2])))
	op = str(op2)+str(op1)+str(op0)
	return op

# alu
def alu(op, v1, v2):
	r = 0
	if op == "000":
		r = int(v1 and v2)
	elif op == "001":
		r = int(v1 or v2)
	elif op == "010":
		r = v1 + v2
	elif op == "110":
		r = v1 - v2
	elif op == "111":
		r = int(v1 < v2)
	return r

def print_regs():
	for k,v in regs_def.items():	
		print(k+":",regs[v])
def print_data_memory():
	printed_chars = 0
	for x in data_memory:
		print(x, end="\t")
		printed_chars += len(str(x)) + 1
		
		if printed_chars > 15:
			print()
			printed_chars = 0

	if printed_chars != 0:
		print()
clear_screen = lambda: subprocess.call('cls||clear', shell=True)

# Start program

for inst in code:
	add_to_inst_memory(mnem_to_bin(inst))

while True:
	inst = inst_memory[pc] + inst_memory[pc+1] + inst_memory[pc+2] + inst_memory[pc+3] # composes the full instruction
	line_n = int(pc/4) # line of code being executed (index starts at 0)
	clear_screen()
	print("\nPC:",pc, "Line:", line_n)
	print(code[line_n])
	print(inst)
	
	regdst, regwrite, alusrc, aluop1, aluop0, branch, memread, memwrite, memtoreg, jump = control(bin_to_int(inst[0:6])) # control signals by opcode

	# alu operations
	op = alu_control(aluop1, aluop0, bin_to_int(inst[26:32]))
	if not alusrc:
		alu_result = alu(op, regs[bin_to_int(inst[6:11])], regs[bin_to_int(inst[11:16])])
	else:
		alu_result = alu(op, regs[bin_to_int(inst[6:11])], bin_to_int(inst[16:32]))
	
	pcsrc = branch and not(alu_result) # branch or not
	if not pcsrc:
		pc+=4
	else:
		pc=pc+4+bin_to_int(inst[16:32]) # sums memory offset
	
	if memwrite:
		data_memory[alu_result] = regs[bin_to_int(inst[11:16])]
	
	if memread:
		read_data = data_memory[alu_result]
	
	if regwrite:
		if regdst:
			write_reg_addr = bin_to_int(inst[16:21])
		else:
			write_reg_addr = bin_to_int(inst[11:16])
		if memtoreg:
			regs[write_reg_addr] = read_data
		else:
			regs[write_reg_addr] = alu_result
	
	if jump:
		pc=bin_to_int(format(bin_to_int(inst[6:32])*4, '28b')+format((pc+4), '32b')[0:4])
	
	print_regs()
	print_data_memory()
	
	time.sleep(0.5)
	
	if pc == len(inst_memory): # if last instruction done
		break