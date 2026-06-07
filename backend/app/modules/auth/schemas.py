from pydantic import BaseModel

from app.modules.users.schemas import UserRead


class LoginRequest(BaseModel):
    login: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MeResponse(UserRead):
    pass
