import re
from typing import Dict, List, Optional, Tuple

# Base abrangente de placas e GPUs NVIDIA (todas as séries e VRAMs)
NVIDIA_GPU_CATALOG: Dict[str, Dict] = {
    # --- GeForce RTX 50 Series ---
    "RTX 5090": {
        "series": "GeForce",
        "default_vram": 32,
        "keywords": ["rtx 5090", "rtx5090", "geforce rtx 5090"],
        "architecture": "Blackwell"
    },
    "RTX 5080": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 5080", "rtx5080", "geforce rtx 5080"],
        "architecture": "Blackwell"
    },
    "RTX 5070 Ti": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 5070 ti", "rtx 5070ti", "5070 ti"],
        "architecture": "Blackwell"
    },
    "RTX 5070": {
        "series": "GeForce",
        "default_vram": 12,
        "keywords": ["rtx 5070", "rtx5070", "geforce rtx 5070"],
        "exclude": ["5070 ti"],
        "architecture": "Blackwell"
    },

    # --- GeForce RTX 40 Series ---
    "RTX 4090": {
        "series": "GeForce",
        "default_vram": 24,
        "keywords": ["rtx 4090", "rtx4090", "geforce rtx 4090"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4080 Super": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 4080 super", "rtx 4080super", "4080 super"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4080": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 4080", "rtx4080"],
        "exclude": ["4080 super"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4070 Ti Super": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 4070 ti super", "4070 ti super", "4070tisuper"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4070 Ti": {
        "series": "GeForce",
        "default_vram": 12,
        "keywords": ["rtx 4070 ti", "4070 ti", "4070ti"],
        "exclude": ["ti super"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4070 Super": {
        "series": "GeForce",
        "default_vram": 12,
        "keywords": ["rtx 4070 super", "4070 super", "4070super"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4070": {
        "series": "GeForce",
        "default_vram": 12,
        "keywords": ["rtx 4070", "rtx4070", "geforce rtx 4070"],
        "exclude": ["4070 ti", "4070 super"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4060 Ti 16GB": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["4060 ti 16gb", "4060ti 16gb", "4060 ti 16 gb", "4060ti 16 gb"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4060 Ti": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 4060 ti", "rtx 4060ti", "4060 ti", "4060ti"],
        "exclude": ["16gb", "16 gb"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4060": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 4060", "rtx4060", "geforce rtx 4060", " 4060 "],
        "exclude": ["4060 ti", "4060ti"],
        "architecture": "Ada Lovelace"
    },

    # --- GeForce RTX 30 Series ---
    "RTX 3090 Ti": {
        "series": "GeForce",
        "default_vram": 24,
        "keywords": ["rtx 3090 ti", "rtx 3090ti", "rtx3090ti"],
        "architecture": "Ampere"
    },
    "RTX 3090": {
        "series": "GeForce",
        "default_vram": 24,
        "keywords": ["rtx 3090", "rtx3090"],
        "exclude": ["3090 ti"],
        "architecture": "Ampere"
    },
    "RTX 3080 Ti": {
        "series": "GeForce",
        "default_vram": 12,
        "keywords": ["rtx 3080 ti", "rtx 3080ti", "3080 ti"],
        "architecture": "Ampere"
    },
    "RTX 3080": {
        "series": "GeForce",
        "default_vram": 10,
        "keywords": ["rtx 3080", "rtx3080"],
        "exclude": ["3080 ti"],
        "architecture": "Ampere"
    },
    "RTX 3070 Ti": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 3070 ti", "rtx 3070ti", "3070 ti"],
        "architecture": "Ampere"
    },
    "RTX 3070": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 3070", "rtx3070"],
        "exclude": ["3070 ti"],
        "architecture": "Ampere"
    },
    "RTX 3060 Ti": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 3060 ti", "rtx 3060ti", "3060 ti", "3060ti"],
        "architecture": "Ampere"
    },
    "RTX 3060": {
        "series": "GeForce",
        "default_vram": 12,
        "keywords": ["rtx 3060", "rtx3060"],
        "exclude": ["3060 ti", "3060ti"],
        "architecture": "Ampere"
    },
    "RTX 3050": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 3050", "rtx3050"],
        "architecture": "Ampere"
    },

    # --- GeForce RTX 20 Series ---
    "RTX 2080 Ti": {
        "series": "GeForce",
        "default_vram": 11,
        "keywords": ["rtx 2080 ti", "rtx 2080ti", "2080 ti"],
        "architecture": "Turing"
    },
    "RTX 2080 Super": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 2080 super", "2080 super"],
        "architecture": "Turing"
    },
    "RTX 2080": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 2080", "rtx2080"],
        "exclude": ["2080 ti", "2080 super"],
        "architecture": "Turing"
    },
    "RTX 2070 Super": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 2070 super", "2070 super"],
        "architecture": "Turing"
    },
    "RTX 2070": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 2070", "rtx2070"],
        "exclude": ["2070 super"],
        "architecture": "Turing"
    },
    "RTX 2060 Super": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["rtx 2060 super", "2060 super"],
        "architecture": "Turing"
    },
    "RTX 2060": {
        "series": "GeForce",
        "default_vram": 6,
        "keywords": ["rtx 2060", "rtx2060"],
        "exclude": ["2060 super"],
        "architecture": "Turing"
    },
    "RTX 2050": {
        "series": "GeForce",
        "default_vram": 4,
        "keywords": ["rtx 2050", "rtx2050"],
        "architecture": "Ampere"
    },

    # --- GeForce GTX 16 Series ---
    "GTX 1660 Ti": {
        "series": "GeForce",
        "default_vram": 6,
        "keywords": ["gtx 1660 ti", "gtx 1660ti", "1660 ti"],
        "architecture": "Turing"
    },
    "GTX 1660 Super": {
        "series": "GeForce",
        "default_vram": 6,
        "keywords": ["gtx 1660 super", "1660 super"],
        "architecture": "Turing"
    },
    "GTX 1660": {
        "series": "GeForce",
        "default_vram": 6,
        "keywords": ["gtx 1660", "gtx1660"],
        "exclude": ["1660 ti", "1660 super"],
        "architecture": "Turing"
    },
    "GTX 1650 Super": {
        "series": "GeForce",
        "default_vram": 4,
        "keywords": ["gtx 1650 super", "1650 super"],
        "architecture": "Turing"
    },
    "GTX 1650": {
        "series": "GeForce",
        "default_vram": 4,
        "keywords": ["gtx 1650", "gtx1650"],
        "exclude": ["1650 super"],
        "architecture": "Turing"
    },

    # --- GeForce GTX 10 Series ---
    "GTX 1080 Ti": {
        "series": "GeForce",
        "default_vram": 11,
        "keywords": ["gtx 1080 ti", "gtx 1080ti", "1080 ti"],
        "architecture": "Pascal"
    },
    "GTX 1080": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["gtx 1080", "gtx1080"],
        "exclude": ["1080 ti"],
        "architecture": "Pascal"
    },
    "GTX 1070 Ti": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["gtx 1070 ti", "gtx 1070ti", "1070 ti"],
        "architecture": "Pascal"
    },
    "GTX 1070": {
        "series": "GeForce",
        "default_vram": 8,
        "keywords": ["gtx 1070", "gtx1070"],
        "exclude": ["1070 ti"],
        "architecture": "Pascal"
    },
    "GTX 1060": {
        "series": "GeForce",
        "default_vram": 6,
        "keywords": ["gtx 1060", "gtx1060"],
        "architecture": "Pascal"
    },
    "GTX 1050 Ti": {
        "series": "GeForce",
        "default_vram": 4,
        "keywords": ["gtx 1050 ti", "gtx 1050ti", "1050 ti"],
        "architecture": "Pascal"
    },
    "GTX 1050": {
        "series": "GeForce",
        "default_vram": 2,
        "keywords": ["gtx 1050", "gtx1050"],
        "exclude": ["1050 ti"],
        "architecture": "Pascal"
    },
    "GT 1030": {
        "series": "GeForce",
        "default_vram": 2,
        "keywords": ["gt 1030", "gt1030"],
        "architecture": "Pascal"
    },

    # --- GeForce Clássicas (GTX 900 / 700 / 600 / GT) ---
    "GTX 980 Ti": { "series": "GeForce", "default_vram": 6, "keywords": ["gtx 980 ti", "980 ti"], "architecture": "Maxwell" },
    "GTX 980": { "series": "GeForce", "default_vram": 4, "keywords": ["gtx 980", "gtx980"], "exclude": ["980 ti"], "architecture": "Maxwell" },
    "GTX 970": { "series": "GeForce", "default_vram": 4, "keywords": ["gtx 970", "gtx970"], "architecture": "Maxwell" },
    "GTX 960": { "series": "GeForce", "default_vram": 2, "keywords": ["gtx 960", "gtx960"], "architecture": "Maxwell" },
    "GTX 750 Ti": { "series": "GeForce", "default_vram": 2, "keywords": ["gtx 750 ti", "gtx 750ti", "750 ti"], "architecture": "Maxwell" },
    "GTX 750": { "series": "GeForce", "default_vram": 2, "keywords": ["gtx 750", "gtx750"], "exclude": ["750 ti"], "architecture": "Maxwell" },
    "GTX 680": { "series": "GeForce", "default_vram": 2, "keywords": ["gtx 680", "gtx680"], "architecture": "Kepler" },
    "GT 730": { "series": "GeForce", "default_vram": 2, "keywords": ["gt 730", "gt730", "n730"], "architecture": "Kepler" },
    "GT 710": { "series": "GeForce", "default_vram": 2, "keywords": ["gt 710", "gt710"], "architecture": "Kepler" },
    "GT 630": { "series": "GeForce", "default_vram": 2, "keywords": ["gt 630", "gt630"], "architecture": "Kepler" },
    "GT 610": { "series": "GeForce", "default_vram": 2, "keywords": ["gt 610", "gt610"], "architecture": "Fermi" },

    # --- Titan ---
    "Titan RTX": { "series": "Titan", "default_vram": 24, "keywords": ["titan rtx"], "architecture": "Turing" },
    "Titan V": { "series": "Titan", "default_vram": 12, "keywords": ["titan v"], "architecture": "Volta" },

    # --- Datacenter Tesla ---
    "Tesla P40": { "series": "Tesla", "default_vram": 24, "keywords": ["tesla p40", "p40 24gb"], "architecture": "Pascal" },
    "Tesla M40": { "series": "Tesla", "default_vram": 24, "keywords": ["tesla m40", "m40 24gb"], "architecture": "Maxwell" },
    "Tesla K80": { "series": "Tesla", "default_vram": 24, "keywords": ["tesla k80", "k80 24gb"], "architecture": "Kepler" },
    "Tesla V100": { "series": "Tesla", "default_vram": 16, "keywords": ["tesla v100", "v100 16gb", "v100 32gb"], "architecture": "Volta" },
    "Tesla T4": { "series": "Tesla", "default_vram": 16, "keywords": ["tesla t4", "t4 16gb"], "architecture": "Turing" },
    "Tesla P100": { "series": "Tesla", "default_vram": 16, "keywords": ["tesla p100", "p100 16gb", "p100 hbm2"], "architecture": "Pascal" },

    # --- Quadro / RTX Workstation ---
    "Quadro RTX 6000": { "series": "Quadro RTX", "default_vram": 24, "keywords": ["quadro rtx 6000", "rtx 6000 quadro"], "architecture": "Turing" },
    "Quadro RTX 5000": { "series": "Quadro RTX", "default_vram": 16, "keywords": ["quadro rtx 5000", "rtx 5000 quadro"], "architecture": "Turing" },
    "Quadro P6000": { "series": "Quadro", "default_vram": 24, "keywords": ["quadro p6000"], "architecture": "Pascal" },
    "Quadro P5000": { "series": "Quadro", "default_vram": 16, "keywords": ["quadro p5000"], "architecture": "Pascal" },
    "Quadro P4000": { "series": "Quadro", "default_vram": 8, "keywords": ["quadro p4000"], "architecture": "Pascal" },
    "Quadro P2000": { "series": "Quadro", "default_vram": 5, "keywords": ["quadro p2000"], "architecture": "Pascal" },
    "Quadro P600": { "series": "Quadro", "default_vram": 2, "keywords": ["quadro p600", "p600"], "architecture": "Pascal" },
    "Quadro M6000": { "series": "Quadro", "default_vram": 24, "keywords": ["quadro m6000"], "architecture": "Maxwell" },
    "Quadro K5200": { "series": "Quadro", "default_vram": 8, "keywords": ["quadro k5200", "k5200"], "architecture": "Kepler" },
    "Quadro K2000": { "series": "Quadro", "default_vram": 2, "keywords": ["quadro k2000", "k2000"], "architecture": "Kepler" },
    "Quadro 4000": { "series": "Quadro", "default_vram": 2, "keywords": ["quadro 4000"], "exclude": ["rtx 4000"], "architecture": "Fermi" },
    "RTX A6000": { "series": "RTX Workstation", "default_vram": 48, "keywords": ["rtx a6000", "a6000"], "architecture": "Ampere" },
    "RTX A5000": { "series": "RTX Workstation", "default_vram": 24, "keywords": ["rtx a5000", "a5000"], "architecture": "Ampere" },
    "RTX A4500": { "series": "RTX Workstation", "default_vram": 20, "keywords": ["rtx a4500", "a4500"], "architecture": "Ampere" },
    "RTX A4000": { "series": "RTX Workstation", "default_vram": 16, "keywords": ["rtx a4000", "a4000"], "architecture": "Ampere" },
    "RTX 4000 Ada": { "series": "RTX Workstation", "default_vram": 20, "keywords": ["rtx 4000 ada", "4000 ada"], "architecture": "Ada Lovelace" }
}

NVIDIA_HIGH_VRAM_CATALOG = NVIDIA_GPU_CATALOG # retrocompatibilidade

# Palavras que eliminam imediatamente anúncios não-NVIDIA
NON_NVIDIA_EXCLUSIONS = [
    r"\brx\s*(?:480|570|580|590|5500|5600|5700|6600|6700|6750|6800|6900|6950|7600|7700|7800|7900)\b",
    r"\bradeon\b",
    r"\bamd\b",
    r"\barc\s*(?:a380|a580|a750|a770|b580)\b",
    r"\bintel\s+arc\b",
    r"\bplaystation\b",
    r"\bps[45]\b",
    r"\bxbox\b"
]

def is_non_nvidia(text: str) -> bool:
    """Verifica se o texto contém termos de marcas concorrentes (AMD, Intel Arc, etc)."""
    text_lower = text.lower()
    for pattern in NON_NVIDIA_EXCLUSIONS:
        if re.search(pattern, text_lower):
            if "radeon" in text_lower or "amd" in text_lower or "arc a770" in text_lower:
                return True
    return False

def extract_explicit_vram(text: str) -> Optional[int]:
    """Extrai valor explícito de VRAM em GB a partir do texto."""
    text_lower = text.lower()
    # Padrões comuns: '16gb', '24 gb', '8gb vram', '12g', '2gb'
    matches = re.findall(r"\b(1|2|3|4|5|6|8|10|11|12|16|20|24|32|48)\s*(?:gb|g\b|gigas?)\b", text_lower)
    if matches:
        nums = [int(m) for m in matches]
        # Dá prioridade para números comuns de placas de vídeo
        for n in nums:
            if n in [24, 32, 16, 20, 12, 10, 11, 8, 6, 4, 3, 2, 1]:
                return n
        return nums[0]
    return None

def identify_gpu(title: str, description: str = "") -> Optional[Tuple[str, int]]:
    """
    Identifica QUALQUER GPU NVIDIA presente no anúncio e sua memória VRAM.
    Retorna uma tupla (nome_do_modelo, vram_em_gb) ou None se não for NVIDIA.
    """
    full_text = f"{title} {description}".lower()

    if is_non_nvidia(full_text):
        return None

    explicit_vram = extract_explicit_vram(full_text)

    # 1. Busca por modelos conhecidos no catálogo
    for model_name, info in NVIDIA_GPU_CATALOG.items():
        matched = False
        for kw in info["keywords"]:
            if kw in full_text:
                matched = True
                break

        if not matched:
            continue

        if "exclude" in info:
            if any(exc in full_text for exc in info["exclude"]):
                continue

        # VRAM determinada: se o texto traz menção explícita de VRAM coerente, usa ela
        vram = explicit_vram if (explicit_vram and explicit_vram in [1, 2, 3, 4, 5, 6, 8, 10, 11, 12, 16, 20, 24, 32, 48]) else info["default_vram"]
        return (model_name, vram)

    # 2. Verificação genérica: título menciona "NVIDIA", "GeForce", "RTX", "GTX", "Quadro", "Tesla"
    if re.search(r"\b(rtx|gtx|nvidia|quadro|tesla|titan|geforce)\b", full_text):
        match = re.search(r"\b((?:geforce\s+)?(?:rtx|gtx|gt)\s*\d{3,4}(?:\s*ti)?(?:\s*super)?|quadro\s*[a-z0-9]+|tesla\s*[a-z0-9]+|titan\s*[a-z0-9]+)\b", full_text)
        detected_name = match.group(0).upper() if match else "NVIDIA GPU"
        vram = explicit_vram if explicit_vram else 8
        return (detected_name, vram)

    return None

def get_target_search_queries() -> List[str]:
    """Retorna lista de consultas chave para os scrapers cobrirem todos os modelos de interesse."""
    return [
        "RTX 3090",
        "RTX 3090 Ti",
        "RTX 4080",
        "RTX 4070 Ti Super",
        "RTX 4060 Ti 16GB",
        "Tesla P40",
        "Tesla M40",
        "Tesla V100",
        "Quadro P5000",
        "Quadro P6000",
        "Quadro M6000",
        "Quadro RTX 5000",
        "Quadro RTX 6000",
        "RTX A4000",
        "RTX A5000",
        "Titan RTX"
    ]
