from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db import AsyncSessionLocal
from app.modules.sla.service import mark_overdue_issues

scheduler = AsyncIOScheduler(timezone="UTC")


async def mark_overdue_job() -> None:
    async with AsyncSessionLocal() as session:
        await mark_overdue_issues(session)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(mark_overdue_job, "interval", minutes=5, id="sla-overdue", replace_existing=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
