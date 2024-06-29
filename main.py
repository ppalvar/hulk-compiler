from src.parser import parser
from src.semantic_checker import SemanticChecker
from src.tac_generator import TacGenerator
from src.codegen import MIPSCodeManager

def main(data):
    ast = parser.parse(data)

    if not ast:
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

    # codegen = MIPSCodeManager(semantic_checker.symbols)
    # codegen.generate_mips(tac_generator.code)
    # print(codegen)
    # codegen.store_code('out/a.s')


filename = 'examples/type_decl_simple.hulk'
with open(filename, 'r') as file:
    data = file.read()

if __name__ == '__main__':
    main(data)