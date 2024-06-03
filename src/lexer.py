from ply.lex import lex, Lexer
from src.utils.tokenizer_tools import Token, tokenize

keywords = ('TRUE', 'FALSE')

tokens = ( 'PLUS', 
           'MINUS', 
           'MULTIPLY', 
           'DIVIDE', 
           'LPAREN', 
           'RPAREN', 
           'NUMBER',
           'LESSEQUAL',
           'GREATEQUAL',
           'EQUAL',
           'DISTINCT',
           'LESS',
           'GREAT',
           'AND',
           'OR',
           'NOT',
           'SEMICOLON',
           'LBRACE',
           'RBRACE',
           'IDENTIFIER') + keywords

t_ignore = ' \t'

t_PLUS = r'\+'
t_MINUS = r'-'
t_MULTIPLY = r'\*'
t_DIVIDE = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'

t_LESSEQUAL = r'<='
t_GREATEQUAL = r'>='
t_EQUAL = r'=='
t_DISTINCT = r'!='
t_LESS = r'<'
t_GREAT = r'>'
t_AND = r'&&'
t_OR = r'\|\|'
t_NOT = r'!'

t_SEMICOLON = r';'
t_LBRACE = '{'
t_RBRACE = '}'

t_IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_TRUE(t):
    r'true'
    t.value = True
    return t

def t_FALSE(t):
    r'false'
    t.value = False
    return t

def t_ignore_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')

def t_error(t):
    print(f'Illegal character {t.value[0]!r}')
    t.lexer.skip(1)

lexer = lex()