from pydantic import BaseModel
from app.core.enums.user_role import UserRole


class CurrentUser(BaseModel):
    email: str
    role: UserRole
