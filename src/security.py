import datetime
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pwdlib import PasswordHash

from src.config import config
from src.database import database, user_table

logger = logging.getLogger(__name__)

auth2_scheme = OAuth2PasswordBearer(tokenUrl="user/token")
pwd_context = PasswordHash.recommended()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def access_token_expire_minutes() -> int:
    return 30


def create_access_token(email: str):
    logger.debug("Create access token", extra={"email": email})
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=access_token_expire_minutes(),
    )
    jwt_data = {"sub": email, "exp": expire}
    encoded_jwt = jwt.encode(
        jwt_data,
        key=config.SECRET_KEY,
        algorithm=config.ALGORITHM,
    )
    return encoded_jwt


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_user(email: str):
    logger.debug("Fetching user from the database", extra={"email": email})
    query = user_table.select().where(user_table.c.email == email)
    result = await database.fetch_one(query)
    if result:
        return result

    return None


async def authenticate_user(email: str, password: str):
    logger.debug("Authenticate user", extra={"email": email})
    user = await get_user(email)
    if not user:
        raise credentials_exception

    if not verify_password(password, user.password):
        raise credentials_exception

    return user


async def get_current_user(token: Annotated[str, Depends(auth2_scheme)]):
    try:
        payload = jwt.decode(
            token=token,
            key=config.SECRET_KEY,
            algorithms=[config.ALGORITHM],
        )
        email = payload.get("sub")
        if not email:
            raise credentials_exception

    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except JWTError as e:
        raise credentials_exception from e

    user = await get_user(email=email)
    if not user:
        raise credentials_exception

    return user
