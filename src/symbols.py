from typing import Literal

class SymbolType:
    def __init__(self, annotation: str, type: str, is_error: bool = False) -> None:
        self.annotation = annotation
        self.type = type
        self.is_error = is_error
        self.is_array = False
        self.size = 4

    def __str__(self) -> str:
        return f'TYPE <{self.annotation}>'
    
    __repr__ = __str__

    def __eq__(self, __value: object) -> bool:
        return  self  and __value and\
                type(self) == type(__value) and\
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
        st.size = size * items_type.size
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
            tmp = cls.make_array_type(item_type, 0)
            tmp.size = 4
            return tmp
        return TYPE_NOT_FOUND
    
    @classmethod
    def resolve_from_name(cls, name):
        if name in TYPES:
            return TYPES[name]
        return TYPE_NOT_FOUND
    
    @classmethod
    def can_convert(cls, type_a, type_b):
        if type_a == type_b:
            return True
        # if type_a not in ALLOWED_CONVERTIONS:
        #     return False
        # return type_b in ALLOWED_CONVERTIONS[type_a]
        return False

    @classmethod
    def create_type(cls, type):
        if not isinstance(type, SymbolObject):
            raise Exception("cannot create non-type as a type")
        
        # size = TYPES[type.parent_type.name].size if type.parent_type else 0
        size = sum([4 for prop in type.properties]) + 4
        
        type = SymbolType(type.name, type.name)
        type.size = size

        TYPES[type.type] = ANNOTATIONS[type.annotation] = type
    
    @classmethod
    def __getitem__(cls, index):
        return TYPES[index]

#region Symbols
class Symbol:
    def __init__(self, name: str, _type: SymbolType, alias: int = 0) -> None:
        self.name = name
        self.type = SymbolType.resolve_from_name(_type) if type(_type) is not SymbolType else _type
        self.alias = alias


class SymbolFunction(Symbol):
    def __init__(self, name: str, return_type: SymbolType, param_types: tuple[SymbolType]) -> None:
        super().__init__(name, TYPES['function'], 0)
        self.return_type = return_type
        self.param_types = param_types


class SymbolObject(Symbol):
    def __init__(self,name: str, properties: list[Symbol], methods: list[SymbolFunction], params: list[SymbolType], parent_type = None) -> None:
        super().__init__(name, TYPES['type'], 0)

        if isinstance(parent_type, SymbolObject):
            self.ancestors = parent_type.ancestors

            self.ancestors.append(parent_type)

            properties = list(parent_type.properties.values()) + properties
            methods = list(parent_type.methods.values()) + methods
            
            self.inheritance = parent_type.inheritance
            for symbol in parent_type.methods:
                if symbol in self.inheritance:
                    continue
                inherit_name = symbol
                tmp = inherit_name.split('_')[-1]
                ref_name = f'method_{name}_{tmp}'
                if ref_name in [s.name for s in methods]:
                    continue
                self.inheritance[ref_name] = inherit_name
        else:
            self.ancestors = []
            self.inheritance = dict()
        

        self.properties = {symbol.name: symbol for symbol in properties}
        self.methods = {symbol.name: symbol for symbol in methods}
        self.params = params
        self.parent_type = parent_type
#endregion


class SymbolTable:
    def __init__(self) -> None:
        self.variables = dict()
        self.functions = dict()
        self.types = dict()
        self.globals = dict()

        self.current_function = 'main'
        self.loops = 0
        self.current_type = None

        self.object_property_address = dict()

    def make_child(self):
        child = SymbolTable()

        child.variables = self.variables.copy()
        child.functions = self.functions.copy()
        child.types = self.types.copy()
        child.globals = self.globals.copy()
        child.current_function = self.current_function[:]
        child.loops = self.loops
        child.current_type = self.current_type[:] if isinstance(self.current_type, str) else None
        child.object_property_address = self.object_property_address.copy()

        return child
    
    def make_child_inside_type(self, type_name: str):
        type = self.get_symbol(type_name, 'type')

        if not type:
            return None
        
        child = SymbolTable()
        
        if not self.is_on_type_body():
            child.globals = self.variables
        else:
            child.globals = self.globals

        for prop in type.properties:
            child.variables[prop] = type.properties[prop]
        
        for meth in type.methods:
            child.functions[meth] = type.methods[meth]
        
        child.types = self.types.copy()
        child.object_property_address = self.object_property_address.copy()
        child.current_type = type_name
        
        return child

    def define_var(self, name: str, type : SymbolType, alias = 0):
        self.variables[name] = Symbol(name, type, alias)
    
    def define_function(self, name: str, return_type: SymbolType, param_types: list[SymbolType]):
        self.functions[name] = SymbolFunction(name, return_type, param_types)
    
    def define_type(self, name: str, properties: list[Symbol], methods: list[SymbolFunction], params: list[SymbolType], parent_type: SymbolObject = None):
        self.types[name] = SymbolObject(name, properties, methods, params, parent_type)

        if parent_type:
            self.object_property_address[name] = self.object_property_address[parent_type.name].copy()
        else:
            self.object_property_address[name] = dict()

        for i, prop in enumerate(properties):
            if prop.name in self.object_property_address[name]:
                continue
            self.object_property_address[name][prop.name] = len( self.object_property_address[name])
    
    def is_defined(self, name: str, select: Literal['var', 'func', 'type', 'builtin']):
        return self.get_symbol(name, select) != None
    
    def is_builtin(self, name: str) -> bool:
        return name in BUILTIN_FUNCTIONS

    def get_type(self, name: str) -> str:
        sym = self.get_symbol(name, 'var')
        return sym.type if sym else None
    
    def get_return_type(self, name: str) -> str:
        sym = self.get_symbol(name, 'func')
        return sym.return_type if sym else None
    
    def get_params_type(self, name: str) -> tuple[str]:
        sym = self.get_symbol(name, 'func')
        if not sym:
            sym = self.get_symbol(name, 'builtin')
        return sym.param_types if sym else None

    def get_symbol(self, name: str, select: Literal['var', 'func', 'type', 'builtin']) -> Symbol|None:
        if name in self.variables and select == 'var':
            return self.variables[name]
        elif name in self.functions and select == 'func':
            return self.functions[name]
        elif name in self.types and select == 'type':
            return self.types[name]
        elif name in BUILTIN_FUNCTIONS and select == 'builtin':
            return BUILTIN_FUNCTIONS[name]
        return None
    
    def set_function(self, name:str) -> None:
        self.current_function = name
    
    def unset_function(self) -> None:
        self.current_function = 'main'
    
    def add_loop(self) -> None:
        self.loops += 1
    
    def remove_loop(self) -> None:
        self.loops -= 1

    def is_on_function(self) -> bool:
        return self.current_function != 'main'

    def is_on_loop(self) -> bool:
        return 0 != self.loops

    def set_current_type(self, name: str):
        self.current_type = name
    
    def unset_current_type(self):
        self.current_type = None
    
    def is_on_type_body(self) -> bool:
        return self.current_type != None

class TypeInferenceService:
    return_statements_types = dict()

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

    @classmethod
    def try_deduce_properties_and_methods_types(cls, type):
        _, _, name, body = type
        
        methods = {func[2] : cls.try_deduce_function_types(func) for func in body['methods']}

        properties = dict()
        for _, name, value in body['properties']:
            _, name, annotation = name

            type = SymbolType.resolve_from_annotation(annotation)
            properties[name] = type

        return methods, properties

    #endregion

    @classmethod
    def deduce_type(cls, ast, symbols: SymbolTable):
        try:
            if symbols.current_function not in cls.return_statements_types:
                cls.return_statements_types[symbols.current_function] = []

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
        elif operator in ('&&', '||') and t1 == TYPES['bool']:
            return TYPES['bool']
        elif operator in ('@', '@@') and t1 == TYPES['string']:
            return TYPES['string']
        else :
            return TYPE_NO_DEDUCIBLE
    
    @classmethod
    def deduce_type_str_concat(cls, ast, symbols: SymbolTable):
        _, _, t0, t1 = ast
        
        t0 = cls.deduce_type(t0, symbols)
        t1 = cls.deduce_type(t1, symbols)

        if t0 != t1 or t0 != TYPES['string']:
            return TYPE_NO_DEDUCIBLE
        
        return TYPES['string']

    @classmethod
    def deduce_type_unary(cls, ast, symbols: SymbolTable):
        _, operator, term = ast

        t1 = cls.deduce_type(ast[2], symbols)
        
        if ast[1] in ('-', '+') and t1 == TYPES['number']:
            return TYPES['number']
        elif ast[1] == '!' and t1 == TYPES['bool']:
            return TYPES['bool']
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

        if not symbols.is_builtin(name) and symbols.is_on_type_body():
            name = f'method_{symbols.current_type}_{name}'
        elif not symbols.is_builtin(name):
            name = f'function_{name}'

        if not symbols.is_builtin(name):
            if symbols.is_defined(name, 'func'):
                return symbols.get_return_type(name)
            
            return TYPE_NO_DEDUCIBLE
        else:
            if symbols.is_defined(name, 'builtin'):
                return symbols.get_symbol(name, 'builtin').return_type
            
            return TYPE_NO_DEDUCIBLE

    @classmethod
    def deduce_type_compound_instruction(cls, ast, symbols: SymbolTable):
        return_type = TYPE_NO_DEDUCED

        _, instructions = ast

        for inst in instructions:
            return_type = cls.deduce_type(inst, symbols)
        
        return return_type

    @classmethod
    def deduce_type_conditional(cls, ast, symbols: SymbolTable):
        _, if_statement, elif_statements, else_statement = ast

        tp = TYPE_NO_DEDUCED

        if if_statement:
            _, _, body = if_statement
            tp = cls.deduce_type(body, symbols)
        if elif_statements:
            for elif_statement in elif_statements:
                _, _, body = elif_statement
                _tp = cls.deduce_type(body, symbols)
                
                if tp == TYPE_NO_DEDUCED or tp == _tp:
                    tp = _tp
                else:
                    tp = TYPE_NO_DEDUCIBLE
        if else_statement:
            _, body = else_statement
            _tp = cls.deduce_type(body, symbols)
            
            if tp == TYPE_NO_DEDUCED or tp == _tp:
                tp = _tp
            else:
                tp = TYPE_NO_DEDUCIBLE
        
        return tp

    @classmethod
    def deduce_type_return_statement(cls, ast, symbols: SymbolTable):
        _, expr = ast
        tp = cls.deduce_type(expr, symbols)
        cls.return_statements_types[symbols.current_function].append(tp)
        return tp
    
    @classmethod
    def deduce_type_executable_expression(cls, ast, symbols: SymbolTable):
        _, expr = ast
        return cls.deduce_type(expr, symbols)
    
    @classmethod
    def deduce_type_var_inst(cls, ast, symbols: SymbolTable):
        _, variables, body, _ = ast

        _symbols = symbols.make_child()

        for _, annotated_name, value in variables:
            _, name, annotation = annotated_name
            tp = SymbolType.resolve_from_annotation(annotation)
            
            _symbols.define_var(name, tp)
        
        return cls.deduce_type(body, _symbols)
    
    @classmethod
    def deduce_type_while_loop(cls, ast, symbols: SymbolTable):
        _, _, body = ast
        return cls.deduce_type(body, symbols)
    
    @classmethod
    def deduce_type_assignment(cls, ast, symbols: SymbolTable):
        return TYPE_NOT_FOUND
    
    @classmethod
    def deduce_type_continue_statement(cls, ast, symbols: SymbolTable):
        return TYPE_NOT_FOUND
    
    @classmethod
    def deduce_type_break_statement(cls, ast, symbols: SymbolTable):
        return TYPE_NOT_FOUND
    
    @classmethod
    def deduce_type_access(cls, ast, symbols: SymbolTable):
        _, left, right = ast
        
        if left[0] == 'function_call':
            _, left, _ = left
            type = symbols.get_return_type(left)
        elif left[0] == 'array_access':
            _, left, _ = left
            type = symbols.get_type(left)
            if type.is_array:
                type = type.item_type
            else:
                type = TYPE_NO_DEDUCIBLE
        elif left[0] == 'name':
            _, left = left
            type = symbols.get_type(left)
        else:
            raise Exception(f"There is no behavior for {left}")
        
        if not type:
            return TYPE_NO_DEDUCIBLE

        _symbols = symbols.make_child_inside_type(type.type)
        
        if not isinstance(right, str):
            return cls.deduce_type(right, _symbols)
        
        if _symbols.is_defined(right, 'var'):
            return _symbols.get_type(right)
        
        return TYPE_NO_DEDUCIBLE
    
    @classmethod
    def deduce_type_instance(cls, ast, symbols: SymbolTable):
        _, type, params = ast
        
        ins = symbols.get_symbol(type, 'type')

        if ins:
            return TYPES[ins.name]
        return TYPE_NO_DEDUCIBLE
    
    @classmethod
    def deduce_type_name(cls, ast, symbols: SymbolTable):
        _, name = ast

        type = symbols.get_type(name)

        return type if type != None else TYPE_NO_DEDUCIBLE

    @classmethod
    def deduce_type_assignable(cls, ast, symbols: SymbolTable):
        _, left, right = ast

        if left[0] == 'array_access':
            _, left, _ = left
            type = symbols.get_return_type(left)
            if type != None and type.is_array:
                type = type.item_type
            else:
                type = None
        elif left[0] == 'name':
            left = left[1]
            type = symbols.get_type(left)
        
        if type == None:
            return TYPE_NO_DEDUCIBLE
        
        _symbols = symbols.make_child_inside_type(type.type)
        
        if not isinstance(right, str):
            return cls.deduce_type(right, _symbols)
        
        if _symbols.is_defined(right, 'var'):
            right = _symbols.get_type(right)

            if right != None:
                return right
        
        return TYPE_NO_DEDUCIBLE
    
    @classmethod
    def deduce_type_downcast(cls, ast, symbols: SymbolTable):
        _, var, type = ast

        var_type = symbols.get_type(var[1]).type
        var_type = symbols.get_symbol(var_type, 'type')
        
        new_type = symbols.get_symbol(type[1], 'type')

        if new_type == None or new_type not in var_type.ancestors:
            return TYPE_NO_DEDUCIBLE
        
        return TYPES[new_type.name]

TYPES = {
    'number' : SymbolType('Number', 'number'),
    'string' : SymbolType('String', 'string'),
    'bool' : SymbolType('Bool', 'bool'),
    'function': SymbolType('Function', 'function'),
    'type': SymbolType('Type', 'type'),
    'object': SymbolType('Object', 'object'),
}

TYPE_NO_DEDUCED = SymbolType('NO_DEDUCED', 'NO_DEDUCED')
TYPE_NO_DEDUCIBLE = SymbolType('NO_DEDUCIBLE', 'NO_DEDUCIBLE', True) # This is an type marked as error
TYPE_NOT_FOUND = SymbolType('NOT_FOUND', 'NOT_FOUND', True)

ANNOTATIONS = {TYPES[tp].annotation : TYPES[tp] for tp in TYPES}

BUILTIN_FUNCTIONS = {
    'print' : SymbolFunction('print', TYPES['string'], (TYPES['string'],)),
    'boolToString' : SymbolFunction('boolToString', TYPES['string'], (TYPES['bool'],)),
    'numberToString' : SymbolFunction('numberToString', TYPES['string'], (TYPES['number'],)),
}

FORCE_TYPE_ANNOTATIONS = True