import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from typing import List

from sqlalchemy.orm import Session

from messaging.publishers import publish_remove_member_requested, publish_add_member_requested
from services.validate_members_http import validate_members_with_auth_service
from shared.dependencies import get_db

from shared.exceptions import NotFound, Conflict
from teams.models.teams import Team

from teams.models.team_member import TeamMember

from teams.models.campus import Campus


from teams.schemas.team_members import TeamMemberResponse, TeamMemberCreateRequest, TeamMemberDeleteRequest

router = APIRouter(
    prefix="/api/v1/campus/{campus_code}/teams/{team_id}/members",
    tags=["Team Members"]
)


@router.get("/", response_model=List[TeamMemberResponse], status_code=200)
async def get_team_members_by_team_id(campus_code: str,
                                      team_id: str,
                                      db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    team: Team = db.query(Team).filter(Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    members = team.members

    return members


@router.post("/", status_code=202)
async def add_team_member_to_team(campus_code: str,
                                  team_id: uuid.UUID,
                                  team_member_request: TeamMemberCreateRequest,
                                  db: Session = Depends(get_db)):
    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    team: Team = db.query(Team).filter(Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

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

    auth_service_url = "http://authservice:8000/api/v1/auth/users/"
    is_valid, validation_message = await validate_members_with_auth_service(
        member_ids=[user_id_to_validate],
        auth_service_url=auth_service_url
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)

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


@router.delete("/{team_member_id}", status_code=202)
async def remove_team_member_from_team(campus_code: str,
                                       team_id: uuid.UUID,
                                       team_member_request: TeamMemberDeleteRequest,
                                       db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    team: Team = db.query(Team).filter(Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    member: TeamMember = db.query(TeamMember).filter(TeamMember.user_id == team_member_request.user_id,
                                                     TeamMember.team_id == team_id).first()
    if not member:
        raise NotFound("Membro")

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