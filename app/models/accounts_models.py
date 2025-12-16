from pydantic import BaseModel
from typing import Optional

class NewAccount(BaseModel):
    bank: str
    acc_no : str