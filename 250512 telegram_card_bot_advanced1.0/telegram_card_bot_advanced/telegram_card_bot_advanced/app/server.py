# app/server.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .admin import router as admin_router

def build_app():
    app = FastAPI()

    # 绝对路径挂载 /static
    APP_DIR = Path(__file__).resolve().parent
    STATIC_DIR = APP_DIR / "static"
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # 关键：把 admin 路由挂到根路径（没有 prefix）
    app.include_router(admin_router, prefix="")

    return app

# 让 uvicorn 能直接引用
app = build_app()
