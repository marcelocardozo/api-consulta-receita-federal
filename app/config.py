from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini
    gemini_api_keys: str = ""
    gemini_api_key: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Browser
    browser_headless: bool = False
    browser_timeout: int = 30000
    captcha_execution_timeout: float = 90.0
    captcha_response_timeout: float = 20.0

    # Logging
    log_level: str = "INFO"

    # Rate limiting
    ip_lock_ttl_seconds: int = 300

    @property
    def gemini_keys_list(self) -> list[str]:
        if self.gemini_api_keys:
            return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]
        if self.gemini_api_key:
            return [self.gemini_api_key]
        return []


settings = Settings()
