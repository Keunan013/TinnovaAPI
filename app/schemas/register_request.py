from pydantic import BaseModel, Field

from app.core.enums.user_role import UserRole


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    senha: str = Field(min_length=1)
    role: UserRole = UserRole.USER
