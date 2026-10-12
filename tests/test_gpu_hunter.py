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
    # 4060 Ti 8GB deve ser rejeitada (mínimo exigido é 16GB)
    res_8gb = identify_gpu("RTX 4060 Ti 8GB Gigabyte")
    assert res_8gb is None

    # Placas AMD devem ser rejeitadas
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
