from datetime import datetime
from pydantic import BaseModel, EmailStr, constr

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

class InvitationRequest(BaseModel):
    email: str
    name: str
    role: str

class RemoveUserRequest(BaseModel):
    user_id: int
    

class PendingInvitationResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    created_at: datetime
    expires_at: datetime

class DeleteInvitationResponse(BaseModel):
    message: str

class DeleteInvitationErrorResponse(BaseModel):
    message: str

class LogoutRequest(BaseModel):
    refresh: str

class LogoutResponse(BaseModel):
    message: str

class UserInfoResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    toko_id: int = None
    is_bpr: bool = False