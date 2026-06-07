from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.security import decode_token


class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = None
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            try:
                payload = decode_token(authorization.split(" ", 1)[1])
                request.state.tenant_id = payload.get("tenant_id")
            except Exception:
                request.state.tenant_id = None
        return await call_next(request)
