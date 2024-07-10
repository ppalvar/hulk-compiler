import os
import pytest
from pathlib import Path
from main import compile

def test_files():
    directory_path = Path(__file__).parent / "examples"
    
    for filename in directory_path.iterdir():
        if filename.is_file():
            with open(filename, 'r') as file:
                file_content =  file.read()
                try:
                    result = compile(file_content)
                    assert result is True, f"Test failed for file {filename}"
                except:
                    raise Exception(filename)
