import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

class HardwareConfig(BaseModel):
    brand: str = "nvidia"
    min_vram_gb: int = 16
    max_vram_gb: int = 32
    max_price_brl: float = 5000.0
    min_price_brl: float = 150.0

class LocationConfig(BaseModel):
    center_city: str = "Veranópolis"
    state: str = "RS"
    latitude: float = -28.9358
    longitude: float = -51.5503
    radius_km: int = 40
    target_cities: List[str] = Field(default_factory=lambda: [
        "Veranópolis", "Bento Gonçalves", "Nova Prata", "Cotiporã",
        "Vila Flores", "Fagundes Varela", "Garibaldi", "Carlos Barbosa",
        "Guaporé", "Farroupilha"
    ])

class DefectDetectionConfig(BaseModel):
    keywords: List[str] = Field(default_factory=lambda: [
        "com defeito", "para conserto", "para peças", "para pecas",
        "retirada de peças", "não dá vídeo", "nao da video", "sem vídeo",
        "queimada", "sucata", "tela preta", "dando artefato", "artefato",
        "precisa de reparo", "no estado"
    ])
    negation_keywords: List[str] = Field(default_factory=lambda: [
        "sem defeito", "sem defeitos", "nenhum defeito", "100% funcionando",
        "funcionando perfeitamente", "zero defeito"
    ])

class OLXConfig(BaseModel):
    enabled: bool = True
    state_code: str = "rs"
    subdomain_region: str = "serra-gaucha"
    request_delay_seconds: float = 1.5
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )

class FacebookConfig(BaseModel):
    enabled: bool = True
    headless: bool = True
    email: str = ""
    password: str = ""
    session_file: str = "data/fb_session.json"
    timeout_seconds: int = 30

class ScrapersConfig(BaseModel):
    olx: OLXConfig = Field(default_factory=OLXConfig)
    facebook: FacebookConfig = Field(default_factory=FacebookConfig)

class BenchmarkThresholds(BaseModel):
    great_deal_percent: float = -20.0
    cheap_percent: float = -8.0
    expensive_percent: float = 10.0
    very_expensive_percent: float = 25.0

class NationalBenchmarkConfig(BaseModel):
    enabled: bool = True
    cache_ttl_hours: int = 24
    min_samples_for_stats: int = 3
    thresholds: BenchmarkThresholds = Field(default_factory=BenchmarkThresholds)

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 7860
    debug: bool = False

class AppConfig(BaseModel):
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    location: LocationConfig = Field(default_factory=LocationConfig)
    defect_detection: DefectDetectionConfig = Field(default_factory=DefectDetectionConfig)
    scrapers: ScrapersConfig = Field(default_factory=ScrapersConfig)
    national_benchmark: NationalBenchmarkConfig = Field(default_factory=NationalBenchmarkConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

def load_config(config_path: Optional[Path] = None) -> AppConfig:
    path = config_path or CONFIG_PATH
    if not path.exists():
        cfg = AppConfig()
        save_config(cfg, path)
        return cfg

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    config = AppConfig.model_validate(data)

    # Environment variable overrides for sensitive credentials
    fb_email = os.environ.get("FB_EMAIL")
    fb_password = os.environ.get("FB_PASSWORD")
    if fb_email:
        config.scrapers.facebook.email = fb_email
    if fb_password:
        config.scrapers.facebook.password = fb_password

    return config

def save_config(config: AppConfig, config_path: Optional[Path] = None) -> None:
    path = config_path or CONFIG_PATH
    data = config.model_dump()
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
