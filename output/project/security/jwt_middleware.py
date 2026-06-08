```python
import jwt
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"

security = HTTPBearer()

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(request: Request):
    credentials = await security(request)
    token = credentials.credentials
    payload = verify_token(token)
    return payload

def get_auth_dependency():
    return Depends(get_current_user)
```