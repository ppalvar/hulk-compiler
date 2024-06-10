from src.parser import parser
from src.semantic_checker import SemanticChecker
from src.tac_generator import TacGenerator

def main(data):
    ast = parser.parse(data)

    if not ast:
        print('Error while parsing')

    semantic_checker = SemanticChecker()

    if not semantic_checker.check(ast):
        print("Semantic errors")
        for error in semantic_checker.errors:
            print(error)
        return
    else:
        print("No semantic errors")

    tac_generator = TacGenerator()

    tac_generator.generate(ast)

    print(tac_generator)


filename = 'examples/simple.hulk'
with open(filename, 'r') as file:
    data = file.read()

if __name__ == '__main__':
    main(data)