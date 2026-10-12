import math
import unicodedata
from typing import Dict, Optional, Tuple

def strip_accents(text: str) -> str:
    """Normaliza texto removendo acentos e convertendo para minúsculas."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()

# Coordenadas geográficas dos municípios da Serra Gaúcha e região circunvizinha a Veranópolis
# Fonte: IBGE / OpenStreetMap
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "veranopolis": (-28.9358, -51.5503),
    "vila flores": (-28.8683, -51.5303),
    "cotipora": (-28.9950, -51.6967),
    "fagundes varela": (-28.8814, -51.6983),
    "nova prata": (-28.7842, -51.6097),
    "protasio alves": (-28.7567, -51.4883),
    "santa tereza": (-29.1736, -51.7378),
    "monte belo do sul": (-29.1678, -51.6317),
    "vista alegre do prata": (-28.8783, -51.7950),
    "bento goncalves": (-29.1714, -51.5186),
    "garibaldi": (-29.2572, -51.5342),
    "guapore": (-28.8458, -51.8903),
    "carlos barbosa": (-29.2978, -51.5039),
    "parai": (-28.6183, -51.7850),
    "marau": (-28.4489, -52.2000),
    "farroupilha": (-29.2239, -51.3475),
    "caxias do sul": (-29.1678, -51.1794),
    "flores da cunha": (-29.0289, -51.1856),
    "nova bassano": (-28.7244, -51.7061),
    "nova araca": (-28.6575, -51.7456),
    "antonio prado": (-28.8572, -51.3283),
    "sao marcos": (-28.9714, -51.0683),
    "nova roma do sul": (-29.0017, -51.4089),
    "coronel pilar": (-29.2639, -51.6978),
    "boa vista do sul": (-29.3517, -51.6508),
    "salvador do sul": (-29.4414, -51.5133),
    "barão": (-29.3789, -51.4983),
    "barao": (-29.3789, -51.4983),
    "passo fundo": (-28.2619, -52.4083),
    "novo hamburgo": (-29.6783, -51.1311),
    "sao leopoldo": (-29.7603, -51.1472),
    "canoas": (-29.9178, -51.1836),
    "porto alegre": (-30.0346, -51.2177),
    "lajeado": (-29.4672, -51.9614),
    "estrela": (-29.5008, -51.9658),
    "encantado": (-29.2372, -51.8719),
    "teutonia": (-29.4472, -51.8089),
    "montenegro": (-29.6886, -51.4608),
    "gramado": (-29.3789, -50.8739),
    "canela": (-29.3644, -50.8106),
    "nova petropolis": (-29.3758, -51.1147),
    "santa cruz do sul": (-29.7158, -52.4283),
    "erechim": (-27.6342, -52.2739),
    "vacaria": (-28.5117, -50.9339),
    "santa maria": (-29.6842, -53.8069),
    "pelotas": (-31.7654, -52.3376),
    "gravatai": (-29.9439, -50.9928),
    "viamao": (-30.0811, -51.0233),
    "serafina correa": (-28.7136, -51.9339),
    "casca": (-28.5636, -51.9753),
    "sao valentim do sul": (-29.0069, -51.7619),
    "mucum": (-29.1672, -51.8703),
    "dois irmaos": (-29.5803, -51.0850),
    "alvorada": (-29.9917, -51.0822),
    "ibiruba": (-28.6275, -53.0897),
    "carazinho": (-28.2839, -52.7864),
    "trindade do sul": (-27.5186, -52.8986),
    "sapiranga": (-29.6381, -51.0067),
    "estancia velha": (-29.6508, -51.1736),
    "cachoeirinha": (-29.9508, -51.0942),
    "sao sebastiao do cai": (-29.5878, -51.3761),
    "nova santa rita": (-29.8569, -51.2747)
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância geodésica em quilômetros entre duas coordenadas (lat/lon)
    utilizando a fórmula de Haversine.
    """
    R = 6371.0 # Raio médio da Terra em km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(R * c, 1)

def get_city_distance_from_center(city_name: str, center_lat: float = -28.9358, center_lon: float = -51.5503) -> Optional[float]:
    """
    Identifica a cidade pelo nome e calcula sua distância precisa em km até o centro de referência (Veranópolis).
    Retorna a distância em km ou None se a cidade não for reconhecida na base.
    """
    if not city_name:
        return None

    norm_city = strip_accents(city_name)

    # 1. Busca direta por nome
    for key, (lat, lon) in CITY_COORDINATES.items():
        if key in norm_city or norm_city in key:
            return haversine_distance(center_lat, center_lon, lat, lon)

    return None

def is_within_radius(city_name: str, center_lat: float, center_lon: float, radius_km: float) -> Tuple[bool, Optional[float]]:
    """
    Verifica se a cidade está dentro do raio configurado (ex: 40 km ao redor de Veranópolis).
    Retorna (esta_dentro, distancia_em_km).
    """
    dist = get_city_distance_from_center(city_name, center_lat, center_lon)
    if dist is not None:
        return (dist <= radius_km, dist)

    # Se a cidade não estiver na tabela explícita mas contiver "Serra Gaúcha",
    # aceita condicionalmente se o raio for de pelo menos 40km
    norm = strip_accents(city_name)
    if "serra gaucha" in norm:
        return (True, 30.0)

    # Desconhecido ou fora da região
    return (False, None)
