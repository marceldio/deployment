from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import select
from api.config.utils import load_live_search
from api.auth.auth_config import RoleChecker, PermissionRoleChecker
from api.auth.models import User
from api.config.models import ListLrSearchSystem, LiveSearchList, YandexLr
from api.config.utils import load_live_search
from db.session import get_db_general, async_session_general
from services.load_all_queries import load_queries, get_all_data as get_all_data_queries

from services.load_all_urls import load_urls, get_all_data as get_all_data_urls

from services.load_all_history import load_history, main as all_history_main

from services.load_query_url_merge import main as merge_main

from services.load_live_search import main as live_search_main

from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_config import current_user
from api.config.models import Config

router = APIRouter()

@router.get('/load-queries-script')
async def load_queries_script(
        request: Request,
        #required: bool = Depends(RoleChecker(required_permissions={"Administrator", "Superuser"})),
        required_permission: bool = Depends(PermissionRoleChecker({"access_queries_full", "access_queries_update"}))
):
    request_session = request.session
    res = await get_all_data_queries(request_session)
    if res["status"] == 400:
        raise HTTPException(status_code=400, detail="Нет новых обновлений")
    return res

@router.get('/load-queries-by-config/{config_id}')
async def load_queries_by_config(
        request: Request,
        config_id: int,
        required_permission: bool = Depends(PermissionRoleChecker({"access_queries_full", "access_queries_update"}))):
    group = request.session["group"]
    async with async_session_general() as session:
        config = (await session.execute(select(Config).where(Config.id == config_id))).scalars().first()
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    config = config.__dict__
    print(config)
    res = await load_queries(config, group)
    if res["status"] == 400:
        raise HTTPException(status_code=400, detail="Нет новых обновлений")
    return res


@router.get('/load-urls/{config_id}')
async def load_urls_by_config(
        request: Request,
        config_id: int,
        #required: bool = Depends(RoleChecker(required_permissions={"Administrator", "Superuser"}))
):
    group = request.session["group"]
    async with async_session_general() as session:
        config = (await session.execute(select(Config).where(Config.id == config_id))).scalars().first()
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    config = config.__dict__

    res = await load_urls(config, group)
    if res["status"] == 400:
        raise HTTPException(status_code=400, detail="Нет новых обновлений")
    return res


@router.get('/load-urls-script')
async def load_urls_script(
        request: Request,
        #required: bool = Depends(RoleChecker(required_permissions={"Administrator", "Superuser"}))
):
    request_session = request.session
    res = await get_all_data_urls(request_session)
    if res["status"] == 400:
        raise HTTPException(status_code=400, detail="Нет новых обновлений")
    return res


@router.get("/load-history/{config_id}")
async def load_history_by_config(
        request: Request,
        config_id: int,
        #required: bool = Depends(RoleChecker(required_permissions={"Administrator", "Superuser"}))
):
    group = request.session["group"]
    async with async_session_general() as session:
        config = (await session.execute(select(Config).where(Config.id == config_id))).scalars().first()
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    config = config.__dict__
    try:
        await load_history(config, group)
    except Exception as e:
        print(e)
    return {"status": 200}


@router.get('/load-history-script')
async def load_history_script(
        request: Request,
        #required: bool = Depends(RoleChecker(required_permissions={"Administrator", "Superuser"}))
) -> dict:
    try:
        request_session = request.session
        await all_history_main(request_session)
    except Exception as e:
        print(e)
    return {"status": 200}


@router.get('/load-merge-script')
async def load_merge_script(
        request: Request,
        #required: bool = Depends(RoleChecker(required_permissions={"Administrator", "Superuser"}))
) -> dict:
    try:
        request_session = request.session
        await merge_main(request_session)
    except Exception as e:
        print(e)
    return {"status": 200}


@router.post('/load-live-search')
async def load_live_search_list(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db_general),
    user: User = Depends(current_user),
    #required: bool = Depends(RoleChecker(required_permissions={"Administrator", "Superuser", "Search"}))
):
    list_lr_id = int(data["list_lr_id"])
    print(list_lr_id)
    status = await load_live_search(user, list_lr_id, session)
    if status == 0:
        raise HTTPException(status_code=400, detail="Запросов доступно меньше, чем необходимо")

    return {
        "status": 200,
    }


@router.post("/update_all_regions_by_list_id/{list_id}")
async def update_all_regions_by_list_id(
        list_id: int,
        session: AsyncSession = Depends(get_db_general),
        user: User = Depends(current_user)):
    regions = await session.execute(
        select(ListLrSearchSystem)
        .where(ListLrSearchSystem.list_id == list_id)
    )
    regions = regions.scalars().all()
    for region in regions:
        status = await load_live_search(user, region.id, session)
        if status == 0:
            raise HTTPException(status_code=400, detail="Запросов доступно меньше, чем необходимо")

    return {
        "status": 200,
    }
