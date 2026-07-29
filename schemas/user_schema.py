from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.schemas.auth_schema import TokenResp

class UserCreate(BaseModel):
    username: str
    email: EmailStr | None = None
    password: str

class UserResp(BaseModel):
    id: UUID
    login: str
    full_name: str
    user_identify: int
    profile_id: int
    email: EmailStr | None = None

class UserRespFull(UserResp):
    create_user_login: str
    user_state: str
    last_access_date: datetime | None = None
    
class UserRespWithTokenAndMenu(UserResp):
    auth: TokenResp
    menu: list

# ==========================================
# CRUD SCHEMAS (SuperUsuario)
# ==========================================

class UserCreateRequest(BaseModel):
    """Schema para crear un usuario - Solo SuperUsuario"""
    login: str = Field(..., min_length=3, max_length=50, description="Login del usuario")
    user_identify: int = Field(..., description="Identificación del usuario")
    full_name: str = Field(..., min_length=3, max_length=200, description="Nombre completo")
    profile_id: int = Field(..., ge=1, le=5, description="ID del perfil (1-5)")
    email: EmailStr | None = Field(None, description="Email del usuario")
    user_state: bool = Field(True, description="Estado del usuario (activo/inactivo)")

class UserUpdateRequest(BaseModel):
    """Schema para actualizar un usuario - Solo SuperUsuario"""
    user_identify: int | None = Field(None, description="Identificación del usuario")
    full_name: str | None = Field(None, min_length=3, max_length=200, description="Nombre completo")
    profile_id: int | None = Field(None, ge=1, le=5, description="ID del perfil (1-5)")
    email: EmailStr | None = Field(None, description="Email del usuario")
    user_state: bool | None = Field(None, description="Estado del usuario")

class UserDetailResponse(BaseModel):
    """Schema detallado de un usuario - Solo SuperUsuario"""
    id: UUID
    login: str
    user_identify: int | None
    full_name: str | None
    profile_id: int | None
    email: EmailStr | None
    user_state: bool
    create_user_login: str | None
    create_at: datetime | None
    last_access_date: datetime | None

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """Schema para listado paginado de usuarios - Solo SuperUsuario"""
    total: int
    page: int
    page_size: int
    users: list[UserDetailResponse]
