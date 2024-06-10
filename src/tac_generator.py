class TacGenerator:
    def __init__(self) -> None:
        self.var_count = 0
        self.code = []

    def __str__(self) -> str:
        _code = []
        
        for line in self.code:
            _line = [str(e) if e != None else '' for e in line ]
            _line = f'{_line[0]} = {_line[1]} {_line[2]} {_line[3]};'
            _code.append(_line)

        return '\n'.join(_code)

    def generate(self, ast) -> list[str]:
        try:
            if type(ast[0]) != str:
                for inst in ast:
                    self.generate(inst)
                return None
            method = self.__getattribute__(ast[0])
            self.var_count += 1
            result = method(ast)
            return result
        except:
            raise
    
    def binop(self, ast):
        t0 = f't{self.var_count}'
        t1 = self.generate(ast[2])
        t2 = self.generate(ast[3])

        self.code.append((t0, t1, ast[1], t2))
        
        return t0
    
    def number(self, ast):
        t0 = f't{self.var_count}'
        
        self.code.append((t0, None, None, ast[1]))

        return t0

    def bool(self, ast):
        t0 = f't{self.var_count}'
        
        self.code.append((t0, None, None, ast[1]))

        return t0
    
    def unary(self, ast):
        t0 = f't{self.var_count}'
        t1 = self.generate(ast[2])
        
        self.code.append((t0, None, ast[1], t1))

        return t0
    
    def grouped(self, ast):
        return self.generate(ast[1])
    
    def var_inst(self, ast):
        _, decls, body, symbols = ast

        for decl in decls:
            t = self.generate(decl)
        
        self.generate(body)
    
    def declaration(self, ast):
        _, name, value = ast

        t = self.generate(value)

        self.code.append((name, None, None, t))
    
    def identifier(self, ast):
        return ast[1]
    
    def while_loop(self, ast):
        _, cond, body = ast

        label = f'while_{self.var_count}'
        end_label = f'end_while_{self.var_count}'

        self.code.append(('jump', None, None, end_label))
        self.code.append(('label', None, None, label))

        t2 = self.generate(body)

        self.code.append(('label', None, None, end_label))
        
        t1 = self.generate(cond)
        self.code.append(('if', None, t1, label))

        return t2

    def assignment(self, ast):
        _, var, value = ast
        t = self.generate(value)
        self.code.append((var, None, None, t))
        return var

    def compound_instruction(self, ast):
        return self.generate(ast[1])
    
    def conditional(self, ast):
        _, if_statement, elif_statements, else_statement = ast

        _, cond, body = if_statement

        label = f'if_{self.var_count}'
        end_label = f'end_if_{self.var_count}'
        end_conditional = f'end_conditional_{self.var_count}'

        t1 = self.generate(cond)

        self.code.append(('if', None, t1, label))
        self.code.append(('jump', None, None, end_label))
        self.code.append(('label', None, None, label))

        t2 = self.generate(body)

        self.code.append(('jump', None, None, end_conditional))

        self.code.append(('label', None, None, end_label))

        if elif_statements:
            for _elif in elif_statements:
                _, cond, body = _elif

                label = f'elif_{self.var_count}'
                end_label = f'end_elif_{self.var_count}'

                t1 = self.generate(cond)

                self.code.append(('if', None, t1, label))
                self.code.append(('jump', None, None, end_label))
                self.code.append(('label', None, None, label))

                t2 = self.generate(body)

                self.code.append(('jump', None, None, end_conditional))

                self.code.append(('label', None, None, end_label))
        
        _, body = else_statement
        t2 = self.generate(body)

        self.code.append(('label', None, None, end_conditional))

        return t2