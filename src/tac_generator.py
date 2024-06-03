class TacGenerator:
    def __init__(self) -> None:
        self.var_count = 0
        self.code = []
        pass

    def __str__(self) -> str:
        _code = []
        
        for line in self.code:
            _line = [str(e) if e != None else '' for e in line ]
            _line = f'{_line[0]} = {_line[1]} {_line[2]} {_line[3]};'
            _code.append(_line)

        return '\n'.join(_code)

    def generate(self, ast) -> list[str]:
        try:
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
