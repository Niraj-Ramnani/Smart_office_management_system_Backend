import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Smart Office Management System"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/smart_office",
    )
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ] or [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    # Microsoft Entra ID Settings
    AZURE_TENANT_ID: str = os.getenv(
        "AZURE_TENANT_ID",
        "4f104e29-1d92-473f-8ae7-f975f8a17d72",
    )
    AZURE_CLIENT_ID: str = os.getenv(
        "AZURE_CLIENT_ID",
        "8e96a2cc-643a-40db-9f09-25f521294994",
    )
    AZURE_API_AUDIENCE: str = os.getenv(
        "AZURE_API_AUDIENCE",
        "8e96a2cc-643a-40db-9f09-25f521294994",
    )
    AZURE_API_SCOPE: str = os.getenv(
        "AZURE_API_SCOPE",
        f"api://{AZURE_CLIENT_ID}/access_as_user",
    )


settings = Settings()
