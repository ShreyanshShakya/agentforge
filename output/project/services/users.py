```python
from fastapi import HTTPException, status
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    username: str
    password: str

class UserService:
    def register_user(self, user_data: User) -> dict:
        # Logic to register a new user
        try:
            # Simulate user registration
            return {"message": "User registered successfully"}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    def login_user(self, user_data: User) -> dict:
        # Logic to authenticate user and return JWT token
        try:
            # Simulate user authentication
            if user_data.username == "admin" and user_data.password == "password":
                return {"message": "Login successful", "token": "fake-jwt-token"}
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
```