from fastapi import APIRouter

router = APIRouter()

# Import and include other routers here
from ..todos.routers.v1.todos import router as todos_router

router.include_router(todos_router, prefix="/todos")