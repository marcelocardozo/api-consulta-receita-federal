import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from loguru import logger

from app.config import settings
from app.routes.cnpj import router as cnpj_router
from app.services.browser import BrowserManager

# Configura loguru
logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}",
)

browser_manager = BrowserManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await browser_manager.start()
    yield
    await browser_manager.stop()


def create_app() -> FastAPI:
    application = FastAPI(
        title="API Consulta CNPJ",
        description="Consulta CNPJ na Receita Federal com hCaptcha resolvido via Gemini AI",
        version="3.1.0",
        lifespan=lifespan,
    )
    application.include_router(cnpj_router)
    return application


app = create_app()
