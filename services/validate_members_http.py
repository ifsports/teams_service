import httpx

async def validate_members_with_auth_service(
        member_ids: list[str],
        auth_service_url: str = "http://localhost:8000/api/v1/auth/users/"  # URL do endpoint de validação
) -> tuple[bool, str]:
    """
    Chama o serviço de autenticação para validar uma lista de IDs de membros.
    """

    payload = {"user_ids": member_ids}

    async with httpx.AsyncClient() as client:
        try:
            print(f"Chamando serviço de autenticação em: {auth_service_url} com payload: {payload}")
            response = await client.post(auth_service_url, json=payload)

            response.raise_for_status()

            response_data = response.json()
            print(f"Resposta do serviço de autenticação: {response_data}")

            if response_data.get("all_exist") is True:
                return True, "Todos os membros são válidos."
            else:
                invalid_ids_from_auth = response_data.get("invalid_ids", [])
                message = response_data.get("message", "Alguns membros são inválidos.")
                if invalid_ids_from_auth:
                    message = f"Membros inválidos ou não encontrados: {', '.join(invalid_ids_from_auth)}"
                return False, message

        except httpx.HTTPStatusError as e:
            error_message = f"Erro do serviço de autenticação ao validar membros: {e.response.status_code}."
            try:
                error_detail = e.response.json().get("detail") or e.response.json().get("message")
                if error_detail:
                    error_message += f" Detalhe: {error_detail}"
            except Exception:
                error_message += f" Resposta: {e.response.text}"
            print(error_message)
            return False, error_message

        except httpx.RequestError as e:
            error_message = f"Erro de rede ao contatar serviço de autenticação: {str(e)}"
            print(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"Erro inesperado ao validar membros: {str(e)}"
            print(error_message)
            return False, error_message