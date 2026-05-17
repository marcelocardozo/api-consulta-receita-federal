import asyncio
import itertools
import os

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth
from hcaptcha_challenger import AgentV, AgentConfig
from hcaptcha_challenger.models import ChallengeSignal
from loguru import logger

from app.config import settings

SITE_URL = "https://solucoes.receita.fazenda.gov.br/Servicos/cnpjreva/cnpjreva_Solicitacao.asp"
BASE_URL = "https://solucoes.receita.fazenda.gov.br/Servicos/cnpjreva"


class BrowserManager:

    def __init__(self) -> None:
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._keys: list[str] = []
        self._key_cycle: itertools.cycle | None = None

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=settings.browser_headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        stealth = Stealth()
        self._context = await self._browser.new_context(locale="pt-BR")
        await stealth.apply_stealth_async(self._context)

        self._keys = settings.gemini_keys_list
        self._key_cycle = itertools.cycle(self._keys)
        logger.info(f"Carregadas {len(self._keys)} chave(s) Gemini")

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    def _next_key(self) -> str:
        return next(self._key_cycle)

    def _make_config(self, api_key: str) -> AgentConfig:
        # hcaptcha-challenger lê a chave do env — workaround necessário
        os.environ["GEMINI_API_KEY"] = api_key
        return AgentConfig(
            CHALLENGE_CLASSIFIER_MODEL="gemini-2.5-flash",
            IMAGE_CLASSIFIER_MODEL="gemini-2.5-flash",
            SPATIAL_POINT_REASONER_MODEL="gemini-2.5-flash",
            SPATIAL_PATH_REASONER_MODEL="gemini-2.5-flash",
            EXECUTION_TIMEOUT=settings.captcha_execution_timeout,
            RESPONSE_TIMEOUT=settings.captcha_response_timeout,
            WAIT_FOR_CHALLENGE_VIEW_TO_RENDER_MS=800,
        )

    async def solve_and_query(self, cnpj_formatado: str) -> dict[str, str]:
        cnpj_numeros = cnpj_formatado.replace(".", "").replace("/", "").replace("-", "")

        last_error: Exception | None = None
        for attempt in range(len(self._keys)):
            key = self._next_key()
            logger.info(f"Usando chave ...{key[-8:]} (tentativa {attempt + 1}/{len(self._keys)})")

            page = await self._context.new_page()
            try:
                return await self._do_query(page, cnpj_numeros, cnpj_formatado, key)
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    logger.warning(f"Chave ...{key[-8:]} sem quota, tentando próxima")
                    continue
                raise
            finally:
                if not page.is_closed():
                    await page.close()

        raise Exception(f"Todas as {len(self._keys)} chaves esgotaram quota: {last_error}")

    async def _do_query(
        self, page: Page, cnpj_numeros: str, cnpj_formatado: str, api_key: str
    ) -> dict[str, str]:
        await page.goto(SITE_URL, wait_until="domcontentloaded", timeout=settings.browser_timeout)
        await page.wait_for_selector(".h-captcha iframe", timeout=15000)

        await page.click("#cnpj")
        await page.keyboard.type(cnpj_numeros, delay=50)
        await page.wait_for_timeout(300)

        valor = await page.input_value("#cnpj")
        if "/" not in valor:
            await page.triple_click("#cnpj")
            await page.keyboard.press("Backspace")
            for ch in cnpj_numeros:
                await page.keyboard.type(ch)
                await page.wait_for_timeout(80)
            await page.wait_for_timeout(300)
            valor = await page.input_value("#cnpj")

        logger.info(f"CNPJ no campo: {valor}")

        config = self._make_config(api_key)
        agent = AgentV(page=page, agent_config=config)

        hcaptcha_checkbox = page.frame_locator(
            "iframe[src*='hcaptcha']"
        ).first.locator("#checkbox")
        await hcaptcha_checkbox.click(timeout=5000)

        signal = await agent.wait_for_challenge()
        if signal != ChallengeSignal.SUCCESS:
            raise Exception(f"hCaptcha falhou: {signal}")

        async with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
            await page.click("button[type=submit]")

        for _ in range(20):
            url = page.url
            if "Comprovante" in url or "Erro" in url:
                break
            await page.wait_for_timeout(300)

        current_url = page.url

        if "Erro" in current_url:
            html = await page.content()
            return {"tipo": "erro", "html": html, "url": current_url}

        html_comprovante = await page.content()

        html_qsa = ""
        try:
            await page.goto(
                f"{BASE_URL}/Cnpjreva_qsa.asp",
                wait_until="domcontentloaded",
                timeout=10000,
            )
            html_qsa = await page.content()
        except Exception:
            logger.warning("Falha ao carregar página QSA")

        return {
            "tipo": "sucesso",
            "html_comprovante": html_comprovante,
            "html_qsa": html_qsa,
        }
