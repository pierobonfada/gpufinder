import random
from datetime import datetime, timedelta
from typing import List
from src.defect_detector import DefectDetector
from src.gpu_catalog import identify_gpu
from src.models import GPUListing, GPUCondition

SAMPLE_REGIONAL_DATA = [
    {
        "title": "Placa de Vídeo EVGA RTX 3090 FTW3 Ultra 24GB Impecável",
        "price": 3850.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/rtx-3090-ftw3-24gb-12345678",
        "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=400&q=80",
        "city": "Bento Gonçalves",
        "state": "RS",
        "description": "Placa usada apenas para render 3D em estúdio, funcionando perfeitamente, sem defeito, temperaturas ótimas.",
    },
    {
        "title": "Nvidia RTX 3090 24GB Asus TUF - Com defeito não dá vídeo para conserto",
        "price": 1400.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/rtx-3090-asus-tuf-defeito-23456789",
        "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400&q=80",
        "city": "Nova Prata",
        "state": "RS",
        "description": "Placa parou de dar vídeo após oscilação de energia, liga as ventoinhas mas tela preta. Vendo no estado para retirada de peças ou quem souber consertar.",
    },
    {
        "title": "Placa Aceleradora NVIDIA Tesla P40 24GB para IA e Deep Learning",
        "price": 1650.0,
        "platform": "Facebook",
        "url": "https://www.facebook.com/marketplace/item/345678901234567/",
        "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=400&q=80",
        "city": "Veranópolis",
        "state": "RS",
        "description": "Tesla P40 com 24GB VRAM GDDR5X, perfeita para rodar modelos de linguagem LLM (Llama, DeepSeek) localmente. Funcionando 100%, acompanha suporte de ventoinha blower.",
    },
    {
        "title": "GeForce RTX 4060 Ti 16GB Galax com NF e Garantia",
        "price": 2500.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/galax-rtx-4060-ti-16gb-45678901",
        "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=400&q=80",
        "city": "Carlos Barbosa",
        "state": "RS",
        "description": "Placa com 4 meses de uso, versão com 16GB VRAM, caixa completa, funcionando perfeitamente sem qualquer defeito.",
    },
    {
        "title": "Nvidia RTX 4060 Ti 16GB queimada para peças ou reparo",
        "price": 750.0,
        "platform": "Facebook",
        "url": "https://www.facebook.com/marketplace/item/567890123456789/",
        "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400&q=80",
        "city": "Farroupilha",
        "state": "RS",
        "description": "Não liga, deu curto na entrada 12V. Placa com defeito para técnicos aproveitarem chips de memória ou tentarem reparo.",
    },
    {
        "title": "Nvidia Quadro RTX 5000 16GB GDDR6 Workstation",
        "price": 3100.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/quadro-rtx-5000-16gb-67890123",
        "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=400&q=80",
        "city": "Bento Gonçalves",
        "state": "RS",
        "description": "Quadro arquitetura Turing, 16GB de VRAM com suporte a ECC, excelente para CAD, Blender e IA. 100% revisada e funcional.",
    },
    {
        "title": "Placa de Vídeo NVIDIA Tesla M40 24GB",
        "price": 1050.0,
        "platform": "Facebook",
        "url": "https://www.facebook.com/marketplace/item/789012345678901/",
        "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=400&q=80",
        "city": "Garibaldi",
        "state": "RS",
        "description": "Tesla M40 24GB Maxwell, ótimo custo benefício para quem quer muita VRAM gastando pouco. Testada e aprovada.",
    },
    {
        "title": "Placa Profissional Nvidia Quadro P5000 16GB",
        "price": 2050.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/quadro-p5000-16gb-89012345",
        "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=400&q=80",
        "city": "Veranópolis",
        "state": "RS",
        "description": "Quadro Pascal com 16GB de memória GDDR5X, 4 saídas DisplayPort nativas. Excelente estado.",
    },
    {
        "title": "Nvidia RTX 3090 Founders Edition 24GB",
        "price": 4450.0,
        "platform": "Facebook",
        "url": "https://www.facebook.com/marketplace/item/901234567890123/",
        "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=400&q=80",
        "city": "Bento Gonçalves",
        "state": "RS",
        "description": "Modelo Founders Edition original NVIDIA 24GB VRAM. Funcionamento exemplar.",
    },
    {
        "title": "Quadro M6000 24GB - Placa rara com defeito dando artefatos",
        "price": 890.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/quadro-m6000-24gb-defeito-01234567",
        "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400&q=80",
        "city": "Fagundes Varela",
        "state": "RS",
        "description": "Quadro M6000 com 24GB. Apresenta artefatos listrados na tela após carregar o driver, para peças ou reparo.",
    },
    {
        "title": "Nvidia RTX A4000 16GB Single Slot Workstation",
        "price": 3650.0,
        "platform": "Facebook",
        "url": "https://www.facebook.com/marketplace/item/112233445566778/",
        "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=400&q=80",
        "city": "Farroupilha",
        "state": "RS",
        "description": "Placa moderna arquitetura Ampere, single slot, consome apenas 140W com 16GB GDDR6 ECC. Perfeita.",
    },
    {
        "title": "Aceleradora Nvidia Tesla V100 16GB PCIe 3.0",
        "price": 3400.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/tesla-v100-16gb-22334455",
        "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=400&q=80",
        "city": "Cotiporã",
        "state": "RS",
        "description": "Tensor Cores Volta com memória HBM2 ultrarrápida. Testada em servidor, funcionando 100%.",
    },
    {
        "title": "Nvidia Titan RTX 24GB Turing - Edição de Colecionador",
        "price": 4850.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/titan-rtx-24gb-33445566",
        "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=400&q=80",
        "city": "Bento Gonçalves",
        "state": "RS",
        "description": "Titan RTX dourada com 24GB VRAM. Em excelente estado de conservação, caixa completa.",
    },
    {
        "title": "Nvidia Tesla K80 24GB (2x12GB) Dual GPU",
        "price": 720.0,
        "platform": "OLX",
        "url": "https://rs.olx.com.br/regioes-de-caxias-do-sul-e-passo-fundo/informatica-e-acessorios/pecas-de-computador/placas-de-video/tesla-k80-24gb-44556677",
        "image_url": "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=400&q=80",
        "city": "Vila Flores",
        "state": "RS",
        "description": "Placa dual GPU com 24GB de VRAM total. Requer sistema com refrigeração ativa forçada. Funcionando.",
    },
    {
        "title": "MSI Suprim X RTX 3090 24GB - Top de Linha",
        "price": 4900.0,
        "platform": "Facebook",
        "url": "https://www.facebook.com/marketplace/item/556677889900112/",
        "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=400&q=80",
        "city": "Guaporé",
        "state": "RS",
        "description": "Uma das melhores construções de RTX 3090 já feitas, triple fan gigante, RGB, dual bios, impecável.",
    }
]

def generate_sample_listings(defect_detector: DefectDetector) -> List[GPUListing]:
    """Gera anúncios realistas e formatados da região da Serra Gaúcha para teste e visualização imediata."""
    listings: List[GPUListing] = []
    for item in SAMPLE_REGIONAL_DATA:
        title = item["title"]
        desc = item.get("description", "")
        info = identify_gpu(title, desc)
        if not info:
            continue

        model_name, vram = info
        cond, reasons = defect_detector.analyze(title, desc)

        from src.geo import get_city_distance_from_center
        dist = get_city_distance_from_center(item["city"])

        listing = GPUListing(
            id=f"sample_{abs(hash(item['url'])) % 1000000}",
            title=title,
            price=item["price"],
            platform=item["platform"],
            url=item["url"],
            image_url=item.get("image_url", ""),
            city=item["city"],
            state=item["state"],
            distance_km=dist,
            raw_location=f"{item['city']}, {item['state']}",
            detected_model=model_name,
            detected_vram_gb=vram,
            condition=cond,
            defect_reasons=reasons,
            description=desc,
            created_at=(datetime.now() - timedelta(hours=random.randint(2, 48))).isoformat()
        )
        listings.append(listing)
    return listings
