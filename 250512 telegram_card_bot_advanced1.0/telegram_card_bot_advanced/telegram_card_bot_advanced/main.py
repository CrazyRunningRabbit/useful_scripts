import asyncio
import uvicorn
import webbrowser

from app.server import build_app
from app.config import settings
from app.bot import run_bot

async def main():
    app = build_app()
    config = uvicorn.Config(
        app=app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)

    # 启动
    bot_task = asyncio.create_task(run_bot())

    # 后台交互
    api_task = asyncio.create_task(server.serve())

    # open browser
    await asyncio.sleep(1)
    url = f"http://127.0.0.1:{settings.PORT}"
    webbrowser.open(url)

    # 等两个任务一起运行
    await asyncio.gather(bot_task, api_task)

if __name__ == "__main__":
    asyncio.run(main())
