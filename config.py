import os


class BaseConfig:
    """Shared config for all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")

    # Fallback DB values
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "ghibli_db")
    DB_USER = os.getenv("DB_USER", "ghibli_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "ghibli_pass")

    DATABASE_URL = os.getenv("DATABASE_URL")

    @classmethod
    def get_database_url(cls) -> str:
        if cls.DATABASE_URL:
            return cls.DATABASE_URL
        return (
            f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True

    @classmethod
    def get_database_url(cls) -> str:
        return os.getenv("DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(BaseConfig):
    DEBUG = False
