import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from typing import List

from sqlalchemy.orm import Session

from messaging.publishers import publish_remove_member_requested
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


@router.post("/", response_model=TeamMemberResponse, status_code=201)
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

    db.add(member)
    db.commit()
    db.refresh(member)

    return member


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
        "member_id": member.id
    }