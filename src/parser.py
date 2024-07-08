from src.lexer import *
from ply.yacc import yacc, YaccProduction


def p_program(p):
    """
    program : program statement 
              | statement
    """
    if len(p) == 2 and p[1]:
        p[0] = [p[1]]
    elif len(p) == 3:
        p[0] = p[1]
        if p[2]:
            p[0].append(p[2])


def p_statement(p):
    """
    statement : instruction 
              | function_declaration
              | type_declaration
    """
    p[0] = p[1]


def p_instruction(p):
    """
    instruction : var_declaration
                  | return_instruction 
                  | while_loop 
                  | conditional 
                  | compound_instruction 
                  | executable_expression
                  | assignment
                  | continue_statement
                  | break_statement
    """
    p[0] = p[1]


def p_return_instruction(p):
    """
    return_instruction : RETURN dynamic_expression SEMICOLON
    """
    p[0] = ('return_statement', p[2])


def p_break_statement(p):
    """
    break_statement : BREAK SEMICOLON
    """
    p[0] = ('break_statement',)


def p_continue_statement(p):
    """
    continue_statement : CONTINUE SEMICOLON
    """
    p[0] = ('continue_statement',)


def p_var_declaration(p):
    """
    var_declaration : LET declaration_list IN instruction
    """
    p[0] = ['var_inst', p[2], p[4], None] # last pos is for symbol table


def p_declaration_list(p):
    """
    declaration_list : declaration_list COMMA declaration 
                       | declaration
    """
    if len(p) == 2 and p[1]:
        p[0] = [p[1]]
    elif len(p) == 4:
        p[0] = p[1]
        if p[3]:
            p[0].append(p[3])


def p_declaration(p):
    """
    declaration : annotated_identifier EQUAL dynamic_expression
    """
    p[0] = ('declaration', p[1], p[3])


def p_while_loop(p):
    """
    while_loop : WHILE LPAREN dynamic_expression RPAREN instruction
    """
    p[0] = ('while_loop', p[3], p[5])


def p_conditional(p):
    """
    conditional :   if_statement elif_statement_list else_statement 
                    | if_statement elif_statement_list
                    | if_statement else_statement
                    | if_statement
    """
    if len(p) == 2:
        p[0] = ('conditional', p[1], None, None)
    elif len(p) == 3:
        if p[2][0] == 'else_statement':
            p[0] = ('conditional', p[1], None, p[2])    
        else:
            p[0] = ('conditional', p[1], p[2], None)
    elif len(p) == 4:
        p[0] = ('conditional', p[1], p[2], p[3])


def p_if_statement(p):
    """
    if_statement : IF LPAREN dynamic_expression RPAREN instruction
    """
    p[0] = ('if_statement', p[3], p[5])


def p_elif_statement_list(p):
    """
    elif_statement_list :   elif_statement_list elif_statement
                            | elif_statement
    """
    if len(p) == 2 and p[1]:
        p[0] = [p[1]]
    elif len(p) == 3:
        p[0] = p[1]
        if p[2]:
            p[0].append(p[2])


def p_elif_statement(p):
    """
    elif_statement : ELIF LPAREN dynamic_expression RPAREN instruction
    """
    p[0] = ('elif_statement', p[3], p[5])


def p_else_statement(p):
    """
    else_statement : ELSE instruction
    """
    p[0] = ('else_statement', p[2])


def p_compound_instruction(p):
    """
    compound_instruction : LCURLYBRACE instruction_list RCURLYBRACE
    """
    p[0] = ('compound_instruction', p[2])


def p_instruction_list(p):
    """
    instruction_list :  instruction_list instruction
                        | instruction
    """
    if len(p) == 2:
        p[0] = [p[1]]
    elif len(p) == 3:
        p[0] = p[1]
        if p[2]:
            p[0].append(p[2])
        

def p_assignment(p):
    """
    assignment : property_access ASSIGN dynamic_expression SEMICOLON
    """
    p[0] = ('assignment', p[1], p[3])


def p_executable_expression(p):
    """
    executable_expression : dynamic_expression SEMICOLON
    """
    p[0] = ('executable_expression', p[1])


def p_dynamic_expression(p):
    """
    dynamic_expression :  dynamic_expression CONCAT bool_expression
                        | dynamic_expression DOUBLECONCAT bool_expression
                        | bool_expression
                        | array_declaration
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = ('str_concat', p[2] == '@@', p[1], p[3])


def p_bool_expression(p):
    """
    bool_expression : bool_expression AND bool_term
                    | bool_expression OR bool_term
                    | bool_term
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3])


def p_bool_term(p):
    """
    bool_term :   bool_term LESSEQUAL bool_factor
                | bool_term GREATEQUAL bool_factor
                | bool_term EQUEQUAL bool_factor
                | bool_term DISTINCT bool_factor
                | bool_term LESS bool_factor
                | bool_term GREAT bool_factor
                | bool_factor
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3])


def p_bool_factor(p):
    """
    bool_factor : NOT bool_factor
                | arithmetic_expression
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = ('unary', p[1], p[2])


def p_arithmetic_expression(p):
    """
    arithmetic_expression :   arithmetic_expression PLUS arithmetic_term
                            | arithmetic_expression MINUS arithmetic_term
                            | arithmetic_term
    """    
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3])


def p_arithmetic_term(p):
    """
    arithmetic_term : arithmetic_term TIMES arithmetic_factor
                    | arithmetic_term DIV arithmetic_factor
                    | arithmetic_factor
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3])


def p_arithmetic_factor(p):
    """
    arithmetic_factor :   NUMBER 
                        | STRING 
                        | TRUE
                        | FALSE
                        | property_access
                        | type_instantiation
                        | PLUS arithmetic_factor 
                        | MINUS arithmetic_factor 
                        | LPAREN bool_expression RPAREN 
    """
    if len(p) == 2:
        tp = p.slice[1].type.lower()
        if tp in ('true', 'false'):
            p[0] = ('bool', p[1])
        elif tp in ('array_access', 'function_call', 'type_instantiation', 'property_access'):
            p[0] = p[1]
        else:
            p[0] = (tp, p[1])
    elif len(p) == 3:
        p[0] = ('unary', p[1], p[2])
    elif len(p) == 4:
        p[0] = ('grouped', p[2])


def p_type_instantiation(p):
    """
    type_instantiation : NEW IDENTIFIER arguments
    """
    p[0] = ('instance', p[2], p[3])


def p_property_access(p):
    """
    property_access : name_or_method DOT property_access
                    | name_or_method
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = ('access', p[1], p[3])


def p_name_or_method(p):
    """
    name_or_method : name
                   | array_access
                   | function_call
                   | downcast
    """
    p[0] = p[1]


def p_downcast(p):
    """
    downcast : name AS name
    """
    p[0] = ('downcast', p[1], p[3])


def p_name(p):
    """
    name : IDENTIFIER
    """
    p[0] = ('name', p[1])


def p_array_access(p):
    """
    array_access : IDENTIFIER LBRACKET dynamic_expression RBRACKET
    """
    p[0] = ('array_access', p[1], p[3])


def p_array_declaration(p):
    """
    array_declaration : explicit_array_declaration
    """

    p[0] = p[1]


def p_explicit_array_declaration(p):
    """
    explicit_array_declaration : LBRACKET expression_list RBRACKET 
    """
    p[0] = ('array_declaration_explicit', p[2])


def p_expression_list(p):
    """
    expression_list : expression_list COMMA dynamic_expression
                    | dynamic_expression
    """
    if len(p) == 2 and p[1]:
        p[0] = [p[1]]
    elif len(p) == 4:
        p[0] = p[1]
        if p[3]:
            p[0].append(p[3])


def p_function_call(p):
    """
    function_call : IDENTIFIER arguments
    """
    p[0] = ('function_call', p[1], p[2])


def p_arguments(p):
    """
    arguments : LPAREN expression_list RPAREN
              | LPAREN RPAREN
    """
    if len(p) == 3:
        p[0] = []
    elif len(p) == 4:
        p[0] = p[2]


def p_function_declaration(p):
    """
    function_declaration : FUNCTION IDENTIFIER params function_body
                         | FUNCTION IDENTIFIER params type_annotation function_body
    """
    if len(p) == 5:
        p[0] = ['function', None, p[2], p[3], p[4], None]
    elif len(p) == 6:
        p[0] = ['function', p[4], p[2], p[3], p[5], None]
    

def p_function_body(p):
    """
    function_body : RIGHTARROW instruction
                  | compound_instruction
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = p[2]


def p_params(p):
    """
    params : LPAREN param_list RPAREN
           | LPAREN RPAREN
    """
    if len(p) == 3:
        p[0] = []
    elif len(p) == 4:
        p[0] = p[2]


def p_param_list(p):
    """
    param_list : param_list COMMA annotated_identifier
               | annotated_identifier
    """
    if len(p) == 2 and p[1]:
        p[0] = [p[1]]
    elif len(p) == 4:
        p[0] = p[1]
        if p[3]:
            p[0].append(p[3])


def p_annotated_identifier(p):
    """
    annotated_identifier : IDENTIFIER type_annotation
                         | IDENTIFIER 
    """
    if len(p) == 2:
        p[0] = ('annotated_identifier', p[1], None)
    elif len(p) == 3:
        p[0] = ('annotated_identifier', p[1], p[2])


def p_type_annotation(p):
    """
    type_annotation : COLON IDENTIFIER
    """
    p[0] = p[2]


def p_type_declaration(p):
    """
    type_declaration : TYPE type_declaration_head INHERITS IDENTIFIER LCURLYBRACE type_declaration_body RCURLYBRACE
                     | TYPE type_declaration_head LCURLYBRACE type_declaration_body RCURLYBRACE
    """
    if len(p) == 6:
        p[0] = ('type_declaration',None , p[2], p[4])
    elif len(p) == (8):
        p[0] = ('type_declaration',p[4] , p[2], p[6])


def p_type_declaration_head(p):
    """
    type_declaration_head : IDENTIFIER params
                          | IDENTIFIER
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = ('initialized_type', p[1], p[2])


def p_type_declaration_body(p):
    """
    type_declaration_body : type_declaration_body type_declaration_body_item
                          | type_declaration_body_item
    """
    if len(p) == 2:
        p[0] = {'properties':[], 'methods':[]}
        tmp = p[1]
    elif len(p) == 3:
        p[0] = p[1]
        tmp = p[2]
    
    if tmp[0] == 'declaration':
        p[0]['properties'].append(tmp)
    elif tmp[0] == 'function':
        p[0]['methods'].append(tmp)

def p_type_declaration_body_item(p):
    """
    type_declaration_body_item : declaration SEMICOLON
                               | function_declaration
    """
    p[0] = p[1]


def p_error(p):
    try:
        print(f'Syntax error at {p.value!r} in line {p.lineno} col {p.lexpos}')
    except:
        print('There are some missing token(s)')
    
    IS_ANY_ERROR = True

# Build the parser
IS_ANY_ERROR = False
parser = yacc()