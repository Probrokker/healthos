"""
Точка входа: запускает и Telegram-бот, и FastAPI одновременно.
"""
import asyncio
import logging
import os
import sys
import threading

import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_api():
    from api import app
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="warning"
    )


def run_bot():
    from bot_v2 import main as bot_main
    bot_main()


if __name__ == "__main__":
    from models.database import create_tables
    create_tables()

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "models"))
        from models.profiles_seed import seed_profiles
        seed_profiles()
    except Exception as e:
        logger.warning(f"Seed: {e}")

    mode = os.getenv("RUN_MODE", "both")

    if mode == "api":
        run_api()
    elif mode == "bot":
        run_bot()
    else:
        # Запускаем оба в отдельных потоках
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        logger.info("API запущен на порту 8000")

        run_bot()
