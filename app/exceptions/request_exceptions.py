class TooManyRequestsError(Exception):
    def __init__(self, retry_after_seconds: int):
        super().__init__("Muitas tentativas. Tente novamente mais tarde.")
        self.retry_after_seconds = retry_after_seconds
