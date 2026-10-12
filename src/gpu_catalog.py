import re
from typing import Dict, List, Optional, Tuple

# Base de conhecimento de placas NVIDIA com 16GB a 32GB de VRAM
# Mapeia identificadores canônicos para informações de hardware
NVIDIA_HIGH_VRAM_CATALOG: Dict[str, Dict] = {
    # --- GeForce / Titan ---
    "RTX 3090": {
        "series": "GeForce",
        "default_vram": 24,
        "keywords": ["rtx 3090", "rtx3090"],
        "exclude": ["3090 ti"],
        "architecture": "Ampere"
    },
    "RTX 3090 Ti": {
        "series": "GeForce",
        "default_vram": 24,
        "keywords": ["rtx 3090 ti", "rtx 3090ti", "rtx3090ti"],
        "architecture": "Ampere"
    },
    "RTX 4080": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 4080", "rtx4080"],
        "exclude": ["4080 super"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4080 Super": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 4080 super", "rtx 4080super", "rtx4080 super"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4070 Ti Super": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 4070 ti super", "4070 ti super", "4070tisuper"],
        "architecture": "Ada Lovelace"
    },
    "RTX 4060 Ti 16GB": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["4060 ti 16gb", "4060ti 16gb", "4060 ti 16 gb", "4060ti 16 gb", "4060 ti 16"],
        "architecture": "Ada Lovelace",
        "requires_explicit_vram": True
    },
    "RTX 4090": {
        "series": "GeForce",
        "default_vram": 24,
        "keywords": ["rtx 4090", "rtx4090", "geforce rtx 4090"],
        "architecture": "Ada Lovelace"
    },
    "RTX 5080": {
        "series": "GeForce",
        "default_vram": 16,
        "keywords": ["rtx 5080", "rtx5080", "geforce rtx 5080"],
        "architecture": "Blackwell"
    },
    "RTX 5090": {
        "series": "GeForce",
        "default_vram": 32,
        "keywords": ["rtx 5090", "rtx5090", "geforce rtx 5090"],
        "architecture": "Blackwell"
    },
    "Titan RTX": {
        "series": "Titan",
        "default_vram": 24,
        "keywords": ["titan rtx", "titan-rtx"],
        "architecture": "Turing"
    },

    # --- Série Profissional / Datacenter (Tesla) ---
    "Tesla P40": {
        "series": "Tesla / Data Center",
        "default_vram": 24,
        "keywords": ["tesla p40", "p40 24gb", "nvidia p40"],
        "architecture": "Pascal"
    },
    "Tesla M40": {
        "series": "Tesla / Data Center",
        "default_vram": 24,
        "keywords": ["tesla m40", "m40 24gb", "nvidia m40"],
        "architecture": "Maxwell"
    },
    "Tesla K80": {
        "series": "Tesla / Data Center",
        "default_vram": 24,
        "keywords": ["tesla k80", "k80 24gb", "nvidia k80"],
        "architecture": "Kepler"
    },
    "Tesla V100": {
        "series": "Tesla / Data Center",
        "default_vram": 16, # Existem versões de 16GB e 32GB
        "keywords": ["tesla v100", "v100 16gb", "v100 32gb", "nvidia v100"],
        "architecture": "Volta"
    },
    "Tesla T4": {
        "series": "Tesla / Data Center",
        "default_vram": 16,
        "keywords": ["tesla t4", "nvidia t4", "t4 16gb"],
        "architecture": "Turing"
    },
    "Tesla P100": {
        "series": "Tesla / Data Center",
        "default_vram": 16,
        "keywords": ["tesla p100", "p100 16gb", "nvidia p100", "p100 hbm2"],
        "architecture": "Pascal"
    },

    # --- Série Profissional Quadro / RTX Workstation ---
    "Quadro RTX 5000": {
        "series": "Quadro RTX",
        "default_vram": 16,
        "keywords": ["quadro rtx 5000", "rtx 5000 quadro"],
        "architecture": "Turing"
    },
    "Quadro RTX 6000": {
        "series": "Quadro RTX",
        "default_vram": 24,
        "keywords": ["quadro rtx 6000", "rtx 6000 quadro"],
        "architecture": "Turing"
    },
    "Quadro P5000": {
        "series": "Quadro",
        "default_vram": 16,
        "keywords": ["quadro p5000", "p5000 16gb"],
        "architecture": "Pascal"
    },
    "Quadro P6000": {
        "series": "Quadro",
        "default_vram": 24,
        "keywords": ["quadro p6000", "p6000 24gb"],
        "architecture": "Pascal"
    },
    "Quadro M6000": {
        "series": "Quadro",
        "default_vram": 24, # Existem de 12GB e 24GB
        "keywords": ["quadro m6000", "m6000 24gb"],
        "architecture": "Maxwell"
    },
    "Quadro GP100": {
        "series": "Quadro",
        "default_vram": 16,
        "keywords": ["quadro gp100", "gp100 16gb"],
        "architecture": "Pascal"
    },
    "Quadro GV100": {
        "series": "Quadro",
        "default_vram": 32,
        "keywords": ["quadro gv100", "gv100 32gb"],
        "architecture": "Volta"
    },
    "RTX A4000": {
        "series": "RTX Workstation",
        "default_vram": 16,
        "keywords": ["rtx a4000", "a4000 16gb", "nvidia a4000"],
        "architecture": "Ampere"
    },
    "RTX A4500": {
        "series": "RTX Workstation",
        "default_vram": 20,
        "keywords": ["rtx a4500", "a4500 20gb", "nvidia a4500"],
        "architecture": "Ampere"
    },
    "RTX A5000": {
        "series": "RTX Workstation",
        "default_vram": 24,
        "keywords": ["rtx a5000", "a5000 24gb", "nvidia a5000"],
        "architecture": "Ampere"
    },
    "RTX 4000 Ada": {
        "series": "RTX Workstation",
        "default_vram": 20,
        "keywords": ["rtx 4000 ada", "4000 ada 20gb"],
        "architecture": "Ada Lovelace"
    }
}

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
            # Exceção apenas se explicitamente comparar ("melhor que radeon" etc)
            # Mas se contiver "rx 6800", "rx 7800", "radeon" é AMD
            if "radeon" in text_lower or "amd" in text_lower or "arc a770" in text_lower:
                return True
    return False

def extract_explicit_vram(text: str) -> Optional[int]:
    """Extrai valor explícito de VRAM em GB a partir do texto."""
    text_lower = text.lower()
    # Padrões comuns: '16gb', '24 gb', '32 giga', '16g'
    matches = re.findall(r"\b(8|10|11|12|16|20|24|32|48)\s*(?:gb|g\b|gigas?)\b", text_lower)
    if matches:
        # Retorna o maior número válido encontrado (caso mencione barramento ou outro número menor)
        nums = [int(m) for m in matches]
        # Dá preferência para os números entre 16 e 48
        high_nums = [n for n in nums if n in [16, 20, 24, 32, 48]]
        if high_nums:
            return high_nums[0]
        return nums[0]
    return None

def identify_gpu(title: str, description: str = "") -> Optional[Tuple[str, int]]:
    """
    Identifica se o anúncio é uma GPU NVIDIA com 16GB a 32GB de VRAM.
    Retorna uma tupla (nome_do_modelo, vram_em_gb) ou None se não atender aos critérios.
    """
    full_text = f"{title} {description}".lower()

    if is_non_nvidia(full_text):
        return None

    explicit_vram = extract_explicit_vram(full_text)

    # 1. Busca por modelos no catálogo
    for model_name, info in NVIDIA_HIGH_VRAM_CATALOG.items():
        matched = False
        for kw in info["keywords"]:
            if kw in full_text:
                matched = True
                break

        if not matched:
            continue

        # Verifica exclusões (ex: se é 'RTX 3090', não pode casar se tiver '3090 ti')
        if "exclude" in info:
            if any(exc in full_text for exc in info["exclude"]):
                continue

        # Modelos como 4060 Ti existem em 8GB e 16GB; se for 8GB, descarta
        if info.get("requires_explicit_vram"):
            if explicit_vram == 8:
                return None
            if explicit_vram != 16 and "16gb" not in full_text and "16 gb" not in full_text:
                return None

        # VRAM determinada
        vram = explicit_vram if (explicit_vram and explicit_vram in [16, 20, 24, 32]) else info["default_vram"]

        return (model_name, vram)

    # 2. Verificação genérica: título menciona "NVIDIA" ou "GeForce" ou "RTX" e tem 16GB a 32GB
    # Descarta se "16gb" ou "32gb" for claramente memória RAM do computador (ex: "32gb ram", "16gb ddr")
    if re.search(r"\b(16|24|32)\s*(?:gb)?\s*(?:de\s+)?(?:ram|ddr[45]|memoria\s+ram)\b", full_text):
        # Apenas aceita se também houver menção separada de VRAM ou modelo que tenha 16GB+
        return None

    # Descarta placas que sabidamente têm menos de 16GB de VRAM
    # (3050=8GB, 3060=12GB, 3060 Ti=8GB, 3070/Ti=8GB, 3080/Ti=10-12GB, 4060 normal=8GB, 4070 normal/super=12GB)
    if re.search(r"\b(?:rtx\s*3050|rtx\s*3060(?:\s*ti)?|rtx\s*3070(?:\s*ti)?|rtx\s*3080(?:\s*ti)?|rtx\s*4060(?!\s*ti\s*(?:16|16gb))|rtx\s*4070(?!\s*ti\s*super)|gtx\s*\d{3,4})\b", full_text):
        return None

    # Se for anúncio de PC Gamer / Desktop completo, a menção de '16gb' ou '32gb' é tipicamente RAM do sistema,
    # a menos que a placa de vídeo seja explicitamente uma do catálogo de 16GB+
    if re.search(r"\b(?:pc\s*gamer|computador|desktop|gabinete|setup|i[3579]|ryzen)\b", full_text):
        if not any(k in full_text for k in ["3090", "4080", "4090", "4070 ti super", "4060 ti 16", "tesla", "quadro", "a4000", "a5000"]):
            return None

    if re.search(r"\b(rtx|gtx|nvidia|quadro|tesla|titan)\b", full_text):
        if explicit_vram and 16 <= explicit_vram <= 32:
            match = re.search(r"\b(rtx\s*\d{4}(?:\s*ti)?(?:\s*super)?|quadro\s*[a-z0-9]+|tesla\s*[a-z0-9]+)\b", full_text)
            detected_name = match.group(0).upper() if match else f"NVIDIA {explicit_vram}GB"
            return (detected_name, explicit_vram)

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
