from shared.exceptions import NotFound, Conflict

from fastapi import Request
from fastapi.responses import JSONResponse


async def not_found_exception_handler(request: Request, exc: NotFound):
    return JSONResponse(
        status_code=404,
        content={
            "message": f"Oops! {exc.name} não encontrado(a)."
        },
    )


async def conflict_exception_handler(request: Request, exc: Conflict):
    return JSONResponse(
        status_code=409,
        content={
            "message": exc.name or "A operação não pode ser realizada porque o recurso está em um estado que não permite essa ação."
        },
    )