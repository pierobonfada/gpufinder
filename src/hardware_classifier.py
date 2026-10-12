import re
from typing import Optional, Tuple

# Padrões que identificam computadores completos, notebooks ou setups inteiros (NÃO placas avulsas)
SYSTEM_EXCLUSION_PATTERNS = [
    # Tipos de máquina / gabinetes
    r"\bpc\s+gamer\b",
    r"\bcomputador(?:\s+gamer)?\b",
    r"\bsetup(?:\s+gamer|\s+completo)?\b",
    r"\bdesktop(?:\s+gamer)?\b",
    r"\bcpu\s+gamer\b",
    r"\bgabinete(?:\s+gamer|\s+modular|\s+aquario|\s+vidro)?\b",
    r"\bnotebook(?:\s+gamer)?\b",
    r"\blaptop(?:\s+gamer)?\b",
    r"\bvivobook\b",
    r"\bpredator\s+helios\b",
    r"\bhelios\s+neo\b",
    r"\bnitro\s*5\b",
    r"\bdell\s+g15\b",
    r"\blenovo\s+loq\b",
    r"\bideapad\s+gaming\b",
    r"\bmacbook\b",
    
    # Processadores completos anunciados
    r"\bcore\s+i[3579]\b",
    r"\bi[3579][-\s]\d{4,5}[a-z]?\b",
    r"\bryzen\s+[3579](?:\s*\d{4}[a-z]*)?\b",
    r"\bxeon\s+e\d\b",
    
    # Memória RAM do sistema (confundida com VRAM)
    r"\b\d+\s*gb\s*(?:de\s+)?ram\b",
    r"\b\d+\s*gbram\b",
    r"\bmem[oó]ria\s+ram\b",
    r"\bddr[345]\s+\d+\s*gb\b",
    
    # Outros componentes de PC que indicam venda de máquina inteira
    r"\bssd\s+\d+\s*(?:gb|tb)\b",
    r"\bnvme\s+\d+\s*(?:gb|tb)\b",
    r"\bhd\s+\d+\s*(?:tb|gb)\b",
    r"\bfonte\s+\d+\s*w\b",
    r"\bwater\s*cooler\b",
    r"\bair\s*cooler\b",
    r"\bplaca\s*m[aã]e\b",
    r"\bkit\s+upgrade\b",
    r"\bkit\s+gamer\b",
    r"\bmonitor\s+\d+[\"']?\b",
    r"\bteclado\s+e\s+mouse\b"
]

# URLs proibidas (categorias de PC, notebooks, periféricos, etc)
URL_CATEGORY_EXCLUSIONS = [
    "/computadores-e-desktops/",
    "/notebooks/",
    "/celulares-e-telefonia/",
    "/videogames/",
    "/monitores/",
    "/fontes/",
    "/gabinetes/",
    "/processadores/",
    "/placas-mae/",
    "/memorias-ram/"
]

# Termos que confirmam expressamente placa de vídeo avulsa
POSITIVE_GPU_INDICATORS = [
    r"\bplaca\s+de\s+v[ií]deo\b",
    r"\bplaca\s+de\s+video\b",
    r"\bvga\b",
    r"\bgpu\b",
    r"\bvideo\s+card\b",
    r"\bgraphics\s+card\b"
]

def is_standalone_gpu(
    title: str, 
    description: str = "", 
    url: str = "", 
    category: str = ""
) -> Tuple[bool, str]:
    """
    Classificador rigoroso que garante que o anúncio se refere EXCLUSIVAMENTE
    a uma placa de vídeo avulsa, descartando PCs Gamer, Notebooks, Desktops,
    consoles e kits completos.
    
    Retorna (is_gpu: bool, reason: str).
    """
    url_lower = (url or "").lower()
    title_lower = (title or "").lower()
    desc_lower = (description or "").lower()
    full_text = f"{title_lower} {desc_lower}"

    # 1. Checagem de categoria de URL
    for forbidden_url in URL_CATEGORY_EXCLUSIONS:
        if forbidden_url in url_lower:
            return (False, f"URL pertence à categoria proibida ({forbidden_url})")

    # 2. Se o título anuncia explicitamente uma máquina completa
    # Ex: "Pc gamer 2k ultra", "Dell G15 Gamer i7", "Computador Gamer RTX 3060", "Notebook Acer"
    for pattern in SYSTEM_EXCLUSION_PATTERNS:
        if re.search(pattern, title_lower):
            # Exceção apenas se o título começar enfaticamente com "placa de vídeo" e disser "apenas a placa"
            if re.search(r"^placa\s+de\s+v[ií]deo\b", title_lower) and "apenas" in title_lower:
                continue
            return (False, f"Título indica computador/notebook completo ({pattern})")

    # 3. Na descrição: se listar especificação completa de PC (RAM + Processador + Gabinete + Fonte)
    pc_component_count = 0
    if re.search(r"\b(core\s+i[3579]|i[3579][-\s]\d{4,5}|ryzen\s+[3579]|xeon)\b", full_text):
        pc_component_count += 1
    if re.search(r"\b(ram|ddr[345]|memoria\s+ram)\b", full_text):
        pc_component_count += 1
    if re.search(r"\b(ssd|nvme|hd\s+\d+tb)\b", full_text):
        pc_component_count += 1
    if re.search(r"\b(gabinete|fonte\s+\d+w|water\s*cooler|placa\s+m[aã]e)\b", full_text):
        pc_component_count += 1

    # Se tiver 3 ou mais componentes de máquina inteira e não for expressamente a venda só da placa
    if pc_component_count >= 3:
        if not re.search(r"\b(vendo\s+apenas|somente\s+a\s+placa|vendo\s+separado)\b", full_text):
            return (False, f"Descrição descreve um setup/computador completo ({pc_component_count} componentes de PC)")

    # 4. Deve conter ao menos uma menção a GPU NVIDIA ou identificador de placa
    has_gpu_name = bool(re.search(r"\b(rtx|gtx|quadro|tesla|titan|geforce|nvidia|n730|gt\s*\d{3})\b", full_text))
    if not has_gpu_name:
        return (False, "Nenhum modelo de GPU NVIDIA reconhecido no anúncio")

    return (True, "Placa de vídeo avulsa válida")
