from __future__ import annotations

import pytest

from types import SimpleNamespace

import app.domain.validators.email_validator as validator_module

from app.exceptions.user_exceptions import EmailInvalidoError


@pytest.fixture(autouse=True)
def patch_default_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validator_module.settings, "email_require_mx", False)
    monkeypatch.setattr(validator_module.settings, "email_allow_domains", "")
    monkeypatch.setattr(validator_module.settings, "email_block_domains", "")


def test_parse_csv_none_returns_empty_set():
    assert validator_module._parse_csv(None) == set()


def test_parse_csv_empty_returns_empty_set():
    assert validator_module._parse_csv("") == set()


def test_parse_csv_trims_lowercases_and_ignores_blanks():
    got = validator_module._parse_csv("  Gmail.com , , EXAMPLE.ORG  ,")
    assert got == {"gmail.com", "example.org"}


def test_validate_and_normalize_success(monkeypatch: pytest.MonkeyPatch):
    def fake_validate_email(email: str, check_deliverability: bool):
        assert email == "User@Example.com"
        assert check_deliverability is False
        return SimpleNamespace(normalized="User@Example.com")

    monkeypatch.setattr(validator_module, "validate_email", fake_validate_email)

    out = validator_module.StrongEmailValidator.validate_and_normalize("  User@Example.com  ")

    assert out.value == "user@example.com"
    assert out.domain == "example.com"


def test_validate_and_normalize_passes_check_deliverability_flag(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validator_module.settings, "email_require_mx", True)

    def fake_validate_email(email: str, check_deliverability: bool):
        assert check_deliverability is True
        return SimpleNamespace(normalized="a@b.com")

    monkeypatch.setattr(validator_module, "validate_email", fake_validate_email)

    out = validator_module.StrongEmailValidator.validate_and_normalize("a@b.com")
    assert out.value == "a@b.com"
    assert out.domain == "b.com"


def test_validate_and_normalize_invalid_email_raises_email_invalido(monkeypatch: pytest.MonkeyPatch):
    def fake_validate_email(email: str, check_deliverability: bool):
        raise validator_module.EmailNotValidError("bad email")

    monkeypatch.setattr(validator_module, "validate_email", fake_validate_email)

    with pytest.raises(EmailInvalidoError) as exc:
        validator_module.StrongEmailValidator.validate_and_normalize("not-an-email")

    assert "Email inválido:" in str(exc.value)


def test_allowlist_blocks_when_domain_not_in_allow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validator_module.settings, "email_allow_domains", "allowed.com")

    monkeypatch.setattr(
        validator_module,
        "validate_email",
        lambda email, check_deliverability: SimpleNamespace(normalized="x@notallowed.com"),
    )

    with pytest.raises(EmailInvalidoError) as exc:
        validator_module.StrongEmailValidator.validate_and_normalize("x@notallowed.com")

    assert "Email não permitido" in str(exc.value)


def test_allowlist_allows_when_domain_in_allow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validator_module.settings, "email_allow_domains", "allowed.com, other.com")

    monkeypatch.setattr(
        validator_module,
        "validate_email",
        lambda email, check_deliverability: SimpleNamespace(normalized="X@Allowed.com"),
    )

    out = validator_module.StrongEmailValidator.validate_and_normalize("X@Allowed.com")
    assert out.value == "x@allowed.com"
    assert out.domain == "allowed.com"


def test_blocklist_blocks_when_domain_in_block(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validator_module.settings, "email_block_domains", "blocked.com")

    monkeypatch.setattr(
        validator_module,
        "validate_email",
        lambda email, check_deliverability: SimpleNamespace(normalized="x@blocked.com"),
    )

    with pytest.raises(EmailInvalidoError) as exc:
        validator_module.StrongEmailValidator.validate_and_normalize("x@blocked.com")

    assert "Domínio de email não permitido" in str(exc.value)


def test_allow_and_block_allow_passes_allow_but_block_wins(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validator_module.settings, "email_allow_domains", "blocked.com")
    monkeypatch.setattr(validator_module.settings, "email_block_domains", "blocked.com")

    monkeypatch.setattr(
        validator_module,
        "validate_email",
        lambda email, check_deliverability: SimpleNamespace(normalized="x@blocked.com"),
    )

    with pytest.raises(EmailInvalidoError) as exc:
        validator_module.StrongEmailValidator.validate_and_normalize("x@blocked.com")

    assert "Domínio de email não permitido" in str(exc.value)
