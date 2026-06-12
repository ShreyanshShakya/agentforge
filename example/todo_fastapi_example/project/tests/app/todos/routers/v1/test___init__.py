import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import create_app
from app.todos.routers.v1.todos import todos_router

@pytest.fixture
def client():
    app = create_app()
    app.include_router(todos_router)
    return TestClient(app)

@pytest.fixture
def mock_todo_service():
    with patch('app.todos.routers.v1.todos.TodoService') as mock:
        yield mock.return_value

# Success path tests
def test_create_todo_success(client, mock_todo_service):
    mock_todo_service.create.return_value = {'id': 1, 'title': 'Test Todo', 'description': 'Test Description'}
    response = client.post("/todos", json={"title": "Test Todo", "description": "Test Description"})
    assert response.status_code == 201
    assert response.json() == {'id': 1, 'title': 'Test Todo', 'description': 'Test Description'}

def test_get_todos_success(client, mock_todo_service):
    mock_todo_service.get_all.return_value = [{'id': 1, 'title': 'Test Todo', 'description': 'Test Description'}]
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == [{'id': 1, 'title': 'Test Todo', 'description': 'Test Description'}]

def test_update_todo_success(client, mock_todo_service):
    mock_todo_service.update.return_value = {'id': 1, 'title': 'Updated Todo', 'description': 'Updated Description'}
    response = client.put("/todos/1", json={"title": "Updated Todo", "description": "Updated Description"})
    assert response.status_code == 200
    assert response.json() == {'id': 1, 'title': 'Updated Todo', 'description': 'Updated Description'}

def test_delete_todo_success(client, mock_todo_service):
    mock_todo_service.delete.return_value = True
    response = client.delete("/todos/1")
    assert response.status_code == 204

# Error path tests
def test_create_todo_invalid_payload(client, mock_todo_service):
    mock_todo_service.create.side_effect = ValueError("Invalid payload")
    response = client.post("/todos", json={"title": "Test Todo"})
    assert response.status_code == 422
    assert response.json() == {"detail": [{"loc": ["body", "description"], "msg": "field required", "type": "value_error.missing"}]}

def test_get_todos_empty(client, mock_todo_service):
    mock_todo_service.get_all.return_value = []
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_update_todo_not_found(client, mock_todo_service):
    mock_todo_service.update.side_effect = ValueError("Todo not found")
    response = client.put("/todos/999", json={"title": "Updated Todo"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}

def test_delete_todo_not_found(client, mock_todo_service):
    mock_todo_service.delete.side_effect = ValueError("Todo not found")
    response = client.delete("/todos/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}