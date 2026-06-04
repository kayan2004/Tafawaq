"""Vault secrets resolution.

Called once in the FastAPI lifespan. Raises VaultUnavailable if Vault is
unreachable or the token is invalid — the app refuses to boot (Constitution Principle II).
"""
import os

import hvac
from pydantic import BaseModel

from app.domain.exceptions import VaultUnavailable

_VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://vault:8200")
_VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
_SECRET_PATH = "lebanese-math-coach"


class AppSecrets(BaseModel):
    anthropic_api_key: str
    voyage_api_key: str
    db_url: str
    db_password: str
    minio_access_key: str
    minio_secret_key: str
    jwt_secret: str


def resolve_secrets() -> AppSecrets:
    """Resolve all application secrets from Vault KV v2.

    Raises:
        VaultUnavailable: If Vault is unreachable or the token is not authenticated.
    """
    client = hvac.Client(url=_VAULT_ADDR, token=_VAULT_TOKEN)

    if not client.is_authenticated():
        raise VaultUnavailable(
            f"Vault at {_VAULT_ADDR} is unreachable or token is invalid. "
            "Application cannot start without secrets."
        )

    try:
        response = client.secrets.kv.v2.read_secret_version(
            path=_SECRET_PATH,
            mount_point="secret",
        )
        data: dict = response["data"]["data"]
    except Exception as exc:
        raise VaultUnavailable(
            f"Failed to read secret '{_SECRET_PATH}' from Vault: {exc}"
        ) from exc

    return AppSecrets(**data)
