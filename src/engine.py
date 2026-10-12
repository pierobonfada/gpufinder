import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.benchmark import BenchmarkEngine
from src.config import AppConfig, load_config
from src.defect_detector import DefectDetector
from src.gpu_catalog import get_target_search_queries
from src.models import GPUListing, GPUCondition, PriceClassification, ScanSummary
from src.outlier_detector import OutlierDetector
from src.scrapers.facebook_scraper import FacebookMarketplaceScraper
from src.scrapers.olx_scraper import OLXScraper
from src.scrapers.sample_generator import generate_sample_listings

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "listings.json"

class GPUHunterEngine:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.defect_detector = DefectDetector(
            keywords=self.config.defect_detection.keywords,
            negation_keywords=self.config.defect_detection.negation_keywords
        )
        self.benchmark_engine = BenchmarkEngine(self.config.national_benchmark)
        self.olx_scraper = OLXScraper(self.config, self.defect_detector)
        self.facebook_scraper = FacebookMarketplaceScraper(self.config, self.defect_detector)
        self.is_scanning = False
        self.last_summary: Optional[ScanSummary] = None

    def load_listings_from_disk(self) -> List[GPUListing]:
        """Carrega os anúncios persistidos no disco."""
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [GPUListing.model_validate(item) for item in data]
            except Exception as e:
                logger.error(f"Erro ao carregar anúncios de {DATA_FILE}: {e}")
        return []

    def save_listings_to_disk(self, listings: List[GPUListing]) -> None:
        """Salva a lista atualizada de anúncios no disco."""
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [item.model_dump() for item in listings]
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def calculate_summary(self, listings: List[GPUListing]) -> ScanSummary:
        """Calcula métricas agregadas da varredura atual."""
        if not listings:
            return ScanSummary()

        working = [i for i in listings if i.condition == GPUCondition.WORKING]
        defective = [i for i in listings if i.condition == GPUCondition.DEFECTIVE]
        outliers = [i for i in listings if i.is_outlier]
        prices = [i.price for i in listings if i.price > 0]

        best_deal = None
        # Encontra o anúncio funcional com o melhor desconto percentual vs média nacional
        working_with_benchmark = [
            i for i in working if i.price_diff_percent is not None and i.price_diff_percent < 0
        ]
        if working_with_benchmark:
            best_deal = min(working_with_benchmark, key=lambda x: x.price_diff_percent)
        elif working:
            best_deal = min(working, key=lambda x: x.price)

        return ScanSummary(
            total_found=len(listings),
            working_count=len(working),
            defective_count=len(defective),
            outliers_count=len(outliers),
            lowest_price=min(prices) if prices else 0.0,
            highest_price=max(prices) if prices else 0.0,
            average_price=round(sum(prices) / len(prices), 2) if prices else 0.0,
            best_deal=best_deal,
            scanned_at=datetime.now().isoformat()
        )

    async def run_scan(self, include_live_scrapers: bool = True) -> ScanSummary:
        """Executa o ciclo completo de varredura regional, benchmark nacional e análise de outliers."""
        if self.is_scanning:
            logger.warning("Varredura já em andamento.")
            return self.last_summary or ScanSummary()

        self.is_scanning = True
        try:
            listings_dict: Dict[str, GPUListing] = {}

            # Carrega anúncios já salvos anteriormente
            for item in self.load_listings_from_disk():
                listings_dict[item.id] = item

            # Se a base estiver vazia, carrega dados de amostra da região para visualização inicial
            if not listings_dict:
                for item in generate_sample_listings(self.defect_detector):
                    listings_dict[item.id] = item

            if include_live_scrapers:
                queries = get_target_search_queries()
                logger.info(f"Iniciando varredura regional para {len(queries)} termos...")

                # 1. OLX Regional
                if self.config.scrapers.olx.enabled:
                    for q in queries[:6]: # Varre os principais termos
                        try:
                            found = await self.olx_scraper.search_regional(q)
                            for item in found:
                                listings_dict[item.id] = item
                            await asyncio.sleep(self.config.scrapers.olx.request_delay_seconds)
                        except Exception as e:
                            logger.error(f"Erro ao varrer OLX para '{q}': {e}")

                # 2. Facebook Marketplace
                if self.config.scrapers.facebook.enabled:
                    for q in ["RTX 3090", "RTX 4060 Ti 16GB", "Tesla P40", "Quadro"]:
                        try:
                            found = await self.facebook_scraper.search_regional(q)
                            for item in found:
                                listings_dict[item.id] = item
                            await asyncio.sleep(2)
                        except Exception as e:
                            logger.error(f"Erro ao varrer Facebook para '{q}': {e}")

            all_listings = list(listings_dict.values())

            # Garante cálculo de distância geodésica (Haversine) para cada anúncio
            from src.geo import get_city_distance_from_center
            for item in all_listings:
                if item.distance_km is None and item.city:
                    item.distance_km = get_city_distance_from_center(item.city)

            # 3. Pesquisa e atualização de Benchmark Nacional para cada modelo encontrado
            if self.config.national_benchmark.enabled:
                unique_models = set(item.detected_model for item in all_listings if item.detected_model != "Desconhecido")
                for model in unique_models:
                    # Busca preços ao vivo no OLX Brasil para alimentar o benchmark nacional
                    try:
                        national_prices = await self.olx_scraper.search_national(model)
                        if national_prices:
                            self.benchmark_engine.update_model_stats(model, national_prices)
                    except Exception as e:
                        logger.debug(f"Benchmark ao vivo não respondeu para {model}: {e}")

                # Aplica enriquecimento de benchmark em todos os itens
                all_listings = self.benchmark_engine.enrich_all(all_listings)

            # 4. Detecção e destaque de outliers com IQR
            all_listings = OutlierDetector.detect_outliers_iqr(all_listings)

            # 5. Salva dados e calcula sumário
            self.save_listings_to_disk(all_listings)
            self.last_summary = self.calculate_summary(all_listings)
            return self.last_summary

        finally:
            self.is_scanning = False
