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
    # --- RTX 50 Series ---
    "RTX 5090": { "min": 15000.0, "median": 18500.0, "mean": 18900.0, "max": 23000.0, "q1": 17000.0, "q3": 20500.0, "count": 10, "vram_gb": 32 },
    "RTX 5080": { "min": 8500.0, "median": 9800.0, "mean": 10000.0, "max": 12500.0, "q1": 9200.0, "q3": 10800.0, "count": 12, "vram_gb": 16 },
    "RTX 5070 Ti": { "min": 6500.0, "median": 7400.0, "mean": 7500.0, "max": 8800.0, "q1": 6900.0, "q3": 8100.0, "count": 10, "vram_gb": 16 },
    "RTX 5070": { "min": 4800.0, "median": 5600.0, "mean": 5700.0, "max": 6800.0, "q1": 5200.0, "q3": 6100.0, "count": 15, "vram_gb": 12 },
    "RTX 5060 Ti 16GB": { "min": 3300.0, "median": 3750.0, "mean": 3800.0, "max": 4500.0, "q1": 3500.0, "q3": 4100.0, "count": 15, "vram_gb": 16 },
    "RTX 5060 Ti 8GB": { "min": 2600.0, "median": 3050.0, "mean": 3100.0, "max": 3700.0, "q1": 2850.0, "q3": 3350.0, "count": 20, "vram_gb": 8 },
    "RTX 5060 Ti": { "min": 2600.0, "median": 3050.0, "mean": 3100.0, "max": 3700.0, "q1": 2850.0, "q3": 3350.0, "count": 20, "vram_gb": 8 },
    "RTX 5060 12GB": { "min": 2400.0, "median": 2800.0, "mean": 2850.0, "max": 3400.0, "q1": 2600.0, "q3": 3100.0, "count": 18, "vram_gb": 12 },
    "RTX 5060 8GB": { "min": 1950.0, "median": 2300.0, "mean": 2350.0, "max": 2800.0, "q1": 2100.0, "q3": 2550.0, "count": 25, "vram_gb": 8 },
    "RTX 5060": { "min": 1950.0, "median": 2300.0, "mean": 2350.0, "max": 2800.0, "q1": 2100.0, "q3": 2550.0, "count": 25, "vram_gb": 8 },

    # --- RTX 40 Series ---
    "RTX 4090": { "min": 9800.0, "median": 11800.0, "mean": 11950.0, "max": 14500.0, "q1": 10800.0, "q3": 12800.0, "count": 35, "vram_gb": 24 },
    "RTX 4080 Super": { "min": 5800.0, "median": 6600.0, "mean": 6650.0, "max": 7800.0, "q1": 6200.0, "q3": 7100.0, "count": 25, "vram_gb": 16 },
    "RTX 4080": { "min": 5200.0, "median": 6100.0, "mean": 6150.0, "max": 7200.0, "q1": 5600.0, "q3": 6600.0, "count": 30, "vram_gb": 16 },
    "RTX 4070 Ti Super": { "min": 4400.0, "median": 4900.0, "mean": 4950.0, "max": 5800.0, "q1": 4650.0, "q3": 5300.0, "count": 28, "vram_gb": 16 },
    "RTX 4070 Ti": { "min": 4000.0, "median": 4500.0, "mean": 4550.0, "max": 5300.0, "q1": 4250.0, "q3": 4800.0, "count": 26, "vram_gb": 12 },
    "RTX 4070 Super": { "min": 3500.0, "median": 3950.0, "mean": 4000.0, "max": 4700.0, "q1": 3700.0, "q3": 4300.0, "count": 32, "vram_gb": 12 },
    "RTX 4070": { "min": 2900.0, "median": 3400.0, "mean": 3450.0, "max": 4100.0, "q1": 3150.0, "q3": 3700.0, "count": 38, "vram_gb": 12 },
    "RTX 4060 Ti 16GB": { "min": 2400.0, "median": 2750.0, "mean": 2780.0, "max": 3300.0, "q1": 2550.0, "q3": 2950.0, "count": 30, "vram_gb": 16 },
    "RTX 4060 Ti 8GB": { "min": 2000.0, "median": 2350.0, "mean": 2380.0, "max": 2850.0, "q1": 2200.0, "q3": 2550.0, "count": 45, "vram_gb": 8 },
    "RTX 4060 Ti": { "min": 2000.0, "median": 2350.0, "mean": 2380.0, "max": 2850.0, "q1": 2200.0, "q3": 2550.0, "count": 45, "vram_gb": 8 },
    "RTX 4060": { "min": 1500.0, "median": 1800.0, "mean": 1820.0, "max": 2250.0, "q1": 1650.0, "q3": 1980.0, "count": 55, "vram_gb": 8 },

    # --- RTX 30 Series ---
    "RTX 3090 Ti": { "min": 4200.0, "median": 4850.0, "mean": 4920.0, "max": 5800.0, "q1": 4500.0, "q3": 5300.0, "count": 18, "vram_gb": 24 },
    "RTX 3090": { "min": 3400.0, "median": 4200.0, "mean": 4250.0, "max": 5200.0, "q1": 3800.0, "q3": 4600.0, "count": 42, "vram_gb": 24 },
    "RTX 3080 Ti": { "min": 2700.0, "median": 3150.0, "mean": 3200.0, "max": 3850.0, "q1": 2900.0, "q3": 3450.0, "count": 30, "vram_gb": 12 },
    "RTX 3080 12GB": { "min": 2400.0, "median": 2800.0, "mean": 2850.0, "max": 3400.0, "q1": 2600.0, "q3": 3100.0, "count": 20, "vram_gb": 12 },
    "RTX 3080 10GB": { "min": 2200.0, "median": 2650.0, "mean": 2680.0, "max": 3300.0, "q1": 2400.0, "q3": 2900.0, "count": 50, "vram_gb": 10 },
    "RTX 3080": { "min": 2200.0, "median": 2650.0, "mean": 2680.0, "max": 3300.0, "q1": 2400.0, "q3": 2900.0, "count": 50, "vram_gb": 10 },
    "RTX 3070 Ti": { "min": 1900.0, "median": 2250.0, "mean": 2280.0, "max": 2750.0, "q1": 2050.0, "q3": 2480.0, "count": 45, "vram_gb": 8 },
    "RTX 3070": { "min": 1650.0, "median": 1950.0, "mean": 1980.0, "max": 2450.0, "q1": 1800.0, "q3": 2150.0, "count": 60, "vram_gb": 8 },
    "RTX 3060 Ti": { "min": 1350.0, "median": 1650.0, "mean": 1680.0, "max": 2100.0, "q1": 1500.0, "q3": 1850.0, "count": 65, "vram_gb": 8 },
    "RTX 3060 12GB": { "min": 1250.0, "median": 1500.0, "mean": 1520.0, "max": 1850.0, "q1": 1380.0, "q3": 1650.0, "count": 70, "vram_gb": 12 },
    "RTX 3060 8GB": { "min": 950.0, "median": 1150.0, "mean": 1180.0, "max": 1400.0, "q1": 1050.0, "q3": 1280.0, "count": 30, "vram_gb": 8 },
    "RTX 3060": { "min": 1250.0, "median": 1500.0, "mean": 1520.0, "max": 1850.0, "q1": 1380.0, "q3": 1650.0, "count": 80, "vram_gb": 12 },
    "RTX 3050 8GB": { "min": 850.0, "median": 1050.0, "mean": 1070.0, "max": 1350.0, "q1": 950.0, "q3": 1180.0, "count": 35, "vram_gb": 8 },
    "RTX 3050 6GB": { "min": 680.0, "median": 850.0, "mean": 870.0, "max": 1100.0, "q1": 750.0, "q3": 950.0, "count": 25, "vram_gb": 6 },
    "RTX 3050": { "min": 850.0, "median": 1050.0, "mean": 1070.0, "max": 1350.0, "q1": 950.0, "q3": 1180.0, "count": 40, "vram_gb": 8 },

    # --- RTX 20 Series ---
    "RTX 2080 Ti": { "min": 1700.0, "median": 2100.0, "mean": 2150.0, "max": 2650.0, "q1": 1900.0, "q3": 2350.0, "count": 25, "vram_gb": 11 },
    "RTX 2080 Super": { "min": 1400.0, "median": 1700.0, "mean": 1740.0, "max": 2150.0, "q1": 1550.0, "q3": 1900.0, "count": 22, "vram_gb": 8 },
    "RTX 2080": { "min": 1250.0, "median": 1500.0, "mean": 1530.0, "max": 1900.0, "q1": 1380.0, "q3": 1680.0, "count": 28, "vram_gb": 8 },
    "RTX 2070 Super": { "min": 1150.0, "median": 1400.0, "mean": 1420.0, "max": 1750.0, "q1": 1280.0, "q3": 1550.0, "count": 35, "vram_gb": 8 },
    "RTX 2070": { "min": 1050.0, "median": 1250.0, "mean": 1270.0, "max": 1580.0, "q1": 1150.0, "q3": 1390.0, "count": 30, "vram_gb": 8 },
    "RTX 2060 Super": { "min": 950.0, "median": 1150.0, "mean": 1180.0, "max": 1450.0, "q1": 1050.0, "q3": 1280.0, "count": 40, "vram_gb": 8 },
    "RTX 2060 12GB": { "min": 950.0, "median": 1150.0, "mean": 1180.0, "max": 1450.0, "q1": 1050.0, "q3": 1280.0, "count": 25, "vram_gb": 12 },
    "RTX 2060 6GB": { "min": 780.0, "median": 950.0, "mean": 970.0, "max": 1250.0, "q1": 870.0, "q3": 1080.0, "count": 45, "vram_gb": 6 },
    "RTX 2060": { "min": 780.0, "median": 950.0, "mean": 970.0, "max": 1250.0, "q1": 870.0, "q3": 1080.0, "count": 55, "vram_gb": 6 },

    # --- GTX 16 Series ---
    "GTX 1660 Ti": { "min": 650.0, "median": 780.0, "mean": 795.0, "max": 1000.0, "q1": 720.0, "q3": 870.0, "count": 32, "vram_gb": 6 },
    "GTX 1660 Super": { "min": 620.0, "median": 750.0, "mean": 765.0, "max": 980.0, "q1": 690.0, "q3": 840.0, "count": 48, "vram_gb": 6 },
    "GTX 1660": { "min": 550.0, "median": 680.0, "mean": 690.0, "max": 880.0, "q1": 610.0, "q3": 760.0, "count": 30, "vram_gb": 6 },
    "GTX 1650 Super": { "min": 480.0, "median": 600.0, "mean": 615.0, "max": 780.0, "q1": 540.0, "q3": 680.0, "count": 28, "vram_gb": 4 },
    "GTX 1650": { "min": 400.0, "median": 520.0, "mean": 530.0, "max": 690.0, "q1": 460.0, "q3": 590.0, "count": 50, "vram_gb": 4 },

    # --- GTX 10 Series ---
    "GTX 1080 Ti": { "min": 1050.0, "median": 1350.0, "mean": 1370.0, "max": 1750.0, "q1": 1200.0, "q3": 1520.0, "count": 24, "vram_gb": 11 },
    "GTX 1080": { "min": 780.0, "median": 950.0, "mean": 970.0, "max": 1250.0, "q1": 870.0, "q3": 1080.0, "count": 30, "vram_gb": 8 },
    "GTX 1070 Ti": { "min": 700.0, "median": 850.0, "mean": 870.0, "max": 1100.0, "q1": 780.0, "q3": 960.0, "count": 26, "vram_gb": 8 },
    "GTX 1070": { "min": 600.0, "median": 750.0, "mean": 765.0, "max": 980.0, "q1": 680.0, "q3": 840.0, "count": 38, "vram_gb": 8 },
    "GTX 1060 6GB": { "min": 480.0, "median": 580.0, "mean": 595.0, "max": 750.0, "q1": 530.0, "q3": 650.0, "count": 45, "vram_gb": 6 },
    "GTX 1060 3GB": { "min": 320.0, "median": 420.0, "mean": 430.0, "max": 550.0, "q1": 370.0, "q3": 480.0, "count": 35, "vram_gb": 3 },
    "GTX 1060": { "min": 480.0, "median": 580.0, "mean": 595.0, "max": 750.0, "q1": 530.0, "q3": 650.0, "count": 50, "vram_gb": 6 },
    "GTX 1050 Ti": { "min": 320.0, "median": 420.0, "mean": 430.0, "max": 560.0, "q1": 370.0, "q3": 480.0, "count": 60, "vram_gb": 4 },
    "GTX 1050": { "min": 250.0, "median": 340.0, "mean": 350.0, "max": 450.0, "q1": 290.0, "q3": 390.0, "count": 40, "vram_gb": 2 },
    "GT 1030": { "min": 180.0, "median": 260.0, "mean": 270.0, "max": 380.0, "q1": 220.0, "q3": 310.0, "count": 35, "vram_gb": 2 },

    # --- Clássicas e Profissionais / Datacenter ---
    "GTX 980 Ti": { "min": 580.0, "median": 720.0, "mean": 740.0, "max": 950.0, "q1": 650.0, "q3": 820.0, "count": 15, "vram_gb": 6 },
    "GTX 980": { "min": 350.0, "median": 450.0, "mean": 465.0, "max": 600.0, "q1": 400.0, "q3": 520.0, "count": 22, "vram_gb": 4 },
    "GTX 970": { "min": 350.0, "median": 450.0, "mean": 465.0, "max": 600.0, "q1": 400.0, "q3": 520.0, "count": 22, "vram_gb": 4 },
    "GTX 750 Ti": { "min": 180.0, "median": 250.0, "mean": 260.0, "max": 350.0, "q1": 210.0, "q3": 290.0, "count": 30, "vram_gb": 2 },
    "GT 730 4GB": { "min": 180.0, "median": 250.0, "mean": 260.0, "max": 350.0, "q1": 210.0, "q3": 290.0, "count": 20, "vram_gb": 4 },
    "GT 730 2GB": { "min": 120.0, "median": 180.0, "mean": 190.0, "max": 260.0, "q1": 150.0, "q3": 210.0, "count": 30, "vram_gb": 2 },
    "GT 730": { "min": 150.0, "median": 220.0, "mean": 230.0, "max": 320.0, "q1": 180.0, "q3": 260.0, "count": 40, "vram_gb": 2 },
    "Titan RTX": { "min": 3900.0, "median": 4700.0, "mean": 4800.0, "max": 5800.0, "q1": 4300.0, "q3": 5250.0, "count": 8, "vram_gb": 24 },
    "Tesla P40": { "min": 1450.0, "median": 1950.0, "mean": 2010.0, "max": 2750.0, "q1": 1700.0, "q3": 2300.0, "count": 19, "vram_gb": 24 },
    "Tesla M40 24GB": { "min": 1100.0, "median": 1450.0, "mean": 1480.0, "max": 1950.0, "q1": 1250.0, "q3": 1700.0, "count": 12, "vram_gb": 24 },
    "Tesla M40 12GB": { "min": 750.0, "median": 950.0, "mean": 980.0, "max": 1300.0, "q1": 850.0, "q3": 1100.0, "count": 10, "vram_gb": 12 },
    "Tesla M40": { "min": 850.0, "median": 1250.0, "mean": 1280.0, "max": 1750.0, "q1": 1050.0, "q3": 1450.0, "count": 15, "vram_gb": 24 },
    "Tesla K80": { "min": 580.0, "median": 850.0, "mean": 890.0, "max": 1300.0, "q1": 720.0, "q3": 1020.0, "count": 12, "vram_gb": 24 },
    "Tesla V100 32GB": { "min": 3800.0, "median": 4800.0, "mean": 4900.0, "max": 6200.0, "q1": 4200.0, "q3": 5500.0, "count": 8, "vram_gb": 32 },
    "Tesla V100 16GB": { "min": 2900.0, "median": 3800.0, "mean": 3950.0, "max": 4900.0, "q1": 3400.0, "q3": 4400.0, "count": 11, "vram_gb": 16 },
    "Tesla V100": { "min": 2900.0, "median": 3800.0, "mean": 3950.0, "max": 4900.0, "q1": 3400.0, "q3": 4400.0, "count": 11, "vram_gb": 16 },
    "Tesla T4": { "min": 2100.0, "median": 2650.0, "mean": 2700.0, "max": 3400.0, "q1": 2400.0, "q3": 2950.0, "count": 9, "vram_gb": 16 },
    "Quadro P5000": { "min": 1800.0, "median": 2350.0, "mean": 2400.0, "max": 3100.0, "q1": 2100.0, "q3": 2700.0, "count": 14, "vram_gb": 16 },
    "Quadro P6000": { "min": 3300.0, "median": 4100.0, "mean": 4180.0, "max": 5100.0, "q1": 3700.0, "q3": 4650.0, "count": 10, "vram_gb": 24 },
    "Quadro M6000": { "min": 2000.0, "median": 2600.0, "mean": 2680.0, "max": 3500.0, "q1": 2300.0, "q3": 3050.0, "count": 7, "vram_gb": 24 },
    "Quadro RTX 5000": { "min": 2800.0, "median": 3500.0, "mean": 3580.0, "max": 4500.0, "q1": 3150.0, "q3": 3950.0, "count": 13, "vram_gb": 16 },
    "Quadro RTX 6000": { "min": 4100.0, "median": 4950.0, "mean": 5100.0, "max": 6400.0, "q1": 4550.0, "q3": 5600.0, "count": 9, "vram_gb": 24 },
    "RTX A4000": { "min": 3200.0, "median": 3850.0, "mean": 3920.0, "max": 4750.0, "q1": 3550.0, "q3": 4300.0, "count": 16, "vram_gb": 16 },
    "RTX A4500": { "min": 4200.0, "median": 4950.0, "mean": 5050.0, "max": 6100.0, "q1": 4600.0, "q3": 5500.0, "count": 6, "vram_gb": 20 },
    "Quadro GV100": { "min": 4500.0, "median": 5500.0, "mean": 5600.0, "max": 6800.0, "q1": 4950.0, "q3": 6200.0, "count": 4, "vram_gb": 32 },
    "T1000 8GB": { "min": 1100.0, "median": 1400.0, "mean": 1430.0, "max": 1800.0, "q1": 1250.0, "q3": 1600.0, "count": 8, "vram_gb": 8 },
    "T1000 4GB": { "min": 700.0, "median": 900.0, "mean": 920.0, "max": 1200.0, "q1": 800.0, "q3": 1050.0, "count": 15, "vram_gb": 4 },
    "T1000": { "min": 700.0, "median": 900.0, "mean": 920.0, "max": 1200.0, "q1": 800.0, "q3": 1050.0, "count": 15, "vram_gb": 4 }
}

class BenchmarkEngine:
    def __init__(self, config: NationalBenchmarkConfig):
        self.config = config
        self.cache: Dict[str, NationalStats] = {}
        self.load_cache()

    def load_cache(self) -> None:
        """Carrega cache persistido do disco ou inicializa com valores de base."""
        # 1. Popula com os benchmarks padrão de referência (inclui variantes de VRAM)
        for model, st in DEFAULT_NATIONAL_BENCHMARKS.items():
            iqr = st["q3"] - st["q1"]
            self.cache[model] = NationalStats(
                model_name=model,
                vram_gb=st.get("vram_gb"),
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

        # 2. Carrega cache salvo no disco (se existir) mesclando atualizações
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    item = NationalStats.model_validate(v)
                    if item.vram_gb is None and k in DEFAULT_NATIONAL_BENCHMARKS:
                        item.vram_gb = DEFAULT_NATIONAL_BENCHMARKS[k].get("vram_gb")
                    self.cache[k] = item
            except Exception as e:
                logger.warning(f"Erro ao carregar benchmark cache: {e}")

    def save_cache(self) -> None:
        """Salva cache no disco."""
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.model_dump() for k, v in self.cache.items()}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_stats_for_model(self, model_name: str, vram_gb: Optional[int] = None) -> Optional[NationalStats]:
        """
        Obtém estatísticas nacionais consolidadas para um modelo e variante de VRAM específica.
        Diferencia estritamente placas com mesma nomenclatura e VRAMs diferentes (ex: 8GB vs 12GB vs 16GB).
        """
        if not model_name or model_name == "Desconhecido":
            return None

        import re

        # Se vram_gb foi informado explicitamente (> 0):
        if vram_gb and vram_gb > 0:
            vram_suffix = f"{vram_gb}GB"

            # 1. Chave exata com VRAM (ex: "RTX 5060 8GB" ou "RTX 4060 Ti 16GB")
            exact_key = f"{model_name} {vram_suffix}"
            if exact_key in self.cache:
                return self.cache[exact_key]

            # 2. Se o próprio model_name já tem a VRAM inclusa e confere com vram_gb
            if model_name in self.cache and self.cache[model_name].vram_gb in (None, vram_gb):
                return self.cache[model_name]

            # 3. Procura no cache por item com o mesmo vram_gb e nome de modelo compatível
            norm_name = re.sub(r'[^a-z0-9]', '', model_name.lower())
            for k, v in self.cache.items():
                if v.vram_gb == vram_gb:
                    norm_k = re.sub(r'[^a-z0-9]', '', k.lower())
                    if norm_name in norm_k or norm_k in norm_name:
                        return v

        # Se não encontrou variante de VRAM específica ou vram_gb não foi fornecido:
        # 1. Match exato
        if model_name in self.cache:
            return self.cache[model_name]

        # 2. Match case-insensitive
        for k, v in self.cache.items():
            if k.lower() == model_name.lower():
                return v

        # 3. Match normalizado (sem espaços ou hífens)
        norm_input = re.sub(r'[^a-z0-9]', '', model_name.lower())
        for k, v in self.cache.items():
            if re.sub(r'[^a-z0-9]', '', k.lower()) == norm_input:
                return v

        # 4. Match estrito de sufixos (Ti e Super não podem colidir com modelos base)
        has_ti = bool(re.search(r'\bti\b', model_name, re.I))
        has_super = bool(re.search(r'\bsuper\b', model_name, re.I))
        for k, v in self.cache.items():
            k_has_ti = bool(re.search(r'\bti\b', k, re.I))
            k_has_super = bool(re.search(r'\bsuper\b', k, re.I))
            if has_ti == k_has_ti and has_super == k_has_super:
                norm_k = re.sub(r'[^a-z0-9]', '', k.lower())
                if norm_input in norm_k or norm_k in norm_input:
                    # Se foi pedido um vram_gb específico e a entrada tem vram_gb conflitante, não use
                    if vram_gb and v.vram_gb and v.vram_gb != vram_gb:
                        continue
                    return v

        return None

    def update_model_stats(self, model_name: str, national_prices: List[float], vram_gb: Optional[int] = None) -> NationalStats:
        """Atualiza estatísticas com dados coletados ao vivo de todo o Brasil para um modelo e variante de VRAM."""
        valid_prices = [p for p in national_prices if p > 100]

        # Define chave no cache
        cache_key = model_name
        if vram_gb and vram_gb > 0 and f"{vram_gb}gb" not in model_name.lower():
            cache_key = f"{model_name} {vram_gb}GB"

        if not valid_prices:
            # Retorna o existente se houver
            existing = self.get_stats_for_model(model_name, vram_gb=vram_gb)
            if existing:
                return existing
            return NationalStats(model_name=cache_key, vram_gb=vram_gb)

        q1 = float(np.percentile(valid_prices, 25))
        median = float(np.median(valid_prices))
        q3 = float(np.percentile(valid_prices, 75))
        stats = NationalStats(
            model_name=cache_key,
            vram_gb=vram_gb,
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
        self.cache[cache_key] = stats
        self.save_cache()
        return stats

    def enrich_listing(self, listing: GPUListing) -> GPUListing:
        """
        Enriquece um anúncio local com a comparação detalhada contra o mercado de todo o Brasil.
        Calcula percentual de economia/ágio e classifica como Barata, Na Média ou Cara,
        respeitando estritamente a variante de VRAM (ex: 8GB vs 12GB vs 16GB).
        """
        stats = self.get_stats_for_model(listing.detected_model, vram_gb=listing.detected_vram_gb)
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
