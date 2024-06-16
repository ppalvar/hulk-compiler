import copy

class SymbolType:
    def __init__(self, annotation: str, type: str, is_error: bool = False) -> None:
        self.annotation = annotation
        self.type = type
        self.is_error = is_error
        self.is_array = False
        self.size = 0

    def __str__(self) -> str:
        return f'TYPE <{self.annotation}>'
    
    __repr__ = __str__

    def __eq__(self, __value: object) -> bool:
        return  self  and __value and\
                self.annotation == __value.annotation  and\
                self.type == __value.type and\
                self.is_error == __value.is_error and\
                self.is_array == __value.is_array 
    
    def __ne__(self, __value: object) -> bool:
        return not self == __value
    
    def __hash__(self):
        return hash((self.annotation, self.type, self.is_error, self.is_array, self.size))

    @classmethod
    def make_array_type(cls, items_type, size: int):
        if type(items_type) != SymbolType:
            return TYPE_NOT_FOUND
        ann = f'Array<{items_type.annotation}>'
        tpn = f'array:{items_type.type}'

        st = SymbolType(ann, tpn)
        st.size = size
        st.is_array = True
        st.item_type = items_type

        return st

    @classmethod
    def get_array_item_type(cls, array_type):
        if type(array_type) != SymbolType:
            return TYPE_NOT_FOUND
        
        return array_type.item_type
    
    @classmethod
    def resolve_from_annotation(cls, annotation):
        if annotation is None:
            return TYPE_NO_DEDUCED
        if type(annotation) != str:
            raise TypeError(f'Type for <{annotation}> must be \'str\'')
        if annotation in ANNOTATIONS:
            return ANNOTATIONS[annotation]
        if annotation.startswith('Array_'):
            new_annotation = annotation[6 :]
            item_type = cls.resolve_from_annotation(new_annotation)
            return cls.make_array_type(item_type, 0)
        return TYPE_NOT_FOUND
    
    @classmethod
    def resolve_from_name(cls, name):
        if name in TYPES:
            return TYPES[name]
        return TYPE_NOT_FOUND
    
    @classmethod
    def can_convert(cls, type_a, type_b):
        if type_a not in ALLOWED_CONVERTIONS:
            return False
        return type_b in ALLOWED_CONVERTIONS[type_a]


class Symbol:
    def __init__(self, _type:str, alias: int, return_type: str = None, param_types: tuple[str] = None) -> None:
        self.type = SymbolType.resolve_from_name(_type) if type(_type) is not SymbolType else _type
        self.alias = alias
        self.return_type = SymbolType.resolve_from_name(return_type) if type(return_type) is not SymbolType else return_type
        self.param_types = [SymbolType.resolve_from_name(name) if type(name) is not SymbolType else name for name in param_types] if param_types else None


class SymbolTable:
    def __init__(self) -> None:
        self.symbols = dict()
        self.inside_function = False
        self.loops = []

    def make_child(self):
        return copy.deepcopy(self)
    
    def define(self, name: str, _type: str, alias: int=None, return_type: str = None, param_types: list[str] = None):
        if alias == None:
            alias = len(self.symbols)
        if type(_type) is str:
            _type = TYPES[_type]
        elif type(_type) is not SymbolType:
            raise Exception(f'Cannot use object of type <{type(_type)}> to typing a symbol')
        
        self.symbols[name] = Symbol(_type, alias, return_type, param_types)
    
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
    
    def set_function(self) -> None:
        self.inside_function = True
    
    def unset_function(self) -> None:
        self.inside_function = False
    
    def add_loop(self) -> None:
        self.loops.append(None)
    
    def remove_loop(self) -> None:
        self.loops.pop(0)

    def is_on_function(self) -> bool:
        return self.inside_function

    def is_on_loop(self) -> bool:
        return 0 != len(self.loops)


class TypeInferenceService:
    #region: type inference for function parameters and return type

    @classmethod
    def try_deduce_function_types(cls, func):
        _, return_type, _, params, _, _ = func

        return_type = SymbolType.resolve_from_annotation(return_type)

        param_types = {}
        for param in params:
            _, param_name, annotation = param
            param_type = SymbolType.resolve_from_annotation(annotation)
            param_types[param_name] = param_type
        
        
        if FORCE_TYPE_ANNOTATIONS:
            return return_type, param_types

        raise NotImplementedError('Implement type inference for func parameters')

    #endregion

    @classmethod
    def deduce_type(cls, ast, symbols: SymbolTable = None):
        try:
            method = getattr(cls, 'deduce_type_' + ast[0], None)
            result = method(ast, symbols)
            
            return result
        except:
            if type(ast[0]) is str:
                tp = SymbolType.resolve_from_name(ast[0])

                if tp is TYPE_NOT_FOUND:
                    print(f'Cannot deduce type for {ast}')
                    raise
                
                return tp
            raise
    
    @classmethod
    def deduce_type_binop(cls, ast, symbols: SymbolTable):
        _, operator, term_a, term_b = ast
        
        t1 = cls.deduce_type(term_a, symbols)
        t2 = cls.deduce_type(term_b, symbols)

        if t1 != t2 or t1 == TYPE_NO_DEDUCIBLE:
            return TYPE_NO_DEDUCIBLE
        elif operator in ('==', '<=', '>=', '>', '<', '!=') and t1 == TYPES['number']:
            return TYPES['bool']
        elif operator in ('+', '-', '*', '/') and t1 == TYPES['number']:
            return TYPES['number']
        elif operator in ('&&', '||') and t1 == TYPES[bool]:
            return TYPES['bool']
        else :
            return TYPE_NO_DEDUCIBLE
    
    @classmethod
    def deduce_type_unary(cls, ast, symbols: SymbolTable):
        _, operator, term = ast

        t1 = cls.deduce_type(ast[2], symbols)
        
        if ast[1] in ('-', '+') and t1 == 'number':
            return t1
        elif ast[1] == '!' and t1 == 'bool':
            return 'bool'
        else:
            return TYPE_NO_DEDUCIBLE
    
    @classmethod
    def deduce_type_identifier(cls, ast, symbols: SymbolTable):
        if symbols.is_defined(ast[1]):
            return symbols.get_type(ast[1])
        return TYPE_NO_DEDUCIBLE
    
    @classmethod
    def deduce_type_grouped(cls, ast, symbols: SymbolTable):
        return cls.deduce_type(ast[1], symbols)
    
    @classmethod
    def deduce_type_array_declaration_explicit(cls, ast, symbols: SymbolTable):
        _, items = ast

        types = []
        for item in items:
            tp = cls.deduce_type(item, symbols)
            
            if not tp:
                return TYPE_NO_DEDUCIBLE
            
            types.append(tp)

        type_matches = all(x == types[0] and x != TYPE_NO_DEDUCIBLE for x in types)

        if type_matches:
            return SymbolType.make_array_type(types[0], len(items))

        return TYPE_NO_DEDUCIBLE
    
    @classmethod
    def deduce_type_array_access(cls, ast, symbols: SymbolTable):
        _, name, _ = ast

        _tp = symbols.get_type(name)

        tp = SymbolType.get_array_item_type(_tp)

        return tp
    
    @classmethod
    def deduce_type_function_call(cls, ast, symbols: SymbolTable):
        _, name, _ = ast

        if symbols.is_defined(name):
            return symbols.get_return_type(name)
        
        return TYPE_NO_DEDUCIBLE


class SemanticChecker:
    def __init__(self) -> None:
        self.errors = []

    def check(self, ast, symbols: SymbolTable=None):
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
    
    def var_inst(self, ast, symbols:SymbolTable):
        _, declarations, body, _ = ast
        
        result = True
        _symbols = symbols.make_child()
        
        for decl in declarations:
            tmp = self.check(decl, _symbols)
            result = tmp and result

        ast[3] = _symbols
        result = result and self.check(body, _symbols)
        return result

    def declaration(self, ast, symbols: SymbolTable):
        _, annotated_name, value = ast
        _, name, annotation = annotated_name

        a_type = SymbolType.resolve_from_annotation(annotation)
        
        tp = TypeInferenceService.deduce_type(value, symbols)
        
        result = self.check(value, symbols)

        if tp is TYPE_NO_DEDUCIBLE:
            self.errors.append(f'Assigned expression for <{name}> has undefined type')
            result = False
        
        if a_type != TYPE_NO_DEDUCED and a_type != tp:
            self.errors.append(f'Type annotation <{a_type}> for <{name}> doesn\'t matches expression of type <{tp}>')
            result = False
        
        if FORCE_TYPE_ANNOTATIONS and a_type is TYPE_NO_DEDUCED:
            self.errors.append(f'Must provide type annotation for variable <{name}>')
            result = False
        
        if result:
            symbols.define(name, tp)

        return result


    def while_loop(self, ast, symbols: SymbolTable):
        _, condition, body = ast

        result = self.check(condition, symbols)
        ct = TypeInferenceService.deduce_type(condition, symbols)

        if ct != TYPES['bool']:
            self.errors.append(f'While loop condition must be of type bool, {ct} deduced')
            result = False

        symbols.add_loop()

        result = result and self.check(body, symbols)

        symbols.remove_loop()
        return result
    
    def conditional(self, ast, symbols: SymbolTable):
        _, condition, body = ast[1]

        result = self.check(condition, symbols)
        ct = TypeInferenceService.deduce_type(condition, symbols)

        if ct != TYPES['bool']:
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

    def elif_statement(self, ast, symbols: SymbolTable):
        _, condition, body = ast

        result = self.check(condition, symbols)
        ct = TypeInferenceService.deduce_type(condition, symbols)

        if ct != TYPES['bool']:
            self.errors.append(f'Elif statement condition must be of type bool, {ct} deduced')
            result = False
        
        result = result and self.check(body, symbols)
        return result
    
    def binop(self, ast, symbols: SymbolTable):
        result = self.check(ast[2], symbols) and self.check(ast[3], symbols) 
        tp = TypeInferenceService.deduce_type(ast, symbols)
        return result and (tp != TYPE_NO_DEDUCIBLE)

    def number(self, ast, symbols: SymbolTable):
        return True

    def identifier(self, ast, symbols: SymbolTable):
        result = symbols.is_defined(ast[1])
        if not result:
            self.errors.append(f'Variable {ast[1]} used but not defined')
        return result
    
    def grouped(self, ast, symbols: SymbolTable):
        return self.check(ast[1], symbols)
    
    def unary(self, ast, symbols: SymbolTable):
        result = self.check(ast[2], symbols)
        tp = TypeInferenceService.deduce_type(ast, symbols)
        return result and tp
    
    def bool(self, ast, symbols: SymbolTable):
        return True
    
    def string(self, ast, symbols: SymbolTable):
        return True
    
    def str_concat(self, ast, symbols: SymbolTable):
        result = self.check(ast[1], symbols) and self.check(ast[2], symbols)

        return result
    
    def assignment(self, ast, symbols: SymbolTable): # TODO
        _, lvalue, rvalue = ast
        
        result0 = self.check(lvalue, symbols) if type(lvalue) != str else symbols.is_defined(lvalue)
        tp_left = symbols.deduce_type(lvalue, symbols) if type(lvalue) != str else symbols.get_type(lvalue)

        if not result0:
            if type(lvalue) == str:
                self.errors.append(f'Variable {lvalue} used but never declared')
            elif lvalue[0] == 'array_access':
                self.errors.append(f'Variable {lvalue[1]} used but never declared')
            else:
                self.errors.append('Fatal Error: unassigned variable')
            
            return False

        result1 = self.check(rvalue, symbols)
        tp_right = TypeInferenceService.deduce_type(rvalue, symbols)

        if tp_left != tp_right:
            self.errors.append(f'Cannot convert type <{tp_right}> to <{tp_left}>')
        
        return result0 and result1 and tp_left == tp_right and tp_right != TYPE_NO_DEDUCIBLE
    
    def compound_instruction(self, ast, symbols: SymbolTable):
        return self.check(ast[1], symbols)
    
    def array_declaration_explicit(self, ast, symbols: SymbolTable):
        _, items = ast

        types = []
        result = True
        for item in items:
            tp = TypeInferenceService.deduce_type(item, symbols)
            types.append(tp)

            result = result and self.check(item, symbols)

            if tp is TYPE_NO_DEDUCIBLE:
                self.errors.append('No deducible type for array item')
                break
            if not result:
                break

        type_matches = all(x == types[0] and x != None for x in types)
    
        return type_matches and result
    
    def array_access(self, ast, symbols: SymbolTable):
        _, name, index = ast

        index_tp = TypeInferenceService.deduce_type(index, symbols)

        result = True

        if not symbols.is_defined(name):
            self.errors.append(f'Variable {name} used but not defined')
            result = False
        
        if result:
            tp = symbols.get_type(name)
            if not tp.is_array:
                self.errors.append(f'Object of type <{tp}> cannot be indexed')
                result = False

        if index_tp != TYPES['number']:
            self.errors.append('Can only index array using a number')
            result = False

        return result
    
    def function_call(self, ast, symbols: SymbolTable):
        _, func, params = ast
        
        result = symbols.is_defined(func)

        if not result:
            self.errors.append(f'Function <{func}> not defined')
            return False

        param_types = symbols.get_params_type(func)
        for i, param in enumerate(params):
            tp = TypeInferenceService.deduce_type(param, symbols)
            
            if not SymbolType.can_convert(tp, param_types[i]):
                self.errors.append(F'Cannot convert parameter from <{tp}> to <{param_types[i]}>')
                return False
        
        return True
        
    def function(self, ast, symbols: SymbolTable):
        _, _, name, params, body, _ = ast
        ret_type, param_types = TypeInferenceService.try_deduce_function_types(ast)
        
        symbols.define(name, TYPES['function'], None, ret_type, param_types.values())

        result = True

        _symbols = symbols.make_child()
        for _, param, _ in params :
            if param_types[param] in (TYPE_NO_DEDUCED, TYPE_NO_DEDUCIBLE, TYPE_NOT_FOUND):
                self.errors.append(f'Type for param <{param}> could not be infered')
                result = False
            else:
                _symbols.define(param, param_types[param])
        
        _symbols.set_function()
        result = result and self.check(body, _symbols)
        ast[5] = _symbols
        return result
    
    def return_statement(self, ast, symbols: SymbolTable):
        if not symbols.inside_function:
            self.errors.append('Cannot use a return statement oustside a function')
            return False
        return True

    def break_statement(self, ast, symbols: SymbolTable):
        if not symbols.is_on_loop():
            self.errors.append('Cannot use a break statement oustside a loop')
            return False
        return True
    

    def continue_statement(self, ast, symbols: SymbolTable):
        if not symbols.is_on_loop():
            self.errors.append('Cannot use a continue statement oustside a loop')
            return False
        return True


TYPES = {
    'number' : SymbolType('Number', 'number'),
    'string' : SymbolType('String', 'string'),
    'bool' : SymbolType('Bool', 'bool'),
    'function': SymbolType('Function', 'function'),
    'object': SymbolType('Object', 'object'),
}

# TODO: change the default conversions
ALLOWED_CONVERTIONS = {
    TYPES['number'] : (TYPES['number'], TYPES['string'], TYPES['object']),
    TYPES['string'] : (TYPES['string'], TYPES['object']),
    TYPES['bool'] : (TYPES['bool'], TYPES['string'], TYPES['object']),
    TYPES['object'] : (TYPES['string'], TYPES['object']),
    TYPES['function'] : (TYPES['function'], TYPES['string'], TYPES['object']),
}

TYPE_NO_DEDUCED = SymbolType('NO_DEDUCED', 'NO_DEDUCED')
TYPE_NO_DEDUCIBLE = SymbolType('NO_DEDUCIBLE', 'NO_DEDUCIBLE', True) # This is an type marked as error
TYPE_NOT_FOUND = SymbolType('NOT_FOUND', 'NOT_FOUND', True)

ANNOTATIONS = {TYPES[tp].annotation : TYPES[tp] for tp in TYPES}

BUILTIN_FUNCTIONS = {
    'print' : Symbol(TYPES['string'], 0, TYPES['string'], (TYPES['object'],))
}

FORCE_TYPE_ANNOTATIONS = True