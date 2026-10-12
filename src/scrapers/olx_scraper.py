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

    async def search_regional(self, query: str) -> List[GPUListing]:
        """Realiza busca de anúncios na Serra Gaúcha / cidades ao redor de Veranópolis."""
        listings: List[GPUListing] = []
        encoded_q = query.replace(" ", "%20")
        url = f"https://www.olx.com.br/estado-rs/regioes-de-caxias-do-sul-e-passo-fundo?q={encoded_q}"

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code != 200:
                    logger.warning(f"OLX respondeu status {resp.status_code} para {url}")
                    return listings

                soup = BeautifulSoup(resp.text, "lxml")
                raw_ads = self._extract_from_next_data(soup)
                if not raw_ads:
                    raw_ads = self._extract_from_html(soup)

                for ad in raw_ads:
                    title = ad["title"]
                    price = ad["price"]
                    city = ad["city"]

                    # 1. Filtro de preço configurável
                    if price <= 0 or price > self.config.hardware.max_price_brl or price < self.config.hardware.min_price_brl:
                        continue

                    # 2. Filtro de localização por raio geodésico de Veranópolis (Haversine)
                    in_radius, distance_km = self._matches_target_region(city)
                    if not in_radius:
                        continue

                    # 3. Identificação de GPU NVIDIA e VRAM (16GB a 32GB)
                    gpu_info = identify_gpu(title, ad.get("description", ""))
                    if not gpu_info:
                        continue

                    model_name, vram = gpu_info

                    # 4. Verificação de limites de VRAM configurados
                    if not (self.config.hardware.min_vram_gb <= vram <= self.config.hardware.max_vram_gb):
                        continue

                    # 5. Detecção de defeito / peças / conserto
                    cond, reasons = self.defect_detector.analyze(title, ad.get("description", ""))

                    listing_id = f"olx_{re.sub(r'[^a-zA-Z0-9]', '', ad['url'])[-16:]}" if ad["url"] else f"olx_{len(listings)}"

                    item = GPUListing(
                        id=listing_id,
                        title=title,
                        price=price,
                        platform="OLX",
                        url=ad["url"],
                        image_url=ad.get("image_url") or "",
                        city=city or self.config.location.center_city,
                        state="RS",
                        distance_km=distance_km,
                        raw_location=city,
                        detected_model=model_name,
                        detected_vram_gb=vram,
                        condition=cond,
                        defect_reasons=reasons,
                        description=ad.get("description", "")
                    )
                    listings.append(item)

        except Exception as e:
            logger.error(f"Erro ao buscar no OLX regional ({query}): {e}")

        return listings

    async def search_national(self, query: str) -> List[float]:
        """Busca preços do modelo em todo o Brasil no OLX para benchmark estatístico."""
        prices: List[float] = []
        encoded_q = query.replace(" ", "%20")
        url = f"https://www.olx.com.br/brasil?q={encoded_q}"

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
                        # Descarta preços absurdos ou simbólicos (< R$ 200 ou > R$ 15.000)
                        if 200.0 <= p <= 15000.0:
                            # Confirma que é a GPU pesquisada
                            info = identify_gpu(ad["title"], ad.get("description", ""))
                            if info and info[0] == query:
                                prices.append(p)
        except Exception as e:
            logger.debug(f"Erro no benchmark nacional OLX para '{query}': {e}")

        return prices
