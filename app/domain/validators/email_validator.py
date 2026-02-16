from __future__ import annotations

from typing import Optional
from email_validator import validate_email, EmailNotValidError

from app.core.config import settings
from app.domain.normalized_email import NormalizedEmail
from app.exceptions.user_exceptions import EmailInvalidoError


def _parse_csv(value: Optional[str]) -> set[str]:
    if not value:
        return set()
    return {x.strip().lower() for x in value.split(",") if x.strip()}


class StrongEmailValidator:
    @staticmethod
    def validate_and_normalize(email: str) -> NormalizedEmail:
        email = (email or "").strip()
        try:
            # check_deliverability faz MX/DNS; controlado via env
            result = validate_email(
                email,
                check_deliverability=bool(settings.email_require_mx),
            )
            normalized = result.normalized
        except EmailNotValidError as e:
            raise EmailInvalidoError(f"Email inválido: {str(e)}")

        domain = normalized.split("@")[-1].lower()

        # Allowlist / blocklist
        allow = _parse_csv(settings.email_allow_domains)
        block = _parse_csv(settings.email_block_domains)

        if allow and domain not in allow:
            raise EmailInvalidoError("Email não permitido para este domínio.")

        if block and domain in block:
            raise EmailInvalidoError("Domínio de email não permitido.")

        return NormalizedEmail(value=normalized.lower(), domain=domain)
