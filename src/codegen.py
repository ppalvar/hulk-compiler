import os
from os import path
from uuid import uuid1
from queue import LifoQueue as stack

from src.semantic_checker import SymbolTable, TYPES

class MIPSCodeManager:
    def __init__(self, symbol_table) -> None:
        self.data_section = []
        self.code = {}
        self.reset_registers()
        self.current_function = ''
        self.symbol_table = symbol_table
        self.sp_value = 0
        self.current_params_size = 0
        self.all_params_size = stack()
    
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

        data_code += '\n'
        data_code += '\n'.join([f'\t\t{name}:\t\t   {type}    {value}' for name, type, value in self.data_section])

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
        # $t0, $s0 and $f12 registers are for special uses like float conversions and memory addressing
        self.normal_registers = {
			'$t1' : None, '$t2' : None, '$t3' : None, '$t4' : None, '$t5' : None, 
			'$t6' : None, '$t7' : None, '$t8' : None, '$t9' : None, '$s1' : None, 
			'$s2' : None, '$s3' : None, '$s4' : None     
        }

        self.float_registers = {
            '$f13' : None, '$f14' : None, '$f15' : None, '$f15' : None, 
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

        if self.symbol_table.is_defined(t0, 'var'):
            if type(value) != str:
                return
            symb = self.symbol_table.get_symbol(t0, 'var')
            reg = self.get_register(value)

            inst = 'swc1' if symb.type == TYPES['number'] else 'sw'

            return f'{inst} {reg}, {self.sp_value-symb.alias-symb.type.size}($sp)'
        
        elif self.symbol_table.is_defined(value, 'var'):
            reg = self.get_register(t0)
            symb = self.symbol_table.get_symbol(value, 'var')
            
            inst = 'lwc1' if t0.startswith('f') else 'lw'

            return f'{inst} {reg}, {self.sp_value-symb.alias-symb.type.size}($sp)'

        elif type(value) is not str:
            reg = self.get_register(t0)
            if reg.startswith('$f'):
                return f'li.s {reg}, {value}'
            else:
                return f'li {reg}, {int(value)}'

        elif value.startswith('\"'): # this is a string
            str_name = f'string_{len(self.data_section) + 1}'
            self.data_section.append((str_name, '.asciiz', value))

            if self.symbol_table.is_defined(t0, 'var'):
                symb = self.symbol_table.get_symbol(t0, 'var')

                return (
                    f'la $t0, {str_name}',
                    f'sw $t0, {self.sp_value-symb.alias-symb.type.size}($sp)'
                )
            else:
                reg = self.get_register(t0)
                return f'la {reg}, {str_name}'
    
    def generate_clear(self, tac_code):
        _, name = tac_code
        symb = self.symbol_table.get_symbol(name, 'var')

        self.symbol_table.variables.pop(name)

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
        self.symbol_table.define_var(name, type, alias=self.sp_value)

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
        for name, type in reversed(params):
            total += type.size
            self.symbol_table.define_var(name, type, alias=-(total + 8))

        return 'nop'

    def generate_function_call_start(self, tac_code):
        self.all_params_size.put(self.current_params_size)
        self.current_params_size = 0
        self.sp_value += 92
        return 'jal push_all'
    
    def generate_set_param(self, tac_code):
        _, t0, type = tac_code

        self.current_params_size += type.size
        self.sp_value += type.size

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

        tmp = self.current_params_size
        self.sp_value -= 92 + tmp
        self.current_params_size = 0

        return (
            f'jal {func}',
            f'addi $sp, $sp, {tmp}',
            'jal pop_all',
            f'{inst} {reg}, {retv}'
        )
    
    def generate_function_call_end(self, tac_code):
        self.current_params_size = self.all_params_size.get()
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

    def generate_alloc_array(self, tac_code):
        _, t0, tp, size = tac_code
        
        reg = self.get_register(t0)

        return (
            f'li $a0, {size * tp.size}',
            'li $v0, 9',
            'syscall',
            f'move {reg}, $v0'
        )

    def generate_set_index(self, tac_code):
        _, name, index, t0 = tac_code

        symb = self.symbol_table.get_symbol(name, 'var')
        inst = 'swc1' if symb.type.item_type == TYPES['number'] else 'sw'
        reg = self.get_register(t0)
        
        if type(index) is int:
            return (
                f'lw $t0, {self.sp_value-symb.alias-symb.type.size}($sp)',
                f'addi $t0, $t0, {index * 4}',
                f'{inst} {reg}, 0($t0)'
            )
        else:
            rgi = self.get_register(index)
            return (
                f'cvt.w.s $f12, {rgi}',
                f'mfc1 $t0, $f12',
                f'sll $t0, $t0, 2',
                f'lw $s0, {self.sp_value-symb.alias-symb.type.size}($sp)',
                f'add $t0, $t0, $s0',
                f'{inst} {reg}, 0($t0)'
            )
    
    def generate_get_index(self, tac_code):
        _, t0, index, name = tac_code

        symb = self.symbol_table.get_symbol(name, 'var')
        inst = 'lwc1' if symb.type.item_type == TYPES['number'] else 'lw'
        reg = self.get_register(t0)

        if type(index) is int:
            return (
                f'lw $t0, {self.sp_value-symb.alias-symb.type.size}($sp)',
                f'addi $t0, $t0, {index * 4}',
                f'{inst} {reg}, 0($t0)'
            )
        else:
            rgi = self.get_register(index)
            return (
                f'cvt.w.s $f12, {rgi}',
                f'mfc1 $t0, $f12',
                f'sll $t0, $t0, 2',
                f'lw $s0, {self.sp_value-symb.alias-symb.type.size}($sp)',
                f'add $t0, $t0, $s0',
                f'{inst} {reg}, 0($t0)'
            )
    
    def generate_alloc(self, tac_code):
        _, t0, type = tac_code
        
        r0 = self.get_register(t0)

        return (f'li $a0, {type.size}',
                'li $v0, 9',
                'syscall',
                f'move {r0}, $v0')

    def generate_set(self, tac_code):
        _, t0, addr, t1 = tac_code
        
        r0 = self.get_register(t0)
        r1 = self.get_register(t1)

        inst = 'swc1' if t1.startswith('f') else 'sw'
        return f'{inst} {r1}, {addr}({r0})'
    
    def generate_get(self, tac_code):
        _, t0, t1, addr = tac_code
        
        r0 = self.get_register(t0)
        r1 = self.get_register(t1)

        inst = 'lwc1' if t1.startswith('f') else 'lw'
        return f'{inst} {r0}, {addr}({r1})'


def random_label():
    tmp = uuid1().__str__().replace('-', '_')
    return f'_{tmp}'