import os

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your_secret_key_here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes