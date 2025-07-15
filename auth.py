from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from typing import List

SECRET_KEY = "django-insecure-f=td$@o*6$utz@_2kvjf$zss#*r_8f74whhgo9y#p7rz@t*ii("
ALGORITHM = "HS256"

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
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )