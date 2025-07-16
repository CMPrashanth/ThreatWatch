import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Manages application settings using Pydantic's BaseSettings.
    """
    # --- THIS IS THE FIX ---
    # The 'extra' setting tells Pydantic to ignore any variables in the .env file
    # that are not explicitly defined in this class.
    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # --- Database Configuration ---
    DATABASE_URL: str

    # --- JWT Secret Key ---
    SECRET_KEY: str

    # --- Azure Blob Storage ---
    AZURE_STORAGE_CONNECTION_STRING: str

    # --- AI Model Paths ---
    YOLO_MODEL_PATH: str
    STRONGSORT_CONFIG_PATH: str
    STRONGSORT_WEIGHTS_PATH: str
    
    # --- Notification Services (Service-wide credentials) ---
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    
    # --- Email (SMTP) Settings ---
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # --- Application Settings ---
    PROJECT_NAME: str = "AI Threat Detection API"
    API_V1_STR: str = "/api/v1"

# Create a single, importable instance of the settings
settings = Settings()
