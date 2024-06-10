import copy

class SemanticChecker:
    def __init__(self) -> None:
        self.errors = []

    def check(self, ast, symbols=None):
        if symbols == None:
            symbols = SymbolTable()
        try:
            if type(ast[0]) != str:
                result = True
                for line in ast:
                    result = result and self.check(line, symbols)
                return result
            else :
                method = self.__getattribute__(ast[0])
                result = method(ast, symbols)
                
                return result
        except:
            # print(ast[0])
            raise
    
    def var_inst(self, ast, symbols):
        _, declarations, body, _ = ast
        
        result = True
        _symbols = symbols.make_child()
        
        for _, name, value in declarations:
            result = result and self.check(value, _symbols)
            tp = _symbols.deduce_type(value)

            if tp is None:
                self.errors.append(f'Cannot deduce type for variable \'{name}\'')

            _symbols.define(name, tp)
        
        ast[3] = _symbols
        result = result and self.check(body, _symbols)
        return result

    def declaration(self, ast, symbols):
        pass

    def while_loop(self, ast, symbols):
        _, condition, body = ast

        result = self.check(condition, symbols)
        ct = symbols.deduce_type(condition)        
        if ct != 'bool':
            self.errors.append(f'While loop condition must be of type bool, {ct} deduced')
            result = False

        result = result and self.check(body, symbols)
        return result
    
    def conditional(self, ast, symbols):
        _, condition, body = ast[1]

        result = self.check(condition, symbols)
        ct = symbols.deduce_type(condition)    

        if ct != 'bool':
            self.errors.append(f'If statement condition must be of type bool, {ct} deduced')
            result = False
        
        result = result and self.check(body, symbols)

        if ast[2]:
            for elif_ in ast[2]:
                result = result and self.check(elif_, symbols)
        if ast[3]:
            _, body = ast[3]
            result = result and self.check(body, symbols)
        
        return result

    def elif_statement(self, ast, symbols):
        _, condition, body = ast

        result = self.check(condition, symbols)
        ct = symbols.deduce_type(condition)    

        if ct != 'bool':
            self.errors.append(f'Elif statement condition must be of type bool, {ct} deduced')
            result = False
        
        result = result and self.check(body, symbols)
        return result
    
    def binop(self, ast, symbols):
        result = self.check(ast[2], symbols) and self.check(ast[3], symbols) 
        tp = symbols.deduce_type(ast)
        return result and tp

    def number(self, ast, symbols):
        return True

    def identifier(self, ast, symbols):
        result = symbols.is_defined(ast[1])
        if not result:
            print(symbols.symbols)
            self.errors.append(f'Variable {ast[1]} used but not defined')
        return result
    
    def grouped(self, ast, symbols):
        return self.check(ast[1], symbols)
    
    def unary(self, ast, symbols):
        result = self.check(ast[2], symbols)
        tp = symbols.deduce_type(ast)
        return result and tp
    
    def bool(self, ast, symbols):
        return True
    
    def string(self, ast, symbols):
        return True
    
    def str_concat(self, ast, symbols):
        result = self.check(ast[1], symbols) and self.check(ast[2], symbols)

        return result
    
    def assignment(self, ast, symbols):
        result = symbols.is_defined(ast[1]) and self.check(ast[2], symbols)
        tp = symbols.deduce_type(ast[2])

        if symbols.get_type(ast[1]) != tp:
            self.errors.append(f'Cannot assign type {tp} to variable {ast[1]} of type {symbols.get_type(ast[1])}')
            result = False
        
        return result and tp
    
    def compound_instruction(self, ast, symbols):
        return self.check(ast[1], symbols)

class SymbolTable:
    def __init__(self) -> None:
        self.symbols = dict()

    def make_child(self):
        return copy.deepcopy(self)
    
    def define(self, name: str, type: str, alias: int=None):
        if alias == None:
            alias = len(self.symbols)
        self.symbols[name] = (type, alias, True)
    
    def undefine(self, name: str):
        if self.is_defined(name):
            raise NameError(f"{name} is not defined")
        self.symbols[name][2] = False
    
    def is_defined(self, name: str):
        return name in self.symbols and self.symbols[name][2]

    def get_type(self, name: str):
        if not self.symbols[name]:
            raise NameError(f"{name} is not defined")
        return self.symbols[name][0]

    def deduce_type(self, ast):
        try:
            method = self.__getattribute__('deduce_type_' + ast[0])
            result = method(ast)
            
            return result
        except(AttributeError):
            if type(ast[0]) is str:
                if ast[0] in ('number', 'string', 'bool'):
                    return ast[0]
                else:
                    print(f'Cannot deduce type for {ast}')
            raise
    
    def deduce_type_binop(self, ast):
        t1 = self.deduce_type(ast[2])
        t2 = self.deduce_type(ast[3])
        if t1 != t2:
            return None
        elif ast[1] in ('==', '<=', '>=', '>', '<', '!=') and t1 == 'number':
            return 'bool'
        elif ast[1] in ('+', '-', '*', '/') and t1 == 'number':
            return t1
        elif ast[1] in ('&&', '||') and t1 == 'bool':
            return t1
        else :
            return None
    
    def deduce_type_unary(self, ast):
        t1 = self.deduce_type(ast[2])
        if ast[1] in ('-', '+') and t1 == 'number':
            return t1
        elif ast[1] == '!' and t1 == 'bool':
            return 'bool'
        else:
            return None
    
    def deduce_type_identifier(self, ast):
        if self.is_defined(ast[1]):
            return self.get_type(ast[1])
        return None
    
    def deduce_type_grouped(self, ast):
        return self.deduce_type(ast[1])