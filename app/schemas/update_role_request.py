from pydantic import BaseModel

from app.core.enums.user_role import UserRole


class UpdateRoleRequest(BaseModel):
    role: UserRole
