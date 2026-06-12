import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.main import app
from app.todos.schemas import TodoCreate, TodoUpdate
from app.todos.models import Todo
from app.todos.crud import create_todo, get_todos, update_todo, delete_todo
from app.dependencies import get_db
from app.auth.routers.login import authenticate_user, create_access_token

client = TestClient(app)

# Mock the database session for testing
@pytest.fixture
def mock_db():
    with patch("app.todos.crud.SessionLocal") as mock_session:
        yield mock_session.return_value

# Mock the current user for testing
@pytest.fixture
def mock_current_user(mock_db):
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com"
    }

# Test creating a new to-do item
def test_create_new_todo(mock_db, mock_current_user):
    todo_data = TodoCreate(title="Test Todo", description="This is a test todo", due_date="2023-10-31", priority=1)
    
    with patch("app.todos.routers.v1.todos.get_current_user") as mock_get_current_user:
        mock_get_current_user.return_value = mock_current_user
        response = client.post("/todos/", json={"todo": todo_data.dict()})
        
    assert response.status_code == 200
    created_todo = response.json()
    assert created_todo["title"] == "Test Todo"
    assert created_todo["description"] == "This is a test todo"
    assert created_todo["due_date"] == "2023-10-31"
    assert created_todo["priority"] == 1
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

# Test retrieving all to-do items
def test_read_todos(mock_db, mock_current_user):
    with patch("app.todos.routers.v1.todos.get_current_user") as mock_get_current_user:
        mock_get_current_user.return_value = mock_current_user
        response = client.get("/todos/")
        
    assert response.status_code == 200
    todos = response.json()
    assert isinstance(todos, list)
    mock_db.query.assert_called_once()

# Test updating an existing to-do item
def test_update_todo_item(mock_db, mock_current_user):
    todo_data = TodoCreate(title="Test Todo", description="This is a test todo", due_date="2023-10-31", priority=1)
    created_todo = create_todo(db=mock_db, todo=todo_data)
    
    update_data = TodoUpdate(description="Updated Description")
    
    with patch("app.todos.routers.v1.todos.get_current_user") as mock_get_current_user:
        mock_get_current_user.return_value = mock_current_user
        response = client.put(f"/todos/{created_todo.id}", json={"todo_update": update_data.dict()})
        
    assert response.status_code == 200
    updated_todo = response.json()
    assert updated_todo["description"] == "Updated Description"
    mock_db.query.assert_called_once()
    mock_db.commit.assert_called_once()

# Test deleting an existing to-do item
def test_delete_todo_item(mock_db, mock_current_user):
    todo_data = TodoCreate(title="Test Todo", description="This is a test todo", due_date="2023-10-31", priority=1)
    created_todo = create_todo(db=mock_db, todo=todo_data)
    
    with patch("app.todos.routers.v1.todos.get_current_user") as mock_get_current_user:
        mock_get_current_user.return_value = mock_current_user
        response = client.delete(f"/todos/{created_todo.id}")
        
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Todo deleted successfully"
    mock_db.query.assert_called_once()
    mock_db.commit.assert_called_once()

# Test updating a non-existent to-do item
def test_update_non_existent_todo_item(mock_db, mock_current_user):
    update_data = TodoUpdate(description="Updated Description")
    
    with patch("app.todos.routers.v1.todos.get_current_user") as mock_get_current_user:
        mock_get_current_user.return_value = mock_current_user
        response = client.put("/todos/999", json={"todo_update": update_data.dict()})
        
    assert response.status_code == 404
    error = response.json()
    assert error["detail"] == "Todo not found"

# Test deleting a non-existent to-do item
def test_delete_non_existent_todo_item(mock_db, mock_current_user):
    
    with patch("app.todos.routers.v1.todos.get_current_user") as mock_get_current_user:
        mock_get_current_user.return_value = mock_current_user
        response = client.delete("/todos/999")
        
    assert response.status_code == 404
    error = response.json()
    assert error["detail"] == "Todo not found"