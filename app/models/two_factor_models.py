from pydantic import BaseModel, Field
from typing import Optional, List


class TwoFactorStatusResponse(BaseModel):
    enabled: bool
    backup_codes_remaining: int


class TwoFactorSetupResponse(BaseModel):
    otpauth_uri: str
    qr_code_data_url: str
    manual_entry_key: str


class TwoFactorVerifySetupRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class TwoFactorVerifySetupResponse(BaseModel):
    backup_codes: List[str]


class TwoFactorLoginRequest(BaseModel):
    code: Optional[str] = None
    backup_code: Optional[str] = None


class TwoFactorDisableRequest(BaseModel):
    password: str
    code: Optional[str] = None
    backup_code: Optional[str] = None


class TwoFactorRegenerateRequest(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=6)
