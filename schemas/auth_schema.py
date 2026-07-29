from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResp(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    access_expires_at: int
    refresh_expires_at: int
