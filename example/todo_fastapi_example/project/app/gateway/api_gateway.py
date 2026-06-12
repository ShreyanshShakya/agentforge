from fastapi import FastAPI, Depends
from app.auth.routers.login import auth_dependency
from app.todos.routers.v1.todos import router as todos_router

app = FastAPI()

# Include the routes from the Todo Management Service
app.include_router(todos_router, prefix="/api/v1/todos", dependencies=[Depends(auth_dependency)])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Todo API Gateway"}