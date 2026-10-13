# 🎯 GPU Finder - Buscador e Avaliador de Placas NVIDIA por Capacidade Computacional (TFLOPS) e Preço

O **GPU Finder** é um sistema completo e automatizado para rastrear, classificar e auditar placas de vídeo NVIDIA seminovas e usadas no **OLX**, **Facebook Marketplace** e **Mercado Livre**, focado na região de **Veranópolis - RS** e cidades da Serra Gaúcha (raio configurável).

O sistema conta com enriquecimento em tempo real de **Capacidade Computacional (FP32 TFLOPS)**, classificação comparativa contra a mediana do **Benchmark Nacional (Brasil todo)**, coloração visual por vantagem de preço (Verde/Laranja/Vermelho), filtro anti-PC Gamer (exclui anúncios de computadores completos e memória RAM de sistema) e painel interativo com Plotly.js.

---

## ✨ Funcionalidades Principais

1. **Filtros Específicos de Hardware NVIDIA**:
   - Abrange tanto modelos GeForce (ex: **RTX 3090 24GB**, **RTX 4080 16GB**, **RTX 4070 Ti Super 16GB**, **RTX 4060 Ti 16GB**, **Titan RTX 24GB**) quanto modelos de Datacenter e Estação de Trabalho (**Tesla P40 24GB**, **Tesla M40 24GB**, **Tesla V100 16/32GB**, **Quadro RTX 5000/6000**, **Quadro P5000/P6000**, **Quadro M6000 24GB**, **RTX A4000/A5000**, etc.).
   - Rejeição automática de placas AMD (Radeon RX) e Intel Arc.
   - Rejeição de modelos com menos de 16GB (ex: 4060 Ti de 8GB é automaticamente descartada).

2. **Geolocalização Customizada (Veranópolis - RS + Raio de 40km)**:
   - Cidades monitoradas: **Veranópolis**, **Bento Gonçalves**, **Nova Prata**, **Cotiporã**, **Vila Flores**, **Fagundes Varela**, **Garibaldi**, **Carlos Barbosa**, **Guaporé**, **Farroupilha**, etc.
   - Raio e cidades facilmente ajustáveis via `config.yaml` ou direto no painel web.

3. **Detecção e Diferenciação Visual de Placas com Defeito**:
   - Heurística que varre termos como *"com defeito"*, *"para conserto"*, *"para peças"*, *"não dá vídeo"*, *"queimada"*, *"sucata"*, *"dando artefatos"*, *"precisa de reparo"*.
   - Tratamento de negações (*"sem defeito"*, *"funcionando perfeitamente"* não são marcadas incorretamente).
   - **Placas Boas / Funcionais**: Exibidas em **VERDE** (`#10B981`).
   - **Placas com Defeito / Peças**: Exibidas em **VERMELHO** (`#EF4444`).

4. **Gráfico Interativo de Dispersão e Outliers (Plotly.js)**:
   - Eixo X com os modelos encontrados, Eixo Y com os preços em Reais.
   - Outliers destacados com anel dourado pulsante e formato diferenciado.
   - **Passe o mouse**: Card flutuante com foto, título, modelo, VRAM, preço, status de funcionamento e comparativo nacional.
   - **Clique no ponto**: **Abre imediatamente o anúncio original** do OLX ou Facebook em uma nova aba do navegador!

5. **Benchmark Nacional (Preço Brasil Todo)**:
   - Para cada modelo encontrado na região, o sistema avalia a mediana de preços de seminovos em todo o Brasil.
   - Classifica o anúncio local como:
     - 🚀 **Oportunidade / Muito Barata** (Mais de 20% abaixo da mediana nacional)
     - 🟢 **Barata** (8% a 20% abaixo)
     - ⚪ **Na Média** (dentro de ±10% da mediana)
     - 🟠 **Cara** (10% a 25% acima)
     - 🔴 **Muito Cara** (Mais de 25% acima)

6. **Autenticação e Suporte ao Facebook Marketplace**:
   - Integração com automação de navegador via **Playwright**.
   - Aceita credenciais de e-mail e senha no `config.yaml` ou variáveis de ambiente.
   - Persistência de cookies e sessão em `data/fb_session.json` após o primeiro login.

---

## 📦 Instalação Automática no Ubuntu 26.04 LTS (e 24.04 / 22.04)

O GPU Finder possui um instalador totalmente automatizado (`install.sh`) que:
1. Atualiza e instala todas as dependências de sistema via APT (`python3`, `python3-venv`, `python3-pip`, `git`, `build-essential`).
2. Cria o ambiente virtual isolado (`.venv`) e instala os pacotes do `requirements.txt`.
3. Instala o **Playwright Chromium** e todas as bibliotecas de sistema necessárias para execução headless.
4. **Solicita interativamente as credenciais do Facebook Marketplace** (com digitação oculta de senha via `getpass`/`read -s`).
5. Protege o arquivo `config.yaml` com permissões restritas de leitura/escrita (`chmod 600`).
6. Valida todo o sistema executando a suíte de testes automatizados (`pytest`).
7. Oferece o registro automático do serviço no **Systemd** (`gpufinder.service`) para inicialização no boot.

### ⚡ Passo a Passo Rápido

Basta clonar o repositório e executar o instalador:

```bash
git clone git@github.com:pierobonfada/gpufinder.git
cd gpufinder
chmod +x install.sh
./install.sh
```

Durante a execução, o instalador perguntará:
- **E-mail do Facebook** (opcional, pressione Enter para pular);
- **Senha do Facebook** (a digitação fica oculta no terminal por segurança);
- **Cidade centro de referência** (padrão: `Veranópolis`);
- **Raio de busca em km** (padrão: `50`);
- **Deseja instalar como serviço Systemd?** (`S/n`).

---

### 🤖 Modo Não Interativo / Desatendido (CI/CD ou Servidor VPS)

Para instalar sem nenhuma interação no teclado (100% silencioso):

```bash
# Instalação completa aceitando todos os padrões
./install.sh -y

# Ou passando credenciais e parâmetros diretamente por argumentos:
./install.sh \
  --non-interactive \
  --fb-email "seu_email@facebook.com" \
  --fb-password "sua_senha_secreta" \
  --center-city "Veranópolis" \
  --radius 50 \
  --service
```

---

## 🚀 Como Executar

### 1. Iniciar o Dashboard Web Interativo (Recomendado)
Para abrir o servidor local com o painel gráfico completo:
```bash
./run.sh
```
ou
```bash
./run.sh --server
```
Abra o navegador em: **`http://localhost:7860`**

### 2. Executar Varredura Rápida via Terminal (Modo CLI)
Se quiser apenas ver o relatório impresso no terminal:
```bash
./run.sh --scan
```

### 3. Gerenciamento pelo Systemd (Serviço em Segundo Plano)
Se o serviço foi configurado no instalador:
```bash
# Iniciar o serviço
sudo systemctl start gpufinder

# Parar o serviço
sudo systemctl stop gpufinder

# Ver status operacional
sudo systemctl status gpufinder

# Acompanhar logs em tempo real
journalctl -u gpufinder -f
```

---

## ⚙️ Configuração (`config.yaml`)

Todos os parâmetros são editáveis no arquivo `config.yaml` ou diretamente no botão **"Configurações"** do Dashboard Web:

```yaml
# Filtros de Hardware da GPU
hardware:
  brand: "nvidia"
  min_vram_gb: 16                    # Mínimo de 16GB de VRAM
  max_vram_gb: 32                    # Máximo de 32GB de VRAM
  max_price_brl: 5000.0              # Teto de R$ 5.000
  min_price_brl: 150.0

# Localização e Raio de Busca
location:
  center_city: "Veranópolis"
  state: "RS"
  latitude: -28.9358
  longitude: -51.5503
  radius_km: 40                      # Raio de 40km
  target_cities:
    - "Veranópolis"
    - "Bento Gonçalves"
    - "Nova Prata"
    - "Cotiporã"
    - "Vila Flores"
    - "Fagundes Varela"
    - "Garibaldi"
    - "Carlos Barbosa"
    - "Guaporé"
    - "Farroupilha"

# Autenticação Facebook Marketplace
scrapers:
  facebook:
    enabled: true
    headless: true
    email: ""                        # Seu e-mail do Facebook
    password: ""                     # Sua senha do Facebook
    session_file: "data/fb_session.json"
```

### 🔐 Autenticação no Facebook Marketplace
O Facebook exige login para permitir navegação ampla no Marketplace. Você pode fornecer suas credenciais de duas maneiras:
1. **Via `config.yaml` ou Painel Web**: Preencha os campos `email` e `password` no `config.yaml` ou clique em **"Configurações"** no Dashboard. O sistema fará o login automatizado via Playwright e salvará a sessão em `data/fb_session.json` para não precisar logar novamente.
2. **Via Variáveis de Ambiente**:
   ```bash
   export FB_EMAIL="seu_email@facebook.com"
   export FB_PASSWORD="sua_senha"
   ./run.sh
   ```

---

## 🧪 Testes Automatizados

Para rodar a suíte de testes unitários:
```bash
PYTHONPATH=. .venv/bin/pytest tests/ -v
```
Testes inclusos:
- Identificação precisa de GPUs NVIDIA com 16GB a 32GB.
- Rejeição de GPUs de marcas concorrentes (AMD Radeon, Intel Arc) e placas < 16GB.
- Detecção precisa de defeitos e negações.
- Cálculo de outliers estatísticos pelo método IQR.
- Enriquecimento e cálculo de desconto contra a média nacional.

---

## 📁 Estrutura do Projeto

```
gpu_hunter/
├── config.yaml                  # Configurações do usuário (preço, raio, cidades, Facebook)
├── config.example.yaml          # Template de backup das configurações
├── run.py                       # Ponto de entrada CLI e Web
├── run.sh                       # Script de inicialização rápida
├── data/
│   ├── listings.json            # Base de anúncios coletados
│   ├── benchmark_cache.json     # Cache estatístico nacional de preços
│   └── fb_session.json          # Sessão e cookies salvos do Facebook
├── src/
│   ├── config.py                # Leitor/Validador Pydantic do config.yaml
│   ├── models.py                # Modelos de dados
│   ├── gpu_catalog.py           # Catálogo e analisador de modelos NVIDIA 16GB-32GB
│   ├── defect_detector.py       # Detector heurístico de placas com defeito/peças
│   ├── outlier_detector.py      # Calculador de outliers IQR
│   ├── benchmark.py             # Motor de comparação com o mercado nacional (Brasil todo)
│   ├── engine.py                # Pipeline orquestrador das buscas
│   ├── scrapers/
│   │   ├── base.py              # Interface base dos scrapers
│   │   ├── olx_scraper.py       # Scraper OLX (regional Serra Gaúcha e nacional Brasil)
│   │   ├── facebook_scraper.py  # Scraper Playwright Facebook Marketplace
│   │   └── sample_generator.py  # Dados semente realistas da região para visualização inicial
│   └── web/
│       ├── app.py               # Servidor FastAPI com endpoints REST
│       └── static/
│           ├── index.html       # Dashboard web moderno (Tailwind + Plotly)
│           ├── app.js           # Lógica do gráfico, hover card e clique-para-abrir
│           └── style.css        # Efeitos visuais e animações
└── tests/
    └── test_gpu_hunter.py       # Testes unitários do sistema
```
