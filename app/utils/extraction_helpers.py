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
    
def is_date(line):
    return re.match(r"\d{2}\s[A-Za-z]{3}\s\d{4}", line)

def is_amount(line):
    return re.match(r"^\d{1,3}(,\d{3})*\.\d{2}$", line.strip())

def clean_amount(x):
    return float(x.replace(",", ""))