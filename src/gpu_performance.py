"""
GPU Hunter - Mapeamento de Performance de Capacidade Computacional (GPGPU / IA / CUDA / FP32)
Fonte Oficial Confiável:
- NVIDIA Architecture Technical Specifications & Whitepapers (Pascal, Volta, Turing, Ampere, Ada Lovelace)
- TechPowerUp GPU Compute Database (FP32 Single-Precision TFLOPS & Tensor Compute)
FOCO EXCLUSIVO: Capacidade de Computação / IA / Machine Learning (TFLOPS FP32), NÃO jogos/games.
"""

from typing import Dict, List, Optional, Tuple

# Base de capacidade computacional oficial em Teraflops (FP32 TFLOPS)
# Quanto maior o número de TFLOPS, mais à direita a placa fica no eixo X.
GPU_COMPUTE_DATABASE: Dict[str, Dict] = {
    "Tesla K80": {
        "compute_tflops": 4.1,
        "tensor_tflops": 0.0,
        "memory_bandwidth_gbs": 480.0,
        "architecture": "Kepler (GK210)",
        "vram_gb": 24,
        "display_name": "Tesla K80 (4.1 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Tesla M40": {
        "compute_tflops": 7.0,
        "tensor_tflops": 0.0,
        "memory_bandwidth_gbs": 288.0,
        "architecture": "Maxwell (GM200)",
        "vram_gb": 24,
        "display_name": "Tesla M40 (7.0 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Quadro M6000": {
        "compute_tflops": 7.0,
        "tensor_tflops": 0.0,
        "memory_bandwidth_gbs": 317.0,
        "architecture": "Maxwell (GM200)",
        "vram_gb": 24,
        "display_name": "Quadro M6000 (7.0 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Tesla T4": {
        "compute_tflops": 8.1,
        "tensor_tflops": 65.0,
        "memory_bandwidth_gbs": 320.0,
        "architecture": "Turing (TU104)",
        "vram_gb": 16,
        "display_name": "Tesla T4 (8.1 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Quadro P5000": {
        "compute_tflops": 8.9,
        "tensor_tflops": 0.0,
        "memory_bandwidth_gbs": 288.0,
        "architecture": "Pascal (GP104)",
        "vram_gb": 16,
        "display_name": "Quadro P5000 (8.9 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Tesla P100": {
        "compute_tflops": 10.6,
        "tensor_tflops": 21.2, # FP16 Half Precision
        "memory_bandwidth_gbs": 732.0,
        "architecture": "Pascal (GP100 HBM2)",
        "vram_gb": 16,
        "display_name": "Tesla P100 (10.6 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Quadro GP100": {
        "compute_tflops": 10.6,
        "tensor_tflops": 21.2,
        "memory_bandwidth_gbs": 732.0,
        "architecture": "Pascal (GP100 HBM2)",
        "vram_gb": 16,
        "display_name": "Quadro GP100 (10.6 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Quadro RTX 5000": {
        "compute_tflops": 11.2,
        "tensor_tflops": 89.0,
        "memory_bandwidth_gbs": 448.0,
        "architecture": "Turing (TU104)",
        "vram_gb": 16,
        "display_name": "Quadro RTX 5000 (11.2 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Tesla P40": {
        "compute_tflops": 12.0,
        "tensor_tflops": 47.0, # INT8 Inference TOPS
        "memory_bandwidth_gbs": 346.0,
        "architecture": "Pascal (GP102)",
        "vram_gb": 24,
        "display_name": "Tesla P40 (12.0 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Quadro P6000": {
        "compute_tflops": 12.0,
        "tensor_tflops": 0.0,
        "memory_bandwidth_gbs": 432.0,
        "architecture": "Pascal (GP102)",
        "vram_gb": 24,
        "display_name": "Quadro P6000 (12.0 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Tesla V100": {
        "compute_tflops": 14.1,
        "tensor_tflops": 112.0,
        "memory_bandwidth_gbs": 900.0,
        "architecture": "Volta (GV100 HBM2)",
        "vram_gb": 16,
        "display_name": "Tesla V100 (14.1 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Quadro GV100": {
        "compute_tflops": 14.8,
        "tensor_tflops": 118.0,
        "memory_bandwidth_gbs": 870.0,
        "architecture": "Volta (GV100 HBM2)",
        "vram_gb": 32,
        "display_name": "Quadro GV100 (14.8 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Titan RTX": {
        "compute_tflops": 16.3,
        "tensor_tflops": 130.0,
        "memory_bandwidth_gbs": 672.0,
        "architecture": "Turing (TU102)",
        "vram_gb": 24,
        "display_name": "Titan RTX (16.3 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "Quadro RTX 6000": {
        "compute_tflops": 16.3,
        "tensor_tflops": 130.0,
        "memory_bandwidth_gbs": 672.0,
        "architecture": "Turing (TU102)",
        "vram_gb": 24,
        "display_name": "Quadro RTX 6000 (16.3 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX A4000": {
        "compute_tflops": 17.4,
        "tensor_tflops": 140.0,
        "memory_bandwidth_gbs": 448.0,
        "architecture": "Ampere (GA104)",
        "vram_gb": 16,
        "display_name": "RTX A4000 (17.4 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 4060 Ti 16GB": {
        "compute_tflops": 22.1,
        "tensor_tflops": 177.0,
        "memory_bandwidth_gbs": 288.0,
        "architecture": "Ada Lovelace (AD106)",
        "vram_gb": 16,
        "display_name": "RTX 4060 Ti 16GB (22.1 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX A4500": {
        "compute_tflops": 23.7,
        "tensor_tflops": 189.0,
        "memory_bandwidth_gbs": 640.0,
        "architecture": "Ampere (GA102)",
        "vram_gb": 20,
        "display_name": "RTX A4500 (23.7 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 4000 Ada": {
        "compute_tflops": 26.7,
        "tensor_tflops": 300.0,
        "memory_bandwidth_gbs": 360.0,
        "architecture": "Ada Lovelace (AD104)",
        "vram_gb": 20,
        "display_name": "RTX 4000 Ada (26.7 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX A5000": {
        "compute_tflops": 27.8,
        "tensor_tflops": 222.0,
        "memory_bandwidth_gbs": 768.0,
        "architecture": "Ampere (GA102)",
        "vram_gb": 24,
        "display_name": "RTX A5000 (27.8 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 3090": {
        "compute_tflops": 35.6,
        "tensor_tflops": 285.0,
        "memory_bandwidth_gbs": 936.0,
        "architecture": "Ampere (GA102)",
        "vram_gb": 24,
        "display_name": "RTX 3090 (35.6 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 3090 Ti": {
        "compute_tflops": 40.0,
        "tensor_tflops": 320.0,
        "memory_bandwidth_gbs": 1008.0,
        "architecture": "Ampere (GA102)",
        "vram_gb": 24,
        "display_name": "RTX 3090 Ti (40.0 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 4070 Ti Super": {
        "compute_tflops": 44.1,
        "tensor_tflops": 353.0,
        "memory_bandwidth_gbs": 672.0,
        "architecture": "Ada Lovelace (AD103)",
        "vram_gb": 16,
        "display_name": "RTX 4070 Ti Super (44.1 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 4080": {
        "compute_tflops": 48.7,
        "tensor_tflops": 390.0,
        "memory_bandwidth_gbs": 717.0,
        "architecture": "Ada Lovelace (AD103)",
        "vram_gb": 16,
        "display_name": "RTX 4080 (48.7 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 4080 Super": {
        "compute_tflops": 52.2,
        "tensor_tflops": 418.0,
        "memory_bandwidth_gbs": 736.0,
        "architecture": "Ada Lovelace (AD103)",
        "vram_gb": 16,
        "display_name": "RTX 4080 Super (52.2 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 4090": {
        "compute_tflops": 82.6,
        "tensor_tflops": 660.0,
        "memory_bandwidth_gbs": 1008.0,
        "architecture": "Ada Lovelace (AD102)",
        "vram_gb": 24,
        "display_name": "RTX 4090 (82.6 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 5080": {
        "compute_tflops": 57.0,
        "tensor_tflops": 900.0,
        "memory_bandwidth_gbs": 960.0,
        "architecture": "Blackwell (GB203)",
        "vram_gb": 16,
        "display_name": "RTX 5080 (57.0 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    },
    "RTX 5090": {
        "compute_tflops": 104.8,
        "tensor_tflops": 1600.0,
        "memory_bandwidth_gbs": 1792.0,
        "architecture": "Blackwell (GB202)",
        "vram_gb": 32,
        "display_name": "RTX 5090 (104.8 TFLOPS)",
        "source": "NVIDIA Whitepaper / TechPowerUp"
    }
}

DEFAULT_COMPUTE = {
    "compute_tflops": 15.0,
    "tensor_tflops": 100.0,
    "memory_bandwidth_gbs": 400.0,
    "architecture": "NVIDIA",
    "vram_gb": 16,
    "display_name": "NVIDIA Compute GPU",
    "source": "TechPowerUp Estimativa"
}

def normalize_model_name(name: str) -> str:
    n = name.strip()
    for key in GPU_COMPUTE_DATABASE:
        if key.lower() == n.lower():
            return key
        if key.lower() in n.lower():
            return key
    return n

def get_gpu_compute_data(model_name: str) -> Dict:
    """Retorna dados de capacidade computacional (FP32 TFLOPS) para o modelo."""
    norm = normalize_model_name(model_name)
    if norm in GPU_COMPUTE_DATABASE:
        return GPU_COMPUTE_DATABASE[norm]
    for key, data in GPU_COMPUTE_DATABASE.items():
        if key.lower() in norm.lower() or norm.lower() in key.lower():
            return data
    return DEFAULT_COMPUTE

def get_gpu_compute_tflops(model_name: str) -> float:
    """Retorna FP32 TFLOPS para posicionamento numérico e ordenação no eixo X."""
    return get_gpu_compute_data(model_name)["compute_tflops"]

def get_sorted_models_by_compute() -> List[str]:
    """Retorna todos os modelos de interesse ordenados do menor para o maior poder computacional."""
    return sorted(GPU_COMPUTE_DATABASE.keys(), key=lambda m: GPU_COMPUTE_DATABASE[m]["compute_tflops"])
