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
from src.models import GPUListing, GPUCondition, PriceClassification, ScanSummary, ScanProgress

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GPU Hunter",
    description="Caçador de Placas NVIDIA de Alta VRAM (16GB-32GB) no OLX e Facebook em Veranópolis - RS e Região",
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

@app.get("/api/listings", response_model=List[GPUListing])
async def get_listings(
    vram: Optional[int] = Query(None, description="Filtrar por VRAM em GB"),
    condition: Optional[str] = Query(None, description="Filtrar por 'WORKING' ou 'DEFECTIVE'"),
    platform: Optional[str] = Query(None, description="Filtrar por 'OLX' ou 'Facebook'"),
    max_price: Optional[float] = Query(None, description="Preço máximo em R$"),
    min_price: Optional[float] = Query(None, description="Preço mínimo em R$"),
    outlier_only: bool = Query(False, description="Apenas outliers")
):
    items = engine.load_listings_from_disk()

    filtered = items
    if vram:
        filtered = [i for i in filtered if i.detected_vram_gb == vram]
    if condition:
        filtered = [i for i in filtered if i.condition.value == condition]
    if platform:
        filtered = [i for i in filtered if i.platform.lower() == platform.lower()]
    if max_price is not None:
        filtered = [i for i in filtered if i.price <= max_price]
    if min_price is not None:
        filtered = [i for i in filtered if i.price >= min_price]
    if outlier_only:
        filtered = [i for i in filtered if i.is_outlier]

    return filtered

@app.get("/api/summary", response_model=ScanSummary)
async def get_summary():
    items = engine.load_listings_from_disk()
    return engine.calculate_summary(items)

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
    max_price: Optional[float] = None
    radius_km: Optional[float] = None

@app.post("/api/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    live: bool = Query(True),
    max_price: Optional[float] = Query(None),
    radius_km: Optional[float] = Query(None),
    payload: Optional[ScanRequestPayload] = None
):
    if engine.is_scanning:
        return {"status": "busy", "message": "Uma varredura já está em andamento."}

    req_live = payload.live if payload and payload.live is not None else live
    req_max_price = payload.max_price if payload and payload.max_price is not None else max_price
    req_radius_km = payload.radius_km if payload and payload.radius_km is not None else radius_km

    background_tasks.add_task(
        engine.run_scan,
        include_live_scrapers=req_live,
        custom_max_price=req_max_price,
        custom_radius_km=req_radius_km
    )
    return {"status": "started", "message": "Varredura iniciada em segundo plano."}

@app.get("/api/benchmark/{model_name}")
async def get_model_benchmark(model_name: str):
    stats = engine.benchmark_engine.get_stats_for_model(model_name)
    if not stats:
        raise HTTPException(status_code=404, detail="Modelo não encontrado no benchmark")
    return stats
