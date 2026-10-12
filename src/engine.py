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
            i for i in working if i.price_diff_percent is not None and i.price_diff_percent <= -5.0
        ]
        if working_with_benchmark:
            best_deal = min(working_with_benchmark, key=lambda x: x.price_diff_percent)

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

    def filter_listings(
        self,
        listings: List[GPUListing],
        min_vram_gb: Optional[int] = None,
        max_vram_gb: Optional[int] = None,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        radius_km: Optional[float] = None,
        condition: Optional[str] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None,
        outliers_only: bool = False
    ) -> List[GPUListing]:
        """Filtra instantaneamente os anúncios do banco de dados de acordo com os parâmetros do usuário."""
        result = []
        for item in listings:
            # 1. Filtro de Range de Memória VRAM (de X a Y GB)
            if min_vram_gb is not None and item.detected_vram_gb < min_vram_gb:
                continue
            if max_vram_gb is not None and item.detected_vram_gb > max_vram_gb:
                continue

            # 2. Filtro de Preço
            if max_price is not None and item.price > max_price:
                continue
            if min_price is not None and item.price < min_price:
                continue

            # 3. Filtro de Raio
            if radius_km is not None and item.distance_km is not None and item.distance_km > radius_km:
                continue

            # 4. Condição
            if condition and condition != "all" and item.condition.value != condition:
                continue

            # 5. Plataforma
            if platform and platform != "all" and item.platform.lower() != platform.lower():
                continue

            # 6. Outliers
            if outliers_only and not item.is_outlier:
                continue

            # 7. Busca por texto
            if search:
                s = search.lower().strip()
                text_corpus = f"{item.title} {item.city} {item.detected_model} {item.platform}".lower()
                if s not in text_corpus:
                    continue

            result.append(item)
        return result

    async def run_scan(
        self, 
        include_live_scrapers: bool = True,
        center_city: Optional[str] = None,
        custom_radius_km: Optional[float] = None,
        custom_max_price: Optional[float] = None
    ) -> ScanSummary:
        """
        Executa a varredura ao vivo da web para a cidade e raio especificados,
        alimentando o banco de dados com TODOS os anúncios reais da NVIDIA.
        """
        if self.is_scanning:
            logger.warning("Varredura já em andamento.")
            return self.last_summary or ScanSummary()

        self.is_scanning = True
        total_steps = 7

        from src.geo import get_city_coordinates, get_city_distance_from_center
        if center_city:
            self.config.location.center_city = center_city
            lat, lon = get_city_coordinates(center_city)
            self.config.location.latitude = lat
            self.config.location.longitude = lon

        if custom_radius_km is not None and custom_radius_km > 0:
            self.config.location.radius_km = custom_radius_km

        city = self.config.location.center_city
        radius = self.config.location.radius_km
        lat = self.config.location.latitude
        lon = self.config.location.longitude

        self.progress = ScanProgress(
            is_scanning=True,
            current_task=f"Iniciando varredura na web ao redor de {city} (Raio {radius}km)...",
            current_step=1,
            total_steps=total_steps,
            found_count=0,
            logs=[],
            started_at=datetime.now().isoformat()
        )

        try:
            self._log_progress(
                1, total_steps,
                f"Configurando busca ao redor de {city} (Raio {radius}km)...",
                f"🚀 Iniciando varredura web completa: Centro em {city} ({lat}, {lon}) | Raio de {radius}km"
            )

            # Carrega banco existente para fazer merge sem perder anúncios já conhecidos
            existing_items = {i.id: i for i in self.load_listings_from_disk()}
            listings_dict: Dict[str, GPUListing] = {}

            if include_live_scrapers:
                # 1. OLX Regional (regiões circunvizinhas)
                if self.config.scrapers.olx.enabled:
                    self._log_progress(
                        2, total_steps,
                        f"Varrendo OLX Regional para 'nvidia' ao redor de {city}...",
                        f"🌐 OLX Regional: Buscando anúncios de 'nvidia' (páginas 1 a 3) e inspecionando descrições..."
                    )
                    try:
                        found = await self.olx_scraper.search_regional("nvidia", max_pages=3)
                        for item in found:
                            listings_dict[item.id] = item
                        self.progress.found_count = len(listings_dict)
                        self._log_progress(
                            2, total_steps,
                            f"OLX Regional: {len(found)} anúncios NVIDIA encontrados",
                            f"✅ OLX: {len(found)} placa(s) NVIDIA encontrada(s) no raio de {radius}km de {city} (Total: {len(listings_dict)})"
                        )
                    except Exception as e:
                        logger.error(f"Erro ao varrer OLX para 'nvidia': {e}")

                    # 2. OLX Estadual (Placas de vídeo no Rio Grande do Sul)
                    self._log_progress(
                        3, total_steps,
                        "Varrendo OLX RS categoria Placas de Vídeo para 'nvidia'...",
                        "🌐 OLX RS: Buscando 'nvidia' na categoria de informática/placas de vídeo..."
                    )
                    try:
                        found_state = await self.olx_scraper.search_state_rs(["nvidia"])
                        for item in found_state:
                            listings_dict[item.id] = item
                        self.progress.found_count = len(listings_dict)
                        self._log_progress(
                            3, total_steps,
                            f"OLX RS: {len(found_state)} placas adicionadas",
                            f"✅ OLX Estadual: {len(found_state)} anúncio(s) no raio de {radius}km de {city} (Total: {len(listings_dict)})"
                        )
                    except Exception as e:
                        logger.error(f"Erro ao varrer OLX Estadual: {e}")

                # 3. Facebook Marketplace
                if self.config.scrapers.facebook.enabled:
                    self._log_progress(
                        4, total_steps,
                        f"Consultando Facebook Marketplace RS ao redor de {city}...",
                        f"🔎 Facebook Marketplace: Conectando sessão automatizada e pesquisando 'nvidia'..."
                    )
                    try:
                        found_fb = await self.facebook_scraper.search_regional("nvidia")
                        for item in found_fb:
                            listings_dict[item.id] = item
                        self.progress.found_count = len(listings_dict)
                        self._log_progress(
                            4, total_steps,
                            f"Facebook: {len(found_fb)} encontrados para 'nvidia'",
                            f"✅ Facebook: {len(found_fb)} anúncio(s) no raio de {radius}km de {city} (Total: {len(listings_dict)})"
                        )
                    except Exception as e:
                        logger.debug(f"Facebook Marketplace: {e}")

            all_raw = list(listings_dict.values())

            # 4. Cálculo de distâncias geodésicas (Haversine) a partir da cidade central
            self._log_progress(
                5, total_steps,
                f"Calculando distâncias geodésicas até {city}...",
                f"📍 Calculando distâncias até {city} ({lat}, {lon}) e aplicando raio de {radius}km..."
            )
            filtered_by_location = []
            for item in all_raw:
                if item.distance_km is None and item.city:
                    item.distance_km = get_city_distance_from_center(item.city, lat, lon)

                # Descarta anúncios fora do raio de busca da cidade selecionada
                if item.distance_km is None or item.distance_km > self.config.location.radius_km:
                    continue

                filtered_by_location.append(item)

            # 5. Atribuição de Capacidade Computacional (FP32 TFLOPS - TechPowerUp/NVIDIA)
            self._log_progress(
                6, total_steps,
                "Atribuindo benchmarks de capacidade computacional (TFLOPS)...",
                "⚡ Enriquecendo banco de dados com capacidade computacional FP32 TFLOPS (NVIDIA / TechPowerUp)..."
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
