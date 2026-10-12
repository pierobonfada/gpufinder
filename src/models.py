from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class GPUCondition(str, Enum):
    WORKING = "WORKING"        # Placa funcional (Verde)
    DEFECTIVE = "DEFECTIVE"    # Com defeito / conserto / peças (Vermelho)

class PriceClassification(str, Enum):
    OPPORTUNITY = "OPPORTUNITY"        # Muito Barata / Oportunidade rara (< -20%)
    CHEAP = "CHEAP"                    # Barata (abaixo da média nacional)
    AVERAGE = "AVERAGE"                # Na média nacional
    EXPENSIVE = "EXPENSIVE"            # Cara (acima da média nacional)
    VERY_EXPENSIVE = "VERY_EXPENSIVE"  # Muito Cara (> +25%)
    UNKNOWN = "UNKNOWN"                # Sem dados suficientes de benchmark

class OutlierType(str, Enum):
    LOW = "LOW_OUTLIER"       # Preço excessivamente baixo (possível golpe ou sucata não identificada)
    HIGH = "HIGH_OUTLIER"     # Preço surreal / descolado da realidade
    NONE = "NONE"

class NationalStats(BaseModel):
    model_name: str
    count: int = 0
    min_price: float = 0.0
    median_price: float = 0.0
    mean_price: float = 0.0
    max_price: float = 0.0
    q1_price: float = 0.0
    q3_price: float = 0.0
    iqr: float = 0.0
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

class GPUListing(BaseModel):
    id: str
    title: str
    price: float
    platform: str                     # "OLX" ou "Facebook"
    url: str
    image_url: Optional[str] = None
    city: str = ""
    state: str = "RS"
    distance_km: Optional[float] = None
    raw_location: str = ""
    detected_model: str = "Desconhecido"
    detected_vram_gb: int = 0
    condition: GPUCondition = GPUCondition.WORKING
    defect_reasons: List[str] = Field(default_factory=list)
    is_outlier: bool = False
    outlier_type: OutlierType = OutlierType.NONE
    national_benchmark: Optional[NationalStats] = None
    price_classification: PriceClassification = PriceClassification.UNKNOWN
    price_diff_percent: Optional[float] = None  # Diferença % vs mediana nacional
    price_diff_brl: Optional[float] = None      # Diferença R$ vs mediana nacional
    compute_tflops: Optional[float] = None      # Capacidade Computacional FP32 em Teraflops (NVIDIA/TechPowerUp)
    memory_bandwidth_gbs: Optional[float] = None# Largura de banda da memória em GB/s
    architecture: Optional[str] = None          # Arquitetura (ex: Pascal, Ampere, Ada Lovelace)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    description: Optional[str] = None

class ScanSummary(BaseModel):
    total_found: int = 0
    working_count: int = 0
    defective_count: int = 0
    outliers_count: int = 0
    lowest_price: float = 0.0
    highest_price: float = 0.0
    average_price: float = 0.0
    best_deal: Optional[GPUListing] = None
    lowest_item: Optional[GPUListing] = None
    scanned_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class ScanProgress(BaseModel):
    is_scanning: bool = False
    current_task: str = "Aguardando início..."
    current_step: int = 0
    total_steps: int = 0
    found_count: int = 0
    logs: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
