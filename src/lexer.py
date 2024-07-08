from ply.lex import lex, Lexer

keywords = ('TRUE', 'FALSE', 'IF', 'ELIF', 'ELSE', 'WHILE',
            'FOR', 'IN', 'LET', 'FUNCTION', 'RETURN', 'BREAK', 'CONTINUE',
            'TYPE', 'INHERITS', 'NEW', 'AS')

tokens = ( 'PLUS', 
           'MINUS', 
           'TIMES', 
           'DIV', 
           'LPAREN', 
           'RPAREN', 
           'NUMBER',
           'LESSEQUAL',
           'GREATEQUAL',
           'ASSIGN',
           'EQUEQUAL',
           'DISTINCT',
           'LESS',
           'GREAT',
           'AND',
           'OR',
           'NOT',
           'SEMICOLON',
           'COLON',
           'LBRACKET',
           'RBRACKET',
           'IDENTIFIER',
           'DOUBLECONCAT',
           'CONCAT',
           'COMMA',
           'EQUAL',
           'STRING',
           'LCURLYBRACE',
           'RCURLYBRACE',
           'RIGHTARROW',
           'DOT') + keywords

t_ignore = ' \t'

t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIV = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'

t_RIGHTARROW = r'=>'
t_LESSEQUAL = r'<='
t_GREATEQUAL = r'>='
t_EQUEQUAL = r'=='
t_DISTINCT = r'!='
t_LESS = r'<'
t_GREAT = r'>'
t_AND = r'&&'
t_OR = r'\|\|'
t_NOT = r'!'
t_ASSIGN = r':='
t_EQUAL = r'='

t_SEMICOLON = r';'
t_COLON = r'\:'
t_DOUBLECONCAT = r'\@\@'
t_CONCAT = r'\@'
t_COMMA = r'\,'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_LCURLYBRACE = r'\{'
t_RCURLYBRACE = r'\}'
t_DOT = r'\.'

t_IF = r'if'
t_ELIF = r'elif'
t_ELSE = r'else'
t_WHILE = r'while'
t_FOR = r'for'
t_IN = r'in'
t_LET = r'let'
t_FUNCTION = r'function'
t_RETURN = r'return'
t_BREAK = r'break'
t_CONTINUE = r'continue'
t_TYPE = r'type'
t_INHERITS = r'inherits'
t_NEW = r'new'
t_AS = r'as'

t_STRING = r'\".*?\"'

def t_NUMBER(t):
    r'([0-9]*[.])?[0-9]+'
    t.value = float(t.value)
    return t

def t_TRUE(t):
    r'true'
    t.value = True
    return t

def t_FALSE(t):
    r'false'
    t.value = False
    return t

def t_IDENTIFIER(t):
    r"[a-zA-Z_][a-zA-Z0-9_]*"
    if t.value.upper() in keywords:
        t.type = t.value.upper()
    return t

def t_ignore_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')

def t_error(t):
    print(f'Illegal character {t.value[0]!r}')
    t.lexer.skip(1)

lexer = lex()

if __name__ == '__main__':
    input_string = "\
    let a = 1, b = 1, n = 10 in {\
            while (n != 0) {\
                let c = a + b;\
                b := a;\
                a := c;\
                n := n - 1;\
            }\
        }\
    "

    lexer.input(input_string)

    while True:
        tok = lexer.token()
        if not tok:
            break
        print(tok)