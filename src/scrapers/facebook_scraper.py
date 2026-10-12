import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from src.config import AppConfig
from src.defect_detector import DefectDetector
from src.gpu_catalog import identify_gpu
from src.models import GPUListing, GPUCondition
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

class FacebookMarketplaceScraper(BaseScraper):
    def __init__(self, config: AppConfig, defect_detector: DefectDetector):
        self.config = config
        self.defect_detector = defect_detector
        self.session_path = Path(__file__).resolve().parent.parent.parent / config.scrapers.facebook.session_file
        self.session_path.parent.mkdir(parents=True, exist_ok=True)

    def _extract_price(self, price_str: str) -> float:
        if not price_str:
            return 0.0
        cleaned = re.sub(r"[^\d,]", "", str(price_str))
        if "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    async def _setup_browser_context(self, playwright) -> BrowserContext:
        """Configura o navegador Playwright com geolocalização fixada em Veranópolis."""
        lat = self.config.location.latitude
        lon = self.config.location.longitude

        browser = await playwright.chromium.launch(
            headless=self.config.scrapers.facebook.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )

        context_kwargs = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "locale": "pt-BR",
            "geolocation": {"latitude": lat, "longitude": lon},
            "permissions": ["geolocation"]
        }

        # Carrega sessão persistida se existir
        if self.session_path.exists() and self.session_path.stat().st_size > 10:
            try:
                context_kwargs["storage_state"] = str(self.session_path)
                logger.info(f"Sessão do Facebook carregada de {self.session_path}")
            except Exception as e:
                logger.warning(f"Falha ao carregar storage_state: {e}")

        context = await browser.new_context(**context_kwargs)
        return context

    async def _ensure_logged_in(self, page: Page) -> bool:
        """Realiza login se as credenciais estiverem configuradas e a sessão não estiver ativa."""
        email = self.config.scrapers.facebook.email or os.environ.get("FB_EMAIL", "")
        password = self.config.scrapers.facebook.password or os.environ.get("FB_PASSWORD", "")

        if not email or not password:
            logger.info("Credenciais do Facebook não configuradas. Tentando acesso anônimo/cookies existentes.")
            return False

        try:
            await page.goto("https://www.facebook.com/", timeout=15000)
            await asyncio.sleep(2)

            # Verifica se já está logado
            if await page.query_selector('div[role="feed"]') or await page.query_selector('a[href*="/marketplace/"]'):
                logger.info("Já logado no Facebook.")
                return True

            # Preenche login se formulário estiver visível
            email_input = await page.query_selector('input[name="email"], input#email')
            pass_input = await page.query_selector('input[name="pass"], input#pass')
            login_btn = await page.query_selector('button[name="login"], button[type="submit"]')

            if email_input and pass_input and login_btn:
                logger.info("Realizando login automático no Facebook...")
                await email_input.fill(email)
                await pass_input.fill(password)
                await login_btn.click()
                await page.wait_for_timeout(5000)

                # Salva sessão autenticada para reutilização
                storage = await page.context.storage_state()
                with open(self.session_path, "w", encoding="utf-8") as f:
                    json.dump(storage, f)
                logger.info(f"Sessão do Facebook salva com sucesso em {self.session_path}")
                return True
        except Exception as e:
            logger.warning(f"Não foi possível completar o login automático no Facebook: {e}")

        return False

    async def search_regional(self, query: str) -> List[GPUListing]:
        """Varre o Facebook Marketplace por anúncios de GPU ao redor de Veranópolis."""
        if not self.config.scrapers.facebook.enabled:
            return []

        listings: List[GPUListing] = []
        encoded_q = query.replace(" ", "%20")
        marketplace_url = f"https://www.facebook.com/marketplace/search/?query={encoded_q}&exact=false"

        async with async_playwright() as p:
            context = None
            try:
                context = await self._setup_browser_context(p)
                page = await context.new_page()

                await self._ensure_logged_in(page)

                logger.info(f"Acessando Facebook Marketplace: {marketplace_url}")
                await page.goto(marketplace_url, timeout=self.config.scrapers.facebook.timeout_seconds * 1000)
                await page.wait_for_timeout(3000)

                # Rola suavemente a página para carregar itens dinâmicos
                await page.evaluate("window.scrollBy(0, 1000)")
                await page.wait_for_timeout(2000)

                # Seleciona cards de anúncios (links contendo '/marketplace/item/')
                items = await page.query_selector_all('a[href*="/marketplace/item/"]')
                logger.info(f"Encontrados {len(items)} itens no Facebook Marketplace para '{query}'")

                for el in items:
                    try:
                        text_content = await el.inner_text()
                        if not text_content:
                            continue

                        lines = [line.strip() for line in text_content.split("\n") if line.strip()]
                        if not lines:
                            continue

                        # Normalmente: [Preço, Título, Localização]
                        price_val = 0.0
                        title_val = ""
                        loc_val = self.config.location.center_city

                        for line in lines:
                            if "R$" in line or re.search(r"^\d+[\.,]?\d*$", line):
                                if price_val == 0.0:
                                    price_val = self._extract_price(line)
                            elif not title_val and len(line) > 3 and not line.startswith("R$"):
                                title_val = line
                            elif not loc_val or loc_val == self.config.location.center_city:
                                if any(c.lower() in line.lower() for c in self.config.location.target_cities):
                                    loc_val = line

                        if not title_val:
                            title_val = lines[0]

                        # Imagem do card
                        img_el = await el.query_selector("img")
                        img_src = await img_el.get_attribute("src") if img_el else ""

                        href = await el.get_attribute("href") or ""
                        if href and not href.startswith("http"):
                            href = f"https://www.facebook.com{href}"

                        # 1. Filtro de preço
                        if price_val <= 0 or price_val > self.config.hardware.max_price_brl or price_val < self.config.hardware.min_price_brl:
                            continue

                        # 2. Identificação de GPU NVIDIA e VRAM (16GB a 32GB)
                        gpu_info = identify_gpu(title_val)
                        if not gpu_info:
                            continue

                        model_name, vram = gpu_info

                        # 3. Verificação de limites de VRAM
                        if not (self.config.hardware.min_vram_gb <= vram <= self.config.hardware.max_vram_gb):
                            continue

                        # 4. Detecção de defeito / peças
                        cond, reasons = self.defect_detector.analyze(title_val)

                        item_id = f"fb_{re.sub(r'[^a-zA-Z0-9]', '', href)[-16:]}" if href else f"fb_{len(listings)}"

                        listing = GPUListing(
                            id=item_id,
                            title=title_val,
                            price=price_val,
                            platform="Facebook",
                            url=href,
                            image_url=img_src,
                            city=loc_val,
                            state="RS",
                            raw_location=loc_val,
                            detected_model=model_name,
                            detected_vram_gb=vram,
                            condition=cond,
                            defect_reasons=reasons,
                            description=text_content
                        )
                        listings.append(listing)
                    except Exception as item_err:
                        logger.debug(f"Erro ao processar item do FB: {item_err}")

            except Exception as e:
                logger.warning(f"Erro ao executar scraper do Facebook Marketplace ({query}): {e}")
            finally:
                if context:
                    await context.close()

        return listings

    async def search_national(self, query: str) -> List[float]:
        """Busca nacional no Facebook para fins de benchmark."""
        # O OLX e a base de referência são prioritários para estatísticas rápidas
        return []
