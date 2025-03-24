from pydantic import BaseModel

class SessionData(BaseModel):
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh: str

class TokenValidationRequest(BaseModel):
    token: str

class AddUserRequest(BaseModel):
    name: str
    email: str
    role: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

class ErrorResponse(BaseModel):
    error: str
