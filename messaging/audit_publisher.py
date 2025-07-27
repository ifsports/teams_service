import asyncio
import aio_pika
import json
import os
import uuid
from datetime import datetime, timezone

RABBITMQ_USER_DEFAULT = "guest"
RABBITMQ_PASSWORD_DEFAULT = "guest"
RABBITMQ_HOST_DEFAULT = "rabbitmq"
RABBITMQ_PORT_DEFAULT = "5672"
RABBITMQ_VHOST_DEFAULT = "/"

RABBITMQ_URL = os.getenv("RABBITMQ_URL")

if not RABBITMQ_URL:
    user = os.getenv("RABBITMQ_USER", RABBITMQ_USER_DEFAULT)
    password = os.getenv("RABBITMQ_PASSWORD", RABBITMQ_PASSWORD_DEFAULT)
    host = os.getenv("RABBITMQ_HOST", RABBITMQ_HOST_DEFAULT)
    port = os.getenv("RABBITMQ_PORT", RABBITMQ_PORT_DEFAULT)
    vhost = os.getenv("RABBITMQ_VHOST", RABBITMQ_VHOST_DEFAULT)

    if not vhost or vhost == "/":
        vhost_path = ""
    elif not vhost.startswith("/"):
        vhost_path = "/" + vhost
    else:
        vhost_path = vhost

    RABBITMQ_URL = f"amqp://{user}:{password}@{host}:{port}{vhost_path}"
    print(f"INFO: RABBITMQ_URL não estava definida no ambiente. URL montada: {RABBITMQ_URL}")
else:
    print(f"INFO: Usando RABBITMQ_URL definida no ambiente: {RABBITMQ_URL}")

def generate_log_payload(
    event_type: str,
    service_origin: str,
    entity_type,
    entity_id,
    operation_type: str,
    campus_code: str,
    user_registration: str,
    request_object,
    old_data: dict | None = None,
    new_data: dict | None = None,
) -> dict:
    """
    Gera um payload de log estruturado com old_data e new_data
    como objetos Python (prontos para serem serializados como JSON nativo).
    """
    
    x_forwarded_for = request_object.META.get('HTTP_X_FORWARDED_FOR')

    ip = "127.0.0.1"

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request_object.META.get('REMOTE_ADDR')


    #if request_object.correlation_id:
    #    correlation_id = request_object.correlation_id
    #else:
    correlation_id = str(uuid.uuid4())

    return{
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
        "campus_code": campus_code,
        "user_id": user_registration,
        "service_origin": service_origin,
        "event_type": event_type,
        "operation_type": operation_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "old_data": old_data,
        "new_data": new_data,
        "ip_address": ip
    }

# --- Função de Publicação com Routing Key Dinâmica ---

AUDIT_EXCHANGE = "events_exchange"

async def publish_audit_log(log_payload: dict):
    """
    Publica uma mensagem de log de auditoria no RabbitMQ com uma routing key específica.

    :param log_payload: Dados de log a serem publicados.
    """
    connection = None
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)

        async with connection:
            channel = await connection.channel()

            exchange = await channel.declare_exchange(
                AUDIT_EXCHANGE,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            message = aio_pika.Message(
                body=json.dumps(log_payload).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            routing_key = f'{log_payload["event_type"]}'

            # A routing_key agora é o parâmetro recebido pela função
            await exchange.publish(message, routing_key=routing_key)

            print(f"[audit_service] Log enviado para exchange '{AUDIT_EXCHANGE}' com routing key '{routing_key}'")
            print(f"[audit_service] Log payload: {log_payload}")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Erro de conexão com RabbitMQ: {e}")
    except Exception as e:
        print(f"Erro ao publicar mensagem de auditoria: {e}")

def model_to_dict(model_instance):
    if not model_instance:
        return {}
    return {c.name: getattr(model_instance, c.name) for c in model_instance.__table__.columns}

def run_async_audit(log_payload: dict):
    try:
        asyncio.run(publish_audit_log(log_payload))
    except Exception as e:
        print(f"CRITICAL: Falha ao publicar log de auditoria!")