import uuid

from shared.dependencies import get_db
from teams.models import TeamMember
from teams.models.teams import Team, TeamStatusEnum

from ..messaging.audit_publisher import (run_async_audit, generate_log_payload, model_to_dict)


def update_team_from_request_in_db(message_data: dict) -> dict:
    db_gen = get_db()
    db = next(db_gen)

    try:
        print(f"DB_SYNC: Processando mensagem: {message_data}")

        team_id_str = message_data.get("team_id")
        campus_code_str = message_data.get("campus_code")
        request_type_str = message_data.get("request_type")
        status_str = message_data.get("status")
        user_id_str = message_data.get("user_id")

        if not team_id_str:
            raise ValueError("'team_id' é obrigatório na mensagem")
        if not campus_code_str:
            raise ValueError("'campus_code' é obrigatório na mensagem")
        if not request_type_str:
            raise ValueError("'request_type' é obrigatório na mensagem")
        if not status_str:
            raise ValueError("'status' é obrigatório na mensagem")

        try:
            team_id_for_db = uuid.UUID(team_id_str)
        except ValueError:
            raise ValueError(f"team_id '{team_id_str}' não é um UUID válido")

        if user_id_str is None:
            if request_type_str in ["add_team_member", "remove_team_member"]:
                raise ValueError(f"'user_id' é obrigatório para request_type '{request_type_str}'")

        print(
            f"DB_SYNC: Parsed data: team_id={team_id_for_db}, campus_code={campus_code_str}, request_type={request_type_str}, user_id={user_id_str}, request_status={status_str}")

        team_instance: Team = db.query(Team).filter(
            Team.id == team_id_for_db,
            Team.campus_code == campus_code_str
        ).first()

        if not team_instance:
            raise ValueError(f"Equipe {team_id_for_db} com campus_code {campus_code_str} não encontrada.")


        if request_type_str == "approve_team":
            if team_instance.status != TeamStatusEnum.pendent:
                raise ValueError(
                    f"Equipe {team_instance.id} (status: {team_instance.status}) não está pendente, não pode ser aprovada/rejeitada.")

            if status_str == "approved":
                team_instance.status = TeamStatusEnum.active

                db.add(team_instance)
                db.commit()

                # audit teams.created
                log_payload = generate_log_payload(
                    event_type="teams.created",
                    service_origin="teams_service",
                    entity_type="team",
                    entity_id=team_instance.id,
                    operation_type="CREATE",
                    user_registration="system",
                    campus_code=team_instance.campus_code,
                    new_data=model_to_dict(team_instance)
                )

                run_async_audit(log_payload)

                message = "Equipe aprovada e ativada."

            elif status_str == "rejected":
                team_instance.status = TeamStatusEnum.closed

                db.add(team_instance)
                db.commit()

                message = "Equipe rejeitada e fechada."

            else:
                message = f"Solicitação de aprovação/rejeição com status '{status_str}' não reconhecido. Nenhuma alteração na equipe."

            db.refresh(team_instance)

            return {"team_id": str(team_instance.id), "status": team_instance.status, "message": message}

        elif request_type_str == "delete_team":
            if team_instance.status not in [TeamStatusEnum.pendent, TeamStatusEnum.active]:
                raise ValueError(
                    f"Equipe {team_instance.id} (status: {team_instance.status}) não pode ser fechada por esta operação.")

            if status_str == "approved":
                if team_instance.status == TeamStatusEnum.closed:
                    message = f"Equipe {team_instance.id} já está fechada."

                else:
                    team_instance.status = TeamStatusEnum.closed

                    db.add(team_instance)
                    db.commit()

                    # audit teams.deleted
                    log_payload = generate_log_payload(
                        event_type="teams.deleted",
                        service_origin="teams_service",
                        entity_type="team",
                        entity_id=team_instance.id,
                        operation_type="DELETE",
                        user_registration="system",
                        campus_code=team_instance.campus_code,
                        old_data= model_to_dict(team_instance)
                    )

                    run_async_audit(log_payload)

                    message = f"Equipe {team_instance.id} marcada como fechada."
            elif status_str == "rejected":
                message = f"Solicitação de deleção para equipe {team_instance.id} foi rejeitada. Nenhuma alteração."

            else:
                message = f"Solicitação de deleção com status '{status_str}' não reconhecido. Nenhuma alteração na equipe."

            db.refresh(team_instance)

            return {
                "team_id": str(team_instance.id),
                "status": team_instance.status,
                "message": message
            }

        elif request_type_str == "add_team_member":
            if team_instance.status != TeamStatusEnum.active:
                raise ValueError(
                    f"Não é possível adicionar membro à equipe {team_instance.id} (status: '{team_instance.status}'). Deve estar ativa.")

            existing_member = db.query(TeamMember).filter(
                TeamMember.user_id == user_id_str,
                TeamMember.team_id == team_instance.id
            ).first()

            if existing_member:
                return {
                    "team_id": str(team_instance.id),
                    "user_id": str(user_id_str),
                    "message": "Membro já existe na equipe."
                }

            if status_str == "approved":
                new_member = TeamMember(user_id=user_id_str, team_id=team_instance.id)

                old_data = model_to_dict(team_instance)

                db.add(new_member)
                db.commit()

                # audit team_members.updated
                log_payload = generate_log_payload(
                    event_type="team.members.updated",
                    service_origin="teams_service",
                    entity_type="team_member",
                    entity_id=new_member.id,
                    operation_type="UPDATE",
                    user_registration="system",
                    campus_code=team_instance.campus_code,
                    old_data=old_data,
                    new_data=model_to_dict(team_instance)
                )

                run_async_audit(log_payload)

                message = "Membro adicionado à equipe."

            elif status_str == "rejected":
                message = "Solicitação de adição de membro rejeitada."

            else:
                message = f"Status de solicitação '{status_str}' não reconhecido para adição de membro."

            return {
                "team_id": str(team_instance.id),
                "user_id": user_id_str,
                "message": message,
                "team_status": team_instance.status
            }

        elif request_type_str == "remove_team_member":
            if team_instance.status != TeamStatusEnum.active:
                raise ValueError(
                    f"Não é possível remover membro da equipe {team_instance.id} (status: '{team_instance.status}'). Deve estar ativa.")

            member_to_remove = db.query(TeamMember).filter(
                TeamMember.team_id == team_instance.id,
                TeamMember.user_id == user_id_str
            ).first()

            if not member_to_remove:
                return {
                    "team_id": str(team_instance.id),
                    "user_id": user_id_str,
                    "message": "Membro não encontrado para remoção."
                }

            if status_str == "approved":
                old_data = model_to_dict(team_instance)
                
                db.delete(member_to_remove)
                db.commit()

                # audit team_members.updated

                log_payload = generate_log_payload(
                    event_type="team.members.updated",
                    service_origin="teams_service",
                    entity_type="team_member",
                    entity_id=new_member.id,
                    operation_type="UPDATE",
                    user_registration="system",
                    campus_code=team_instance.campus_code,
                    old_data=old_data,
                    new_data=model_to_dict(team_instance)
                )

                run_async_audit(log_payload)

                message = "Membro removido da equipe."

            elif status_str == "rejected":
                message = "Solicitação de remoção de membro rejeitada."

            else:
                message = f"Status de solicitação '{status_str}' não reconhecido para remoção de membro."

            return {
                "team_id": str(team_instance.id),
                "user_id": user_id_str,
                "message": message,
                "team_status": team_instance.status
            }

        else:
            raise ValueError(f"Tipo de requisição '{request_type_str}' desconhecido.")

    except ValueError as ve:
        db.rollback()
        print(f"DB_SYNC: Erro de dados ou validação: {ve}")
        raise
    except Exception as e:
        db.rollback()
        print(f"DB_SYNC: Erro inesperado no banco: {e}")
        raise
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
        except Exception as e_close:
            print(f"DB_SYNC: Erro ao fechar a sessão do banco: {e_close}")