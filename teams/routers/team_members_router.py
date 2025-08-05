import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status, Request

from sqlalchemy.orm import Session

from auth import get_current_user
from messaging.publishers import publish_remove_member_requested, publish_add_member_requested
from services.validate_members_http import validate_members_with_auth_service
from shared.auth_utils import has_role
from shared.dependencies import get_db

from shared.exceptions import NotFound, Conflict
from teams.models.teams import Team

from teams.models.team_member import TeamMember


from teams.schemas.team_members import TeamMemberCreateRequest, TeamMemberDeleteRequest

from messaging.audit_publisher import run_async_audit, generate_log_payload, model_to_dict

# Manteremos os 'responses' porque são úteis para as ferramentas interativas
# como /docs e /redoc, mesmo que o Sphinx não os use para gerar os blocos de JSON.
responses_get_members = {
    200: {"description": "Membros da equipe retornados com sucesso."},
    403: {"description": "O usuário não tem permissão para visualizar os membros."},
    404: {"description": "A equipe com o ID fornecido não foi encontrada."}
}
responses_add_member = {
    202: {"description": "Solicitação para adicionar membro foi recebida e enviada para aprovação."},
    400: {"description": "O usuário a ser adicionado não é válido ou não foi encontrado no serviço de autenticação."},
    403: {"description": "O usuário solicitante não tem permissão para adicionar membros."},
    404: {"description": "A equipe com o ID fornecido não foi encontrada."},
    409: {"description": "O usuário já é um membro da equipe."}
}
responses_remove_member = {
    200: {"description": "Solicitação para remover membro foi recebida e enviada para aprovação."},
    400: {"description": "O motivo da remoção é obrigatório e não foi fornecido."},
    403: {"description": "O usuário solicitante não tem permissão para remover membros."},
    404: {"description": "A equipe ou o membro não foram encontrados."}
}

router = APIRouter(
    prefix="/api/v1/teams/{team_id}/members",
    tags=["Team Members"]
)


@router.get("/", responses=responses_get_members)
async def get_team_members_by_team_id(team_id: str,
                                      response: Response,
                                      db: Session = Depends(get_db),
                                      current_user: dict = Depends(get_current_user)):
    """
    Get Team Members By Team Id

    Obtém todos os membros de uma equipe específica.

    - **Autenticação**: Requer um token de usuário válido.
    - **Autorização**: O usuário autenticado deve pertencer ao grupo 'Jogador' ou 'Organizador'.
    - A busca da equipe é limitada ao campus do usuário autenticado.

    **Exemplo de Resposta:**

    .. code-block:: json

       [
         {
           "user_id": "20231012030011",
           "team_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
           "created_at": "2025-08-04T21:14:25.123Z",
           "updated_at": "2025-08-04T21:14:25.123Z"
         },
         {
           "user_id": "20231012030015",
           "team_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
           "created_at": "2025-08-04T21:15:00.456Z",
           "updated_at": "2025-08-04T21:15:00.456Z"
         }
       ]

    """
    campus_code = current_user["campus"]
    groups = current_user["groups"]

    team: Team = db.query(Team).filter(
        Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    if has_role(groups, "Jogador", "Organizador"):
        members = team.members

        response.status_code = status.HTTP_200_OK
        return members

    else:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para visualizar os membros."
        )


@router.post("/", responses=responses_add_member, status_code=status.HTTP_202_ACCEPTED)
async def add_team_member_to_team(team_id: uuid.UUID,
                                  team_member_request: TeamMemberCreateRequest,
                                  response: Response,
                                  request_object: Request,
                                  db: Session = Depends(get_db),
                                  current_user: dict = Depends(get_current_user)):
    """
    Add Team Member To Team

    Envia uma solicitação para adicionar um novo membro a uma equipe.

    - **Autenticação**: Requer um token de usuário válido.
    - **Autorização**: O usuário solicitante deve ser membro da equipe e pertencer aos grupos 'Jogador' ou 'Organizador'.
    - **Validação**: O `user_id` do novo membro é validado contra o serviço de autenticação.

    **Exemplo de Corpo da Requisição (Payload):**

    .. code-block:: json

       {
         "user_id": "20231012030020"
       }

    **Exemplo de Resposta (202 Accepted):**

    .. code-block:: json

       {
         "message": "Solicitação de adição de membro enviada para aprovação!",
         "team_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
         "member_id": "20231012030020"
       }
    """
    user_id = current_user["user_matricula"]
    campus_code = current_user["campus"]
    groups = current_user["groups"]

    team: Team = db.query(Team).filter(
        Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    existing_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == team_member_request.user_id
    ).first()

    if existing_member:
        raise Conflict("Membro já está na equipe.")

    member = TeamMember(user_id=team_member_request.user_id, team_id=team_id)

    user_id_to_validate = team_member_request.user_id

    auth_service_url = "http://authapi:8000/api/v1/auth/users/"
    is_valid, validation_message = await validate_members_with_auth_service(
        member_ids=[user_id_to_validate],
        auth_service_url=auth_service_url
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)

    if has_role(groups, "Jogador", "Organizador"):
        existing_member_requester = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()

        if existing_member_requester:
            add_member_message_data = {
                "team_id": str(team.id),
                "user_id": str(member.user_id),
                "request_type": "add_team_member",
                "campus_code": team.campus_code,
                "status": "pendent",
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            await publish_add_member_requested(add_member_message_data)

            return {
                "message": "Solicitação de adição de membro enviada para aprovação!",
                "team_id": team.id,
                "member_id": member.user_id
            }

        else:
            raise HTTPException(
                status_code=403,
                detail="Você não está nessa equipe pra adicionar um usuário."
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para adicionar esse membro."
        )


@router.delete("/{team_member_id}", responses=responses_remove_member)
async def remove_team_member_from_team(team_id: uuid.UUID,
                                       team_member_request: TeamMemberDeleteRequest,
                                       team_member_id: str,
                                       response: Response,
                                       request_object: Request,
                                       db: Session = Depends(get_db),
                                       current_user: dict = Depends(get_current_user)):
    """
    Remove Team Member From Team

    Envia uma solicitação para remover um membro de uma equipe.

    - **Autenticação**: Requer um token de usuário válido.
    - **Autorização**: O usuário solicitante deve ser membro da equipe e pertencer aos grupos 'Jogador' ou 'Organizador'.
    - **Corpo da Requisição**: É obrigatório fornecer um `reason` (motivo) para a remoção.

    **Exemplo de Corpo da Requisição (Payload):**

    .. code-block:: json

       {
         "reason": "O membro solicitou a sua saída da equipe."
       }

    **Exemplo de Resposta:**

    .. code-block:: json

       {
         "message": "Solicitação de remoção de membro enviada para aprovação!",
         "team_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
         "member_id": "20231012030015"
       }
    """
    user_id = current_user["user_matricula"]
    campus_code = current_user["campus"]
    groups = current_user["groups"]

    team: Team = db.query(Team).filter(
        Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    member: TeamMember = db.query(TeamMember).filter(TeamMember.user_id == team_member_id,
                                                     TeamMember.team_id == team_id).first()

    if not member:
        raise NotFound("Membro")

    if has_role(groups, "Jogador", "Organizador"):
        existing_member_requester = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()

        if existing_member_requester:
            if not team_member_request.reason or not team_member_request.reason.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Motivo da remoção é obrigatório."
                )

            member_deletion_message_data = {
                "team_id": str(team.id),
                "user_id": str(member.user_id),
                "request_type": "remove_team_member",
                "reason": team_member_request.reason,
                "campus_code": team.campus_code,
                "status": "pendent",
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            await publish_remove_member_requested(member_deletion_message_data)

            return {
                "message": "Solicitação de remoção de membro enviada para aprovação!",
                "team_id": team.id,
                "member_id": member.user_id
            }

        else:
            raise HTTPException(
                status_code=403,
                detail="Você não está nessa equipe pra remover um usuário."
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para remover esse membro."
        )
