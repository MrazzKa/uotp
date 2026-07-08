from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.scheduler import start_scheduler, stop_scheduler
import app.modules.audit.models  # noqa: F401
import app.modules.catalog.models  # noqa: F401
import app.modules.issues.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
import app.modules.roles.models  # noqa: F401
import app.modules.sla.models  # noqa: F401
import app.modules.tenants.models  # noqa: F401
import app.modules.users.models  # noqa: F401
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import router as catalog_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.issues.router import router as issues_router
from app.modules.map.router import router as map_router
from app.modules.notifications.router import router as notifications_router
from app.modules.roles.router import router as roles_router
from app.modules.sla.router import router as sla_router
from app.modules.tenants.router import router as tenants_router
from app.modules.users.router import router as users_router
from app.modules.voice.router import router as voice_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="UOTP API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(audit_router, prefix=api_prefix)
app.include_router(auth_router, prefix=api_prefix)
app.include_router(catalog_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(issues_router, prefix=api_prefix)
app.include_router(map_router, prefix=api_prefix)
app.include_router(notifications_router, prefix=api_prefix)
app.include_router(sla_router, prefix=api_prefix)
app.include_router(tenants_router, prefix=api_prefix)
app.include_router(roles_router, prefix=api_prefix)
app.include_router(users_router, prefix=api_prefix)
app.include_router(voice_router, prefix=api_prefix)


@app.get("/health")
async def health():
    return {"status": "ok"}
