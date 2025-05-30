from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Adicionado para ler variáveis de ambiente
import os

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support

# --- Importe sua Base e defina target_metadata ---
# Verifique se estes caminhos de importação estão corretos para sua estrutura de projeto
# dentro do contêiner Docker (relativo ao WORKDIR /app e PYTHONPATH).
# Se necessário, ajuste para algo como: from app.teams.models... ou from app.shared.database...

# noinspection PyUnresolvedReferences
from teams.models.teams import Team
# noinspection PyUnresolvedReferences
from teams.models.team_member import TeamMember
# noinspection PyUnresolvedReferences
from teams.models.campus import Campus

from shared.database import Base  # Certifique-se que 'Base' é a sua Base declarativa do SQLAlchemy

target_metadata = Base.metadata
# --- Fim da importação da Base ---


# ---- INÍCIO DA PARTE CRUCIAL PARA A URL DO BANCO DE DADOS ----
# Lê a URL do banco da variável de ambiente SQLALCHEMY_DATABASE_URL,
# que deve ser injetada pelo Docker Compose.
ACTUAL_DATABASE_URL_FOR_ALEMBIC_ENV = os.getenv("SQLALCHEMY_DATABASE_URL")

if not ACTUAL_DATABASE_URL_FOR_ALEMBIC_ENV:
    # Se esta variável não estiver definida, o Alembic não conseguirá conectar.
    # Este erro ajudará a diagnosticar se o problema é a variável não estar chegando
    # ao ambiente de execução do script Alembic.
    raise ValueError(
        "ALEMBIC ENV.PY ERRO: A variável de ambiente SQLALCHEMY_DATABASE_URL não está definida ou está vazia. "
        "Verifique se ela foi corretamente injetada no contêiner pelo docker-compose.yml "
        "e se o nome está correto no arquivo .env do orquestrador."
    )


# ---- FIM DA PARTE CRUCIAL PARA A URL DO BANCO DE DADOS ----


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Força o uso da URL da variável de ambiente também no modo offline para consistência.
    url = ACTUAL_DATABASE_URL_FOR_ALEMBIC_ENV
    print(f"DEBUG (alembic/env.py - offline): Configurando para modo OFFLINE com URL: {url}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    print(f"DEBUG (alembic/env.py - online): Iniciando run_migrations_online().")
    print(
        f"DEBUG (alembic/env.py - online): Valor de os.getenv('SQLALCHEMY_DATABASE_URL') é: '{ACTUAL_DATABASE_URL_FOR_ALEMBIC_ENV}'")

    # Pega a configuração da seção principal do alembic.ini (pode ter outras configs úteis)
    alembic_ini_config_section = config.get_section(config.config_ini_section, {})

    print(
        f"DEBUG (alembic/env.py - online): sqlalchemy.url do alembic.ini (antes de sobrescrever): '{alembic_ini_config_section.get('sqlalchemy.url')}'")

    # FORÇA o uso da URL da variável de ambiente que lemos acima.
    # Isso sobrescreve qualquer valor de 'sqlalchemy.url' que possa ter vindo do alembic.ini.
    alembic_ini_config_section['sqlalchemy.url'] = ACTUAL_DATABASE_URL_FOR_ALEMBIC_ENV

    print(
        f"DEBUG (alembic/env.py - online): sqlalchemy.url a ser usado pelo engine_from_config: '{alembic_ini_config_section['sqlalchemy.url']}'")

    connectable = engine_from_config(
        alembic_ini_config_section,  # Usa a configuração MODIFICADA
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    print(f"DEBUG (alembic/env.py - online): Engine criado. Tentando conectar...")

    with connectable.connect() as connection:
        print(f"DEBUG (alembic/env.py - online): Conexão estabelecida com sucesso!")
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            print(f"DEBUG (alembic/env.py - online): Iniciando transação e rodando migrações.")
            context.run_migrations()

    print(f"DEBUG (alembic/env.py - online): Migrações (online) concluídas.")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()