from src.parser import parser, IS_ANY_ERROR
from src.semantic_checker import SemanticChecker
from src.tac_generator import TacGenerator
from src.codegen import MIPSCodeManager
from src.utils import remove_comments, scape_characters

def main(input_code: str):
    input_code = remove_comments(input_code)
    input_code = scape_characters(input_code)
    
    ast = parser.parse(input_code)
    
    if IS_ANY_ERROR or not ast:
        print('Error while parsing')
        return

    semantic_checker = SemanticChecker()

    if not semantic_checker.check(ast):
        print("Semantic errors")
        for error in semantic_checker.errors:
            print(error)
        return

    tac_generator = TacGenerator(semantic_checker.symbols)
    tac_generator.generate(ast)
    print(tac_generator)

    codegen = MIPSCodeManager(semantic_checker.symbols)
    codegen.generate_mips(tac_generator.code)
    # print(codegen)
    codegen.store_code('out/a.s')

if __name__ == '__main__':
    filename = 'examples/type_properties.hulk'
    
    with open(filename, 'r') as file:
        input_code = file.read()
        main(input_code)