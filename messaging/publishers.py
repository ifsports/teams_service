import aio_pika
import json
import os

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


TEAMS_COMMANDS_EXCHANGE = "teams_commands_exchange"

async def publish_team_creation_requested(team_data: dict):
    """
    Publica uma mensagem indicando que a criação de uma equipe foi solicitada
    e requer aprovação.
    """
    connection = None
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)

        async with connection.channel() as channel:
            exchange = await channel.declare_exchange(
                TEAMS_COMMANDS_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )

            message_body = json.dumps(team_data).encode()

            routing_key = "team.creation.requested"

            message = aio_pika.Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            await exchange.publish(message, routing_key=routing_key)
            print(f" [teams_service] Sent '{routing_key}':'{team_data}'")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Erro de conexão com RabbitMQ: {e}")
    except Exception as e:
        print(f"Erro ao publicar mensagem: {e}")
    finally:
        if connection and not connection.is_closed:
            await connection.close()


async def publish_team_deletion_requested(team_data: dict):
    """
        Publica uma mensagem indicando que a remoção de uma equipe foi solicitada
        e requer aprovação.
        """
    connection = None
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)

        async with connection.channel() as channel:
            exchange = await channel.declare_exchange(
                TEAMS_COMMANDS_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )

            message_body = json.dumps(team_data).encode()

            routing_key = "team.deletion.requested"

            message = aio_pika.Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            await exchange.publish(message, routing_key=routing_key)
            print(f" [teams_service] Sent '{routing_key}':'{team_data}'")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Erro de conexão com RabbitMQ: {e}")
    except Exception as e:
        print(f"Erro ao publicar mensagem: {e}")
    finally:
        if connection and not connection.is_closed:
            await connection.close()


async def publish_remove_member_requested(team_data: dict):
    """
        Publica uma mensagem indicando que a remoção de um membro foi solicitada
        e requer aprovação.
    """
    connection = None
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)

        async with connection.channel() as channel:
            exchange = await channel.declare_exchange(
                TEAMS_COMMANDS_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )

            message_body = json.dumps(team_data).encode()

            routing_key = "member.removal.requested"

            message = aio_pika.Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            await exchange.publish(message, routing_key=routing_key)
            print(f" [teams_service] Sent '{routing_key}':'{team_data}'")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Erro de conexão com RabbitMQ: {e}")
    except Exception as e:
        print(f"Erro ao publicar mensagem: {e}")
    finally:
        if connection and not connection.is_closed:
            await connection.close()


async def publish_add_member_requested(team_data: dict):
    """
        Publica uma mensagem indicando que a adição de um membro foi solicitada
        e requer aprovação.
    """
    connection = None
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)

        async with connection.channel() as channel:
            exchange = await channel.declare_exchange(
                TEAMS_COMMANDS_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )

            message_body = json.dumps(team_data).encode()

            routing_key = "member.add.requested"

            message = aio_pika.Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            await exchange.publish(message, routing_key=routing_key)
            print(f" [teams_service] Sent '{routing_key}':'{team_data}'")

    except aio_pika.exceptions.AMQPConnectionError as e:
        print(f"Erro de conexão com RabbitMQ: {e}")
    except Exception as e:
        print(f"Erro ao publicar mensagem: {e}")
    finally:
        if connection and not connection.is_closed:
            await connection.close()


if __name__ == "__main__":
    pass