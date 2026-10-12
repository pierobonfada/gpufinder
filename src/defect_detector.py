import re
import unicodedata
from typing import List, Tuple
from src.models import GPUCondition

def strip_accents(text: str) -> str:
    """Remove acentos e normaliza para minúsculas para comparação robusta."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()

class DefectDetector:
    def __init__(self, keywords: List[str] = None, negation_keywords: List[str] = None):
        self.raw_keywords = keywords or [
            "com defeito", "para conserto", "para peças", "para pecas",
            "retirada de peças", "retirada de pecas", "não dá vídeo",
            "nao da video", "sem vídeo", "sem video", "queimada",
            "sucata", "tela preta", "com artefato", "dando artefato",
            "artefatos", "precisa de reparo", "para reparo", "no estado",
            "liga mas não dá vídeo", "liga mas nao da video",
            "sem garantia de funcionamento", "queimou", "em curto",
            "precisa trocar chip", "reballing"
        ]

        self.raw_negations = negation_keywords or [
            "sem defeito", "sem defeitos", "nenhum defeito",
            "100% funcionando", "funcionando perfeitamente",
            "teste na hora", "testada e aprovada", "zero defeito",
            "nunca foi aberta", "em perfeito estado"
        ]

        # Normaliza palavras para busca rápida
        self.normalized_keywords = [strip_accents(kw) for kw in self.raw_keywords]
        self.normalized_negations = [strip_accents(neg) for neg in self.raw_negations]

    def analyze(self, title: str, description: str = "") -> Tuple[GPUCondition, List[str]]:
        """
        Analisa o título e descrição do anúncio para determinar se é uma placa funcional ou com defeito.
        Retorna (GPUCondition, lista_de_motivos_encontrados).
        """
        full_text = f"{title} {description}"
        norm_text = strip_accents(full_text)

        matched_reasons = []

        # 1. Verifica ocorrência de termos indicativos de defeito
        for raw_kw, norm_kw in zip(self.raw_keywords, self.normalized_keywords):
            # Busca de palavra exata ou frase no texto normalizado
            pattern = r"(?:\b|_)" + re.escape(norm_kw) + r"(?:\b|_)"
            if re.search(pattern, norm_text):
                # Checa se há uma negação colada ou explícita (ex: 'sem defeito')
                is_negated = False
                for raw_neg, norm_neg in zip(self.raw_negations, self.normalized_negations):
                    if norm_neg in norm_text:
                        # Se a negação inclui o termo pesquisado, desconsidera
                        if norm_kw in norm_neg:
                            is_negated = True
                            break

                if not is_negated:
                    matched_reasons.append(raw_kw)

        if matched_reasons:
            return (GPUCondition.DEFECTIVE, list(set(matched_reasons)))

        return (GPUCondition.WORKING, [])
