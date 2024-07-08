import re

def remove_comments(code: str, comment_pattern: str = r'(//.*\n)|(\/\*(\*(?!\/)|[^*])*\*\/)') -> str:
    return re.sub(comment_pattern, '', code)

def scape_characters(code: str):
    # chars = {
    #     "\\n": "\n",
    #     "\\t": "\t",
    #     "\\r": "\r",
    # }

    # for pattern, subs in chars.items():
    #     print(repr(pattern), repr(subs))
    #     code = re.sub(pattern, subs, code)

    # print(code)
    return code
