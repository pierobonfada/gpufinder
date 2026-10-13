from typing import List
import numpy as np
from src.models import GPUListing, OutlierType

class OutlierDetector:
    @staticmethod
    def detect_outliers_iqr(listings: List[GPUListing]) -> List[GPUListing]:
        """
        Calcula outliers estatísticos comparando estritamente CADA PLACA com as IGUAIS A ELA
        (mesmo modelo de GPU), NUNCA comparando modelos diferentes entre si.

        Uma placa é classificada como Outlier (cor laranja) se estiver:
        - Muito mais barata que a distribuição/média das placas iguais (LOW_OUTLIER)
        - Muito mais cara que a distribuição/média das placas iguais (HIGH_OUTLIER)
        """
        if not listings:
            return listings

        # Reseta flags de outlier
        for item in listings:
            item.is_outlier = False
            item.outlier_type = OutlierType.NONE

        # 1. Avaliação individual contra o Benchmark Estatístico de Placas IGUAIS (mesmo modelo)
        for item in listings:
            if item.national_benchmark and item.national_benchmark.count >= 3:
                bm = item.national_benchmark
                # Limites IQR do modelo idêntico
                if bm.iqr > 0:
                    bm_lower_iqr = bm.q1_price - 1.5 * bm.iqr
                    bm_upper_iqr = bm.q3_price + 1.5 * bm.iqr
                else:
                    bm_lower_iqr = bm.min_price
                    bm_upper_iqr = bm.max_price

                # Limite por desvio percentual significativo da média das iguais (> 30% abaixo ou > 25% acima)
                mean_price = bm.mean_price or bm.median_price
                sig_lower = mean_price * 0.65  # 35% abaixo da média do modelo
                sig_upper = mean_price * 1.30  # 30% acima da média do modelo

                # Limiar efetivo do modelo
                effective_lower = min(bm_lower_iqr, sig_lower)
                effective_upper = max(bm_upper_iqr, sig_upper)

                if item.price < effective_lower or item.price < bm_lower_iqr:
                    item.is_outlier = True
                    item.outlier_type = OutlierType.LOW
                elif item.price > effective_upper or item.price > bm_upper_iqr:
                    item.is_outlier = True
                    item.outlier_type = OutlierType.HIGH

        # 2. Avaliação complementar por grupo local do EXATO MESMO MODELO E VRAM
        # (Apenas se houver pelo menos 3 unidades do MESMO modelo e VRAM na busca local)
        model_groups = {}
        for item in listings:
            model_groups.setdefault((item.detected_model, item.detected_vram_gb), []).append(item)

        for (model, vram), group in model_groups.items():
            if model == "Desconhecido":
                continue

            prices = [item.price for item in group if item.price > 0]
            if len(prices) >= 3:
                q1 = float(np.percentile(prices, 25))
                q3 = float(np.percentile(prices, 75))
                iqr = q3 - q1
                if iqr > 0:
                    local_lower = q1 - 1.5 * iqr
                    local_upper = q3 + 1.5 * iqr

                    for item in group:
                        if item.price < local_lower:
                            item.is_outlier = True
                            item.outlier_type = OutlierType.LOW
                        elif item.price > local_upper:
                            item.is_outlier = True
                            item.outlier_type = OutlierType.HIGH

        return listings
