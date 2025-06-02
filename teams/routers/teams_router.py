from fastapi import APIRouter, Depends, Query, HTTPException

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

import uuid

from datetime import datetime, timezone

from messaging.publishers import publish_team_creation_requested, publish_team_deletion_requested
from services.validate_members_http import validate_members_with_auth_service
from services.verify_team_exists import verify_team_exists_with_competitions_service

from shared.dependencies import get_db
from shared.exceptions import NotFound, Conflict
from teams.models import TeamMember
from teams.models.campus import Campus
from teams.models.teams import Team, TeamStatusEnum
from teams.schemas.teams import TeamResponse, TeamCreateRequest, TeamUpdateRequest, TeamCreationAcceptedResponse, \
    TeamDeleteRequest

router = APIRouter(
    prefix="/api/v1/campus/{campus_code}/teams",
    tags=["Teams"]
)


@router.get("/", response_model=List[TeamResponse])
async def get_teams_by_campus(campus_code: str,
                              status: Optional[TeamStatusEnum] = Query(None, description="Filtrar equipes por status"),
                              db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    query = db.query(Team).filter(Team.campus_code == campus_code)

    if status:
        query = query.filter(Team.status == status.value)

    return query.all()


@router.post("/", response_model=TeamCreationAcceptedResponse, status_code=202)
async def create_team_in_campus(campus_code: str,
                                team_request: TeamCreateRequest,
                                db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()
    if not campus:
        raise NotFound("Campus")

    if not team_request.members:
        raise HTTPException(status_code=400, detail="A equipe deve ter pelo menos um membro")

    if not team_request.competition_id:
        raise HTTPException(status_code=400, detail="ID da competição é obrigatório")

    auth_service_url = "http://authservice:8000/api/v1/auth/users/"
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
        raise Conflict("Nome ou abreviação já existem em outra equipe do campus")

    temp_team_id = str(uuid.uuid4())

    team_can_subscribe, teams_data = await verify_team_exists_with_competitions_service(
        team_id=temp_team_id,
        auth_service_url=f"http://competitionsservice:8007/api/v1/competitions/{team_request.competition_id}/teams/"
    )

    if not team_can_subscribe:
        error_message = teams_data.get('message', 'Erro desconhecido ao verificar competição')
        raise HTTPException(status_code=400, detail=f"Não foi possível inscrever a equipe: {error_message}")

    existing_team_uuids = []
    if teams_data.get("data") and teams_data["data"].get("team_uuids"):
        existing_team_uuids = teams_data["data"]["team_uuids"]

    if existing_team_uuids:
        conflicting_members = db.query(TeamMember).filter(
            TeamMember.team_id.in_(existing_team_uuids),
            TeamMember.user_id.in_(team_request.members)
        ).all()

        if conflicting_members:
            conflicting_user_ids = [member.user_id for member in conflicting_members]
            raise Conflict(f"Os seguintes membros já estão em outras equipes desta competição: {', '.join(conflicting_user_ids)}")

    api_data = teams_data.get('data')
    if not api_data:
        raise HTTPException(status_code=500, detail="Erro: 'data' não encontrado na resposta da API.")
    min_members = api_data.get('min_members_per_team')
    if min_members is None:
        raise HTTPException(status_code=500, detail="Erro: 'min_members_per_team' não encontrado.")

    if team_request.members and len(team_request.members) < min_members:
        raise HTTPException(status_code=400, detail=f"A equipe precisa ter pelo menos {min_members} membros")

    new_team = Team(
        id=temp_team_id,
        name=team_request.name,
        abbreviation=team_request.abbreviation,
        campus_code=campus_code,
        members=[TeamMember(user_id=user_id) for user_id in team_request.members]
    )

    try:
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar equipe no banco de dados: {str(e)}")

    team_creation_message_data = {
        "team_id": str(new_team.id),
        "request_type": "approve_team",
        "campus_code": new_team.campus_code,
        "status": "pendent",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        await publish_team_creation_requested(team_creation_message_data)
    except Exception as e:
        # Log o erro mas não falhe a requisição já que a equipe foi criada
        print(f"Erro ao publicar mensagem de criação da equipe: {str(e)}")

    return {
        "message": "Solicitação de criação de equipe enviada para aprovação!",
        "team_id": new_team.id
    }


@router.get("/{team_id}", response_model=TeamResponse, status_code=200)
async def get_team_by_id(campus_code: str,
                         team_id: str,
                         db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    team: Team = db.query(Team).filter(Team.id == team_id, Team.campus_code == campus_code).first() # type: ignore

    if not team:
        raise NotFound("Equipe")

    return team


@router.put("/{team_id}", status_code=204)
async def update_team_by_id(campus_code: str,
                            team_id: str,
                            team_request: TeamUpdateRequest,
                            db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    team: Team = db.query(Team).filter(Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    if team_request.name:
        team.name = team_request.name

    if team_request.abbreviation:
        team.abbreviation = team_request.abbreviation

    db.commit()

    return


@router.delete("/{team_id}", status_code=202)
async def delete_team_by_id(campus_code: str,
                            team_id: str,
                            team_request: TeamDeleteRequest,
                            db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    team: Team = db.query(Team).filter(Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    team_deletion_message_data = {
        "team_id": str(team.id),
        "request_type": "delete_team",
        "reason": team_request.reason,
        "campus_code": team.campus_code,
        "status": "pendent",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await publish_team_deletion_requested(team_deletion_message_data)

    return {
        "message": "Solicitação de remoção de equipe enviada para aprovação!",
        "team_id": team.id
    }