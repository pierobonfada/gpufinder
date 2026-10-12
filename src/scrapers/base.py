from abc import ABC, abstractmethod
from typing import List
from src.models import GPUListing

class BaseScraper(ABC):
    @abstractmethod
    async def search_regional(self, query: str) -> List[GPUListing]:
        """Busca anúncios na região configurada (raio de 40km ao redor de Veranópolis)."""
        pass

    @abstractmethod
    async def search_national(self, query: str) -> List[float]:
        """Busca preços do mesmo modelo em todo o Brasil para cálculo de benchmark."""
        pass
