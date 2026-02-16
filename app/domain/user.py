from dataclasses import dataclass
from typing import Optional

from app.core.enums.user_role import UserRole


@dataclass
class User:
    id: Optional[int]
    email: str
    senha_hash: str
    role: UserRole
    ativo: bool = True
