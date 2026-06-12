import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@patch('app.auth.routers.login.verify_password')
def test_login_success(mock_verify_password, client):
    mock_verify_password.return_value = True
    response = client.post('/auth/login', data={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert 'access_token' in response.json()

@patch('app.auth.routers.login.verify_password')
def test_login_failure(mock_verify_password, client):
    mock_verify_password.return_value = False
    response = client.post('/auth/login', data={'username': 'testuser', 'password': 'wrongpass'})
    assert response.status_code == 401
    assert response.json()['detail'] == 'Incorrect username or password'

@patch('app.auth.routers.login.verify_token')
def test_refresh_success(mock_verify_token, client):
    mock_verify_token.return_value = {'sub': 'testuser'}
    response = client.post('/auth/refresh', headers={'Authorization': 'Bearer oldtoken'})
    assert response.status_code == 200
    assert 'access_token' in response.json()

@patch('app.auth.routers.login.verify_token')
def test_refresh_failure(mock_verify_token, client):
    mock_verify_token.return_value = None
    response = client.post('/auth/refresh', headers={'Authorization': 'Bearer invalidtoken'})
    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid token'