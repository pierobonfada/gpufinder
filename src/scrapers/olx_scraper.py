import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

from src.config import AppConfig
from src.defect_detector import DefectDetector
from src.gpu_catalog import identify_gpu
from src.models import GPUListing, GPUCondition
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

class OLXScraper(BaseScraper):
    def __init__(self, config: AppConfig, defect_detector: DefectDetector):
        self.config = config
        self.defect_detector = defect_detector
        self.headers = {
            "User-Agent": config.scrapers.olx.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.olx.com.br/",
        }

    def _extract_price(self, price_str: str) -> float:
        """Converte string de preço (ex: 'R$ 3.850' ou '3850') em float."""
        if not price_str:
            return 0.0
        # Remove R$, pontos e caracteres não numéricos exceto vírgula
        cleaned = re.sub(r"[^\d,]", "", str(price_str))
        if "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _extract_from_next_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Tenta extrair anúncios estruturados diretamente do JSON __NEXT_DATA__ do OLX."""
        ads = []
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if script_tag and script_tag.string:
            try:
                data = json.loads(script_tag.string)
                page_props = data.get("props", {}).get("pageProps", {})
                ads_data = (
                    page_props.get("ads") or
                    page_props.get("adList") or
                    page_props.get("initialState", {}).get("adList", {}).get("ads", [])
                )
                if isinstance(ads_data, list):
                    for ad in ads_data:
                        title = ad.get("subject") or ad.get("title") or ""
                        price_raw = ad.get("price") or ad.get("priceValue") or 0
                        url = ad.get("url") or ""
                        image_url = ""
                        images = ad.get("images") or []
                        if images and isinstance(images, list) and len(images) > 0:
                            image_url = images[0].get("original") or images[0].get("thumbnail") or ""

                        location = ad.get("location") or {}
                        city = location.get("municipality") or location.get("city") or ""
                        state = location.get("uf") or location.get("state") or "RS"

                        ads.append({
                            "title": title,
                            "price": self._extract_price(str(price_raw)),
                            "url": url,
                            "image_url": image_url,
                            "city": city,
                            "state": state,
                            "description": ad.get("body") or ad.get("description") or "",
                            "date": ad.get("date") or ""
                        })
            except Exception as e:
                logger.debug(f"Falha ao interpretar __NEXT_DATA__: {e}")
        return ads

    def _extract_from_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Fallback tradicional via seletores HTML caso o __NEXT_DATA__ não esteja presente."""
        ads = []
        # Seletores comuns de cards do OLX (incluindo o moderno section.olx-adcard)
        cards = soup.select('section.olx-adcard, section[data-ds-component="DS-NewAdCard"], a[data-ds-component="DS-NewAdCard"]')
        if not cards:
            cards = soup.select('li[class*="item"] a, a[class*="olx-ad-card"]')

        for card in cards:
            title_el = card.select_one('h2, [class*="title"], [data-ds-component="DS-NewAdCard-Title"]')
            price_el = card.select_one('[class*="price"], [data-ds-component="DS-NewAdCard-Price"]')
            loc_el = card.select_one('[class*="location"], [data-ds-component="DS-NewAdCard-Location"]')
            img_el = card.select_one('img')

            url = card.get("href") or ""
            if not url:
                link_el = card.select_one("a[href]")
                if link_el:
                    url = link_el.get("href") or ""
            if url and not url.startswith("http"):
                url = f"https://www.olx.com.br{url}"

            title = title_el.get_text(strip=True) if title_el else ""
            price_str = price_el.get_text(strip=True) if price_el else ""
            raw_loc = loc_el.get_text(strip=True) if loc_el else ""

            # Limpa datas e horários da string de localização para obter a cidade limpa
            cleaned_loc = re.sub(r"\d+\s+de\s+[a-z]+.*$", "", raw_loc, flags=re.IGNORECASE)
            cleaned_loc = re.sub(r"ontem.*$", "", cleaned_loc, flags=re.IGNORECASE)
            cleaned_loc = re.sub(r"\d+:\d+.*$", "", cleaned_loc)
            city = cleaned_loc.split(",")[0].strip() if cleaned_loc else raw_loc

            img_url = img_el.get("src") or img_el.get("data-src") if img_el else ""

            if title:
                ads.append({
                    "title": title,
                    "price": self._extract_price(price_str),
                    "url": url,
                    "image_url": img_url,
                    "city": city,
                    "state": "RS",
                    "description": "",
                    "date": ""
                })
        return ads

    def _matches_target_region(self, city_name: str) -> Tuple[bool, Optional[float]]:
        """
        Verifica se a cidade do anúncio está dentro do raio configurado (ex: 40km)
        ao redor de Veranópolis utilizando cálculo geodésico Haversine.
        """
        from src.geo import is_within_radius

        lat = self.config.location.latitude
        lon = self.config.location.longitude
        radius = self.config.location.radius_km

        return is_within_radius(city_name, lat, lon, radius)

    async def _fetch_description(self, client: httpx.AsyncClient, url: str) -> str:
        """Obtém a descrição completa do anúncio na página de detalhe."""
        if not url:
            return ""
        try:
            resp = await client.get(url, headers=self.headers, timeout=8.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                desc_tag = soup.select_one('[data-ds-component="DS-Text"], [class*="description"], span.sc-1sj3nfx-0')
                return desc_tag.get_text(separator=" ").strip() if desc_tag else ""
        except Exception as e:
            logger.debug(f"Falha ao carregar descrição de {url}: {e}")
        return ""

    async def search_regional(self, query: str = "nvidia", max_pages: int = 3) -> List[GPUListing]:
        """
        Realiza busca ampla (ex: 'nvidia') na Serra Gaúcha / cidades ao redor de Veranópolis,
        navegando por múltiplas páginas e inspecionando descrições para filtrar a faixa de VRAM.
        """
        listings: List[GPUListing] = []
        encoded_q = query.replace(" ", "%20")
        all_raw_ads: List[Dict] = []
        seen_urls = set()

        urls_to_crawl = []
        # Categoria estrita e especializada de placas de vídeo na região de Caxias do Sul e Passo Fundo
        # (NÃO pesquisa na raiz geral para não trazer PCs completos e notebooks)
        search_terms = ["nvidia", "rtx", "geforce", "gtx"] if query == "nvidia" else [query]
        for term in search_terms:
            encoded_term = term.replace(" ", "%20")
            for page in range(1, max_pages + 1):
                urls_to_crawl.append(
                    f"https://www.olx.com.br/informatica/placas-de-video/estado-rs/regioes-de-caxias-do-sul-e-passo-fundo?q={encoded_term}&o={page}"
                )

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                for url in urls_to_crawl:
                    try:
                        resp = await client.get(url, headers=self.headers)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, "lxml")
                            extracted = self._extract_from_next_data(soup)
                            if not extracted:
                                extracted = self._extract_from_html(soup)
                            for ad in extracted:
                                if ad["url"] and ad["url"] not in seen_urls:
                                    seen_urls.add(ad["url"])
                                    all_raw_ads.append(ad)
                        await asyncio.sleep(0.3)
                    except Exception as page_err:
                        logger.debug(f"Erro ao buscar {url}: {page_err}")

                # Filtra anúncios candidatos pela localização antes de buscar descrições
                candidates = []
                for ad in all_raw_ads:
                    price = ad["price"]
                    city = ad["city"]
                    if price < 30.0:
                        continue

                    in_radius, distance_km = self._matches_target_region(city)
                    if not in_radius:
                        continue

                    candidates.append((ad, distance_km))

                logger.info(f"OLX Regional: {len(candidates)} anúncios candidatos dentro do raio geodésico.")

                # Busca descrições dos candidatos para validar modelo e detalhes
                for ad, distance_km in candidates:
                    title = ad["title"]
                    desc = ad.get("description", "")
                    
                    # Se não possui descrição completa, busca na página do anúncio
                    if not desc and ad.get("url"):
                        desc = await self._fetch_description(client, ad["url"])
                        ad["description"] = desc
                        await asyncio.sleep(0.2)

                    # Identifica GPU e VRAM (com validação estrita de placa avulsa, descartando PCs)
                    gpu_info = identify_gpu(title, desc, ad.get("url", ""))
                    if not gpu_info:
                        continue

                    model_name, vram = gpu_info

                    # Detecção de defeito / peças / conserto
                    cond, reasons = self.defect_detector.analyze(title, desc)

                    listing_id = f"olx_{re.sub(r'[^a-zA-Z0-9]', '', ad['url'])[-16:]}" if ad["url"] else f"olx_{len(listings)}"

                    item = GPUListing(
                        id=listing_id,
                        title=title,
                        price=ad["price"],
                        platform="OLX",
                        url=ad["url"],
                        image_url=ad.get("image_url") or "",
                        city=ad["city"] or self.config.location.center_city,
                        state="RS",
                        distance_km=distance_km,
                        raw_location=ad["city"],
                        detected_model=model_name,
                        detected_vram_gb=vram,
                        condition=cond,
                        defect_reasons=reasons,
                        description=desc
                    )
                    listings.append(item)

        except Exception as e:
            logger.error(f"Erro ao buscar no OLX regional ({query}): {e}")

        return listings

    async def search_national(self, query: str, target_vram_gb: Optional[int] = None) -> List[float]:
        """Busca preços do modelo em todo o Brasil no OLX (especificamente placas-de-video) para benchmark estatístico."""
        prices: List[float] = []
        search_term = query
        if target_vram_gb and target_vram_gb > 0 and f"{target_vram_gb}gb" not in query.lower():
            search_term = f"{query} {target_vram_gb}gb"

        encoded_q = search_term.replace(" ", "%20")
        url = f"https://www.olx.com.br/informatica/placas-de-video?q={encoded_q}"

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    raw_ads = self._extract_from_next_data(soup)
                    if not raw_ads:
                        raw_ads = self._extract_from_html(soup)

                    for ad in raw_ads:
                        p = ad.get("price", 0.0)
                        # Descarta preços absurdos ou simbólicos (< R$ 200 ou > R$ 35.000)
                        if 200.0 <= p <= 35000.0:
                            # Confirma que é a GPU pesquisada e NÃO um computador
                            info = identify_gpu(ad["title"], ad.get("description", ""), ad.get("url", ""))
                            if info:
                                ad_model, ad_vram = info
                                if ad_model == query or query.lower() in ad_model.lower():
                                    # Validação estrita de VRAM: não mistura 8GB com 12GB ou 16GB
                                    if target_vram_gb is not None and target_vram_gb > 0 and ad_vram != target_vram_gb:
                                        continue
                                    prices.append(p)
        except Exception as e:
            logger.debug(f"Erro no benchmark nacional OLX para '{query}': {e}")

        return prices

    async def search_state_rs(self, queries: List[str] = ["nvidia"]) -> List[GPUListing]:
        """Varre a categoria especializada de informática/placas-de-video no Rio Grande do Sul e filtra pelo raio."""
        listings: List[GPUListing] = []
        seen_urls = set()
        
        search_terms = ["nvidia", "rtx", "geforce", "gtx"] if queries == ["nvidia"] else queries
        for q in search_terms:
            encoded_q = q.replace(" ", "%20")
            for page in range(1, 3):
                url = f"https://www.olx.com.br/informatica/placas-de-video/estado-rs?q={encoded_q}&o={page}"
                try:
                    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                        resp = await client.get(url, headers=self.headers)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, "lxml")
                            raw_ads = self._extract_from_next_data(soup)
                            if not raw_ads:
                                raw_ads = self._extract_from_html(soup)
                            for ad in raw_ads:
                                if ad["url"] in seen_urls:
                                    continue
                                seen_urls.add(ad["url"])

                                title = ad["title"]
                                price = ad["price"]
                                if price < 30.0:
                                    continue

                                city = ad.get("city", "")
                                # Filtra estritamente pelo raio geodésico
                                in_radius, distance_km = self._matches_target_region(city)
                                if not in_radius:
                                    continue

                                desc = ad.get("description", "")
                                if not desc and ad.get("url"):
                                    desc = await self._fetch_description(client, ad["url"])
                                    ad["description"] = desc
                                    await asyncio.sleep(0.2)

                                gpu_info = identify_gpu(title, desc, ad.get("url", ""))
                                if not gpu_info:
                                    continue

                                model_name, vram = gpu_info
                                cond, reasons = self.defect_detector.analyze(title, desc)

                                listing_id = f"olx_{re.sub(r'[^a-zA-Z0-9]', '', ad['url'])[-16:]}" if ad["url"] else f"olx_{len(listings)}"
                                item = GPUListing(
                                    id=listing_id,
                                    title=title,
                                    price=price,
                                    platform="OLX",
                                    url=ad["url"],
                                    image_url=ad.get("image_url") or "",
                                    city=city,
                                    state="RS",
                                    distance_km=distance_km,
                                    raw_location=city,
                                    detected_model=model_name,
                                    detected_vram_gb=vram,
                                    condition=cond,
                                    defect_reasons=reasons,
                                    description=desc
                                )
                                listings.append(item)
                except Exception as e:
                    logger.debug(f"Erro ao buscar no OLX RS ({q}): {e}")
                await asyncio.sleep(0.3)
        return listings
