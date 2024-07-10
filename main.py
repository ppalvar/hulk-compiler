from src.parser import parser, ERRORS
from src.semantic_checker import SemanticChecker
from src.tac_generator import TacGenerator
from src.codegen import MIPSCodeManager
from src.utils import remove_comments, scape_characters

def compile(input_code: str, out_file: str = 'a'):
    input_code = remove_comments(input_code)
    input_code = scape_characters(input_code)
    
    ast = parser.parse(input_code)
    
    if ERRORS or not ast:
        if ENVIRONMENT_IS_MAIN:
            for err in ERRORS:
                print(err)
        return False

    semantic_checker = SemanticChecker()

    if not semantic_checker.check(ast):
        if ENVIRONMENT_IS_MAIN:
            for error in semantic_checker.errors:
                print(error)
        return False

    tac_generator = TacGenerator(semantic_checker.symbols)
    tac_generator.generate(ast)
    if ENVIRONMENT_IS_DEBUG: print(tac_generator)

    codegen = MIPSCodeManager(semantic_checker.symbols)
    codegen.generate_mips(tac_generator.code)
    if ENVIRONMENT_IS_DEBUG:  print(codegen)
    if ENVIRONMENT_IS_MAIN: codegen.store_code(f'out/{out_file}.s')

    if ENVIRONMENT_IS_MAIN: print("Compiled Succesfully!")

    return True

ENVIRONMENT_IS_DEBUG = False
ENVIRONMENT_IS_MAIN = False


if __name__ == '__main__':
    ENVIRONMENT_IS_MAIN = True
    filename = 'examples/string_concat.hulk'
    
    with open(filename, 'r') as file:
        input_code = file.read()
        compile(input_code, filename.split('/')[1][:-5])