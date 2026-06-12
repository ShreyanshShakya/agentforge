from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from fastapi.responses import JSONResponse

class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID required")

        key = f"rate_limit:{user_id}"
        current_time = int(redis_client.time()[0])
        expire_time = 60  # Rate limit per minute

        async with redis_client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    count, last_request_time = pipe.get(key) or (0, None)
                    count = int(count.decode()) if count else 0
                    last_request_time = int(last_request_time.decode()) if last_request_time else None

                    if last_request_time and current_time - last_request_time < expire_time:
                        if count >= 10:  # Allow up to 10 requests per minute
                            return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
                        pipe.multi()
                        pipe.incr(key)
                        pipe.expire(key, expire_time)
                    else:
                        pipe.multi()
                        pipe.set(key, 1)
                        pipe.expire(key, expire_time)

                    await pipe.execute()
                    break
                except redis.WatchError:
                    continue

        response = await call_next(request)
        return response