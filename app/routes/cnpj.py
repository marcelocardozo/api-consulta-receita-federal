import asyncio
import re
import time

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from app.config import settings
from app.models.schemas import CNPJResponse, ErrorResponse, HealthResponse
from app.services.consulta import consultar_cnpj, formatar_cnpj

router = APIRouter()

# IP locks com rastreamento de TTL para evitar memory leak
_ip_locks: dict[str, asyncio.Lock] = {}
_ip_last_used: dict[str, float] = {}


def _get_lock(ip: str) -> asyncio.Lock:
    """Obtém ou cria um lock para o IP, limpando entradas expiradas."""
    now = time.time()

    # Limpa locks expirados
    stale = [
        k for k, t in _ip_last_used.items()
        if now - t > settings.ip_lock_ttl_seconds
    ]
    for k in stale:
        _ip_locks.pop(k, None)
        _ip_last_used.pop(k, None)

    if ip not in _ip_locks:
        _ip_locks[ip] = asyncio.Lock()
    _ip_last_used[ip] = now
    return _ip_locks[ip]


@router.get(
    "/cnpj/{cnpj}",
    response_model=CNPJResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def consultar(cnpj: str, request: Request) -> CNPJResponse:
    numeros = re.sub(r"\D", "", cnpj)

    if len(numeros) != 14:
        raise HTTPException(status_code=400, detail="CNPJ deve ter 14 dígitos")

    try:
        formatar_cnpj(numeros)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    client_ip = request.client.host
    lock = _get_lock(client_ip)

    if lock.locked():
        raise HTTPException(status_code=429, detail="Aguarde a consulta anterior finalizar")

    start = time.time()

    async with lock:
        try:
            from app.main import browser_manager
            resultado = await consultar_cnpj(numeros, browser_manager)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Falha na consulta CNPJ {numeros}: {e}")
            raise HTTPException(status_code=502, detail=f"Falha na consulta: {e}")

    if not resultado.get("sucesso"):
        raise HTTPException(status_code=422, detail=resultado.get("erro", "Erro"))

    resultado["tempo_segundos"] = round(time.time() - start, 1)
    return CNPJResponse(**resultado)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    from app.main import browser_manager
    return HealthResponse(
        status="ok",
        gemini_keys=len(browser_manager._keys),
        ips_ativos=sum(1 for lock in _ip_locks.values() if lock.locked()),
    )
