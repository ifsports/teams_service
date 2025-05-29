import uuid

from fastapi import APIRouter, Depends

from typing import List

from sqlalchemy.orm import Session

from shared.dependencies import get_db

from shared.exceptions import NotFound, Conflict
from teams.models.teams import Team

from teams.models.team_member import TeamMember

from teams.models.campus import Campus


from teams.schemas.team_members import TeamMemberResponse, TeamMemberRequest

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
                                  team_member_request: TeamMemberRequest,
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


@router.delete("/{team_member_id}", status_code=204)
async def remove_team_member_from_team(campus_code: str,
                                       team_id: uuid.UUID,
                                       team_member_request: TeamMemberRequest,
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

    db.delete(member)
    db.commit()

    return