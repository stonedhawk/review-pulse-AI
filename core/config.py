import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from google.oauth2.service_account import Credentials

class Settings(BaseSettings):
    PLAY_STORE_PACKAGE_NAME: str
    GOOGLE_APPLICATION_CREDENTIALS_JSON: str
    GEMINI_API_KEY: str
    TARGET_STORE_RATING: float = 4.5
    DATABASE_URL: str = "sqlite:///data/reviewpulse.db"
    
    JIRA_URL: str | None = None
    JIRA_EMAIL: str | None = None
    JIRA_API_TOKEN: str | None = None
    JIRA_PROJECT_KEY: str | None = "ENG"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_google_credentials(self) -> Credentials:
        """Parses the raw JSON credentials string from memory."""
        try:
            creds_dict = json.loads(self.GOOGLE_APPLICATION_CREDENTIALS_JSON)
            return Credentials.from_service_account_info(creds_dict)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load Google credentials from JSON: {e}")

settings = Settings()
