from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.tenant import TenantMiddleware
import app.modules.roles.models  # noqa: F401
import app.modules.tenants.models  # noqa: F401
import app.modules.users.models  # noqa: F401
from app.modules.auth.router import router as auth_router
from app.modules.roles.router import router as roles_router
from app.modules.tenants.router import router as tenants_router
from app.modules.users.router import router as users_router

app = FastAPI(title="UOTP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)

api_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(tenants_router, prefix=api_prefix)
app.include_router(roles_router, prefix=api_prefix)
app.include_router(users_router, prefix=api_prefix)


@app.get("/health")
async def health():
    return {"status": "ok"}
