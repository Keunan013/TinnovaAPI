from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str

    database_url: str
    database_url_sync: str

    jwt_secret: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60

    redis_url: str

    awesome_api_url: str = 'https://economia.awesomeapi.com.br/json/last/USD-BRL'
    frankfurter_api_url: str = 'https://api.frankfurter.app/latest?from=USD&to=BRL'

    # --- Email policy ---
    email_allow_domains: str | None = None  # ex: "empresa.com,empresa.com.br"
    email_block_domains: str | None = None  # ex: "mailinator.com,10minutemail.com"
    email_require_mx: bool = False  # mx check pode falhar local/ci; default False

    # --- Password policy ---
    password_min_length: int = 8
    password_require_upper: bool = True
    password_require_lower: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True
    password_special_chars: str = "!@#$%^&*(),.?\":{}|<>"

    # --- Rate limit (login) ---
    login_rate_limit_max_attempts: int = 10
    login_rate_limit_window_seconds: int = 60  # 10 tentativas por 60s
    login_rate_limit_block_seconds: int = 300  # bloqueia por 5 min após estourar

    model_config = SettingsConfigDict(env_file='.env')


settings = Settings()
