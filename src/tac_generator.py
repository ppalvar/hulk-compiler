from src.semantic_checker import SymbolTable

class TacGenerator:
    def __init__(self) -> None:
        self.var_count = 0
        self.code = []

    def __str__(self) -> str:
        _code = [repr(t0) for t0 in self.code]
        return '\n'.join(_code)

    def generate(self, ast, symb_table=None) -> list[str]:
        if symb_table == None:
            symb_table = SymbolTable()
        try:
            if type(ast[0]) != str:
                for inst in ast:
                    self.generate(inst)
                return None
            method = self.__getattribute__(ast[0])
            self.var_count += 1
            result = method(ast, symb_table)
            return result
        except:
            raise
    
    def binop(self, ast, symb_table):
        t0 = f't0{self.var_count}'
        t1 = self.generate(ast[2], symb_table)
        t2 = self.generate(ast[3], symb_table)

        self.create_binop(t0, ast[1], t1, t2)
        
        return t0
    
    def number(self, ast, symb_table):
        t0 = f't0{self.var_count}'
        
        self.create_assign(t0, ast[1])

        return t0

    def bool(self, ast, symb_table):
        t0 = f't0{self.var_count}'
        
        self.create_assign(t0, ast[1])

        return t0
    
    def unary(self, ast, symb_table):
        t0 = f't0{self.var_count}'
        t1 = self.generate(ast[2], symb_table)
        
        self.create_unary(t0, ast[1], t1)

        return t0
    
    def grouped(self, ast, symb_table):
        return self.generate(ast[1], symb_table)
    
    def var_inst(self, ast, symb_table):
        _, decls, body, symbols = ast

        for decl in decls:
            t0 = self.generate(decl, symbols)
        
        self.generate(body, symbols)
    
    def declaration(self, ast, symb_table):
        _, name, value = ast

        tp : str = symb_table.get_type(name)
        
        if tp.startswith('array'):
            self.create_array_alloc(name, tp, int(tp.split(':')[-1]))

            _, items = value
            for i, item in enumerate(items):
                t0 = self.generate(item, symb_table)
                
                self.create_array_set(name, i, t0)
        else:
            t0 = self.generate(value, symb_table)
            self.create_assign(name, t0)
        
        return name


    def identifier(self, ast, symb_table):
        return ast[1]
    
    def while_loop(self, ast, symb_table):
        _, cond, body = ast

        label = f'while_{self.var_count}'
        end_label = f'end_while_{self.var_count}'

        self.create_jump_inc(end_label)
        self.create_label(label)

        t2 = self.generate(body, symb_table)

        self.create_label(end_label)
        
        t1 = self.generate(cond, symb_table)
        self.create_jump_cond(t1, label)

        return t2

    def assignment(self, ast, symb_table):
        _, var, value = ast
        
        t0 = self.generate(value, symb_table)
        
        if type(var) == str:
            self.create_assign(var, t0)
        elif var[0] == 'array_access':
            _, name, index = var
            t1 = self.generate(index, symb_table)
            self.create_array_set(name, t1, t0)
        
        return var

    def compound_instruction(self, ast, symb_table):
        return self.generate(ast[1], symb_table)
    
    def conditional(self, ast, symb_table):
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
        
        _, body = else_statement
        t2 = self.generate(body, symb_table)

        self.create_label(end_conditional)

        return t2
    
    def array_declaration_explicit(self, ast, symb_table):
        return ast[0]
    
    def array_access(self, ast, symb_table):
        _, name, index = ast

        t0 = f't0{self.var_count}'
        t1 = self.generate(index, symb_table)

        self.create_array_get(t0, t1, name)

        return t0

    #region code generation helpers
    def create_binop(self, t1, op, t2, t3):
        self.code.append(('binop', t1, op, t2, t3))
    
    def create_unary(self, t1, op, t2):
        self.code.append(('unary', t1, op, t2))
    
    def create_assign(self, t1, t2):
        self.code.append(('assign', t1, t2))
    
    def create_label(self, label):
        self.code.append(('label', label))
    
    def create_jump_inc(self, label):
        self.code.append(('jump', label))
    
    def create_jump_cond(self, t1, label):
        self.code.append(('jump_nz', t1, label))
    
    def create_array_alloc(self, t1, type, size):
        self.code.append(('alloc_array', t1, type, size))
    
    def create_array_get(self, t1, index, t2):
        self.code.append(('get_index', t1, index, t2))
    
    def create_array_set(self, t1, index, t2):
        self.code.append(('set_index', t1, index, t2))
    #endregion