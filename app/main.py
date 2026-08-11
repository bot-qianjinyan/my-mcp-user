from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.routers import bills, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="用户与账单管理 API（注册/登录/资料 + 记账/分享/点赞），供 MCP Server 调用。",
    version="1.1.0",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(bills.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
