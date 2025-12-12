from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    master_db_name: str = "master_db"

    # ✅ JWT settings
    jwt_secret: str = "super-secret-key"  # override in .env
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
