```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models import Todo, User
from app.schemas import TodoCreate, TodoUpdate, TodoResponse, UserRegister
from app.services import get_db, authenticate_user, create_access_token, create_todo, update_todo_item, delete_todo_item, get_all_todos, create_user

router = APIRouter()

@router.post("/todos", response_model=TodoResponse)
def add_todo(todo: TodoCreate, db: Session = Depends(get_db), current_user: User = Depends(authenticate_user)):
    return create_todo(todo, db, current_user)

@router.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, todo_update: TodoUpdate, db: Session = Depends(get_db), current_user: User = Depends(authenticate_user)):
    return update_todo_item(todo_id, todo_update, db, current_user)

@router.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db), current_user: User = Depends(authenticate_user)):
    return delete_todo_item(todo_id, db, current_user)

@router.get("/todos", response_model=List[TodoResponse])
def get_todos(sort_order: str = None, db: Session = Depends(get_db), current_user: User = Depends(authenticate_user)):
    return get_all_todos(current_user, sort_order, db)

@router.post("/auth/register")
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    return create_user(user_data, db)
```