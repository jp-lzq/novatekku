from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://app_user:change_me@localhost:5432/nova_kaitori"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    ad_enabled: bool = False
    ad_provider: str = "none"
    ad_client_id: str = ""
    ad_slot_id: str = ""
    ai_core_module: str = "nova_ai_core"
    admin_username: str = ""  # lower-case username of the single administrator; empty = none
    fx_rates_url: str = "https://open.er-api.com/v6/latest/JPY"
    public_app_url: str = "http://localhost:5173"
    auth_origins: str = "http://localhost:3000,http://localhost:5173"
    auth_session_days: int = 7
    auth_cookie_secure: bool = True
    auth_rate_limit_window_seconds: int = 900
    public_member_auth_enabled: bool = True
    password_reset_token_minutes: int = 30
    password_reset_email_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_starttls: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def auth_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.auth_origins.split(",") if origin.strip()]

    @property
    def password_reset_delivery_ready(self) -> bool:
        return bool(
            self.password_reset_email_enabled
            and self.smtp_host
            and self.smtp_from_email
            and self.public_app_url
        )

settings = Settings()
