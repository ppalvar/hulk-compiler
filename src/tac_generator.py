from queue import LifoQueue as stack
from src.semantic_checker import SymbolTable, SymbolType, TYPES, TypeInferenceService, ANNOTATIONS

class TacGenerator:
    def __init__(self, symbol_table: SymbolTable) -> None:
        self.var_count = 0
        self.code = dict()
        self.loop_labels = stack()
        self.current_function = 'main'
        self.symbol_table = symbol_table
        self.current_type = None

        self.symbol_renames = dict()

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
    
    def name(self, ast, symb_table: SymbolTable):
        _, name = ast
        type = symb_table.get_type(name)
        
        if not type and name in symb_table.globals:
            type = symb_table.globals[name].type

        t0 = self.get_next_var(type == TYPES['number'])
        
        self.create_assign(t0, name)

        return t0
    
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
            _, items = value

            tp.size = 4
            
            self.create_declare(name, 1, tp)
            
            t0 = self.get_next_var()
            self.create_array_alloc(t0, tp.item_type, len(items))
            self.create_assign(name, t0)

            for i, item in enumerate(items):
                t1 = self.generate(item, symb_table)
                self.create_array_set(name, i, t1)
            
        else:
            self.create_declare(name, 1, tp)
            t0 = self.generate(value, symb_table)
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
        elif var[0] == 'name':
            self.create_assign(var[1], t0)
        elif var[0] == 'access':
            var = self.flatten_access(var)

            t1 = self.generate(var[0], symb_table)
            _type, _symb_table = self.resolve_inner_props(var[0], symb_table)

            for prop in var[1 : -1]:
                tmp = prop
                   
                if prop[0] == 'array_access':
                    _, prop, index = prop
                
                    addr = _symb_table.object_property_address[_symb_table.current_type][prop] * 4
                    self.create_prop_get(t1, t1, addr)
                    
                    index = self.generate(index, _symb_table)
                    self.create_array_get(t1, index, t1)
                elif prop[0] == 'name':
                    prop = prop[1]
                    addr = _symb_table.object_property_address[_type.type][prop] * 4
                    self.create_prop_get(t1, t1, addr)
                else:
                    raise Exception(f"There is no behavior for {tmp}")
                
                _type, _symb_table = self.resolve_inner_props(tmp, _symb_table)
            
            var = var[-1]
            
            if var[0] == 'name':
                var = var[1]
                addr = _symb_table.object_property_address[_type.type][var] * 4
                self.create_prop_set(t1, addr, t0)
            elif var[0] == 'array_access':
                _, var, index = var
                
                addr = _symb_table.object_property_address[_symb_table.current_type][var] * 4
                self.create_prop_get(t1, t1, addr)
                
                index = self.generate(index, _symb_table)
                self.create_array_set(t1, index, t0)

        
        return t0

    def compound_instruction(self, ast, symb_table: SymbolTable):
        _, instructions = ast
        for line in instructions:
            t0 = self.generate(line, symb_table)
        return t0
    
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
        _, items = ast
        
        t0 = self.get_next_var()

        self.create_array_alloc(t0, TypeInferenceService.deduce_type(items[0], symb_table), len(items))

        for i, item in enumerate(items):
            t1 = self.generate(item, symb_table)
            self.create_array_set(t0, i, t1)
        
        return t0
    
    def array_access(self, ast, symb_table: SymbolTable):
        _, name, index = ast
        t0 = self.get_next_var(symb_table.get_type(name).item_type == TYPES['number'])
        t1 = self.generate(index, symb_table)

        self.create_array_get(t0, t1, name)

        return t0
    
    def function_call(self, ast, symb_table: SymbolTable):
        _, name, params = ast

        if name.startswith('type') or symb_table.is_builtin(name):
            pass
        elif symb_table.current_type == None:
            name = f'function_{name}'
        else:
            name = f'method_{self.current_type}_{name}'
        
            symb = symb_table.get_symbol(symb_table.current_type, 'type')
            if name in symb.inheritance:
                name = symb.inheritance[name]
        
        if name.startswith('type'):
            param_types = symb_table.get_symbol(name[5 : ], 'type')
            param_types = param_types.params if param_types != None else []
            param_types = [p.type for p in param_types]
        else:
            param_types = symb_table.get_params_type(name)

        self.create_function_call_start()

        for i, param in enumerate(params):
            t0 = self.generate(param, symb_table)
            self.create_set_param(t0, param_types[i])
        
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
        
        if name.startswith('type'):
            pass
        elif self.current_type == None:
            name = f'function_{name}'
        else:
            name = f'method_{self.current_type}_{name}'

        tmp = []
        self.set_current_function(name)

        for i, _parm in enumerate(params):
            _, param, _ = _parm
            tmp.append((param, symb_table.get_params_type(self.current_function)[i]))
        
        self.create_get_params(tuple(tmp))
        
        t0 = self.generate(body, symbols)

        if t0:
            self.create_return(t0)
        
        self.reset_current_function()
        return None
    
    def return_statement(self, ast, symb_table: SymbolTable):
        _, value = ast

        t0 = self.generate(value, symb_table)

        self.create_return(t0)
        return None
    
    def executable_expression(self, ast, symb_table: SymbolTable):
        _, expr = ast
        t0 = self.generate(expr, symb_table)
        return t0
    
    def str_concat(self, ast, symb_table: SymbolTable):
        _, is_double, t0, t1 = ast

        self.create_function_call_start()

        t0 = self.generate(t0, symb_table)
        self.create_set_param(t0, TYPES['string'])
        t1 = self.generate(t1, symb_table)
        self.create_set_param(t1, TYPES['string'])

        t2 = self.get_next_var()
        self.create_assign(t2, is_double)
        self.create_set_param(t2, TYPES['bool'])
        
        t3 = self.get_next_var()
        self.create_func_call(t3, 'concat_strings')

        self.create_function_call_end()

        return t3
    
    def type_declaration(self, ast, symb_table: SymbolTable):
        _, parent_type, name, body = ast

        params = []
        if not isinstance(name, str):
            _, name, params = name
        
        self.set_current_type(name)
        
        params = [nm for _, nm, _ in params]
        params = [(e.name, e.type) for e in symb_table.get_symbol(name, 'type').params]

        symbols = symb_table.make_child()
        
        for _name, _type in params:
            symbols.define_var(_name, _type)

        #region TypeConstructor
        self.set_current_function(f'type_{name}')

        self.create_get_params(tuple(params))

        t0 = self.get_next_var()

        self.create_object_alloc(t0, SymbolType.resolve_from_name(name))
        
        for i, prop in enumerate(body['properties']):
            prop_name = prop[1][1]
            addr = symb_table.object_property_address[name][prop_name] * 4
            t1 = self.generate(prop[2], symbols)
            self.create_prop_set(t0, addr, t1)
        
        self.create_return(t0)
        self.reset_current_function()
        #endregion

        for method in body['methods']:
            # method_name = method[2]
            # method_name = f'type_{name}_method_{method_name}'

            # method[2] = method_name
            self.generate(method, symb_table.make_child_inside_type(name))

        self.reset_current_type()
        return t0
    
    def access(self, ast, symb_table: SymbolTable):
        ast = self.flatten_access(ast)
        
        t0 = self.generate(ast[0], symb_table)
        f0 = self.get_next_var(True)

        _type, _symb_table = self.resolve_inner_props(ast[0], symb_table)

        r = None

        for prop in ast[1 : ]:
            tmp = prop

            if prop[0] == 'function_call':
                name = f'method_{_symb_table.current_type}_{prop[1]}'
                symb = _symb_table.get_symbol(_symb_table.current_type, 'type')
                if name in symb.inheritance:
                    name = symb.inheritance[name]

                self.create_function_call_start()

                self.create_set_param(t0, _type)

                params = [p for p in prop[2]]

                for i, param in enumerate(params):
                    _t0 = self.generate(param, symb_table)

                    self.create_set_param(_t0, symb_table.get_params_type(name)[i])
                
                r = f0 if _symb_table.get_return_type(name) == TYPES['number'] else t0

                self.create_func_call(r, name)
                self.create_function_call_end()
                
            elif prop[0] == 'array_access':
                _, prop, index = prop
                addr = _symb_table.object_property_address[_type.type][prop] * 4
                self.create_prop_get(t0, t0, addr)

                index = self.generate(index, _symb_table)

                r = t0 if _symb_table.get_type(prop).item_type != TYPES['number'] else f0
                
                self.create_array_get(r, index, t0)
            elif prop[0] == 'name':
                prop = prop[1]
                r = t0 if _symb_table.get_type(prop) != TYPES['number'] else f0
                addr = _symb_table.object_property_address[_type.type][prop] * 4
                self.create_prop_get(r, t0, addr)

            else:
                raise Exception(f"There is no behavior for {tmp}")
            
            _type, _symb_table = self.resolve_inner_props(tmp, _symb_table)
        return r

    def instance(self, ast, symb_table: SymbolTable):
        _, name, args = ast

        # symb_table = symb_table.make_child_inside_type(name)

        name = f'type_{name}'

        # args = [a for a in reversed(args)]

        ast = ('function_call', name, args)

        return self.generate(ast, symb_table)
    
    def downcast(self, ast, symb_table: SymbolTable):
        _, var, _ = ast

        
        t0 = self.get_next_var()

        self.create_assign(t0, var[1])

        return t0

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
    
    def create_object_alloc(self, t0, type):
        self.create_function_codespace()
        self.code[self.current_function].append(('alloc', t0, type))
    
    def create_prop_set(self, t0, address, t1):
        self.create_function_codespace()
        self.code[self.current_function].append(('set', t0, address, t1))
    
    def create_prop_get(self, t0, obj, address):
        self.create_function_codespace()
        self.code[self.current_function].append(('get', t0, obj, address))
    
    @classmethod
    def flatten_access(cls, access) -> list:
        _, left, right = access

        if right[0] in ('access', 'assignable'):
            return [left] + cls.flatten_access(right)
        
        return [left, right]
    
    @classmethod
    def resolve_inner_props(cls, prop, symbols: SymbolTable):
        if prop[0] == 'function_call':
            _, prop, _ = prop
            func = f'method_{symbols.current_type}_{prop}'
            symb = symbols.get_symbol(symbols.current_type, 'type')

            if func in symb.inheritance:
                func = symb.inheritance[func]
            
            type = symbols.get_return_type(func)

        elif prop[0] == 'array_access':
            _, prop, _ = prop
            type = symbols.get_type(prop)
            if type.is_array:
                type = type.item_type
            else:
                type = None
        elif prop[0] == 'name':
            _, prop = prop
            type = symbols.get_type(prop)
            if prop == 'self':
                type_name = symbols.get_symbol(symbols.current_type, 'type').name
                type = TYPES[type_name]
        else:
            raise Exception(f"There is no behavior for {prop}")

        return (type, symbols.make_child_inside_type(type.type))
    #endregion
    
    #region context managers
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
    
    def set_current_type(self, name: str):
        self.current_type = name
    
    def reset_current_type(self):
        self.current_type = None
    #endregion