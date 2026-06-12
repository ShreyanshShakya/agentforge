```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "your_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    SQLALCHEMY_DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    
    class Config:
        env_file = ".env"

settings = Settings()
```