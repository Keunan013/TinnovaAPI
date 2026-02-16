import re

from app.core.config import settings
from app.exceptions.user_exceptions import SenhaInvalidaError


class PasswordValidator:
    @staticmethod
    def validate(password: str) -> None:
        password = password or ""
        if len(password) < settings.password_min_length:
            raise SenhaInvalidaError(
                f"A senha deve conter no mínimo {settings.password_min_length} caracteres."
            )
        if settings.password_require_upper and not re.search(r"[A-Z]", password):
            raise SenhaInvalidaError("A senha deve conter pelo menos uma letra maiúscula.")
        if settings.password_require_lower and not re.search(r"[a-z]", password):
            raise SenhaInvalidaError("A senha deve conter pelo menos uma letra minúscula.")
        if settings.password_require_digit and not re.search(r"\d", password):
            raise SenhaInvalidaError("A senha deve conter pelo menos um número.")
        if settings.password_require_special:
            specials = re.escape(settings.password_special_chars)
            if not re.search(rf"[{specials}]", password):
                raise SenhaInvalidaError("A senha deve conter pelo menos um caractere especial.")
