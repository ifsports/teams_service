from fastapi import APIRouter, Depends

from typing import List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from shared.dependencies import get_db
from shared.exceptions import NotFound, Conflict
from teams.models import TeamMember
from teams.models.campus import Campus
from teams.models.teams import Team
from teams.schemas.teams import TeamResponse, TeamCreateRequest, TeamUpdateRequest

router = APIRouter(
    prefix="/api/v1/campus/{campus_code}/teams",
    tags=["Teams"]
)


@router.get("/", response_model=List[TeamResponse])
async def get_teams_by_campus(campus_code: str,
                              db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    teams = db.query(Team).filter(Team.campus_code == campus_code).all() # type: ignore

    return teams


@router.post("/", response_model=TeamResponse, status_code=201)
async def create_team_in_campus(campus_code: str,
                                team_request: TeamCreateRequest,
                                db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    team_exists = db.query(Team).filter(
        or_(
            Team.name == team_request.name,
            Team.abbreviation == team_request.abbreviation,
        ),
        Team.campus_code == campus_code
    ).first()

    if team_exists:
        raise Conflict("Nome ou abreviação já existem em outra equipe do campus")

    new_team = Team(
        name=team_request.name,
        abbreviation=team_request.abbreviation,
        campus_code=campus_code,
        members=[TeamMember(user_id=user_id) for user_id in team_request.members]
    )

    new_team.campus_code = campus_code

    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    return new_team


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


@router.delete("/{team_id}", status_code=204)
async def delete_team_by_id(campus_code: str,
                            team_id: str,
                            db: Session = Depends(get_db)):

    campus: Campus = db.query(Campus).filter(Campus.code == campus_code).first()  # type: ignore

    if not campus:
        raise NotFound("Campus")

    team: Team = db.query(Team).filter(Team.id == team_id, Team.campus_code == campus_code).first()  # type: ignore

    if not team:
        raise NotFound("Equipe")

    db.delete(team)
    db.commit()

    return