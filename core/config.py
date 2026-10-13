import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from google.oauth2.service_account import Credentials

def missing_key_message(key: str) -> str:
    return f"{key} is not set. Add it to .env, or run `python pulse.py demo` to try ReviewPulse without keys."

class Settings(BaseSettings):
    # Optional so the demo and dashboard can start without keys. The clients that need them
    # raise a clear error on first use instead.
    PLAY_STORE_PACKAGE_NAME: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS_JSON: str | None = None
    GEMINI_API_KEY: str | None = None
    TARGET_STORE_RATING: float = 4.5
    DATABASE_URL: str = "sqlite:///data/reviewpulse.db"
    
    JIRA_URL: str | None = None
    JIRA_EMAIL: str | None = None
    JIRA_API_TOKEN: str | None = None
    JIRA_PROJECT_KEY: str | None = "ENG"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_google_credentials(self) -> Credentials:
        """Parses the raw JSON credentials string from memory."""
        if not self.GOOGLE_APPLICATION_CREDENTIALS_JSON:
            raise ValueError(missing_key_message("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
        try:
            creds_dict = json.loads(self.GOOGLE_APPLICATION_CREDENTIALS_JSON)
            return Credentials.from_service_account_info(creds_dict)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load Google credentials from JSON: {e}")

settings = Settings()
