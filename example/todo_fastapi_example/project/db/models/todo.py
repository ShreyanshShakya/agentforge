```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime

from config.database import Base
from models.user import User  # Adjust the path according to your project structure

class TodoStatus(str, Enum):
    TO_DO = "To do"
    IN_PROGRESS = "In progress"
    COMPLETED = "Completed"

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    due_date = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(TodoStatus), default=TodoStatus.TO_DO)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)

    owner = relationship("User", back_populates="todos")
```