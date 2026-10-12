import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from src.config import AppConfig
from src.defect_detector import DefectDetector
from src.geo import is_within_radius, get_city_distance_from_center
from src.gpu_catalog import identify_gpu
from src.models import GPUCondition, GPUListing

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

class MercadoLivreScraper:
    """
    Scraper automatizado para Mercado Livre focado em placas de vídeo NVIDIA no RS e Serra Gaúcha.
    Suporta persistência de sessão autenticada (cookies/storage_state) para contornar verificações.
    """

    def __init__(self, config: AppConfig, defect_detector: DefectDetector):
        self.config = config
        self.defect_detector = defect_detector
        self.session_path = Path(self.config.scrapers.mercadolivre.session_file)
        if not self.session_path.is_absolute():
            self.session_path = DATA_DIR / self.session_path.name

    def _extract_price(self, text: str) -> float:
        """Extrai o valor numérico do preço brasileiro."""
        cleaned = re.sub(r"[^\d,\.]", "", text)
        if not cleaned:
            return 0.0
        if "." in cleaned and "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        elif "." in cleaned:
            parts = cleaned.split(".")
            if len(parts) > 1 and len(parts[-1]) == 3:
                cleaned = "".join(parts)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    async def _setup_browser_context(self, p: Playwright) -> BrowserContext:
        """Configura o contexto Chromium com headers legítimos e sessão salva se houver."""
        browser = await p.chromium.launch(
            headless=self.config.scrapers.mercadolivre.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        lat = self.config.location.latitude
        lon = self.config.location.longitude

        context_kwargs = {
            "viewport": {"width": 1366, "height": 768},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "locale": "pt-BR",
            "geolocation": {"latitude": lat, "longitude": lon},
            "permissions": ["geolocation"]
        }

        # Carrega sessão salva se disponível
        if self.session_path.exists() and self.session_path.stat().st_size > 10:
            try:
                context_kwargs["storage_state"] = str(self.session_path)
                logger.info(f"Sessão do Mercado Livre carregada de {self.session_path}")
            except Exception as e:
                logger.warning(f"Falha ao carregar storage_state do ML: {e}")

        context = await browser.new_context(**context_kwargs)
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        return context

    async def _ensure_logged_in(self, page: Page) -> bool:
        """Tenta autenticação automática se credenciais foram fornecidas."""
        email = self.config.scrapers.mercadolivre.email or os.environ.get("ML_EMAIL", "")
        password = self.config.scrapers.mercadolivre.password or os.environ.get("ML_PASSWORD", "")

        if not email or not password:
            return False

        try:
            await page.goto("https://www.mercadolivre.com.br/", timeout=15000)
            await asyncio.sleep(2)

            # Verifica se já está logado
            if await page.query_selector('a[href*="/my-account"]'):
                return True

            # Tenta preencher login
            login_link = await page.query_selector('a[data-link-id="login"], a:has-text("Entre")')
            if login_link:
                await login_link.click()
                await page.wait_for_timeout(3000)

                user_input = await page.query_selector('input[name="user_id"], input#user_id')
                if user_input:
                    await user_input.fill(email)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(3000)

                    pass_input = await page.query_selector('input[name="password"], input#password')
                    if pass_input:
                        await pass_input.fill(password)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(4000)

                        storage = await page.context.storage_state()
                        with open(self.session_path, "w", encoding="utf-8") as f:
                            json.dump(storage, f)
                        logger.info(f"Sessão do Mercado Livre salva com sucesso em {self.session_path}")
                        return True
        except Exception as e:
            logger.warning(f"Não foi possível completar o login automático no Mercado Livre: {e}")

        return False

    async def search_regional(self, query: str = "nvidia", max_pages: int = 2) -> List[GPUListing]:
        """Varre o Mercado Livre por placas de vídeo no Rio Grande do Sul e proximidades."""
        if not self.config.scrapers.mercadolivre.enabled:
            return []

        listings: List[GPUListing] = []
        encoded_q = query.replace(" ", "%20")
        
        # URLs de busca: Rio Grande do Sul e Usados no RS
        target_urls = [
            f"https://lista.mercadolivre.com.br/informatica/componentes-pc/placas-video/placas-video/rio-grande-do-sul/{encoded_q}",
            f"https://lista.mercadolivre.com.br/informatica/componentes-pc/placas-video/placas-video/usado/rio-grande-do-sul/{encoded_q}"
        ]

        async with async_playwright() as p:
            context = None
            try:
                context = await self._setup_browser_context(p)
                page = await context.new_page()

                await self._ensure_logged_in(page)

                for target_url in target_urls:
                    for page_num in range(1, max_pages + 1):
                        current_url = target_url if page_num == 1 else f"{target_url}_Desde_{(page_num - 1) * 50 + 1}"
                        logger.info(f"Acessando Mercado Livre RS: {current_url}")
                        
                        try:
                            resp = await page.goto(
                                current_url,
                                timeout=self.config.scrapers.mercadolivre.timeout_seconds * 1000,
                                wait_until="domcontentloaded"
                            )
                            await page.wait_for_timeout(2000)

                            # Verifica se caiu em página de desafio/bloqueio
                            if "account-verification" in page.url or "login" in page.url:
                                logger.info(
                                    "Mercado Livre: Verificação de conta necessária para acesso direto ao ML. "
                                    "Salve a sessão em data/ml_session.json se desejar resultados adicionais do ML."
                                )
                                break

                            # Localiza cards de produtos
                            cards = await page.query_selector_all(
                                ".ui-search-layout__item, li.ui-search-layout__item, .poly-card, div.ui-search-result__wrapper"
                            )
                            if not cards:
                                break

                            for card in cards:
                                try:
                                    title_el = await card.query_selector(
                                        ".poly-component__title, h2.ui-search-item__title, a.ui-search-item__group__element, [class*='title']"
                                    )
                                    price_el = await card.query_selector(
                                        ".andes-money-amount__fraction, .price-tag-fraction, [class*='price']"
                                    )
                                    loc_el = await card.query_selector(
                                        ".poly-component__location, .ui-search-item__location, [class*='location']"
                                    )
                                    link_el = await card.query_selector("a[href]")
                                    img_el = await card.query_selector("img")

                                    if not title_el or not price_el or not link_el:
                                        continue

                                    title = await title_el.inner_text()
                                    price_text = await price_el.inner_text()
                                    price_val = self._extract_price(price_text)
                                    raw_href = await link_el.get_attribute("href") or ""
                                    img_url = await img_el.get_attribute("src") if img_el else ""

                                    loc_text = await loc_el.inner_text() if loc_el else ""
                                    city_name = ""
                                    if loc_text:
                                        # E.g. "Caxias do Sul, Rio Grande do Sul"
                                        city_name = loc_text.split(",")[0].strip()

                                    # Filtro de preço básico
                                    if price_val < 30.0:
                                        continue

                                    # Filtro geodésico
                                    effective_city = city_name or self.config.location.center_city
                                    in_radius, distance_km = is_within_radius(
                                        effective_city,
                                        self.config.location.latitude,
                                        self.config.location.longitude,
                                        self.config.location.radius_km
                                    )
                                    if not in_radius and city_name:
                                        continue

                                    # Identificação e classificação de GPU (rejeitando PCs e notebooks)
                                    gpu_info = identify_gpu(title, "", raw_href)
                                    if not gpu_info:
                                        continue

                                    model_name, vram = gpu_info
                                    cond, reasons = self.defect_detector.analyze(title, "")

                                    item_id = f"ml_{re.sub(r'[^a-zA-Z0-9]', '', raw_href)[-16:]}"

                                    listing = GPUListing(
                                        id=item_id,
                                        title=title,
                                        price=price_val,
                                        platform="MercadoLivre",
                                        url=raw_href,
                                        image_url=img_url,
                                        city=effective_city,
                                        state="RS",
                                        distance_km=distance_km,
                                        raw_location=loc_text,
                                        detected_model=model_name,
                                        detected_vram_gb=vram,
                                        condition=cond,
                                        defect_reasons=reasons,
                                        description=""
                                    )
                                    listings.append(listing)
                                except Exception as card_err:
                                    logger.debug(f"Erro ao extrair card do ML: {card_err}")

                        except Exception as page_e:
                            logger.debug(f"Erro ao processar página do ML {current_url}: {page_e}")

            except Exception as e:
                logger.warning(f"Erro ao executar scraper do Mercado Livre: {e}")
            finally:
                if context:
                    await context.close()

        return listings
