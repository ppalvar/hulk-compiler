from queue import LifoQueue as stack
from src.semantic_checker import SymbolTable, TYPES

class TacGenerator:
    def __init__(self, symbol_table: SymbolTable) -> None:
        self.var_count = 0
        self.code = dict()
        self.loop_labels = stack()
        self.current_function = 'main'
        self.symbol_table = symbol_table

    def __str__(self) -> str:
        _code = []
        for func in self.code:
            _code.append(f'{func}:')
            tmp = ['\t' + repr(t0) for t0 in self.code[func]]
            _code.append('\n'.join(tmp))
        return '\n'.join(_code)

    def generate(self, ast, symb_table: SymbolTable=None) -> list[str]:
        if symb_table == None:
            symb_table = self.symbol_table
        try:
            if type(ast[0]) != str:
                for inst in ast:
                    self.generate(inst, symb_table)
                return None
            method = self.__getattribute__(ast[0])
            result = method(ast, symb_table)
            return result
        except:
            raise
    
    def binop(self, ast, symb_table: SymbolTable):
        t1 = self.generate(ast[2], symb_table)
        t2 = self.generate(ast[3], symb_table)

        t0 = self.get_next_var(t1.startswith('f') and ast[1] in ('+', '-', '/', '*'))

        self.create_binop(t0, ast[1], t1, t2)
        
        return t0
    
    def number(self, ast, symb_table: SymbolTable):
        t0 = self.get_next_var(True)
        
        self.create_assign(t0, ast[1])

        return t0

    def bool(self, ast, symb_table: SymbolTable):
        t0 = self.get_next_var()
        
        self.create_assign(t0, ast[1])

        return t0
    
    def string(self, ast, symb_table: SymbolTable):
        t0 = self.get_next_var()
        
        self.create_assign(t0, ast[1])

        return t0
    
    def unary(self, ast, symb_table: SymbolTable):
        t1 = self.generate(ast[2], symb_table)
        
        t0 = self.get_next_var(t1.startswith('f'))
        
        self.create_unary(t0, ast[1], t1)

        return t0
    
    def grouped(self, ast, symb_table: SymbolTable):
        return self.generate(ast[1], symb_table)
    
    def var_inst(self, ast, symb_table: SymbolTable):
        _, decls, body, symbols = ast

        for decl in decls:
            self.generate(decl, symbols)
        
        t0 = self.generate(body, symbols)

        for decl in reversed(decls):
            self.clear_variable(decl)
        
        return t0

    
    def declaration(self, ast, symb_table: SymbolTable):
        _, annotated_name, value = ast
        _, name, annotated_type = annotated_name
        tp = symb_table.get_type(name)
        
        if tp.is_array:
            self.create_array_alloc(name, tp, tp.size)

            source, _value = value
            if source == 'array_declaration_explicit':
                for i, item in enumerate(_value):
                    t0 = self.generate(item, symb_table)
                    
                    self.create_array_set(name, i, t0)
            elif source == 'identifier':
                t0 = self.generate(value, symb_table)
                self.create_assign(name, t0)

        else:
            t0 = self.generate(value, symb_table)
            self.create_declare(name, 1, tp)
            self.create_assign(name, t0)
        
        return name


    def clear_variable(self, ast):
        # This method assumes the variable is stored in the stack
        _, annotated_name, _ = ast
        _, name, _ = annotated_name

        self.create_var_clear(name)


    def identifier(self, ast, symb_table: SymbolTable):
        _, name = ast
        t0 = self.get_next_var(symb_table.get_type(name) == TYPES['number'])
        self.create_assign(t0, name)
        return t0
    
    def while_loop(self, ast, symb_table: SymbolTable):
        _, cond, body = ast

        label = f'while_{self.var_count}'
        end_label = f'end_while_{self.var_count}'
        skip_label = f'skip_while_{self.var_count}'
        

        self.create_jump_inc(end_label)
        self.create_label(label)

        self.enter_loop(end_label, skip_label)

        t2 = self.generate(body, symb_table)

        self.exit_loop()

        self.create_label(end_label)
        
        t1 = self.generate(cond, symb_table)
        self.create_jump_cond(t1, label)

        self.create_label(skip_label)

        return t2

    def assignment(self, ast, symb_table: SymbolTable):
        _, var, value = ast
        
        t0 = self.generate(value, symb_table)
        
        if type(var) == str:
            self.create_assign(var, t0)
        elif var[0] == 'array_access':
            _, name, index = var
            t1 = self.generate(index, symb_table)
            self.create_array_set(name, t1, t0)
        
        return var

    def compound_instruction(self, ast, symb_table: SymbolTable):
        return self.generate(ast[1], symb_table)
    
    def conditional(self, ast, symb_table: SymbolTable):
        _, if_statement, elif_statements, else_statement = ast

        _, cond, body = if_statement

        label = f'if_{self.var_count}'
        end_label = f'end_if_{self.var_count}'
        end_conditional = f'end_conditional_{self.var_count}'

        t1 = self.generate(cond, symb_table)

        self.create_jump_cond(t1, label)
        self.create_jump_inc(end_label)
        self.create_label(label)

        t2 = self.generate(body, symb_table)

        self.create_jump_inc(end_conditional)
        self.create_label(end_label)

        if elif_statements:
            for _elif in elif_statements:
                _, cond, body = _elif

                label = f'elif_{self.var_count}'
                end_label = f'end_elif_{self.var_count}'

                t1 = self.generate(cond, symb_table)
                
                self.create_jump_cond(t1, label)
                self.create_jump_inc(end_label)
                self.create_label(label)

                t2 = self.generate(body, symb_table)

                self.create_jump_inc(end_conditional)
                self.create_label(end_label)
        
        if else_statement:
            _, body = else_statement
            t2 = self.generate(body, symb_table)

        self.create_label(end_conditional)

        return t2
    
    def array_declaration_explicit(self, ast, symb_table: SymbolTable):
        raise NotImplementedError('array_declaration_explicit')
    
    def array_access(self, ast, symb_table: SymbolTable):
        _, name, index = ast

        t0 = self.get_next_var()
        t1 = self.generate(index, symb_table)

        self.create_array_get(t0, t1, name)

        return t0
    
    def function_call(self, ast, symb_table: SymbolTable):
        _, name, params = ast

        self.create_function_call_start()

        for i, param in enumerate(params):
            t0 = self.generate(param, symb_table)

            self.create_set_param(t0, symb_table.get_params_type(name)[i])
        
        t1 = self.get_next_var(symb_table.get_return_type(name) == TYPES['number'])

        self.create_func_call(t1, name)
        self.create_function_call_end()
        return t1
    
    def break_statement(self, ast, symb_table: SymbolTable):
        _, end_label = self.get_current_loop()

        self.create_jump_inc(end_label)
    
    def continue_statement(self, ast, symb_table: SymbolTable):
        start_label, _ = self.get_current_loop()

        self.create_jump_inc(start_label)
    
    def function(self, ast, symb_table: SymbolTable):
        _, _, name, params, body, symbols = ast
        self.set_current_function(name)

        tmp = []
        for i, _parm in enumerate(params):
            _, param, _ = _parm
            tmp.append((param, symb_table.get_params_type(self.current_function)[i]))
            
        self.create_get_params(tuple(tmp))
        
        t0 = self.generate(body, symbols)

        self.create_return(t0)
        self.reset_current_function()
        return None
    
    def return_statement(self, ast, symb_table: SymbolTable):
        _, value = ast

        t0 = self.generate(value, symb_table)

        self.create_return(t0)
        return None
 
        
    def get_next_var(self, is_float: bool = False) -> str:
        self.var_count += 1
        if is_float:
            return f'f0{self.var_count}#'    
        return f't0{self.var_count}#'

    #region code generation helpers
    def create_function_codespace(self):
        if self.current_function not in self.code:
            self.code[self.current_function] = []

    def create_binop(self, t1, op, t2, t3):
        self.create_function_codespace()
        self.code[self.current_function].append(('binop', t1, op, t2, t3))
    
    def create_function_call_start(self):
        self.create_function_codespace()
        self.code[self.current_function].append(('function_call_start',))
    
    def create_function_call_end(self):
        self.create_function_codespace()
        self.code[self.current_function].append(('function_call_end',))
    
    def create_unary(self, t1, op, t2):
        self.create_function_codespace()
        self.code[self.current_function].append(('unary', t1, op, t2))
    
    def create_assign(self, t1, t2):
        self.create_function_codespace()
        self.code[self.current_function].append(('assign', t1, t2))
    
    def create_label(self, label):
        self.create_function_codespace()
        self.code[self.current_function].append(('label', label))
    
    def create_jump_inc(self, label):
        self.create_function_codespace()
        self.code[self.current_function].append(('jump', label))
    
    def create_jump_cond(self, t1, label):
        self.create_function_codespace()
        self.code[self.current_function].append(('jump_nz', t1, label))
    
    def create_array_alloc(self, t1, type, size):
        self.create_function_codespace()
        self.code[self.current_function].append(('alloc_array', t1, type, size))
    
    def create_array_get(self, t1, index, t2):
        self.create_function_codespace()
        self.code[self.current_function].append(('get_index', t1, index, t2))
    
    def create_array_set(self, t1, index, t2):
        self.create_function_codespace()
        self.code[self.current_function].append(('set_index', t1, index, t2))
    
    def create_set_param(self, value, type):
        self.create_function_codespace()
        self.code[self.current_function].append(('set_param', value, type))
    
    def create_get_params(self, params):
        self.create_function_codespace()
        self.code[self.current_function].append(('get_params', params))
    
    def create_func_call(self, t0, name):
        self.create_function_codespace()
        self.code[self.current_function].append(('call', t0, name))
    
    def create_return(self, t0):
        self.create_function_codespace()
        self.code[self.current_function].append(('return', t0))
    
    def create_declare(self, name, size, type):
        self.create_function_codespace()
        self.code[self.current_function].append(('declare', name, size, type))
    
    def create_var_clear(self, name):
        self.create_function_codespace()
        self.code[self.current_function].append(('clear', name))
    #endregion
        
    def enter_loop(self, start_label, end_label) -> None:
        self.loop_labels.put((start_label, end_label))
    
    def exit_loop(self) -> None:
        self.loop_labels.get()
    
    def get_current_loop(self) -> tuple[str, str]:
        start_label, end_label = self.loop_labels.get()
        self.enter_loop(start_label, end_label)
        return start_label, end_label
    
    def set_current_function(self, name: str):
        self.current_function = name
    
    def reset_current_function(self):
        self.current_function = 'main'