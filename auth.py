from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from typing import List, Optional

SECRET_KEY = "django-insecure-f=td$@o*6$utz@_2kvjf$zss#*r_8f74whhgo9y#p7rz@t*ii("
ALGORITHM = "HS256"

class OptionalHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        authorization: str = request.headers.get("Authorization")
        if not authorization:
            return None
        return await super().__call__(request)

optional_security = OptionalHTTPBearer()

security = HTTPBearer()

def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_matricula: str = payload.get("matricula")
        campus: str = payload.get("campus")
        groups: List[str] = payload.get("groups")

        if user_matricula is None or campus is None:
            raise ValueError("Dados incompletos no token")

        return {
            "user_matricula": user_matricula,
            "campus": campus,
            "groups": groups,
            "access_token": token
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[dict]:
    if credentials is None:
        return None

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_matricula: str = payload.get("matricula")
        campus: str = payload.get("campus")
        groups: List[str] = payload.get("groups")

        if user_matricula is None or campus is None:
            return None

        return {
            "user_matricula": user_matricula,
            "campus": campus,
            "groups": groups,
            "access_token": token
        }

    except JWTError:
        return None