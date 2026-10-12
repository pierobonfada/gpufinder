import pytest
from src.benchmark import BenchmarkEngine
from src.config import AppConfig, load_config
from src.defect_detector import DefectDetector
from src.gpu_catalog import identify_gpu
from src.models import GPUCondition, GPUListing, PriceClassification
from src.outlier_detector import OutlierDetector

def test_gpu_identification_nvidia_high_vram():
    # Modelos válidos da NVIDIA
    res1 = identify_gpu("Placa de vídeo EVGA RTX 3090 24GB FTW3")
    assert res1 is not None
    assert res1[0] == "RTX 3090"
    assert res1[1] == 24

    res2 = identify_gpu("Tesla P40 24GB aceleradora IA")
    assert res2 is not None
    assert res2[0] == "Tesla P40"
    assert res2[1] == 24

    res3 = identify_gpu("GeForce RTX 4060 Ti 16GB Galax")
    assert res3 is not None
    assert res3[0] == "RTX 4060 Ti 16GB"
    assert res3[1] == 16

    res4 = identify_gpu("Nvidia Quadro RTX 5000 16GB")
    assert res4 is not None
    assert res4[0] == "Quadro RTX 5000"
    assert res4[1] == 16

    res5 = identify_gpu("Nvidia Quadro P5000 16GB GDDR5X")
    assert res5 is not None
    assert res5[0] == "Quadro P5000"
    assert res5[1] == 16

def test_gpu_identification_rejections():
    # Placas NVIDIA de qualquer VRAM são identificadas para alimentação do banco de dados completo
    res_8gb = identify_gpu("RTX 4060 Ti 8GB Gigabyte")
    assert res_8gb is not None
    assert res_8gb[0] == "RTX 4060 Ti"
    assert res_8gb[1] == 8

    # Placas não-NVIDIA (AMD Radeon) devem ser rejeitadas
    assert identify_gpu("Radeon RX 6800 XT 16GB") is None
    assert identify_gpu("AMD RX 7800 XT 16GB") is None
    assert identify_gpu("XFX RX 6900 XT 16GB") is None

    # Placas Intel devem ser rejeitadas
    assert identify_gpu("Intel Arc A770 16GB") is None

def test_defect_detector():
    detector = DefectDetector()

    # Anúncios com defeito
    cond1, reasons1 = detector.analyze("RTX 3090 com defeito não dá vídeo para conserto")
    assert cond1 == GPUCondition.DEFECTIVE
    assert len(reasons1) > 0

    cond2, reasons2 = detector.analyze("Placa de vídeo queimada para retirada de peças")
    assert cond2 == GPUCondition.DEFECTIVE

    cond3, reasons3 = detector.analyze("RTX 4060 Ti sucata no estado tela preta")
    assert cond3 == GPUCondition.DEFECTIVE

    # Anúncios 100% funcionais (com negações explícitas)
    cond4, reasons4 = detector.analyze("RTX 3090 funcionando perfeitamente sem defeito testada")
    assert cond4 == GPUCondition.WORKING
    assert len(reasons4) == 0

    cond5, reasons5 = detector.analyze("Quadro RTX 5000 em perfeito estado e com garantia")
    assert cond5 == GPUCondition.WORKING

def test_outlier_detection_iqr():
    # Amostra com mediana ~4000 e dois outliers extremos
    listings = [
        GPUListing(id="1", title="A", price=800.0, platform="OLX", url="u1", detected_model="RTX 3090"), # Outlier baixo
        GPUListing(id="2", title="B", price=3800.0, platform="OLX", url="u2", detected_model="RTX 3090"),
        GPUListing(id="3", title="C", price=3900.0, platform="OLX", url="u3", detected_model="RTX 3090"),
        GPUListing(id="4", title="D", price=4100.0, platform="OLX", url="u4", detected_model="RTX 3090"),
        GPUListing(id="5", title="E", price=4200.0, platform="OLX", url="u5", detected_model="RTX 3090"),
        GPUListing(id="6", title="F", price=4300.0, platform="OLX", url="u6", detected_model="RTX 3090"),
        GPUListing(id="7", title="G", price=4400.0, platform="OLX", url="u7", detected_model="RTX 3090"),
        GPUListing(id="8", title="H", price=9500.0, platform="OLX", url="u8", detected_model="RTX 3090"), # Outlier alto
    ]

    result = OutlierDetector.detect_outliers_iqr(listings)
    assert result[0].is_outlier is True
    assert result[0].outlier_type.value == "LOW_OUTLIER"

    assert result[-1].is_outlier is True
    assert result[-1].outlier_type.value == "HIGH_OUTLIER"

    # Valores centrais não devem ser outliers
    assert result[3].is_outlier is False

def test_different_models_not_compared():
    # Tesla K80 por R$ 750 é normal para Tesla K80 (não deve ser outlier só porque RTX 3090 é mais cara)
    k80 = GPUListing(id="k1", title="Tesla K80 24GB", price=750.0, platform="OLX", url="u", detected_model="Tesla K80")
    rtx3090 = GPUListing(id="r1", title="RTX 3090 24GB", price=4200.0, platform="OLX", url="u", detected_model="RTX 3090")

    config = AppConfig()
    engine = BenchmarkEngine(config.national_benchmark)
    engine.enrich_listing(k80)
    engine.enrich_listing(rtx3090)

    res = OutlierDetector.detect_outliers_iqr([k80, rtx3090])
    # Como R$ 750 está próximo da média de Tesla K80 (~850), ela NÃO deve ser outlier!
    assert k80.is_outlier is False
    assert rtx3090.is_outlier is False

def test_national_benchmark_enrichment():
    config = AppConfig()
    engine = BenchmarkEngine(config.national_benchmark)

    # RTX 3090 com preço de 3100 (mediana nacional é ~4200 -> ~ -26%)
    item_cheap = GPUListing(id="c1", title="3090", price=3100.0, platform="OLX", url="u", detected_model="RTX 3090")
    engine.enrich_listing(item_cheap)

    assert item_cheap.price_classification in [PriceClassification.OPPORTUNITY, PriceClassification.CHEAP]
    assert item_cheap.price_diff_percent < 0
    assert item_cheap.national_benchmark is not None

    # RTX 3090 com preço de 4800 (acima da mediana de 4200)
    item_exp = GPUListing(id="c2", title="3090", price=4800.0, platform="OLX", url="u", detected_model="RTX 3090")
    engine.enrich_listing(item_exp)
    assert item_exp.price_classification in [PriceClassification.EXPENSIVE, PriceClassification.VERY_EXPENSIVE]
    assert item_exp.price_diff_percent > 0

def test_haversine_distance_veranopolis():
    from src.geo import get_city_distance_from_center, is_within_radius

    # Distância exata até Veranópolis
    assert get_city_distance_from_center("Veranópolis") == 0.0
    assert get_city_distance_from_center("Vila Flores") < 10.0
    assert 15.0 < get_city_distance_from_center("Nova Prata") < 22.0
    assert 20.0 < get_city_distance_from_center("Bento Gonçalves") < 30.0

    # Dentro do raio de 40km
    in_rad, dist = is_within_radius("Bento Gonçalves", -28.9358, -51.5503, 40.0)
    assert in_rad is True
    assert dist < 40.0

    in_rad_np, dist_np = is_within_radius("Nova Prata", -28.9358, -51.5503, 40.0)
    assert in_rad_np is True

    # Fora do raio de 40km
    in_rad_cx, dist_cx = is_within_radius("Caxias do Sul", -28.9358, -51.5503, 40.0)
    assert in_rad_cx is False
    assert dist_cx > 40.0

    in_rad_poa, dist_poa = is_within_radius("Porto Alegre", -28.9358, -51.5503, 40.0)
    assert in_rad_poa is False
    assert dist_poa > 100.0

def test_vram_range_filter_and_cities():
    from src.geo import get_all_known_cities
    from src.engine import GPUHunterEngine

    # Valida cidades conhecidas
    cities = get_all_known_cities()
    assert "Veranópolis" in cities or "Veranopolis" in cities
    assert "Bento Gonçalves" in cities or "Bento Goncalves" in cities
    assert "Caxias Do Sul" in cities or "Caxias do Sul" in [c.lower() for c in cities]
    assert len(cities) >= 20

    # Valida filtro em memória com range de VRAM
    engine = GPUHunterEngine()
    dummy_listings = [
        GPUListing(id="1", title="RTX 3060 12GB", price=1800, platform="OLX", url="u1", detected_model="RTX 3060", detected_vram_gb=12),
        GPUListing(id="2", title="RTX 4060 Ti 16GB", price=3200, platform="OLX", url="u2", detected_model="RTX 4060 Ti", detected_vram_gb=16),
        GPUListing(id="3", title="RTX 3090 24GB", price=4500, platform="OLX", url="u3", detected_model="RTX 3090", detected_vram_gb=24),
        GPUListing(id="4", title="Tesla V100 32GB", price=7000, platform="OLX", url="u4", detected_model="Tesla V100", detected_vram_gb=32),
        GPUListing(id="5", title="RTX 3070 8GB", price=2000, platform="OLX", url="u5", detected_model="RTX 3070", detected_vram_gb=8),
    ]

    # Filtro padrão: 16 a 32 GB
    f_16_32 = engine.filter_listings(dummy_listings, min_vram_gb=16, max_vram_gb=32)
    assert len(f_16_32) == 3
    assert {i.detected_vram_gb for i in f_16_32} == {16, 24, 32}

    # Filtro: 8 a 16 GB
    f_8_16 = engine.filter_listings(dummy_listings, min_vram_gb=8, max_vram_gb=16)
    assert len(f_8_16) == 3
    assert {i.detected_vram_gb for i in f_8_16} == {8, 12, 16}

    # Filtro: Preço máximo R$ 4000
    f_cheap = engine.filter_listings(dummy_listings, min_vram_gb=16, max_vram_gb=32, max_price=4000)
    assert len(f_cheap) == 1
    assert f_cheap[0].detected_model == "RTX 4060 Ti"

def test_pc_gamer_and_notebook_rejections():
    # PCs, Notebooks e setups completos devem ser 100% rejeitados
    assert identify_gpu("PC Gamer i7 10700k RTX 3060 16GB RAM 512GB SSD") is None
    assert identify_gpu("Notebook Gamer Dell G15 RTX 3050 16GB") is None
    assert identify_gpu("Setup Completo Ryzen 5 5600X RTX 4060 32GB RAM") is None
    assert identify_gpu("Computador Gamer i5 RTX 2060 16GB RAM Gabinete Aquario") is None
    assert identify_gpu("Gabinete Gamer com placa de video GTX 1660") is None
    assert identify_gpu("Kit Upgrade Ryzen 7 + RTX 3070") is None

    # Anúncios em categorias de computadores ou notebooks
    assert identify_gpu(
        "RTX 3060 em ótimo estado",
        description="Vendo placa",
        url="https://rs.olx.com.br/regioes/computadores-e-desktops/rtx-3060-12345"
    ) is None
    assert identify_gpu(
        "RTX 4060",
        description="Vendo notebook",
        url="https://rs.olx.com.br/regioes/notebooks/rtx-4060-12345"
    ) is None

def test_standalone_gpu_acceptance_and_ram_not_vram():
    # Placas de vídeo avulsas devem ser aceitas com sucesso
    res1 = identify_gpu("Placa de Vídeo RTX 4060 8GB Gigabyte Eagle")
    assert res1 is not None
    assert res1[0] == "RTX 4060"
    assert res1[1] == 8

    res2 = identify_gpu("Placa de Vídeo Galax GeForce RTX 4060 8GB GDDR6")
    assert res2 is not None
    assert res2[0] == "RTX 4060"
    assert res2[1] == 8

    res3 = identify_gpu("Placa de Vídeo RTX 3060 12GB Asus Dual")
    assert res3 is not None
    assert res3[0] == "RTX 3060"
    assert res3[1] == 12

    # Menção de memória RAM do PC não pode contaminar a VRAM da placa
    res4 = identify_gpu("Placa de Vídeo RTX 4060", description="Vendo minha placa de vídeo, rodava em PC com 32GB de RAM")
    assert res4 is not None
    assert res4[0] == "RTX 4060"
    assert res4[1] == 8  # RTX 4060 só existe com 8GB de VRAM, 32GB RAM foi ignorado!

def test_best_deal_only_discounts():
    from src.engine import GPUHunterEngine
    from src.models import GPUCondition, GPUListing

    engine = GPUHunterEngine()

    # Cenário 1: Todas as placas estão mais caras que a média (+20%, +75%)
    # "Melhor Oportunidade" NÃO DEVE existir (deve ser None)!
    expensive_listings = [
        GPUListing(id="e1", title="RTX 3060", price=2500, platform="OLX", url="u1",
                   condition=GPUCondition.WORKING, price_diff_percent=78.5),
        GPUListing(id="e2", title="RTX 4060", price=2300, platform="OLX", url="u2",
                   condition=GPUCondition.WORKING, price_diff_percent=27.7),
    ]
    summary1 = engine.calculate_summary(expensive_listings)
    assert summary1.best_deal is None, "Nenhuma placa com ágio deve ser marcada como Melhor Oportunidade!"

    # Cenário 2: Uma placa com -25% de desconto real vs mediana nacional
    deal_listings = [
        GPUListing(id="d1", title="RTX 3060 Oportunidade", price=1050, platform="OLX", url="u1",
                   condition=GPUCondition.WORKING, price_diff_percent=-25.0),
        GPUListing(id="e2", title="RTX 4060 Cara", price=2300, platform="OLX", url="u2",
                   condition=GPUCondition.WORKING, price_diff_percent=27.7),
    ]
    summary2 = engine.calculate_summary(deal_listings)
    assert summary2.best_deal is not None
    assert summary2.best_deal.id == "d1"
    assert summary2.best_deal.price_diff_percent == -25.0

def test_benchmark_strict_model_matching():
    config = AppConfig()
    engine = BenchmarkEngine(config.national_benchmark)

    # RTX 3060 vs RTX 3060 Ti
    stats_3060 = engine.get_stats_for_model("RTX 3060")
    stats_3060_ti = engine.get_stats_for_model("RTX 3060 Ti")

    assert stats_3060 is not None
    assert stats_3060_ti is not None
    assert stats_3060.model_name == "RTX 3060"
    assert stats_3060_ti.model_name == "RTX 3060 Ti"
    assert stats_3060.median_price == 1400.0
    assert stats_3060_ti.median_price == 1650.0

    # RTX 4060 vs RTX 4060 Ti 16GB
    stats_4060 = engine.get_stats_for_model("RTX 4060")
    stats_4060_ti_16 = engine.get_stats_for_model("RTX 4060 Ti 16GB")
    assert stats_4060 is not None
    assert stats_4060_ti_16 is not None
    assert stats_4060.model_name == "RTX 4060"
    assert stats_4060_ti_16.model_name == "RTX 4060 Ti 16GB"
    assert stats_4060.median_price > 0
    assert stats_4060_ti_16.median_price > 0

def test_mercadolivre_scraper_and_platform_filter():
    from src.scrapers.mercadolivre_scraper import MercadoLivreScraper
    from src.defect_detector import DefectDetector
    from src.engine import GPUHunterEngine

    config = AppConfig()
    detector = DefectDetector()
    ml_scraper = MercadoLivreScraper(config, detector)

    # Preço parsing
    assert ml_scraper._extract_price("1.250") == 1250.0
    assert ml_scraper._extract_price("R$ 2.499,90") == 2499.90
    assert ml_scraper._extract_price("850") == 850.0

    # Teste de filtro por plataforma MercadoLivre no Engine
    engine = GPUHunterEngine()
    listings = [
        GPUListing(id="ml_1", title="RTX 3070 8GB", price=1900, platform="MercadoLivre", url="u1", detected_model="RTX 3070", detected_vram_gb=8),
        GPUListing(id="olx_1", title="RTX 3070 8GB", price=1950, platform="OLX", url="u2", detected_model="RTX 3070", detected_vram_gb=8),
        GPUListing(id="fb_1", title="RTX 3070 8GB", price=1800, platform="Facebook", url="u3", detected_model="RTX 3070", detected_vram_gb=8),
    ]

    filtered_ml = engine.filter_listings(listings, platform="MercadoLivre")
    assert len(filtered_ml) == 1
    assert filtered_ml[0].platform == "MercadoLivre"
    assert filtered_ml[0].id == "ml_1"

    filtered_fb = engine.filter_listings(listings, platform="Facebook")
    assert len(filtered_fb) == 1
    assert filtered_fb[0].platform == "Facebook"

    filtered_olx = engine.filter_listings(listings, platform="OLX")
    assert len(filtered_olx) == 1
    assert filtered_olx[0].platform == "OLX"

def test_facebook_multi_search_terms():
    from src.scrapers.facebook_scraper import FacebookMarketplaceScraper

    # Verifica que termos ampliados estão configurados
    assert hasattr(FacebookMarketplaceScraper, "SEARCH_TERMS")
    assert "rtx" in FacebookMarketplaceScraper.SEARCH_TERMS
    assert "geforce" in FacebookMarketplaceScraper.SEARCH_TERMS
    assert "gtx" in FacebookMarketplaceScraper.SEARCH_TERMS
    assert "nvidia" in FacebookMarketplaceScraper.SEARCH_TERMS

