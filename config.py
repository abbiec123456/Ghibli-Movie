import os

class Config:
    # Defaults 
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "ghibli_db")
    DB_USER = os.getenv("DB_USER", "ghibli_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "ghibli_pass")

    # Connection string
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
