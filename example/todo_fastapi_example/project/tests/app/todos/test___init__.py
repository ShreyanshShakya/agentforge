import pytest
from unittest.mock import patch, MagicMock
from app.todos.routers.v1.todos import router as todos_router
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(todos_router)
    return TestClient(app)

@patch('app.todos.service.TodoService.get_todos')
def test_get_todos_success(mock_service, client):
    mock_service.return_value = [{'id': 1, 'title': 'Task 1'}]
    
    response = client.get('/v1/todos/')
    
    assert response.status_code == 200
    assert response.json() == [{'id': 1, 'title': 'Task 1'}]

@patch('app.todos.service.TodoService.get_todos')
def test_get_todos_failure(mock_service, client):
    mock_service.side_effect = Exception("Database error")
    
    response = client.get('/v1/todos/')
    
    assert response.status_code == 500
    assert 'Database error' in response.json()['detail']

@patch('app.todos.service.TodoService.create_todo')
def test_create_todo_success(mock_service, client):
    mock_service.return_value = {'id': 2, 'title': 'Task 2'}
    
    data = {
        'title': 'Task 2',
        'description': 'Description of task 2',
        'due_date': '2023-10-01T12:00:00Z',
        'priority_level': 'high',
        'status': 'pending'
    }
    
    response = client.post('/v1/todos/', json=data)
    
    assert response.status_code == 201
    assert response.json() == {'id': 2, 'title': 'Task 2'}

@patch('app.todos.service.TodoService.create_todo')
def test_create_todo_failure(mock_service, client):
    mock_service.side_effect = Exception("Database error")
    
    data = {
        'title': 'Task 2',
        'description': 'Description of task 2',
        'due_date': '2023-10-01T12:00:00Z',
        'priority_level': 'high',
        'status': 'pending'
    }
    
    response = client.post('/v1/todos/', json=data)
    
    assert response.status_code == 500
    assert 'Database error' in response.json()['detail']

@patch('app.todos.service.TodoService.update_todo')
def test_update_todo_success(mock_service, client):
    mock_service.return_value = {'id': 3, 'title': 'Updated Task'}
    
    data = {
        'title': 'Updated Task',
        'description': 'Updated description',
        'due_date': '2023-10-02T12:00:00Z',
        'priority_level': 'medium',
        'status': 'completed'
    }
    
    response = client.put('/v1/todos/3', json=data)
    
    assert response.status_code == 200
    assert response.json() == {'id': 3, 'title': 'Updated Task'}

@patch('app.todos.service.TodoService.update_todo')
def test_update_todo_failure(mock_service, client):
    mock_service.side_effect = Exception("Database error")
    
    data = {
        'title': 'Updated Task',
        'description': 'Updated description',
        'due_date': '2023-10-02T12:00:00Z',
        'priority_level': 'medium',
        'status': 'completed'
    }
    
    response = client.put('/v1/todos/3', json=data)
    
    assert response.status_code == 500
    assert 'Database error' in response.json()['detail']

@patch('app.todos.service.TodoService.delete_todo')
def test_delete_todo_success(mock_service, client):
    mock_service.return_value = True
    
    response = client.delete('/v1/todos/4')
    
    assert response.status_code == 204

@patch('app.todos.service.TodoService.delete_todo')
def test_delete_todo_failure(mock_service, client):
    mock_service.side_effect = Exception("Database error")
    
    response = client.delete('/v1/todos/4')
    
    assert response.status_code == 500
    assert 'Database error' in response.json()['detail']