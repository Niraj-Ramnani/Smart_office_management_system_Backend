import logging
from typing import Any

import jwt
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer

from app.core.config import settings
from app.core.constants import DEFAULT_TOKEN_LEEWAY_SECONDS

logger = logging.getLogger("uvicorn.error")


class EntraIDAuthScheme(SingleTenantAzureAuthorizationCodeBearer):
    def __init__(
        self,
        app_client_id: str,
        tenant_id: str,
        api_audience: str | None = None,
        scopes: dict[str, str] | None = None,
        allow_guest_users: bool = True,
        leeway: int = DEFAULT_TOKEN_LEEWAY_SECONDS,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            app_client_id=app_client_id,
            tenant_id=tenant_id,
            scopes=scopes,
            allow_guest_users=allow_guest_users,
            leeway=leeway,
            **kwargs,
        )
        self.api_audience = api_audience or app_client_id

    def validate(
        self,
        access_token: str,
        key: Any,
        iss: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        tenant_id = self.openid_config.tenant_id or settings.AZURE_TENANT_ID

        audiences = list(
            {
                self.app_client_id,
                f"api://{self.app_client_id}",
            }
        )

        issuers = list(
            {
                iss,
                f"https://login.microsoftonline.com/{tenant_id}/v2.0",
                f"https://sts.windows.net/{tenant_id}/",
            }
        )

        custom_options = dict(options)
        if "require" in custom_options:
            custom_options["require"] = [c for c in custom_options["require"] if c != "nbf"]

        try:
            return dict(
                jwt.decode(
                    access_token,
                    key=key,
                    algorithms=["RS256"],
                    audience=audiences,
                    issuer=issuers,
                    leeway=max(self.leeway, DEFAULT_TOKEN_LEEWAY_SECONDS),
                    options=custom_options,
                )
            )
        except Exception as exc:
            logger.warning("Entra ID token validation failed: %s", exc)
            raise


azure_scheme = EntraIDAuthScheme(
    app_client_id=settings.AZURE_CLIENT_ID,
    tenant_id=settings.AZURE_TENANT_ID,
    api_audience=settings.AZURE_API_AUDIENCE,
    allow_guest_users=True,
    leeway=DEFAULT_TOKEN_LEEWAY_SECONDS,
    scopes={
        settings.AZURE_API_SCOPE: "access_as_user",
    },
)


async def load_azure_openid_config() -> None:
    try:
        await azure_scheme.openid_config.load_config()
        logger.info("Microsoft Entra ID OpenID configuration loaded successfully.")
    except Exception as exc:
        logger.warning(
            "Could not pre-fetch Entra ID OpenID configuration on startup: %s",
            exc,
        )
