class SenhaInvalidaError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class EmailInvalidoError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class UserNaoEncontradoError(Exception):
    """Usuário não encontrado (404)."""


class EmailDuplicadoError(Exception):
    """Email já cadastrado (409)."""


class CredenciaisInvalidasError(Exception):
    """Login inválido (401)."""
