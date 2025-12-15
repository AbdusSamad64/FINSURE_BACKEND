import re

def clean_brackets(value: str):
    """'(123.45)' → '123.45', otherwise same value"""
    match = re.search(r'\(([^)]+)\)', value)
    if match:
        return match.group(1)
    return value.strip()

def is_number(value):
    try:
        # commas hata ke float convert karne ki koshish
        float(value.replace(',', ''))
        return True
    except (ValueError, TypeError, AttributeError):
        return False
    

def is_int_convertible(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False
    
# print(is_int_convertible('0107955074'))    

