from fastapi import APIRouter

# Intentional placeholder: role management (CRUD, permission editing) is a planned
# module (see ТЗ Admin endpoints). Roles are currently seeded and resolved by code.
router = APIRouter(prefix="/roles", tags=["roles"])
