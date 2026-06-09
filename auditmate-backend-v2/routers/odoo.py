"""Эндпоинты для данных из Odoo (проекты, задачи)."""

from fastapi import APIRouter, Depends, Query
from schemas import OdooProject, OdooTask, CurrentUser
from services import odoo as odoo_svc
from services.auth import get_current_user

router = APIRouter(prefix="/odoo", tags=["odoo"])


@router.get("/projects", response_model=list[OdooProject])
async def list_projects(
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Список проектов из Odoo (project.project).
    Требует авторизации.
    """
    return await odoo_svc.get_projects(limit=limit)


@router.get("/projects/{project_id}/tasks", response_model=list[OdooTask])
async def list_tasks(
    project_id: int,
    limit: int = Query(100, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Задачи конкретного проекта (project.task).
    Требует авторизации.
    """
    return await odoo_svc.get_tasks(project_id=project_id, limit=limit)
