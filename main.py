from src.parser import parser
from src.semantic_checker import SemanticChecker
from src.tac_generator import TacGenerator

def main(data):
    ast = parser.parse(data)

    semantic_checker = SemanticChecker()

    if not semantic_checker.check(ast):
        print("Semantic error")
        return

    tac_generator = TacGenerator()

    tac_generator.generate(ast)

    print(tac_generator)


data = "1 + (1 - -1) > 10 || 1 < 2 && !false"

if __name__ == '__main__':
    main(data)