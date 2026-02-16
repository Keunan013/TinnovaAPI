from __future__ import annotations

import pytest

import app.domain.validators.password_validator as validator_module

from app.exceptions.user_exceptions import SenhaInvalidaError


@pytest.fixture(autouse=True)
def patch_default_settings(monkeypatch):
    monkeypatch.setattr(validator_module.settings, "password_min_length", 8)
    monkeypatch.setattr(validator_module.settings, "password_require_upper", True)
    monkeypatch.setattr(validator_module.settings, "password_require_lower", True)
    monkeypatch.setattr(validator_module.settings, "password_require_digit", True)
    monkeypatch.setattr(validator_module.settings, "password_require_special", True)
    monkeypatch.setattr(validator_module.settings, "password_special_chars", "!@#")


def test_senha_none_deve_falhar_por_tamanho():
    with pytest.raises(SenhaInvalidaError):
        validator_module.PasswordValidator.validate(None)  # type: ignore


def test_senha_muito_curta_deve_falhar():
    with pytest.raises(SenhaInvalidaError) as exc:
        validator_module.PasswordValidator.validate("Ab1!")

    assert "no mínimo" in str(exc.value)


def test_sem_maiuscula_deve_falhar():
    with pytest.raises(SenhaInvalidaError) as exc:
        validator_module.PasswordValidator.validate("abc123!@")

    assert "maiúscula" in str(exc.value)


def test_sem_minuscula_deve_falhar():
    with pytest.raises(SenhaInvalidaError) as exc:
        validator_module.PasswordValidator.validate("ABC123!@")

    assert "minúscula" in str(exc.value)


def test_sem_digito_deve_falhar():
    with pytest.raises(SenhaInvalidaError) as exc:
        validator_module.PasswordValidator.validate("Abcdef!@")

    assert "número" in str(exc.value)


def test_sem_caractere_especial_deve_falhar():
    with pytest.raises(SenhaInvalidaError) as exc:
        validator_module.PasswordValidator.validate("Abcdef12")

    assert "caractere especial" in str(exc.value)


def test_senha_valida_deve_passar():
    validator_module.PasswordValidator.validate("Abcdef1!")


def test_quando_flags_desligadas_deve_aceitar_senha_simples(monkeypatch):
    monkeypatch.setattr(validator_module.settings, "password_require_upper", False)
    monkeypatch.setattr(validator_module.settings, "password_require_lower", False)
    monkeypatch.setattr(validator_module.settings, "password_require_digit", False)
    monkeypatch.setattr(validator_module.settings, "password_require_special", False)

    validator_module.PasswordValidator.validate("qualquersenha")
