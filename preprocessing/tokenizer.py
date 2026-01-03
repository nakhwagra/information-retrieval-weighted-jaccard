import re

def case_folding(text):
    return text.lower()

def tokenizing(text):
    text = case_folding(text)
    tokens = re.findall(r'\b[a-zA-Z]+\b', text)
    return tokens