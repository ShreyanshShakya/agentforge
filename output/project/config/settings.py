```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "default_secret_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

    class Config:
        env_file = ".env"

settings = Settings()
```