import httpx
from typing import Tuple, Dict, Any

async def verify_team_exists_with_competitions_service(
        team_id: str,
        auth_service_url: str,
        access_token: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Chama o serviço de competições para verificar se uma equipe pode ser inscrita
    e retorna as equipes já inscritas na competição.
    """

    payload = {
        "team_id": team_id
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(auth_service_url, json=payload, headers={"Authorization": f"Bearer {access_token}"})
            response.raise_for_status()

            response_data = response.json()
            print(f"Resposta do serviço de competições: {response_data}")

            if response_data.get("can_be_inscribed") is True:
                return True, {
                    "message": response_data.get("message", "Sucesso"),
                    "data": response_data.get("data", {})
                }
            else:
                return False, {
                    "message": response_data.get("message", "Competição não permite inscrições"),
                    "data": response_data.get("data", {})
                }

        except httpx.HTTPStatusError as e:
            error_message = f"Erro do serviço de competição (Status {e.response.status_code})"

            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail") or error_data.get("message")
                if error_detail:
                    error_message += f": {error_detail}"
            except Exception:
                error_message += f": {e.response.text}"

            print(error_message)
            return False, {"message": error_message}

        except httpx.TimeoutException:
            error_message = "Timeout ao contatar serviço de competição"
            print(error_message)
            return False, {"message": error_message}

        except httpx.RequestError as e:
            error_message = f"Erro de rede ao contatar serviço de competição: {str(e)}"
            print(error_message)
            return False, {"message": error_message}

        except Exception as e:
            error_message = f"Erro inesperado ao validar competição: {str(e)}"
            print(error_message)
            return False, {"message": error_message}