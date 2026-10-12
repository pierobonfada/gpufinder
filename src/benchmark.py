import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from src.config import NationalBenchmarkConfig
from src.models import GPUListing, NationalStats, PriceClassification

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "benchmark_cache.json"

# Valores de referência nacional de mercado de seminovos/usados no Brasil
# Atualizados dinamicamente pelo scraper nacional quando online
DEFAULT_NATIONAL_BENCHMARKS: Dict[str, Dict] = {
    "RTX 3090": {
        "min": 3400.0, "median": 4200.0, "mean": 4290.0, "max": 5300.0,
        "q1": 3800.0, "q3": 4650.0, "count": 28
    },
    "RTX 3090 Ti": {
        "min": 4200.0, "median": 4850.0, "mean": 4920.0, "max": 5800.0,
        "q1": 4500.0, "q3": 5300.0, "count": 14
    },
    "RTX 4080": {
        "min": 5200.0, "median": 6200.0, "mean": 6150.0, "max": 7200.0,
        "q1": 5600.0, "q3": 6700.0, "count": 22
    },
    "RTX 4070 Ti Super": {
        "min": 4300.0, "median": 4850.0, "mean": 4890.0, "max": 5500.0,
        "q1": 4600.0, "q3": 5150.0, "count": 18
    },
    "RTX 4060 Ti 16GB": {
        "min": 2300.0, "median": 2750.0, "mean": 2780.0, "max": 3350.0,
        "q1": 2550.0, "q3": 3000.0, "count": 35
    },
    "Titan RTX": {
        "min": 3900.0, "median": 4700.0, "mean": 4800.0, "max": 5800.0,
        "q1": 4300.0, "q3": 5250.0, "count": 8
    },
    "Tesla P40": {
        "min": 1450.0, "median": 1950.0, "mean": 2010.0, "max": 2750.0,
        "q1": 1700.0, "q3": 2300.0, "count": 19
    },
    "Tesla M40": {
        "min": 850.0, "median": 1250.0, "mean": 1280.0, "max": 1750.0,
        "q1": 1050.0, "q3": 1450.0, "count": 15
    },
    "Tesla K80": {
        "min": 580.0, "median": 850.0, "mean": 890.0, "max": 1300.0,
        "q1": 720.0, "q3": 1020.0, "count": 12
    },
    "Tesla V100": {
        "min": 2900.0, "median": 3800.0, "mean": 3950.0, "max": 4900.0,
        "q1": 3400.0, "q3": 4400.0, "count": 11
    },
    "Tesla T4": {
        "min": 2100.0, "median": 2650.0, "mean": 2700.0, "max": 3400.0,
        "q1": 2400.0, "q3": 2950.0, "count": 9
    },
    "Quadro P5000": {
        "min": 1800.0, "median": 2350.0, "mean": 2400.0, "max": 3100.0,
        "q1": 2100.0, "q3": 2700.0, "count": 14
    },
    "Quadro P6000": {
        "min": 3300.0, "median": 4100.0, "mean": 4180.0, "max": 5100.0,
        "q1": 3700.0, "q3": 4650.0, "count": 10
    },
    "Quadro M6000": {
        "min": 2000.0, "median": 2600.0, "mean": 2680.0, "max": 3500.0,
        "q1": 2300.0, "q3": 3050.0, "count": 7
    },
    "Quadro RTX 5000": {
        "min": 2800.0, "median": 3500.0, "mean": 3580.0, "max": 4500.0,
        "q1": 3150.0, "q3": 3950.0, "count": 13
    },
    "Quadro RTX 6000": {
        "min": 4100.0, "median": 4950.0, "mean": 5100.0, "max": 6400.0,
        "q1": 4550.0, "q3": 5600.0, "count": 9
    },
    "RTX A4000": {
        "min": 3200.0, "median": 3850.0, "mean": 3920.0, "max": 4750.0,
        "q1": 3550.0, "q3": 4300.0, "count": 16
    },
    "RTX A4500": {
        "min": 4200.0, "median": 4950.0, "mean": 5050.0, "max": 6100.0,
        "q1": 4600.0, "q3": 5500.0, "count": 6
    },
    "Quadro GV100": {
        "min": 4500.0, "median": 5500.0, "mean": 5600.0, "max": 6800.0,
        "q1": 4950.0, "q3": 6200.0, "count": 4
    }
}

class BenchmarkEngine:
    def __init__(self, config: NationalBenchmarkConfig):
        self.config = config
        self.cache: Dict[str, NationalStats] = {}
        self.load_cache()

    def load_cache(self) -> None:
        """Carrega cache persistido do disco ou inicializa com valores de base."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    self.cache[k] = NationalStats.model_validate(v)
                return
            except Exception as e:
                logger.warning(f"Erro ao carregar benchmark cache: {e}")

        # Popula com benchmarks padrão
        for model, st in DEFAULT_NATIONAL_BENCHMARKS.items():
            iqr = st["q3"] - st["q1"]
            self.cache[model] = NationalStats(
                model_name=model,
                count=st["count"],
                min_price=st["min"],
                median_price=st["median"],
                mean_price=st["mean"],
                max_price=st["max"],
                q1_price=st["q1"],
                q3_price=st["q3"],
                iqr=iqr,
                last_updated=datetime.now().isoformat()
            )

    def save_cache(self) -> None:
        """Salva cache no disco."""
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.model_dump() for k, v in self.cache.items()}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_stats_for_model(self, model_name: str) -> Optional[NationalStats]:
        """Obtém estatísticas nacionais consolidadas para um modelo."""
        if model_name in self.cache:
            return self.cache[model_name]

        # Tenta casamento parcial
        for k, v in self.cache.items():
            if k.lower() in model_name.lower() or model_name.lower() in k.lower():
                return v

        return None

    def update_model_stats(self, model_name: str, national_prices: List[float]) -> NationalStats:
        """Atualiza estatísticas com dados coletados ao vivo de todo o Brasil."""
        valid_prices = [p for p in national_prices if p > 100]
        if not valid_prices:
            # Retorna o existente se houver
            existing = self.get_stats_for_model(model_name)
            if existing:
                return existing
            return NationalStats(model_name=model_name)

        q1 = float(np.percentile(valid_prices, 25))
        median = float(np.median(valid_prices))
        q3 = float(np.percentile(valid_prices, 75))
        stats = NationalStats(
            model_name=model_name,
            count=len(valid_prices),
            min_price=float(min(valid_prices)),
            median_price=median,
            mean_price=float(np.mean(valid_prices)),
            max_price=float(max(valid_prices)),
            q1_price=q1,
            q3_price=q3,
            iqr=q3 - q1,
            last_updated=datetime.now().isoformat()
        )
        self.cache[model_name] = stats
        self.save_cache()
        return stats

    def enrich_listing(self, listing: GPUListing) -> GPUListing:
        """
        Enriquece um anúncio local com a comparação detalhada contra o mercado de todo o Brasil.
        Calcula percentual de economia/ágio e classifica como Barata, Na Média ou Cara.
        """
        stats = self.get_stats_for_model(listing.detected_model)
        if not stats or stats.median_price <= 0:
            listing.price_classification = PriceClassification.UNKNOWN
            return listing

        listing.national_benchmark = stats
        median = stats.median_price
        diff_brl = listing.price - median
        diff_pct = (diff_brl / median) * 100.0

        listing.price_diff_brl = round(diff_brl, 2)
        listing.price_diff_percent = round(diff_pct, 1)

        t = self.config.thresholds

        # Classificação baseada no percentual vs mediana nacional
        if diff_pct <= t.great_deal_percent:
            listing.price_classification = PriceClassification.OPPORTUNITY
        elif diff_pct <= t.cheap_percent:
            listing.price_classification = PriceClassification.CHEAP
        elif diff_pct >= t.very_expensive_percent:
            listing.price_classification = PriceClassification.VERY_EXPENSIVE
        elif diff_pct >= t.expensive_percent:
            listing.price_classification = PriceClassification.EXPENSIVE
        else:
            listing.price_classification = PriceClassification.AVERAGE

        return listing

    def enrich_all(self, listings: List[GPUListing]) -> List[GPUListing]:
        """Aplica o enriquecimento de benchmark para todos os anúncios."""
        for item in listings:
            self.enrich_listing(item)
        return listings
