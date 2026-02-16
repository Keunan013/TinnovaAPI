from pydantic import BaseModel

from app.core.enums.user_role import UserRole


class UserPublic(BaseModel):
    id: int
    email: str
    role: UserRole
    ativo: bool
