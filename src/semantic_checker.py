import copy


TYPE_NUMBER = 'number'
TYPE_STRING = 'string'
TYPE_BOOL   = 'bool'
TYPE_OBJECT = 'object'
TYPE_CLASS  = 'class'
TYPE_FUNCTION = 'function'

# TODO: change the default conversions
ALLOWED_CONVERTIONS = {
    TYPE_NUMBER : (TYPE_NUMBER, TYPE_STRING, TYPE_OBJECT),
    TYPE_STRING : (TYPE_STRING, TYPE_OBJECT),
    TYPE_BOOL : (TYPE_BOOL, TYPE_STRING, TYPE_OBJECT),
    TYPE_OBJECT : (TYPE_OBJECT, TYPE_STRING, TYPE_OBJECT),
    TYPE_CLASS : (TYPE_CLASS, TYPE_STRING, TYPE_OBJECT),
    TYPE_FUNCTION : (TYPE_FUNCTION, TYPE_STRING, TYPE_OBJECT),
}


class Symbol:
        def __init__(self, type:str, alias: int, return_type: str = None, param_types: tuple[str] = None) -> None:
            self.type = type
            self.alias = alias
            self.return_type = return_type
            self.param_types = param_types


BUILTIN_FUNCTIONS = {
    'print' : Symbol(TYPE_FUNCTION, 0, TYPE_STRING, (TYPE_OBJECT,))
}


class SymbolType:
    def __init__(self, annotation: str, type: str, is_error: bool = False) -> None:
        self.annotation = annotation
        self.type = type
        self.is_error = is_error

TYPES = (
    SymbolType('String', TYPE_STRING),
    SymbolType('Bool', TYPE_BOOL),
    SymbolType('Number', TYPE_NUMBER),
    SymbolType('None', 'none', True),
    SymbolType('NoDeduced', 'no_deduced', False)
)

ANNOTATIONS = {tp.annotation : tp.type for tp in TYPES}

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
        
        for decl in declarations:
            tmp = self.check(decl, _symbols)
            result = tmp and result

        ast[3] = _symbols
        result = result and self.check(body, _symbols)
        return result

    def declaration(self, ast, symbols):
        _, annotated_name, value = ast

        name, a_type = SymbolTable.resolve_annotation(annotated_name)
        
        tp = symbols.deduce_type(value)
        result = self.check(value, symbols)

        if tp is None:
            self.errors.append(f'Cannot deduce type for variable <{name}>')
            result = False
        
        if a_type != None and a_type != tp:
            self.errors.append(f'Type annotation <{a_type}> for <{name}> doesn\'t matches expression of type <{tp}>')
            result = False
        
        if result:
            symbols.define(name, tp)

        return result


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
        _, lvalue, rvalue = ast
        
        result0 = self.check(lvalue, symbols) if type(lvalue) != str else symbols.is_defined(lvalue)
        tp_left = symbols.deduce_type(lvalue) if type(lvalue) != str else symbols.get_type(lvalue)

        if not result0:
            if type(lvalue) == str:
                self.errors.append(f'Variable {lvalue} used but never declared')
            elif lvalue[0] == 'array_access':
                self.errors.append(f'Variable {lvalue[1]} used but never declared')
            else:
                self.errors.append('Fatal Error: unassigned variable')
            
            return False

        result1 = self.check(rvalue, symbols)
        tp_right = symbols.deduce_type(rvalue)

        if tp_left != tp_right:
            self.errors.append(f'Cannot convert type <{tp_right}> to <{tp_left}>')
        
        return result0 and result1 and tp_left == tp_right and tp_right != None
    
    def compound_instruction(self, ast, symbols):
        return self.check(ast[1], symbols)
    
    def array_declaration_explicit(self, ast, symbols):
        _, items = ast

        types = []
        result = True
        for item in items:
            tp = symbols.deduce_type(item)
            types.append(tp)

            result = result and self.check(item, symbols)

            if not result or not tp:
                break
        

        type_matches = all(x == types[0] and x != None for x in types)
        return type_matches and result
    
    def array_access(self, ast, symbols):
        _, name, index = ast

        index_tp = symbols.deduce_type(index)

        result = True

        if not symbols.is_defined(name):
            self.errors.append(f'Variable {name} used but not defined')
            result = False
        
        if result:
            tp = symbols.get_type(name)
            if not tp.startswith('array'):
                self.errors.append(f'Object of type <{tp}> cannot be indexed')
                result = False

        if index_tp != 'number':
            self.errors.append('Can only index array using a number')
            result = False

        return result
    
    def function_call(self, ast, symbols):
        _, func, params = ast
        
        result = symbols.is_defined(func)

        if not result:
            self.errors.append(f'Function <{func}> not defined')
            return False

        param_types = symbols.get_params_type(func)
        for i, param in enumerate(params):
            tp = symbols.deduce_type(param)
            
            if not symbols.can_convert(tp, param_types[i]):
                self.errors.append(F'Cannot convert parameter from <{tp}> to <{param_types[i]}>')
                return False
        
        return True
        
    
    def function(self, ast, symbols):
        symbols.try_deduce_function_types(ast)


class SymbolTable:
    def __init__(self) -> None:
        self.symbols = dict()

    def make_child(self):
        return copy.deepcopy(self)
    
    def define(self, name: str, type: str, alias: int=None, return_type: str = None, param_types: list[str] = None):
        if alias == None:
            alias = len(self.symbols)
        self.symbols[name] = Symbol(type, alias, return_type, param_types)
    
    def is_defined(self, name: str):
        return name in self.symbols or name in BUILTIN_FUNCTIONS

    def get_type(self, name: str) -> str:
        sym = self.get_symbol(name)
        return sym.type if sym else None
    
    def get_return_type(self, name: str) -> str:
        sym = self.get_symbol(name)
        return sym.return_type if sym else None
    
    def get_params_type(self, name: str) -> tuple[str]:
        sym = self.get_symbol(name)
        return sym.param_types if sym else None

    def get_symbol(self, name: str) -> Symbol|None:
        if name not in self.symbols:
            if name not in BUILTIN_FUNCTIONS:
                return None
            return BUILTIN_FUNCTIONS[name]
        return self.symbols[name]

    def can_convert(self, type_a : str, type_b : str):
        if type_a not in ALLOWED_CONVERTIONS:
            return False
        
        return type_b in ALLOWED_CONVERTIONS[type_a]
    
    @classmethod
    def resolve_annotation(cls, annotated_identifier) -> tuple[str, str] | str:
        if annotated_identifier is None:
            return None
        elif type(annotated_identifier) == str:
            annotation = annotated_identifier
            name = None
        else :
            _, name, annotation = annotated_identifier

        if annotation in ANNOTATIONS:
            annotation = ANNOTATIONS[annotation]
        
        if not name:
            return annotation
        return name, annotation
    
    #region: type inference for function parameters and return type

    def try_deduce_function_types(self, func):
        _, return_type, name, params, body = func

        return_type = SymbolTable.resolve_annotation(None)
        print(return_type)

        param_types = {}
        for param in params:
            param_name, param_type = SymbolTable.resolve_annotation(param)
            param_types[param_name] = param_type
        print(param_types)
        if type(body) != list:
            self.try_unify_types(params, body)
    
    def try_unify_types(self, varibles, instruction):
        pass

    #endregion

    #region: type inference for expressions
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
    
    def deduce_type_array_declaration_explicit(self, ast):
        _, items = ast

        types = []
        for item in items:
            tp = self.deduce_type(item)
            
            if not tp:
                return None
            
            types.append(tp)

        type_matches = all(x == types[0] and x != None for x in types)

        if type_matches:
            return f'array:{types[0]}:{len(items)}'
            # return types[0]
        return None
    
    def deduce_type_array_access(self, ast):
        _, name, _ = ast

        _tp = self.get_type(name)

        tp = _tp.split(':')[1:-1]
        tp = ':'.join(tp)

        return tp
    #endregion
