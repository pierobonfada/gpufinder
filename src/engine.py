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
from src.gpu_performance import get_gpu_compute_data
from src.models import GPUListing, GPUCondition, PriceClassification, ScanSummary, ScanProgress
from src.outlier_detector import OutlierDetector
from src.scrapers.facebook_scraper import FacebookMarketplaceScraper
from src.scrapers.olx_scraper import OLXScraper

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
        self.progress: ScanProgress = ScanProgress()

    def load_listings_from_disk(self) -> List[GPUListing]:
        """Carrega exclusivamente anúncios reais do disco, descartando qualquer dado de teste."""
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Garante exclusão total de dados de teste (sem prefixo sample_)
                return [
                    GPUListing.model_validate(item) 
                    for item in data 
                    if not item.get("id", "").startswith("sample_")
                ]
            except Exception as e:
                logger.error(f"Erro ao carregar anúncios de {DATA_FILE}: {e}")
        return []

    def save_listings_to_disk(self, listings: List[GPUListing]) -> None:
        """Salva a lista atualizada de anúncios reais no disco."""
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Filtra novamente para garantir 0 dados de teste
        clean_listings = [item for item in listings if not item.id.startswith("sample_")]
        data = [item.model_dump() for item in clean_listings]
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def calculate_summary(self, listings: List[GPUListing]) -> ScanSummary:
        """Calcula métricas agregadas da varredura atual."""
        clean = [i for i in listings if not i.id.startswith("sample_")]
        if not clean:
            return ScanSummary()

        working = [i for i in clean if i.condition == GPUCondition.WORKING]
        defective = [i for i in clean if i.condition == GPUCondition.DEFECTIVE]
        outliers = [i for i in clean if i.is_outlier]
        prices = [i.price for i in clean if i.price > 0]

        lowest_item = None
        valid_items = [i for i in clean if i.price > 0]
        if valid_items:
            lowest_item = min(valid_items, key=lambda x: x.price)

        best_deal = None
        working_with_benchmark = [
            i for i in working if i.price_diff_percent is not None and i.price_diff_percent < 0
        ]
        if working_with_benchmark:
            best_deal = min(working_with_benchmark, key=lambda x: x.price_diff_percent)
        elif working:
            best_deal = min(working, key=lambda x: x.price)

        return ScanSummary(
            total_found=len(clean),
            working_count=len(working),
            defective_count=len(defective),
            outliers_count=len(outliers),
            lowest_price=min(prices) if prices else 0.0,
            highest_price=max(prices) if prices else 0.0,
            average_price=round(sum(prices) / len(prices), 2) if prices else 0.0,
            best_deal=best_deal,
            lowest_item=lowest_item,
            scanned_at=datetime.now().isoformat()
        )

    def _log_progress(self, step: int, total_steps: int, task: str, log_msg: Optional[str] = None):
        """Atualiza o estado de progresso em tempo real acessível pela API."""
        self.progress.current_step = step
        self.progress.total_steps = total_steps
        self.progress.current_task = task
        if log_msg:
            ts = datetime.now().strftime("%H:%M:%S")
            entry = f"[{ts}] {log_msg}"
            self.progress.logs.append(entry)
            # Mantém apenas os últimos 30 logs para performance
            if len(self.progress.logs) > 30:
                self.progress.logs = self.progress.logs[-30:]
            logger.info(log_msg)

    async def run_scan(
        self, 
        include_live_scrapers: bool = True,
        custom_max_price: Optional[float] = None,
        custom_radius_km: Optional[float] = None
    ) -> ScanSummary:
        """
        Executa a varredura ao vivo COMPLETA e EXCLUSIVAMENTE com anúncios reais.
        Zero dados de teste sintéticos.
        """
        if self.is_scanning:
            logger.warning("Varredura já em andamento.")
            return self.last_summary or ScanSummary()

        self.is_scanning = True
        total_steps = 7

        if custom_max_price is not None and custom_max_price > 0:
            self.config.hardware.max_price_brl = custom_max_price
        if custom_radius_km is not None and custom_radius_km > 0:
            self.config.location.radius_km = custom_radius_km

        self.progress = ScanProgress(
            is_scanning=True,
            current_task="Iniciando varredura ao vivo...",
            current_step=1,
            total_steps=total_steps,
            found_count=0,
            logs=[],
            started_at=datetime.now().isoformat()
        )

        try:
            radius = self.config.location.radius_km
            max_price = self.config.hardware.max_price_brl
            self._log_progress(
                1, total_steps,
                f"Configurando busca (Raio: {radius}km de Veranópolis, Preço Máx: R$ {max_price:,.2f})",
                f"🚀 Iniciando varredura real: Raio {radius}km ao redor de Veranópolis - RS | Preço até R$ {max_price:,.2f}"
            )

            listings_dict: Dict[str, GPUListing] = {}

            if include_live_scrapers:
                # 1. OLX Regional (Caxias do Sul e Passo Fundo)
                if self.config.scrapers.olx.enabled:
                    regional_queries = ["RTX 3090", "RTX 4080", "RTX 4060 Ti 16GB", "Tesla", "Quadro", "RTX 16GB", "Titan"]
                    for idx, q in enumerate(regional_queries, 1):
                        self._log_progress(
                            2, total_steps,
                            f"Varrendo OLX Regional para '{q}'...",
                            f"🌐 OLX Regional ({idx}/{len(regional_queries)}): Buscando '{q}' em Caxias do Sul / Passo Fundo..."
                        )
                        try:
                            found = await self.olx_scraper.search_regional(q)
                            for item in found:
                                listings_dict[item.id] = item
                            self.progress.found_count = len(listings_dict)
                            if found:
                                self._log_progress(
                                    2, total_steps,
                                    f"OLX Regional: {len(found)} anúncios encontrados para '{q}'",
                                    f"✅ OLX: {len(found)} placa(s) encontrada(s) para '{q}' (Total até agora: {len(listings_dict)})"
                                )
                            await asyncio.sleep(self.config.scrapers.olx.request_delay_seconds)
                        except Exception as e:
                            logger.error(f"Erro ao varrer OLX para '{q}': {e}")

                    # 2. OLX Estadual (Placas de vídeo em todo o Rio Grande do Sul)
                    self._log_progress(
                        3, total_steps,
                        "Varrendo categoria de Placas de Vídeo no RS...",
                        "🌐 OLX RS: Buscando no catálogo de informática/placas de vídeo do estado do RS..."
                    )
                    try:
                        state_queries = ["3090", "4080", "tesla", "quadro", "16gb", "24gb"]
                        found_state = await self.olx_scraper.search_state_rs(state_queries)
                        for item in found_state:
                            listings_dict[item.id] = item
                        self.progress.found_count = len(listings_dict)
                        if found_state:
                            self._log_progress(
                                3, total_steps,
                                f"OLX RS: {len(found_state)} placas encontradas no estado",
                                f"✅ OLX Estadual: {len(found_state)} anúncio(s) adicionado(s) de GPUs no RS (Total: {len(listings_dict)})"
                            )
                    except Exception as e:
                        logger.error(f"Erro ao varrer OLX Estadual: {e}")

                # 3. Facebook Marketplace
                if self.config.scrapers.facebook.enabled:
                    self._log_progress(
                        4, total_steps,
                        "Consultando Facebook Marketplace...",
                        "🔎 Facebook Marketplace: Conectando sessão automatizada..."
                    )
                    fb_queries = ["RTX 3090", "RTX 4060 Ti 16GB", "Tesla P40", "Quadro"]
                    for q in fb_queries:
                        try:
                            self._log_progress(
                                4, total_steps,
                                f"Facebook Marketplace: buscando '{q}'...",
                                f"🔍 Facebook: Pesquisando '{q}' na região..."
                            )
                            found_fb = await self.facebook_scraper.search_regional(q)
                            for item in found_fb:
                                listings_dict[item.id] = item
                            self.progress.found_count = len(listings_dict)
                            if found_fb:
                                self._log_progress(
                                    4, total_steps,
                                    f"Facebook: {len(found_fb)} encontrados para '{q}'",
                                    f"✅ Facebook: {len(found_fb)} anúncio(s) encontrado(s) para '{q}'"
                                )
                            await asyncio.sleep(1.5)
                        except Exception as e:
                            logger.debug(f"Facebook Marketplace: {e}")

            all_raw = list(listings_dict.values())

            # 4. Cálculo de distâncias geodésicas (Haversine) a partir de Veranópolis
            self._log_progress(
                5, total_steps,
                "Calculando distâncias geodésicas para cada cidade...",
                f"📍 Calculando distâncias até Veranópolis (-28.9358, -51.5503) e filtrando por raio de {radius}km..."
            )
            from src.geo import get_city_distance_from_center
            filtered_by_location = []
            for item in all_raw:
                if item.distance_km is None and item.city:
                    item.distance_km = get_city_distance_from_center(item.city)

                # Aplica filtro de preço máximo configurado pelo usuário
                if item.price > self.config.hardware.max_price_brl:
                    continue

                # Aplica filtro de raio configurado pelo usuário
                if item.distance_km is not None and item.distance_km > self.config.location.radius_km:
                    continue

                filtered_by_location.append(item)

            # 5. Atribuição de Capacidade Computacional (FP32 TFLOPS - TechPowerUp/NVIDIA)
            self._log_progress(
                6, total_steps,
                "Atribuindo benchmarks de capacidade computacional (TFLOPS)...",
                "⚡ Enriquecendo anúncios com capacidade computacional FP32 TFLOPS (NVIDIA / TechPowerUp)..."
            )
            for item in filtered_by_location:
                c_data = get_gpu_compute_data(item.detected_model)
                item.compute_tflops = c_data["compute_tflops"]
                item.memory_bandwidth_gbs = c_data["memory_bandwidth_gbs"]
                item.architecture = c_data["architecture"]

            # 6. Benchmark Nacional de Preços no Brasil
            if self.config.national_benchmark.enabled and filtered_by_location:
                unique_models = set(
                    item.detected_model 
                    for item in filtered_by_location 
                    if item.detected_model != "Desconhecido"
                )
                for model in unique_models:
                    self._log_progress(
                        7, total_steps,
                        f"Pesquisando preços médios no Brasil para {model}...",
                        f"🇧🇷 Benchmark Nacional: Buscando preços médios no mercado brasileiro para {model}..."
                    )
                    try:
                        national_prices = await self.olx_scraper.search_national(model)
                        if national_prices:
                            self.benchmark_engine.update_model_stats(model, national_prices)
                            self._log_progress(
                                7, total_steps,
                                f"Benchmark atualizado para {model}",
                                f"📊 Mediana calculada para {model}: R$ {self.benchmark_engine.get_stats_for_model(model).median_price:,.2f}"
                            )
                    except Exception as e:
                        logger.debug(f"Benchmark nacional não respondeu para {model}: {e}")

                filtered_by_location = self.benchmark_engine.enrich_all(filtered_by_location)

            # 7. Detecção e destaque de outliers com IQR por modelo idêntico
            filtered_by_location = OutlierDetector.detect_outliers_iqr(filtered_by_location)

            # Salva exclusivamente os dados reais
            self.save_listings_to_disk(filtered_by_location)
            self.last_summary = self.calculate_summary(filtered_by_location)

            self.progress.is_scanning = False
            self.progress.finished_at = datetime.now().isoformat()
            self.progress.found_count = len(filtered_by_location)
            self._log_progress(
                total_steps, total_steps,
                f"Varredura concluída! {len(filtered_by_location)} placas reais encontradas.",
                f"🏁 Varredura finalizada com sucesso! {len(filtered_by_location)} anúncio(s) real(is) dentro dos filtros."
            )

            return self.last_summary

        except Exception as e:
            logger.error(f"Erro geral durante varredura: {e}")
            self.progress.is_scanning = False
            self.progress.finished_at = datetime.now().isoformat()
            self._log_progress(
                total_steps, total_steps,
                "Erro durante a varredura",
                f"❌ Erro durante a varredura: {e}"
            )
            return self.last_summary or ScanSummary()

        finally:
            self.is_scanning = False
