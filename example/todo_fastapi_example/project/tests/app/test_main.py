import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

# Mock the authentication service to simulate user login and token generation
@patch('app.auth.service.authenticate_user')
def test_authenticate_user(mock_authenticate):
    mock_authenticate.return_value = {"username": "testuser", "token": "mock_token"}
    response = client.post("/auth/login", data={"username": "testuser", "password": "testpass"})
    assert response.status_code == 200
    assert response.json() == {"username": "testuser", "token": "mock_token"}

# Mock the todos service to simulate CRUD operations for to-dos
@patch('app.todos.service.create_todo')
def test_create_todo(mock_create):
    mock_create.return_value = {
        'id': 1,
        'title': 'Test Todo',
        'description': 'This is a test todo',
        'due_date': datetime.now(),
        'priority_level': 'high',
        'status': 'in_progress'
    }
    response = client.post("/todos", headers={"Authorization": "Bearer mock_token"}, json={
        'title': 'Test Todo',
        'description': 'This is a test todo',
        'due_date': datetime.now().isoformat(),
        'priority_level': 'high',
        'status': 'in_progress'
    })
    assert response.status_code == 201
    assert response.json() == {
        'id': 1,
        'title': 'Test Todo',
        'description': 'This is a test todo',
        'due_date': mock_create.return_value['due_date'].isoformat(),
        'priority_level': 'high',
        'status': 'in_progress'
    }

@patch('app.todos.service.get_all_todos')
def test_get_all_todos(mock_get_all):
    mock_get_all.return_value = [
        {
            'id': 1,
            'title': 'Test Todo 1',
            'description': 'This is a test todo 1',
            'due_date': datetime.now(),
            'priority_level': 'high',
            'status': 'in_progress'
        },
        {
            'id': 2,
            'title': 'Test Todo 2',
            'description': 'This is a test todo 2',
            'due_date': datetime.now(),
            'priority_level': 'low',
            'status': 'completed'
        }
    ]
    response = client.get("/todos", headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 200
    assert response.json() == [
        {
            'id': 1,
            'title': 'Test Todo 1',
            'description': 'This is a test todo 1',
            'due_date': mock_get_all.return_value[0]['due_date'].isoformat(),
            'priority_level': 'high',
            'status': 'in_progress'
        },
        {
            'id': 2,
            'title': 'Test Todo 2',
            'description': 'This is a test todo 2',
            'due_date': mock_get_all.return_value[1]['due_date'].isoformat(),
            'priority_level': 'low',
            'status': 'completed'
        }
    ]

@patch('app.todos.service.update_todo')
def test_update_todo(mock_update):
    mock_update.return_value = {
        'id': 1,
        'title': 'Updated Test Todo',
        'description': 'This is an updated test todo',
        'due_date': datetime.now(),
        'priority_level': 'medium',
        'status': 'on_hold'
    }
    response = client.put("/todos/1", headers={"Authorization": "Bearer mock_token"}, json={
        'title': 'Updated Test Todo',
        'description': 'This is an updated test todo',
        'due_date': datetime.now().isoformat(),
        'priority_level': 'medium',
        'status': 'on_hold'
    })
    assert response.status_code == 200
    assert response.json() == {
        'id': 1,
        'title': 'Updated Test Todo',
        'description': 'This is an updated test todo',
        'due_date': mock_update.return_value['due_date'].isoformat(),
        'priority_level': 'medium',
        'status': 'on_hold'
    }

@patch('app.todos.service.delete_todo')
def test_delete_todo(mock_delete):
    mock_delete.return_value = None
    response = client.delete("/todos/1", headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 204