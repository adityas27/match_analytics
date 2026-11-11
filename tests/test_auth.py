import pytest
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def registered_user(db):
    return User.objects.create_user(
        email="user@example.com",
        password="strong-password-123",
        first_name="Test",
    )


def test_django_starts_and_database_connects(db):
    connection.ensure_connection()
    assert connection.is_usable()


def test_registration_returns_tokens_and_safe_user(api_client, db):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "new@example.com", "password": "strong-password-123"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user"]["email"] == "new@example.com"
    assert "password" not in response.data["user"]
    assert response.data["access"]
    assert response.data["refresh"]


def test_login_and_token_refresh(api_client, registered_user):
    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": registered_user.email, "password": "strong-password-123"},
        format="json",
    )
    assert login.status_code == status.HTTP_200_OK
    refresh = api_client.post(
        "/api/v1/auth/token/refresh/",
        {"refresh": login.data["refresh"]},
        format="json",
    )
    assert refresh.status_code == status.HTTP_200_OK
    assert refresh.data["access"]
    verify = api_client.post(
        "/api/v1/auth/token/verify/",
        {"token": login.data["access"]},
        format="json",
    )
    assert verify.status_code == status.HTTP_200_OK


def test_authenticated_profile(api_client, registered_user):
    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": registered_user.email, "password": "strong-password-123"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == registered_user.email


def test_logout_blacklists_refresh_token(api_client, registered_user):
    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": registered_user.email, "password": "strong-password-123"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    logout = api_client.post(
        "/api/v1/auth/logout/",
        {"refresh": login.data["refresh"]},
        format="json",
    )
    assert logout.status_code == status.HTTP_205_RESET_CONTENT
    refresh = api_client.post(
        "/api/v1/auth/token/refresh/",
        {"refresh": login.data["refresh"]},
        format="json",
    )
    assert refresh.status_code == status.HTTP_401_UNAUTHORIZED
