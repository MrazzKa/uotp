from fastapi import APIRouter

# Intentional placeholder: tenant administration is a planned module. Tenants are
# currently provisioned via seed/migrations and resolved from the JWT tenant_id.
router = APIRouter(prefix="/tenants", tags=["tenants"])
