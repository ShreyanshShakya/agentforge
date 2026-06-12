```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config.dependencies import get_db
from db.models.todo import Todo
from auth.auth_handler import get_current_user

router = APIRouter()

@router.post("/todos/", status_code=201)
async def create_todo(todo: Todo, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    todo.user_id = current_user['id']
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo

@router.get("/todos/", status_code=200)
async def read_todos(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    todos = db.query(Todo).filter(Todo.user_id == current_user['id']).all()
    return todos

@router.put("/todos/{todo_id}", status_code=200)
async def update_todo(todo_id: int, todo: Todo, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    todo_item = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == current_user['id']).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="Todo item not found")
    todo_item.title = todo.title
    todo_item.description = todo.description
    todo_item.due_date = todo.due_date
    todo_item.status = todo.status
    db.commit()
    db.refresh(todo_item)
    return todo_item

@router.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    todo_item = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == current_user['id']).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="Todo item not found")
    db.delete(todo_item)
    db.commit()
    return {"detail": "Todo item deleted"}
```