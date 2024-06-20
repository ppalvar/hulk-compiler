import os
from os import path
from uuid import uuid1

from src.semantic_checker import SymbolTable, TYPES

class MIPSCodeManager:
    def __init__(self, symbol_table) -> None:
        self.code = {}
        self.reset_registers()
        self.current_function = ''
        self.symbol_table = symbol_table
        self.sp_value = 0
        self.current_params_size = 0
    
    def __str__(self) -> str:
        _code = []
        for func in self.code:
            
            _code.append(f'{func}:')
            tmp = ['\t' + t0 for t0 in self.code[func]]
            _code.append('\n'.join(tmp))
        
        return '\n'.join(_code)
    
    def store_code(self, filename: str):
        data_code = open('lib/data.s').read()
        prep_code = open('lib/code.s').read()

        code = f'{data_code}\n\n.text\n{str(self)}\n\n{prep_code}'

        if not path.exists(path.dirname(filename)):
            os.mkdir(path.dirname(filename))
        
        with open(filename, 'w') as out:
            out.write(code)

    def generate_mips(self, tac: dict):
        for function in tac:
            self.reset_registers()
            self.current_function = function
            if function == 'main':
                self.code[function] = []
            else:
                # This is for reseting the current frame
                # and not to mess with the caller's stack
                self.code[function] = [ 
                    'addi $sp, $sp, -8',
                    'sw $ra, 4($sp)',
                    'sw $fp, 0($sp)',
                    'move $fp, $sp'
                ]

            for line in tac[function]:
                self.add_line_to_code(line)

    def reset_registers(self) -> None:
        self.normal_registers = {
			'$t0' : None, '$t1' : None, '$t2' : None, '$t3' : None, '$t4' : None, '$t5' : None, 
			'$t6' : None, '$t7' : None, '$t8' : None, '$t9' : None, '$s0' : None, '$s1' : None, 
			'$s2' : None, '$s3' : None, '$s4' : None     
        }

        self.float_registers = {
            '$f12' : None, '$f13' : None, '$f14' : None, '$f15' : None, '$f15' : None, 
            '$f16' : None, '$f17' : None, '$f18' : None,
        }

        self.normal_registers_descriptors = {}
        self.float_registers_descriptors = {}

        self.free_normal_registers = [e for e in self.normal_registers.keys()]
        self.free_float_registers = [e for e in self.float_registers.keys()]

        self.busy_normal_registers = []
        self.busy_float_registers = []

        self.current_function = ''
        # self.symbol_table = SymbolTable()
        self.sp_value = 0
    
    def add_line_to_code(self, tac_code) -> bool:
        code = self.code[self.current_function]
        
        try:
            method = self.__getattribute__(f'generate_{tac_code[0]}')
            result = method(tac_code)
            
            assert result != None
            
            if type(result) is str:
                code.append(result)
            elif type(result) is tuple:
                for line in result:
                    code.append(line)
        except:
            raise

    def get_register(self, temp: str) -> str:
        is_float = temp.startswith('f')

        regs = self.normal_registers if not is_float else self.float_registers
        regs_desc = self.normal_registers_descriptors if not is_float else self.float_registers_descriptors
        busy_regs = self.busy_normal_registers if not is_float else self.busy_float_registers
        free_regs = self.free_normal_registers if not is_float else self.free_float_registers

        if temp in regs.values():
            reg = regs_desc[temp]
        
        else:
            if free_regs:
                reg = free_regs.pop(0)
                regs_desc[temp] = reg
                regs[reg] = temp
                busy_regs.append(reg)
            else:
                reg = busy_regs.pop(0)
                regs_desc[temp] = reg
                regs[reg] = temp
                busy_regs.append(reg)

        return reg
    
    def generate_assign(self, tac_code):
        _, t0, value = tac_code

        if self.symbol_table.is_defined(t0):
            if type(value) != str:
                return
            symb = self.symbol_table.get_symbol(t0)
            reg = self.get_register(value)

            inst = 'swc1' if symb.type == TYPES['number'] else 'sw'

            return f'{inst} {reg}, {self.sp_value-symb.alias-symb.type.size}($sp)'
        elif self.symbol_table.is_defined(value):
            reg = self.get_register(t0)
            
            symb = self.symbol_table.get_symbol(value)
            inst = 'lwc1' if symb.type == TYPES['number'] else 'lw'

            return f'{inst} {reg}, {self.sp_value-symb.alias-symb.type.size}($sp)'

        elif type(value) is not str:
            reg = self.get_register(t0)
            if reg.startswith('$f'):
                return f'li.s {reg}, {value}'
            else:
                return f'li {reg}, {int(value)}'
    
    def generate_clear(self, tac_code):
        _, name = tac_code
        symb = self.symbol_table.get_symbol(name)

        self.symbol_table.symbols.pop(name)

        return f'addi $sp, $sp, {symb.type.size}'
    
    def generate_binop(self, tac_code):
        _, t0, op, a, b = tac_code

        rg1 = self.get_register(t0)
        rg2 = self.get_register(a)
        rg3 = self.get_register(b)

        lbl = random_label()

        match op:
            case '+':
                return f'add.s {rg1}, {rg2}, {rg3}'
            case '-':
                return f'sub.s {rg1}, {rg2}, {rg3}'
            case '*':
                return f'mul.s {rg1}, {rg2}, {rg3}'
            case '/':
                return f'div.s {rg1}, {rg2}, {rg3}'
            case '==':
                return (
                    f'c.eq.s {rg2}, {rg3}',
                    f'li {rg1}, 0',
                    f'bc1f {lbl}',
                    f'li {rg1}, 1',
                    f'{lbl}:'
                )
            case '!=':
                return (
                    f'c.eq.s {rg2}, {rg3}',
                    f'li {rg1}, 1',
                    f'bc1f {lbl}',
                    f'li {rg1}, 0',
                    f'{lbl}:'
                )
            case '<=':
                return (
                    f'c.le.s {rg2}, {rg3}',
                    f'li {rg1}, 1',
                    f'bc1t {lbl}',
                    f'li {rg1}, 0',
                    f'{lbl}:'
                )
            case '>=':
                return (
                    f'c.le.s {rg3}, {rg2}',
                    f'li {rg1}, 1',
                    f'bc1t {lbl}',
                    f'li {rg1}, 0',
                    f'{lbl}:'
                )
            case '<':
                return (
                    f'c.lt.s {rg2}, {rg3}',
                    f'li {rg1}, 1',
                    f'bc1t {lbl}',
                    f'li {rg1}, 0',
                    f'{lbl}:'
                )
            case '>':
                return (
                    f'c.lt.s {rg3}, {rg2}',
                    f'li {rg1}, 1',
                    f'bc1t {lbl}',
                    f'li {rg1}, 0',
                    f'{lbl}:'
                )
            case '&&':
                return f'and {rg1}, {rg2}, {rg3}'
            case '||':
                return f'or {rg1}, {rg2}, {rg3}'
        
    def generate_unary(self, tac_code):
        _, t0, op, t1 = tac_code

        rg0 = self.get_register(t0)
        rg1 = self.get_register(t1)

        match op:
            case '-':
                return f'neg.s {rg0}, {rg1}'
            case '+':
                return ''
    
    def generate_declare(self, tac_code):
        _, name, size, type = tac_code
        self.symbol_table.define(name, type, alias=self.sp_value)

        self.sp_value += type.size

        return f'addi $sp, $sp, {-type.size}'
    
    def generate_jump_nz(self, tac_code):
        _, t0, label = tac_code

        reg = self.get_register(t0)
        return f'bnez {reg}, {label}'
    
    def generate_jump(self, tac_code):
        _, label = tac_code
        return f'j {label}'
    
    def generate_label(self, tac_code):
        _, label = tac_code
        return f'{label}:'

    def generate_get_params(self, tac_code):
        _, params = tac_code

        total = 0
        for name, type in params:
            total += type.size
            self.symbol_table.define(name, type, alias=-(total + 8))

        return 'nop'

    def generate_function_call_start(self, tac_code):
        self.sp_value += 92
        return 'jal push_all'
    
    def generate_set_param(self, tac_code):
        _, t0, type = tac_code

        self.current_params_size += type.size

        reg = self.get_register(t0)
        
        inst = 'swc1' if type == TYPES['number'] else 'sw'
        return (
            f'addi $sp, $sp, {-type.size}', 
            f'{inst} {reg}, 0($sp)'
        )
    
    def generate_call(self, tac_code):
        _, t0, func = tac_code

        reg = self.get_register(t0)
        
        inst = 'mov.s' if self.symbol_table.get_return_type(func) == TYPES['number'] else 'move'
        retv = '$f0' if self.symbol_table.get_return_type(func) == TYPES['number'] else '$v0'

        self.sp_value -= 92
        tmp = self.current_params_size
        self.current_params_size = 0

        return (
            f'jal {func}',
            f'addi $sp, $sp, {tmp}',
            'jal pop_all',
            f'{inst} {reg}, {retv}'
        )
    
    def generate_function_call_end(self, tac_code):
        return 'nop'
    
    def generate_return(self, tac_code):
        _, t0 = tac_code
        
        if t0 is None:
            return 'nop'

        reg = self.get_register(t0)
        inst = 'mov.s' if self.symbol_table.get_return_type(self.current_function) == TYPES['number'] else 'move'
        retv = '$f0' if self.symbol_table.get_return_type(self.current_function) == TYPES['number'] else '$v0'

        return (
            f'{inst} {retv}, {reg}',
            'lw $ra, 4($fp)',
            'move $sp, $fp',
            'lw $fp, 0($fp)',
            'addi $sp, $sp, 8',
            'jr $ra'
        )


def random_label():
    tmp = uuid1().__str__().replace('-', '_')
    return f'_{tmp}'