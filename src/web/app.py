import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import AppConfig, load_config, save_config
from src.defect_detector import DefectDetector
from src.engine import GPUHunterEngine
from src.geo import get_all_known_cities
from src.models import GPUListing, GPUCondition, PriceClassification, ScanSummary, ScanProgress

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GPU Hunter",
    description="Caçador de Placas NVIDIA no OLX e Facebook Marketplace - Serra Gaúcha e RS",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

engine = GPUHunterEngine()

@app.on_event("startup")
async def startup_event():
    # Carrega dados reais existentes se houver
    existing = engine.load_listings_from_disk()
    logger.info(f"GPU Hunter iniciado. Anúncios reais na base: {len(existing)}")

@app.get("/")
async def get_index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/cities", response_model=List[str])
async def get_cities():
    """Retorna a lista de todas as cidades disponíveis na base geodésica."""
    return get_all_known_cities()

@app.get("/api/database/stats")
async def get_database_stats():
    """Retorna estatísticas gerais do banco de dados completo de anúncios reais."""
    items = engine.load_listings_from_disk()
    return {
        "total_listings": len(items),
        "center_city": engine.config.location.center_city,
        "radius_km": engine.config.location.radius_km
    }

@app.get("/api/listings", response_model=List[GPUListing])
async def get_listings(
    min_vram: Optional[int] = Query(None, description="VRAM mínima em GB"),
    max_vram: Optional[int] = Query(None, description="VRAM máxima em GB"),
    vram: Optional[int] = Query(None, description="Filtrar por VRAM exata em GB"),
    condition: Optional[str] = Query(None, description="Filtrar por 'WORKING' ou 'DEFECTIVE'"),
    platform: Optional[str] = Query(None, description="Filtrar por 'OLX' ou 'Facebook'"),
    max_price: Optional[float] = Query(None, description="Preço máximo em R$"),
    min_price: Optional[float] = Query(None, description="Preço mínimo em R$"),
    radius_km: Optional[float] = Query(None, description="Raio máximo em km"),
    search: Optional[str] = Query(None, description="Termo de busca textual"),
    outlier_only: bool = Query(False, description="Apenas outliers")
):
    items = engine.load_listings_from_disk()
    min_v = min_vram if min_vram is not None else vram
    max_v = max_vram if max_vram is not None else vram

    return engine.filter_listings(
        listings=items,
        min_vram_gb=min_v,
        max_vram_gb=max_v,
        max_price=max_price,
        min_price=min_price,
        radius_km=radius_km,
        condition=condition,
        platform=platform,
        search=search,
        outliers_only=outlier_only
    )

@app.get("/api/summary", response_model=ScanSummary)
async def get_summary(
    min_vram: Optional[int] = Query(None),
    max_vram: Optional[int] = Query(None),
    max_price: Optional[float] = Query(None),
    condition: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
):
    items = engine.load_listings_from_disk()
    filtered = engine.filter_listings(
        listings=items,
        min_vram_gb=min_vram,
        max_vram_gb=max_vram,
        max_price=max_price,
        condition=condition,
        platform=platform
    )
    return engine.calculate_summary(filtered)

@app.get("/api/config")
async def get_current_config():
    return engine.config.model_dump()

@app.post("/api/config")
async def update_config(new_config: AppConfig):
    save_config(new_config)
    engine.config = new_config
    engine.defect_detector = DefectDetector(
        keywords=new_config.defect_detection.keywords,
        negation_keywords=new_config.defect_detection.negation_keywords
    )
    engine.benchmark_engine.config = new_config.national_benchmark
    return {"status": "success", "message": "Configurações atualizadas com sucesso!"}

@app.get("/api/scan/status")
async def get_scan_status():
    return {"is_scanning": engine.is_scanning}

@app.get("/api/scan/progress", response_model=ScanProgress)
async def get_scan_progress():
    return engine.progress

class ScanRequestPayload(BaseModel):
    live: bool = True
    center_city: Optional[str] = None
    radius_km: Optional[float] = None
    max_price: Optional[float] = None

@app.post("/api/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    live: bool = Query(True),
    center_city: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    radius_km: Optional[float] = Query(None),
    payload: Optional[ScanRequestPayload] = None
):
    if engine.is_scanning:
        return {"status": "busy", "message": "Uma varredura já está em andamento."}

    req_live = payload.live if payload and payload.live is not None else live
    req_center_city = payload.center_city if payload and payload.center_city is not None else center_city
    req_max_price = payload.max_price if payload and payload.max_price is not None else max_price
    req_radius_km = payload.radius_km if payload and payload.radius_km is not None else radius_km

    background_tasks.add_task(
        engine.run_scan,
        include_live_scrapers=req_live,
        center_city=req_center_city,
        custom_radius_km=req_radius_km,
        custom_max_price=req_max_price
    )
    return {"status": "started", "message": "Varredura iniciada em segundo plano."}

@app.get("/api/benchmark/{model_name}")
async def get_model_benchmark(model_name: str):
    stats = engine.benchmark_engine.get_stats_for_model(model_name)
    if not stats:
        raise HTTPException(status_code=404, detail="Modelo não encontrado no benchmark")
    return stats

