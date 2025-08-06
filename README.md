# Teams Service 🏆

Serviço em FastAPI responsável pelo gerenciamento das equipes, membros e processamento de solicitações via mensageria assíncrona para a plataforma IFSports.

## 📋 Descrição

O Teams Service é um microserviço desenvolvido em Python utilizando o framework FastAPI, responsável por:

- **Gerenciamento de Equipes**: Criação, edição, exclusão e consulta de equipes
- **Gestão de Membros**: Controle de membros das equipes, incluindo permissões e funções
- **Mensageria Assíncrona**: Processamento de solicitações e respostas via sistema de mensageria
- **Integração**: Comunicação com outros serviços da plataforma IFSports

## 🚀 Tecnologias Utilizadas

- **Python 3.8+**
- **FastAPI** - Framework web moderno e rápido
- **Uvicorn** - Servidor ASGI
- **SQLAlchemy** - ORM para banco de dados
- **Pydantic** - Validação de dados
- **RabbitMQ** - Mensageria assíncrona
- **PostgreSQL** - Banco de dados principal
- **Redis** - Cache e broker de mensagens

## 🛠️ Instalação e Configuração

### Pré-requisitos

- Python 3.8+
- PostgreSQL
- Redis
- Docker (opcional)

### Configuração Local

1. **Clone o repositório**
```bash
git clone https://github.com/ifsports/teams_service.git
cd teams_service
```

2. **Crie um ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Execute as migrações**
```bash
alembic upgrade head
```

5. **Inicie o servidor**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).

## 👥 Equipe

Desenvolvido pela equipe IFSports.

---

**IFSports Teams Service** - Gerenciamento inteligente de equipes esportivas 🏆
