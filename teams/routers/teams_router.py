from fastapi import APIRouter, Depends, Query, HTTPException, status, Response, Request

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

import uuid

from datetime import datetime, timezone

from auth import get_current_user, get_current_user_optional
from messaging.publishers import publish_team_creation_requested, publish_team_deletion_requested
from services.validate_members_http import validate_members_with_auth_service
from services.verify_team_exists import verify_team_exists_with_competitions_service
from shared.auth_utils import has_role

from shared.dependencies import get_db
from shared.exceptions import NotFound, Conflict
from teams.models import TeamMember
from teams.models.teams import Team, TeamStatusEnum
from teams.schemas.teams import TeamResponse, TeamCreateRequest, TeamUpdateRequest, TeamCreationAcceptedResponse, \
    TeamDeleteRequest

import logging

from messaging.audit_publisher import run_async_audit, generate_log_payload, model_to_dict

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/teams",
    tags=["Teams"]
)


@router.get("/", response_model=List[TeamResponse])
async def get_teams_by_campus(status: Optional[TeamStatusEnum] = Query(None, description="Filtrar equipes por status"),
                              campus: Optional[str] = Query(
                                  None, description="Filtrar equipes por campus"),
                              db: Session = Depends(get_db),
                              current_user: Optional[dict] = Depends(get_current_user_optional)):
    """
    List Teams By Campus

    Lista as equipes, com diferentes comportamentos baseados na autenticação e no papel do usuário.

    - **Usuário não autenticado**: Deve fornecer o parâmetro `campus`.
    - **Usuário autenticado (Jogador)**: Lista apenas as equipes das quais o usuário faz parte no seu campus.
    - **Usuário autenticado (não Jogador)**: Lista todas as equipes do campus do usuário.
    - É possível filtrar por status da equipe (ex: `approved`, `pending`).

    **Exemplo de Resposta:**

    .. code-block:: json

       [
         {
           "id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
           "name": "Titãs do Futsal",
           "abbreviation": "TTF",
           "status": "approved",
           "campus_code": "NAT-CN",
           "members": [
             {
               "user_id": "20231012030011"
             },
             {
               "user_id": "20231012030015"
             }
           ]
         },
         {
           "id": "b2c3d4e5-f6a7-b8c9-d0e1-f2a3b4c5d6e7",
           "name": "Guerreiros do Vôlei",
           "abbreviation": "GDV",
           "status": "pending",
           "campus_code": "NAT-CN",
           "members": [
             {
               "user_id": "20241012030020"
             }
           ]
         }
       ]
    """
    if current_user:
        campus_code = current_user["campus"]
        user_id = current_user["user_matricula"]
        groups = current_user["groups"]

        if has_role(groups, "Jogador"):
            query = (
                db.query(Team)
                .join(Team.members)
                .filter(
                    Team.campus_code == campus_code,
                    TeamMember.user_id == user_id
                )
            )
        else:
            query = db.query(Team).filter(Team.campus_code == campus_code)

    else:
        if not campus:
            raise HTTPException(
                status_code=400, detail="Campus deve ser informado se não estiver autenticado")
        query = db.query(Team).filter(Team.campus_code == campus)

    if status:
        query = query.filter(Team.status == status.value)

    return query.all()


@router.post("/")
async def create_team_in_campus(team_request: TeamCreateRequest,
                                response: Response,
                                request_object: Request,
                                db: Session = Depends(get_db),
                                current_user: dict = Depends(get_current_user)):
    """
    Create Team In Campus

    Cria uma nova equipe e envia para aprovação. O processo envolve múltiplas validações:

    - Valida se os membros existem no serviço de autenticação.
    - Verifica se o nome ou abreviação já existem no campus.
    - Consulta o serviço de competições para validar a inscrição.
    - Verifica se os membros já não estão em outra equipe na mesma competição.
    - Publica uma mensagem para um processo de aprovação assíncrono.

    **Exemplo de Corpo da Requisição (Payload):**

    .. code-block:: json

       {
         "name": "Fúria do Basquete",
         "abbreviation": "FDB",
         "competition_id": "c1d2e3f4-a5b6-7890-1234-567890abcdef",
         "members": [
           "20231012030011",
           "20231012030015",
           "20241012030022",
           "20221012030001",
           "20211012030005"
         ]
       }

    **Exemplo de Resposta (202 Accepted):**

    .. code-block:: json

       {
         "message": "Solicitação de criação de equipe enviada para aprovação!",
         "team_id": "d4e5f6a7-b8c9-d0e1-f2a3-b4c5d6e7f8a9"
       }
    """
    campus_code = current_user["campus"]
    groups = current_user["groups"]

    if not team_request.members:
        raise HTTPException(
            status_code=400, detail="A equipe deve ter pelo menos um membro")

    if not team_request.competition_id:
        raise HTTPException(
            status_code=400, detail="ID da competição é obrigatório")

    auth_service_url = "http://authapi:8000/api/v1/auth/users/"
    are_members_valid, validation_message = await validate_members_with_auth_service(
        member_ids=team_request.members,
        auth_service_url=auth_service_url
    )

    if not are_members_valid:
        raise HTTPException(status_code=400, detail=validation_message)

    team_exists = db.query(Team).filter(
        or_(
            Team.name == team_request.name,
            Team.abbreviation == team_request.abbreviation,
        ),
        Team.campus_code == campus_code
    ).first()

    if team_exists:
        raise Conflict(
            "Nome ou abreviação já existem em outra equipe do campus")

    temp_team_id = str(uuid.uuid4())

    team_can_subscribe, teams_data = await verify_team_exists_with_competitions_service(
        team_id=temp_team_id,
        auth_service_url=f"http://competitionsapi:8007/api/v1/competitions/{team_request.competition_id}/teams/",
        access_token=current_user["access_token"]
    )

    if not team_can_subscribe:
        error_message = teams_data.get(
            'message', 'Erro desconhecido ao verificar competição')
        raise HTTPException(
            status_code=400, detail=f"Não foi possível inscrever a equipe: {error_message}")

    existing_team_uuids = []
    if teams_data.get("data") and teams_data["data"].get("team_uuids"):
        existing_team_uuids = teams_data["data"]["team_uuids"]

    if existing_team_uuids:
        conflicting_members = db.query(TeamMember).filter(
            TeamMember.team_id.in_(existing_team_uuids),
            TeamMember.user_id.in_(team_request.members)
        ).all()

        if conflicting_members:
            conflicting_user_ids = [
                member.user_id for member in conflicting_members]
            raise Conflict(
                f"Os seguintes membros já estão em outras equipes desta competição: {', '.join(conflicting_user_ids)}")

    api_data = teams_data.get('data')
    if not api_data:
        raise HTTPException(
            status_code=500, detail="Erro: 'data' não encontrado na resposta da API.")
    min_members = api_data.get('min_members_per_team')
    if min_members is None:
        raise HTTPException(
            status_code=500, detail="Erro: 'min_members_per_team' não encontrado.")

    if team_request.members and len(team_request.members) < min_members:
        raise HTTPException(
            status_code=400, detail=f"A equipe precisa ter pelo menos {min_members} membros")

    if has_role(groups, "Jogador", "Organizador"):
        new_team = Team(
            id=temp_team_id,
            name=team_request.name,
            abbreviation=team_request.abbreviation,
            campus_code=campus_code,
            members=[TeamMember(user_id=user_id)
                     for user_id in team_request.members]
        )

        try:
            db.add(new_team)
            db.commit()
            db.refresh(new_team)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar equipe no banco de dados"
            )

        team_creation_message_data = {
            "team_id": str(new_team.id),
            "request_type": "approve_team",
            "campus_code": new_team.campus_code,
            "status": "pendent",
            "competition_id": str(team_request.competition_id),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            await publish_team_creation_requested(team_creation_message_data)
        except Exception as e:
            logger.error("Erro ao publicar mensagem...", exc_info=True)

        response.status_code = status.HTTP_202_ACCEPTED
        return {
            "message": "Solicitação de criação de equipe enviada para aprovação!",
            "team_id": new_team.id
        }

    else:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para criar essa equipe."
        )


@router.get("/{team_id}")
async def get_team_by_id(team_id: str,
                         response: Response,
                         db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    """
    Get Team By Id

    Retorna os detalhes de uma equipe específica pelo seu ID.
    O acesso é restrito ao campus do usuário autenticado.

    **Exemplo de Resposta:**

    .. code-block:: json

       {
         "id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
         "name": "Titãs do Futsal",
         "abbreviation": "TTF",
         "status": "approved",
         "campus_code": "NAT-CN",
         "members": [
           {
             "user_id": "20231012030011"
           },
           {
             "user_id": "20231012030015"
           }
         ]
       }
    """
    campus_code = current_user["campus"]
    groups = current_user["groups"]

    team: Team = db.query(Team).filter(
        Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    if has_role(groups, "Jogador", "Organizador"):
        response.status_code = status.HTTP_200_OK
        return team

    else:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para visualizar os dados dessa equipe."
        )


@router.delete("/{team_id}")
async def delete_team_by_id(team_id: str,
                            team_request: TeamDeleteRequest,
                            response: Response,
                            request_object: Request,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_current_user)):
    """
    Delete Team By Id

    Envia uma solicitação para exclusão de uma equipe. A operação não é imediata.

    - Requer um motivo (`reason`) no corpo da requisição.
    - Publica uma mensagem para um processo de aprovação assíncrono.

    **Exemplo de Corpo da Requisição (Payload):**

    .. code-block:: json

       {
         "reason": "A equipe foi desfeita por decisão unânime dos membros."
       }

    **Exemplo de Resposta (202 Accepted):**

    .. code-block:: json

       {
         "message": "Solicitação de remoção de equipe enviada para aprovação!",
         "team_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"
       }
    """
    campus_code = current_user["campus"]
    groups = current_user["groups"]

    team: Team = db.query(Team).filter(
        Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    if has_role(groups, "Jogador", "Organizador"):
        if not team_request:
            raise HTTPException(
                status_code=422,
                detail="O corpo da requisição (reason) é obrigatório para jogadores"
            )

        team_deletion_message_data = {
            "team_id": str(team.id),
            "request_type": "delete_team",
            "reason": team_request.reason,
            "campus_code": team.campus_code,
            "status": "pendent",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        await publish_team_deletion_requested(team_deletion_message_data)

        response.status_code = status.HTTP_202_ACCEPTED
        return {
            "message": "Solicitação de remoção de equipe enviada para aprovação!",
            "team_id": team.id
        }

    else:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para excluir essa equipe."
        )
