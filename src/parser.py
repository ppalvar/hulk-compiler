from src.lexer import *

from ply.yacc import yacc, YaccProduction

# def p_program(p):
#     """
#     program : statement_list
#     """

#     p[0] = p[1]

# def p_statement_list(p):
#     """
#     statement_list : statement SEMICOLON
#     """

def p_expression(p):
    """
    expression : arithmetic_expression
               | boolean_expression
    """

    p[0] = p[1]

def p_arithmetic_expression(p):
    """
    arithmetic_expression : arithmetic_expression PLUS arithmetic_term
               | arithmetic_expression MINUS arithmetic_term
               | arithmetic_term
    """
    if len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3], p.slice[2].lineno, p.slice[2].lexpos)
    elif len(p) == 2:
        p[0] = p[1]

def p_arithmetic_term(p):
    """
    arithmetic_term : arithmetic_term MULTIPLY arithmetic_factor
         | arithmetic_term DIVIDE arithmetic_factor
         | arithmetic_factor
    """

    if len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3], p.slice[2].lineno, p.slice[2].lexpos)
    elif len(p) == 2:
        p[0] = p[1]

def p_arithmetic_factor(p):
    """
    arithmetic_factor : NUMBER
           | PLUS arithmetic_factor
           | MINUS arithmetic_factor
           | LPAREN arithmetic_expression RPAREN
    """

    if len(p) == 2:
        p[0] = ('number', p[1])
    elif len(p) == 3:
        p[0] = ('unary', p[1], p[2])
    elif len(p) == 4:
        p[0] = ('grouped', p[2])

def p_boolean_expression(p):
    """
    boolean_expression : boolean_expression AND boolean_term
                       | boolean_expression OR boolean_term
                       | boolean_term
    """
    if len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3], p.slice[2].lineno, p.slice[2].lexpos)
    elif len(p) == 2:
        p[0] = p[1]

def p_boolean_term(p):
    """
    boolean_term : arithmetic_expression LESSEQUAL arithmetic_expression
                | arithmetic_expression GREATEQUAL arithmetic_expression
                | arithmetic_expression EQUAL arithmetic_expression
                | arithmetic_expression DISTINCT arithmetic_expression
                | arithmetic_expression LESS arithmetic_expression
                | arithmetic_expression GREAT arithmetic_expression
                | NOT boolean_expression
                | TRUE
                | FALSE
    """

    if len(p) == 4:
        p[0] = ('binop', p[2], p[1], p[3], p.slice[2].lineno, p.slice[2].lexpos)
    elif len(p) == 3:
        p[0] = ('unary', p[1], p[2])
    elif len(p) == 2:
        p[0] = ('bool', p[1])

def p_error(p):
    print(f'Syntax error at {p.value!r}')

# Build the parser
parser = yacc()