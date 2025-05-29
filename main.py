import uvicorn

from fastapi import FastAPI

from shared.exceptions import NotFound, Conflict
from shared.exceptions_handler import not_found_exception_handler, conflict_exception_handler

from teams.routers import teams_router

app = FastAPI()

app.include_router(teams_router.router)

app.add_exception_handler(NotFound, not_found_exception_handler)
app.add_exception_handler(Conflict, conflict_exception_handler)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)