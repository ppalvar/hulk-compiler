import copy
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
            properties = list(parent_type.properties.values()) + properties
            methods = list(parent_type.methods.values()) + methods
            
            self.inheritance = parent_type.inheritance
            for symbol in parent_type.methods:
                if symbol in self.inheritance:
                    continue
                inherit_name = symbol
                tmp = inherit_name.split('_')[-1]
                ref_name = f'method_{name}_{tmp}'
                self.inheritance[ref_name] = inherit_name
        else:
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

        self.current_function = 'main'
        self.loops = 0
        self.current_type = None

        self.object_property_address = dict()

    def make_child(self):
        child = SymbolTable()

        child.variables = self.variables.copy()
        child.functions = self.functions.copy()
        child.types = self.types.copy()
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
            self.object_property_address[name][prop.name] = i
    
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
            tp = cls.deduce_type(inst, symbols)
            return_type = tp
        
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
            type = symbols.get_return_type(left)
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

class SemanticChecker:
    def __init__(self) -> None:
        self.errors = []

    def check(self, ast, symbols: SymbolTable=None):
        result = True

        # here we assume this is the first call to this method
        if symbols == None: 
            functions = []
            types = []
            main_code = []

            for line in ast:
                if line[0] == 'function':
                    functions.append(line)
                elif line[0] == 'type_declaration':
                    types.append(line)
                else:
                    main_code.append(line)
            
            result = self.define_all_types(types)

            if not result:
                self.errors.append(f'Some types are being redefined')

            self.symbols = symbols = self.check_functions_and_types(functions, types)

            if symbols == None:
                return False

            for inst in functions + types:
                result = self.check(inst, symbols) and result

            return self.check(main_code, symbols) and result
        try:
            #this is a patch for the case of an empty program
            if not ast: 
                return True
            if type(ast[0]) != str:
                for line in ast:
                    result = result and self.check(line, symbols)
                
                return result
            
            else :
                method = self.__getattribute__(ast[0])
                result = result and method(ast, symbols)

                return result
        except:
            print('Error at:', ast)
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
        
        if tp.is_array and tp.item_type.is_array:
            self.errors.append('Hulk does not support multi-dimensional arrays')
            result = False

        if result:
            symbols.define_var(name, tp)

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
        result = self.check(ast[2], symbols) and self.check(ast[3], symbols)

        tp = TypeInferenceService.deduce_type(ast, symbols)

        if tp != TYPES['string']:
            self.errors.append(f'Cannot concatenate non-string types')
            result = False

        return result
    
    def assignment(self, ast, symbols: SymbolTable): # TODO
        _, lvalue, rvalue = ast
        
        result0 = self.check(lvalue, symbols) if type(lvalue) != str else symbols.is_defined(lvalue)
        tp_left = TypeInferenceService.deduce_type(lvalue, symbols) if type(lvalue) != str else symbols.get_type(lvalue)

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
        _, instructions = ast
        result = True
        for line in instructions:
            result = result and self.check(line, symbols)
        return result
    
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

        if not symbols.is_defined(name, 'var'):
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
        
        if not symbols.is_builtin(func) and symbols.is_on_type_body():
            symb = symbols.get_symbol(symbols.current_type, 'type')
            func = f'method_{symbols.current_type}_{func}'

            if func in symb.inheritance:
                func = symb.inheritance[func]

            result = symbols.is_defined(func, 'func')
        elif not symbols.is_builtin(func):
            func = f'function_{func}'
            result = symbols.is_defined(func, 'func')
        else:
            result = symbols.is_defined(func, 'builtin')
        
        if not result:
            self.errors.append(f'Function <{func}> not defined')
            return False

        param_types = symbols.get_params_type(func)

        if symbols.is_on_type_body() and not symbols.is_builtin(func):
            param_types = param_types[1:]

        i = -1
        for i, param in enumerate(params):
            tp = TypeInferenceService.deduce_type(param, symbols)
            
            if not SymbolType.can_convert(tp, param_types[i]):
                self.errors.append(F'Cannot convert parameter from <{tp}> to <{param_types[i]}>')
                return False
        
        if len(param_types) != i + 1:
            self.errors.append(f'Function <{func[9:]}> requires {len(param_types)} arguments ({i + 1} given)')
            return False

        return True
        
    def function(self, ast, symbols: SymbolTable):
        _, _, name, params, body, _ = ast
        
        if not symbols.is_builtin(name) and symbols.is_on_type_body():
            name = f'method_{symbols.current_type}_{name}'
        elif not symbols.is_builtin(name):
            name = f'function_{name}'

        ret_type, param_types = TypeInferenceService.try_deduce_function_types(ast)

        result = True

        _symbols = symbols.make_child()
        for _, param, _ in params :
            if param_types[param] in (TYPE_NO_DEDUCED, TYPE_NO_DEDUCIBLE, TYPE_NOT_FOUND):
                self.errors.append(f'Type for param <{param}> could not be infered')
                result = False
            else:
                _symbols.define_var(param, param_types[param])
        
        _symbols.set_function(name)

        if body[0] == 'compound_instruction':
            TypeInferenceService.deduce_type(body, _symbols)
            tp = TypeInferenceService.return_statements_types[_symbols.current_function]
            valid = all([tp[0] == t for t in tp])
            if not valid:
                self.errors.append(f'Function <{name[9:]}> has unconsistent return statements')
                result = False
            elif len(tp) == 0:
                self.errors.append(f'Function <{name[9:]}> with compound body requires a return statement')
                result = False
            else:
                tp = tp[0]
        else:
            tp = TypeInferenceService.deduce_type(body, _symbols)      

        if tp != ret_type:
            self.errors.append(f'Function <{name[9:]}> does not returns always type {ret_type} ({tp} found)')
            result = False

        result = result and tp == ret_type
        result = self.check(body, _symbols) and result

        ast[5] = _symbols
        return result
    
    def return_statement(self, ast, symbols: SymbolTable):
        if not symbols.is_on_function():
            self.errors.append('Cannot use a return statement oustside a function')
            return False
        
        _, expr = ast

        return self.check(expr, symbols)

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

    def executable_expression(self, ast, symbols: SymbolTable):
        _, expr = ast
        return self.check(expr, symbols)
    
    def name(self, ast, symbols: SymbolTable):
        _, name = ast

        return symbols.is_defined(name,'var')

    def define_all_types(self, types):
        for type in types:
            _, _, name, _ = type
            if not isinstance(name, str):
                name = name[1]
            
            type = SymbolType(name, name, True)
            
            if name in TYPES:
                return False

            ANNOTATIONS[name] = TYPES[name] = type
            
        return True

    def check_functions_and_types(self, functions, types) -> tuple[list[SymbolFunction], list[SymbolObject]]:
        st = SymbolTable()

        functions = functions.copy()
        types = types.copy()

        constructors = dict()

        while True:
            has_updated = False
            has_finished = True

            for i, func in enumerate(functions):
                if func != None: has_finished = False
                else: continue
                _, _, name, _, _, _ = func
                name = f'function_{name}'
                ret_type, param_types = TypeInferenceService.try_deduce_function_types(func)
                
                if ret_type == TYPE_NOT_FOUND or TYPE_NOT_FOUND in param_types:
                    continue

                st.define_function(name, ret_type, list(param_types.values()))
                functions[i] = None
                has_updated = True
            
            for i, type in enumerate(types):
                if type != None: has_finished = False
                else: continue

                _, parent_type, name, _ = type

                if parent_type != None:
                    _parent_type = st.get_symbol(parent_type, 'type')
                    # parent_type = SymbolType.resolve_from_annotation(parent_type)
                
                    if parent_type == None:
                        continue

                    parent_type = SymbolType.resolve_from_annotation(_parent_type.name)
                else:
                    _parent_type = None

                _methods, _properties = TypeInferenceService.try_deduce_properties_and_methods_types(type)
                
                params = []
                if not isinstance(name, str):
                    _, name, params = name
                
                if self.has_circular_reference(name, parent_type.type if parent_type else None, st):
                    self.errors.append(f'Type declaration for <{name}> has circular references')
                    return None
                
                if FORCE_TYPE_ANNOTATIONS:
                    params = [Symbol(n, SymbolType.resolve_from_annotation(a)) for _, n, a in params]
                else:
                    raise NotImplementedError()
                
                if parent_type:
                    inherited_params = self.get_inherited_params(st.get_symbol(parent_type.type, 'type'), st)
                    _inherited_params = {t.name: t.type for t in inherited_params}
                    _params = {t.name: t.type for t in params}

                    for p in _inherited_params:
                        if p not in _params:
                            self.errors.append(f'Type declaration of <{name}> is missing inherited parameter <{p}> of type <{_inherited_params[p]}>')
                            return None
                        if _inherited_params[p] != _params[p]:
                            self.errors.append(f'Inherited param <{p}> for type <{name}> must be of type <{_inherited_params[p]}>')
                            return None

                methods = []
                properties = []
                for method in _methods:
                    return_type, param_types = _methods[method]
                    if return_type == TYPE_NOT_FOUND or TYPE_NOT_FOUND in param_types.values():
                        break
                    
                    param_types = [TYPES[name]] + list(param_types.values())

                    methods.append(SymbolFunction(f'method_{name}_{method}', return_type, param_types))
                else:    
                    for prop in _properties:
                        if _properties[prop] == TYPE_NOT_FOUND:
                            break
                        properties.append(Symbol(prop, _properties[prop]))
                    else:
                        # If hits here the type can be checked (it may be valid)
                        if parent_type != TYPES['object'] and parent_type:
                            type[3]['properties'].extend(constructors[parent_type.type])
                        constructors[name] = type[3]['properties']

                        has_updated = True
                        st.define_type(name, properties, methods, params, _parent_type)
                        SymbolType.create_type(st.get_symbol(name, 'type'))
                        types[i] = None
            
            if has_finished:
                return st
            if not has_updated:
                self.errors.append('Error while checking types declarations')
                return None
    
    def has_circular_reference(self, type, parent_type, symbols: SymbolTable):
        if not parent_type:
            return False

        inheritance = set()
        inheritance.add(parent_type)

        while True:
            tmp = symbols.get_symbol(parent_type, 'type')
            if not tmp: break
            tmp = tmp.parent_type
            if not tmp: break
            
            parent_type = tmp.type
            if parent_type in inheritance:
                return True
            inheritance.add(parent_type)
        return type in inheritance

    def get_inherited_params(self, type: SymbolObject, symbols: SymbolTable):
        params = []
        
        while type:
            params.extend(type.params)

            type = type.parent_type if type else None
            if type: type = type.type
            type = symbols.get_symbol(type, 'type')
            
        return params        

    def type_declaration(self, ast, symbols: SymbolTable):
        _, parent_type, name, body = ast
        params = []

        if not isinstance(name, str):
            _, name, params = name
        
        symbols.set_current_type(name)

        if FORCE_TYPE_ANNOTATIONS:
            params = {n: SymbolType.resolve_from_annotation(a) for _, n, a in params}
        else:
            raise NotImplementedError()
        
        _symb = symbols.make_child()
        for p in params:
            _symb.define_var(p, params[p])

        result = True
        declared_props = set()
        for prop in body['properties']:
            nm = prop[1][1]
            if nm in declared_props:
                self.errors.append(f'Redeclaration of property <{nm}> from object <{name}>')
            
            declared_props.add(nm)
            
            tmp = self.check(prop, _symb.make_child())
            result = tmp and result

        methods = [[t, 
                    ret, 
                    nam, 
                    [('annotated_identifier', 'self', name)] + par, 
                    bod, None] 
                        for t, ret, nam, par, bod, _ in body['methods']]
        
        result = all([self.check(method, symbols) for method in methods]) and result
        
        body['methods'] = methods #this puts a symbol table in each method

        symbols.unset_current_type()
        return result

    def instance(self, ast, symbols: SymbolTable):
        _, type, args = ast

        sy = symbols.get_symbol(type, 'type')

        if not sy:
            return False
        
        args = [TypeInferenceService.deduce_type(arg, symbols) for arg in args]
        
        tmp = [s.type for s in sy.params]
        result = all([x == y for x, y in zip(tmp, args)])
        
        if not result:
            self.errors.append(f'Some constructor arguments for type <{type}> are incorrect')
            return False
        
        result = len(sy.params) == len(args)

        if not result:
            self.errors.append(f'The constructor for type <{type}> takes {len(sy.params)}, {len(args)} given')
            return False

        return True

    def assignable(self, ast, symbols: SymbolTable):
        _, left, right = ast

        if left[0] == 'array_access':
            _, left, _ = left
            type = symbols.get_return_type(left)
            if type != None and type.is_array:
                type = type.item_type
            else:
                type = None
        elif  left[0] == 'name':
            left = left[1]
            type = symbols.get_type(left)
        
        if type == None:
            self.errors.append(f'Property or variable <{left}> was not found')
            return False
        
        _symbols = symbols.make_child_inside_type(type.type)
        
        if not isinstance(right, str):
            return self.check(right, _symbols)
        
        if _symbols.is_defined(right, 'var'):
            right = _symbols.get_type(right)

            if right != None:
                return True
        self.errors.append(f'Property or variable <{right}> was not found')
        return False
    
    def access(self, ast, symbols: SymbolTable):
        _, left, right = ast
        
        if left[0] == 'function_call':
            _, left, _ = left
            type = symbols.get_return_type(left)
        elif left[0] == 'array_access':
            _, left, _ = left
            type = symbols.get_return_type(left)
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
            self.errors.append(f'Cannot access property or variable <{left}>')
            return False

        _symbols = symbols.make_child_inside_type(type.type)
        
        if not isinstance(right, str):
            return self.check(right, _symbols)
        
        if _symbols.is_defined(right, 'var'):
            result = _symbols.get_type(right) != None
            if not result:
                self.errors.append(f'Cannot access property or variable <{right}>')
        
        raise Exception('This should never happen')

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