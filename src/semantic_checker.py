from src.symbols import *
from typing import Literal

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
            self.errors.append(f'Assigned expression for <{name}> has undefined type, at line {ast.lineno}.')
            result = False
        
        if a_type != TYPE_NO_DEDUCED and a_type != tp:
            self.errors.append(f'Type annotation <{a_type}> for <{name}> doesn\'t matches expression of type <{tp}>, at line {ast.lineno}.')
            result = False
        
        if FORCE_TYPE_ANNOTATIONS and a_type is TYPE_NO_DEDUCED:
            self.errors.append(f'Must provide type annotation for variable <{name}>, at line {ast.lineno}.')
            result = False
        
        if tp.is_array and tp.item_type.is_array:
            self.errors.append(f'Hulk does not support multi-dimensional arrays, at line {ast.lineno}.')
            result = False

        if result:
            symbols.define_var(name, tp)

        return result

    def while_loop(self, ast, symbols: SymbolTable):
        _, condition, body = ast

        result = self.check(condition, symbols)
        ct = TypeInferenceService.deduce_type(condition, symbols)

        if ct != TYPES['bool']:
            self.errors.append(f'While loop condition must be of type bool, {ct} deduced, at line {ast.lineno}.')
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
            self.errors.append(f'If statement condition must be of type bool, {ct} deduced, at line {ast.lineno}.')
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
            self.errors.append(f'Elif statement condition must be of type bool, {ct} deduced, at line {ast.lineno}.')
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
            self.errors.append(f'Variable {ast[1]} used but not defined, at line {ast.lineno}.')
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
            self.errors.append(f'Cannot concatenate non-string types, at line {ast.lineno}.')
            result = False

        return result
    
    def assignment(self, ast, symbols: SymbolTable): # TODO
        _, lvalue, rvalue = ast
        
        result0 = self.check(lvalue, symbols) if type(lvalue) != str else symbols.is_defined(lvalue)
        tp_left = TypeInferenceService.deduce_type(lvalue, symbols) if type(lvalue) != str else symbols.get_type(lvalue)

        if not result0:
            if type(lvalue) == str:
                self.errors.append(f'Variable {lvalue} used but never declared, at line {ast.lineno}.')
            elif lvalue[0] == 'array_access':
                self.errors.append(f'Variable {lvalue[1]} used but never declared, at line {ast.lineno}.')
            else:
                self.errors.append(f'Fatal Error: unassigned variable, at line {ast.lineno}.')
            
            return False

        result1 = self.check(rvalue, symbols)
        tp_right = TypeInferenceService.deduce_type(rvalue, symbols)

        if tp_left != tp_right:
            self.errors.append(f'Cannot convert type <{tp_right}> to <{tp_left}>, at line {ast.lineno}.')
        
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
                self.errors.append(f'No deducible type for array item, at line {ast.lineno}.')
                break
            if not result:
                break

        type_matches = all(x == types[0] and x != None for x in types)
    
        return type_matches and result
    
    def array_access(self, ast, symbols: SymbolTable):
        _, name, index = ast

        index_tp = TypeInferenceService.deduce_type(index, symbols)

        if index_tp == TYPE_NO_DEDUCIBLE:
            _symbols = symbols.make_child()
            _symbols.unset_current_type()
            _symbols.variables = _symbols.globals
            index_tp = TypeInferenceService.deduce_type(index, _symbols)

        result = True

        if not symbols.is_defined(name, 'var'):
            self.errors.append(f'Variable {name} used but not defined, at line {ast.lineno}.')
            result = False
        
        if result:
            tp = symbols.get_type(name)
            if not tp.is_array:
                self.errors.append(f'Object of type <{tp}> cannot be indexed, at line {ast.lineno}.')
                result = False

        if index_tp != TYPES['number']:
            print(index, symbols.variables)
            self.errors.append('Can only index array using a number, at line {ast.lineno}.')
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
            self.errors.append(f'Function <{func}> not defined, at line {ast.lineno}.')
            return False

        param_types = symbols.get_params_type(func)

        if symbols.is_on_type_body() and not symbols.is_builtin(func):
            param_types = param_types[1:]

        i = -1
        for i, param in enumerate(params):
            tp = TypeInferenceService.deduce_type(param, symbols)
            
            if not SymbolType.can_convert(tp, param_types[i]):
                self.errors.append(F'Cannot convert parameter from <{tp}> to <{param_types[i]}>, at line {ast.lineno}.')
                return False
        
        if len(param_types) != i + 1:
            self.errors.append(f'Function <{func[9:]}> requires {len(param_types)} arguments ({i + 1} given), at line {ast.lineno}.')
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
                self.errors.append(f'Type for param <{param}> could not be infered, at line {ast.lineno}.')
                result = False
            else:
                _symbols.define_var(param, param_types[param])
        
        _symbols.set_function(name)

        if body[0] == 'compound_instruction':
            TypeInferenceService.deduce_type(body, _symbols)
            tp = TypeInferenceService.return_statements_types[_symbols.current_function]
            valid = all([tp[0] == t for t in tp])
            if not valid:
                self.errors.append(f'Function <{name[9:]}> has unconsistent return statements, at line {ast.lineno}.')
                result = False
            elif len(tp) == 0:
                self.errors.append(f'Function <{name[9:]}> with compound body requires a return statement, at line {ast.lineno}.')
                result = False
            else:
                tp = tp[0]
        else:
            tp = TypeInferenceService.deduce_type(body, _symbols)      

        if tp != ret_type:
            self.errors.append(f'Function <{name[9:]}> does not returns always type {ret_type} ({tp} found), at line {ast.lineno}.')
            result = False

        result = result and tp == ret_type
        result = self.check(body, _symbols) and result

        ast[5] = _symbols
        return result
    
    def return_statement(self, ast, symbols: SymbolTable):
        if not symbols.is_on_function():
            self.errors.append(f'Cannot use a return statement oustside a function, at line {ast.lineno}.')
            return False
        
        _, expr = ast

        return self.check(expr, symbols)

    def break_statement(self, ast, symbols: SymbolTable):
        if not symbols.is_on_loop():
            self.errors.append(f'Cannot use a break statement oustside a loop, at line {ast.lineno}.')
            return False
        return True
    
    def continue_statement(self, ast, symbols: SymbolTable):
        if not symbols.is_on_loop():
            self.errors.append(f'Cannot use a continue statement oustside a loop, at line {ast.lineno}.')
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
                    self.errors.append(f'Type declaration for <{name}> has circular references, at line {type.lineno}.')
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
                            self.errors.append(f'Type declaration of <{name}> is missing inherited parameter <{p}> of type <{_inherited_params[p]}>, at line {type.lineno}.')
                            return None
                        if _inherited_params[p] != _params[p]:
                            self.errors.append(f'Inherited param <{p}> for type <{name}> must be of type <{_inherited_params[p]}>, at line {type.lineno}.')
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
                self.errors.append(f'Redeclaration of property <{nm}> from object <{name}>, at line {ast.lineno}.')
            
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
            self.errors.append(f'Some constructor arguments for type <{type}> are incorrect, at line {ast.lineno}.')
            return False
        
        result = len(sy.params) == len(args)

        if not result:
            self.errors.append(f'The constructor for type <{type}> takes {len(sy.params)}, {len(args)} given, at line {ast.lineno}.')
            return False

        return True
    
    def access(self, ast, symbols: SymbolTable):
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
            self.errors.append(f'Cannot access property or variable <{left}>, at line {ast.lineno}.')
            return False

        _symbols = symbols.make_child_inside_type(type.type)
        
        if not isinstance(right, str):
            return self.check(right, _symbols)
        
        if _symbols.is_defined(right, 'var'):
            result = _symbols.get_type(right) != None
            if not result:
                self.errors.append(f'Cannot access property or variable <{right}>, at line {ast.lineno}.')
        
        raise Exception('This should never happen')
    
    def downcast(self, ast, symbols: SymbolTable):
        _, var, type = ast

        var_type = symbols.get_type(var[1]).type
        var_type = symbols.get_symbol(var_type, 'type')
        
        new_type = symbols.get_symbol(type[1], 'type')

        if new_type == None:
            self.errors.append(f'Cannot downcast to non existing type, at line {ast.lineno}.')
            return False
        
        if new_type not in var_type.ancestors:
            self.errors.append(f'Type <{TYPES[var_type.name]}> has no valid downcast for type <{TYPES[new_type.name]}>, at line {ast.lineno}.')
        
        
        return TYPES[new_type.name]
