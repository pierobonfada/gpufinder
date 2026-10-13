import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from src.config import AppConfig
from src.defect_detector import DefectDetector
from src.gpu_catalog import identify_gpu
from src.models import GPUListing, GPUCondition
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

class FacebookMarketplaceScraper(BaseScraper):
    SEARCH_TERMS = ["rtx", "geforce", "gtx", "nvidia"]

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

    def _build_search_queries(self, query: str) -> List[Tuple[str, Optional[str]]]:
        """
        Gera tuplas (termo_de_busca, cidade_de_contexto) combinando hardware com as cidades da região.
        Permite encontrar os anúncios reais da Serra Gaúcha mesmo sem depender do feed geral do Facebook.
        """
        if query != "nvidia":
            return [(query, None)]

        from src.geo import is_within_radius, strip_accents

        center = self.config.location.center_city
        rad = self.config.location.radius_km
        lat = self.config.location.latitude
        lon = self.config.location.longitude

        # Cidades da região ordenadas por relevância e população comercial
        regional_hubs = [
            ("caxias", "Caxias do Sul"),
            ("bento", "Bento Gonçalves"),
            ("farroupilha", "Farroupilha"),
            ("flores da cunha", "Flores da Cunha"),
            ("carlos barbosa", "Carlos Barbosa"),
            ("garibaldi", "Garibaldi"),
            ("veranopolis", "Veranópolis"),
            ("guapore", "Guaporé"),
            ("nova prata", "Nova Prata"),
            ("vila flores", "Vila Flores"),
        ]

        queries: List[Tuple[str, Optional[str]]] = []
        seen_queries = set()

        def add_q(term: str, ctx_city: Optional[str]):
            term_clean = term.strip().lower()
            if term_clean not in seen_queries:
                seen_queries.add(term_clean)
                queries.append((term, ctx_city))

        # 1. Busca focada nos polos urbanos da Serra Gaúcha dentro do raio
        for token, city in regional_hubs:
            in_r, dist = is_within_radius(city, lat, lon, rad)
            if not in_r:
                continue

            add_q(f"rtx {token}", city)
            add_q(f"gtx {token}", city)
            add_q(f"placa de video {token}", city)

        # 2. Termos regionais agregados
        add_q("rtx serra gaucha", "Bento Gonçalves")
        add_q("placa de video serra gaucha", "Caxias do Sul")

        # 3. Termos gerais de hardware
        for b in self.SEARCH_TERMS:
            add_q(b, None)

        return queries

    async def search_regional(self, query: str = "nvidia") -> List[GPUListing]:
        """Varre o Facebook Marketplace por anúncios de GPU ao redor de Veranópolis e Serra Gaúcha."""
        if not self.config.scrapers.facebook.enabled:
            return []

        listings: List[GPUListing] = []
        seen_ids = set()
        seen_signatures = set()

        search_queries = self._build_search_queries(query)

        async with async_playwright() as p:
            context = None
            try:
                context = await self._setup_browser_context(p)
                page = await context.new_page()

                await self._ensure_logged_in(page)

                for term, context_city in search_queries:
                    encoded_q = term.replace(" ", "%20")
                    marketplace_url = f"https://www.facebook.com/marketplace/portoalegre/search/?query={encoded_q}"

                    logger.info(f"Facebook Marketplace ({term}): {marketplace_url}")
                    try:
                        await page.goto(marketplace_url, timeout=self.config.scrapers.facebook.timeout_seconds * 1000)
                        await page.wait_for_timeout(1800)

                        # Rola a página para carregar anúncios dinâmicos
                        for _ in range(2):
                            await page.evaluate("window.scrollBy(0, 1000)")
                            await page.wait_for_timeout(600)

                        items = await page.query_selector_all('a[href*="/marketplace/item/"]')

                        for el in items:
                            try:
                                text_content = await el.inner_text()
                                if not text_content:
                                    continue

                                lines = [line.strip() for line in text_content.split("\n") if line.strip()]
                                if not lines:
                                    continue

                                price_val = 0.0
                                title_val = ""
                                loc_val = ""

                                for line in lines:
                                    if "R$" in line or re.search(r"^\d+[\.,]?\d*$", line):
                                        if price_val == 0.0:
                                            price_val = self._extract_price(line)
                                    elif not title_val and len(line) > 3 and not line.startswith("R$") and not line.startswith("US$") and not line.startswith("Gratuito") and not line.startswith("Acabou"):
                                        title_val = line

                                    # Extração precisa de cidade
                                    if not loc_val:
                                        m_city = re.search(r"([A-Za-zÀ-ÿ\s]+),\s*(?:RS|rs)\b", line)
                                        if m_city:
                                            loc_val = m_city.group(1).strip()
                                        else:
                                            from src.geo import get_all_known_cities
                                            for c in get_all_known_cities():
                                                if re.search(r"\b" + re.escape(c.lower()) + r"\b", line.lower()):
                                                    loc_val = c
                                                    break

                                if not title_val:
                                    title_val = lines[0]

                                # 1. Filtro de preço básico (> 30)
                                if price_val < 30.0:
                                    continue

                                # 2. Filtro de localização por raio geodésico (Haversine)
                                from src.geo import is_within_radius
                                effective_city = loc_val or context_city or self.config.location.center_city
                                in_radius, distance_km = is_within_radius(
                                    effective_city,
                                    self.config.location.latitude,
                                    self.config.location.longitude,
                                    self.config.location.radius_km
                                )
                                # Se a cidade estiver fora do raio estipulado, descarta
                                if not in_radius:
                                    continue

                                href = await el.query_selector("a")
                                href_val = ""
                                if href:
                                    href_val = await href.get_attribute("href") or ""
                                elif await el.get_attribute("href"):
                                    href_val = await el.get_attribute("href") or ""

                                if href_val and not href_val.startswith("http"):
                                    href_val = f"https://www.facebook.com{href_val}"

                                # 3. Identificação de GPU NVIDIA e VRAM (descartando PCs e notebooks)
                                gpu_info = identify_gpu(title_val, text_content, href_val)
                                if not gpu_info:
                                    continue

                                model_name, vram = gpu_info

                                m_id = re.search(r"/marketplace/item/(\d+)", href_val)
                                if m_id:
                                    item_id = f"fb_{m_id.group(1)}"
                                    clean_url = f"https://www.facebook.com/marketplace/item/{m_id.group(1)}/"
                                else:
                                    item_id = f"fb_{len(listings)}_{round(price_val)}"
                                    clean_url = href_val

                                if item_id in seen_ids:
                                    continue
                                seen_ids.add(item_id)

                                # Imagem do card
                                img_el = await el.query_selector("img")
                                img_src = await img_el.get_attribute("src") if img_el else ""

                                # 5. Detecção de defeito / peças
                                cond, reasons = self.defect_detector.analyze(title_val, text_content)

                                listing = GPUListing(
                                    id=item_id,
                                    title=title_val,
                                    price=price_val,
                                    platform="Facebook",
                                    url=clean_url,
                                    image_url=img_src,
                                    city=effective_city,
                                    state="RS",
                                    distance_km=distance_km,
                                    raw_location=loc_val or effective_city,
                                    detected_model=model_name,
                                    detected_vram_gb=vram,
                                    condition=cond,
                                    defect_reasons=reasons,
                                    description=text_content
                                )
                                listings.append(listing)
                            except Exception as item_err:
                                logger.debug(f"Erro ao processar item do FB: {item_err}")

                    except Exception as term_err:
                        logger.warning(f"Erro ao buscar termo '{term}' no Facebook: {term_err}")

            except Exception as e:
                logger.warning(f"Erro ao executar scraper do Facebook Marketplace: {e}")
            finally:
                if context:
                    await context.close()

        return listings

    async def search_national(self, query: str, target_vram_gb: Optional[int] = None) -> List[float]:
        """Busca nacional no Facebook para fins de benchmark."""
        # O OLX e a base de referência são prioritários para estatísticas rápidas
        return []
