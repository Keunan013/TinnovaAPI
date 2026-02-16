class PlacaDuplicadaError(Exception):
    """Placa já cadastrada (mapear para HTTP 409 no controller)."""


class VeiculoNaoEncontradoError(Exception):
    """Veículo não encontrado (mapear para HTTP 404 no controller)."""


class InvalidUpdateError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
