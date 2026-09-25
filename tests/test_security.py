import pytest
from jose import jwt

from src import security
from tests.conftest import registered_user


@pytest.mark.anyio
async def test_password_hashes():
    password = "password"

    assert security.verify_password(password, security.get_password_hash(password))


@pytest.mark.anyio
async def test_get_user(registered_user: dict):
    user = await security.get_user(registered_user["email"])

    assert user.email == registered_user["email"]


@pytest.mark.anyio
async def test_get_user_not_found():
    user = await security.get_user("test@example.com")

    assert user is None


@pytest.mark.anyio
async def test_create_access_token():
    token = security.create_access_token("email")

    assert {"sub": "email", "type": "access"}.items() <= jwt.decode(
        token,
        key=security.config.SECRET_KEY,
        algorithms=[security.config.ALGORITHM],
    ).items()


@pytest.mark.anyio
async def test_create_confirmation_token():
    token = security.create_confirmation_token("email")

    assert {"sub": "email", "type": "confirmation"}.items() <= jwt.decode(
        token,
        key=security.config.SECRET_KEY,
        algorithms=[security.config.ALGORITHM],
    ).items()


@pytest.mark.anyio
async def test_get_subject_for_token_type_valid_confirmation():
    email = "test@example.com"
    token = security.create_confirmation_token(email)

    assert email == security.get_subject_for_token_type(token, "confirmation")


@pytest.mark.anyio
async def test_get_subject_for_token_type_valid_access():
    email = "test@example.com"
    token = security.create_access_token(email)

    assert email == security.get_subject_for_token_type(token, "access")


@pytest.mark.anyio
async def test_get_subject_for_token_type_expired(mocker):
    mocker.patch("src.security.access_token_expire_minutes", return_value=-1)
    email = "test@example.com"
    token = security.create_access_token(email)

    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")

    assert "Token has expired" == exc_info.value.detail


@pytest.mark.anyio
async def test_get_subject_for_token_type_invalid():
    token = "invalid"

    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")

    assert "Invalid token" == exc_info.value.detail


@pytest.mark.anyio
async def test_authenticate_user(confirmed_user: dict):
    user = await security.authenticate_user(
        email=confirmed_user["email"],
        password=confirmed_user["password"],
    )

    assert user.email == confirmed_user["email"]


@pytest.mark.anyio
async def test_authenticate_user_not_found():
    with pytest.raises(security.HTTPException):
        await security.authenticate_user(
            email="test@example.net",
            password="1234",
        )


@pytest.mark.anyio
async def test_authenticate_user_with_wrong_password(registered_user: dict):
    with pytest.raises(security.HTTPException):
        await security.authenticate_user(
            email=registered_user["email"],
            password="wrong password",
        )


@pytest.mark.anyio
async def test_get_current_user(registered_user: dict):
    token = security.create_access_token(email=registered_user["email"])
    user = await security.get_current_user(token=token)

    assert user.email == registered_user["email"]


@pytest.mark.anyio
async def test_get_current_user_with_invalid_token():
    with pytest.raises(security.HTTPException):
        await security.get_current_user(token="invalid token")


@pytest.mark.anyio
async def test_get_current_user_wrong_type_token(registered_user: dict):
    token = security.create_confirmation_token(registered_user["email"])

    with pytest.raises(security.HTTPException):
        await security.get_current_user(token)
