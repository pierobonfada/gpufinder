#!/usr/bin/env python3
"""
GPU Hunter - Buscador de Placas de Vídeo NVIDIA de Alta VRAM (16GB a 32GB)
Região: Veranópolis - RS e Cidades Vizinhas (Raio 40km)
Plataformas: OLX e Facebook Marketplace
"""

import argparse
import asyncio
import sys
import uvicorn

from src.config import load_config
from src.engine import GPUHunterEngine

def run_cli_scan():
    """Executa a varredura diretamente no terminal."""
    config = load_config()
    engine = GPUHunterEngine(config)
    print("=" * 70)
    print("🎯 INICIANDO GPU HUNTER (MODO TERMINAL)")
    print(f"📍 Região: {config.location.center_city} - {config.location.state} (Raio {config.location.radius_km}km)")
    print(f"⚡ Hardware: NVIDIA com {config.hardware.min_vram_gb}GB a {config.hardware.max_vram_gb}GB VRAM até R$ {config.hardware.max_price_brl:,.2f}")
    print("=" * 70)

    summary = asyncio.run(engine.run_scan(include_live_scrapers=True))

    listings = engine.load_listings_from_disk()
    print(f"\n📊 RESULTADOS DA VARREDURA:")
    print(f"Total Encontrado: {summary.total_found}")
    print(f"Funcionais (Verde): {summary.working_count}")
    print(f"Com Defeito / Peças (Vermelho): {summary.defective_count}")
    print(f"Outliers Estatísticos: {summary.outliers_count}")
    print(f"Menor Preço: R$ {summary.lowest_price:,.2f}")
    print("-" * 70)

    for item in listings:
        status_icon = "🟢 FUNCIONAL" if item.condition.value == "WORKING" else "🔴 DEFEITO"
        outlier_tag = " [⚠️ OUTLIER]" if item.is_outlier else ""
        diff_str = ""
        if item.price_diff_percent is not None:
            sign = "+" if item.price_diff_percent > 0 else ""
            diff_str = f" | {item.price_classification.value} ({sign}{item.price_diff_percent:.0f}% vs Brasil)"

        print(f"{status_icon}{outlier_tag} R$ {item.price:,.2f} - {item.detected_model} ({item.detected_vram_gb}GB) em {item.city} [{item.platform}]{diff_str}")
        print(f"   Link: {item.url}")

    print("\n💡 Para visualizar o gráfico interativo completo, execute com a interface web:")
    print("   ./run.sh ou python run.py --server")

def run_web_server():
    """Inicia o servidor web FastAPI com o Dashboard interativo."""
    config = load_config()
    print("=" * 70)
    print("🚀 INICIANDO SERVIDOR WEB DO GPU HUNTER")
    print(f"🌐 Dashboard disponível em: http://localhost:{config.server.port}")
    print(f"📍 Monitorando: {config.location.center_city} - {config.location.state} (Raio {config.location.radius_km}km)")
    print(f"🎯 GPUs: NVIDIA {config.hardware.min_vram_gb}GB - {config.hardware.max_vram_gb}GB até R$ {config.hardware.max_price_brl}")
    print("=" * 70)

    uvicorn.run(
        "src.web.app:app",
        host=config.server.host,
        port=config.server.port,
        reload=False
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GPU Hunter")
    parser.add_argument("--scan", action="store_true", help="Executar apenas a varredura no terminal e sair")
    parser.add_argument("--fast", action="store_true", help="Varredura rápida usando cache/banco sem aguardar scrapers web")
    parser.add_argument("--server", action="store_true", help="Executar o servidor do dashboard web (padrão)")

    args = parser.parse_args()
    if args.scan:
        config = load_config()
        engine = GPUHunterEngine(config)
        print("=" * 70)
        print("🎯 INICIANDO GPU HUNTER (MODO TERMINAL)")
        print(f"📍 Região: {config.location.center_city} - {config.location.state} (Raio {config.location.radius_km}km)")
        print(f"⚡ Hardware: NVIDIA com {config.hardware.min_vram_gb}GB a {config.hardware.max_vram_gb}GB VRAM até R$ {config.hardware.max_price_brl:,.2f}")
        print("=" * 70)

        summary = asyncio.run(engine.run_scan(include_live_scrapers=not args.fast))

        listings = engine.load_listings_from_disk()
        print(f"\n📊 RESULTADOS DA VARREDURA:")
        print(f"Total Encontrado: {summary.total_found}")
        print(f"Funcionais (Verde): {summary.working_count}")
        print(f"Com Defeito / Peças (Vermelho): {summary.defective_count}")
        print(f"Outliers Estatísticos: {summary.outliers_count}")
        print(f"Menor Preço: R$ {summary.lowest_price:,.2f}")
        print("-" * 70)

        for item in listings:
            status_icon = "🟢 FUNCIONAL" if item.condition.value == "WORKING" else "🔴 DEFEITO"
            outlier_tag = f" [⚠️ OUTLIER: {item.outlier_type.value}]" if item.is_outlier else ""
            diff_str = ""
            if item.price_diff_percent is not None:
                sign = "+" if item.price_diff_percent > 0 else ""
                diff_str = f" | {item.price_classification.value} ({sign}{item.price_diff_percent:.0f}% vs Brasil)"

            print(f"{status_icon}{outlier_tag} R$ {item.price:,.2f} - {item.detected_model} ({item.detected_vram_gb}GB) em {item.city} [{item.platform}]{diff_str}")
            print(f"   Link: {item.url}")

        print("\n💡 Para visualizar o gráfico interativo completo, execute com a interface web:")
        print("   ./run.sh ou python run.py --server")
    else:
        run_web_server()
