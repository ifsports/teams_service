from contextlib import asynccontextmanager

import asyncio

import uvicorn

from fastapi import FastAPI

from messaging.consumers import main_consumer
from shared.exceptions import NotFound, Conflict
from shared.exceptions_handler import not_found_exception_handler, conflict_exception_handler

from teams.routers import teams_router, team_members_router

consumer_task = None


@asynccontextmanager
async def lifespan_manager(app: FastAPI):
    global consumer_task
    print("INFO:     [requests_service] Lifespan: Iniciando consumidor RabbitMQ...")
    try:
        consumer_task = asyncio.create_task(main_consumer())
        print("INFO:     [requests_service] Lifespan: Tarefa do consumidor RabbitMQ criada e agendada.")
    except Exception as e:
        print(f"ERRO CRÍTICO: [requests_service] Lifespan: Falha ao iniciar a tarefa do consumidor: {e}")

    yield

    print("INFO:     [requests_service] Lifespan: Finalizando. Solicitando cancelamento da tarefa do consumidor...")
    if consumer_task and not consumer_task.done():
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            print("INFO:     [requests_service] Lifespan: Tarefa do consumidor RabbitMQ cancelada com sucesso.")
        except Exception as e:
            print(f"ERRO: [requests_service] Lifespan: Erro durante o cancelamento da tarefa do consumidor: {e}")
    else:
        print(
            "INFO:     [requests_service] Lifespan: Tarefa do consumidor não estava ativa ou já havia sido concluída.")
    print("INFO:     [requests_service] Lifespan: Processo de shutdown concluído.")


app = FastAPI(lifespan=lifespan_manager)

app.include_router(teams_router.router)

app.include_router(team_members_router.router)

app.add_exception_handler(NotFound, not_found_exception_handler)
app.add_exception_handler(Conflict, conflict_exception_handler)

@app.get("/health")
async def health_check():
    task_status = "não iniciada ou já concluída"
    if consumer_task:
        if consumer_task.done():
            if consumer_task.cancelled():
                task_status = "cancelada"
            elif consumer_task.exception():
                task_status = f"falhou com exceção: {consumer_task.exception()}"
            else:
                task_status = "concluída normalmente"
        else:
            task_status = "rodando"

    return {
        "service": "requests_service",
        "status": "healthy_api",
        "consumer_task_status": task_status
    }

if __name__ == "__main__":
    uvicorn.run(app , host="0.0.0.0", port=8003, proxy_headers=True)