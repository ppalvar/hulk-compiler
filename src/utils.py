import re

def remove_comments(code: str, comment_pattern: str = r'(//.*\n)|(\/\*(\*(?!\/)|[^*])*\*\/)') -> str:
    return re.sub(comment_pattern, '', code)