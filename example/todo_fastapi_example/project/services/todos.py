```python
from typing import List, Optional
from sqlalchemy.orm import Session
from models.todo import Todo
from schemas.todo import TodoCreate, TodoUpdate

def get_todo(db: Session, todo_id: int):
    return db.query(Todo).filter(Todo.id == todo_id).first()

def get_todos_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 10):
    return db.query(Todo).filter(Todo.user_id == user_id).offset(skip).limit(limit).all()

def create_todo(db: Session, todo: TodoCreate, user_id: int):
    db_todo = Todo(**todo.dict(), user_id=user_id)
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def update_todo(db: Session, todo_id: int, todo_update: TodoUpdate):
    db_todo = get_todo(db, todo_id)
    if not db_todo:
        return None
    for key, value in todo_update.dict(exclude_unset=True).items():
        setattr(db_todo, key, value)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def delete_todo(db: Session, todo_id: int):
    db_todo = get_todo(db, todo_id)
    if not db_todo:
        return None
    db.delete(db_todo)
    db.commit()
    return db_todo
```