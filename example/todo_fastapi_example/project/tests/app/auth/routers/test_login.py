import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.auth.routers.login import router as auth_router
from app.auth.dependencies import get_db, get_current_active_user

# Mock database and user functions for testing
class MockDB:
    def query(self, model):
        return self

    def filter_by(self, username):
        return self

    def first(self):
        return {"username": "testuser", "password_hash": "hashed_password"}

def mock_get_db():
    return MockDB()

@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(auth_router)
    with TestClient(app) as client:
        yield client

@patch('app.auth.dependencies.get_db', new=mock_get_db)
@patch('app.auth.utils.authenticate_user')
def test_login_for_access_token(mock_authenticate, client):
    mock_authenticate.return_value = {"username": "testuser", "password_hash": "hashed_password"}
    form_data = OAuth2PasswordRequestForm(username="testuser", password="correctpassword")
    response = client.post("/token", data=form_data.dict())
    assert response.status_code == 200
    assert "access_token" in response.json()

@patch('app.auth.dependencies.get_db', new=mock_get_db)
@patch('app.auth.utils.authenticate_user')
def test_login_for_access_token_invalid_credentials(mock_authenticate, client):
    mock_authenticate.return_value = None
    form_data = OAuth2PasswordRequestForm(username="testuser", password="wrongpassword")
    response = client.post("/token", data=form_data.dict())
    assert response.status_code == 401

@patch('app.auth.dependencies.get_db', new=mock_get_db)
def test_read_users_me(client):
    with patch('app.auth.dependencies.get_current_active_user') as mock_user:
        mock_user.return_value = {"username": "testuser"}
        response = client.get("/users/me/")
        assert response.status_code == 200
        assert response.json() == {"username": "testuser"}

@patch('app.auth.dependencies.get_db', new=mock_get_db)
def test_read_users_me_not_authenticated(client):
    response = client.get("/users/me/", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401