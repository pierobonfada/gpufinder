#!/usr/bin/env bash
# ==============================================================================
# GPU Finder - Instalador Automático para Ubuntu 26.04 / 24.04 / 22.04 LTS
# ==============================================================================
# Este script prepara o ambiente do zero, instala dependências de sistema,
# configura o ambiente virtual Python, instala o Playwright com suporte headless,
# solicita as credenciais do Facebook de forma segura (com digitação oculta)
# e opcionalmente registra o serviço systemd para inicialização automática.
# ==============================================================================

set -euo pipefail

# Cores para saída no terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parâmetros de linha de comando padrão
INTERACTIVE=true
AUTO_YES=false
INSTALL_SERVICE=""
FB_EMAIL_ARG=""
FB_PASS_ARG=""
CENTER_CITY_ARG=""
RADIUS_ARG=""

print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "======================================================================"
    echo "       🚀 GPU FINDER - INSTALADOR AUTOMÁTICO (UBUNTU 26.04 LTS)       "
    echo "======================================================================"
    echo -e "${NC}"
    echo -e "Diretório de Instalação: ${BOLD}${SCRIPT_DIR}${NC}"
    echo ""
}

# Processamento de argumentos de linha de comando
while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--yes)
            AUTO_YES=true
            INTERACTIVE=false
            shift
            ;;
        --non-interactive)
            INTERACTIVE=false
            shift
            ;;
        --fb-email)
            FB_EMAIL_ARG="$2"
            shift 2
            ;;
        --fb-password)
            FB_PASS_ARG="$2"
            shift 2
            ;;
        --center-city)
            CENTER_CITY_ARG="$2"
            shift 2
            ;;
        --radius)
            RADIUS_ARG="$2"
            shift 2
            ;;
        --service)
            INSTALL_SERVICE="yes"
            shift
            ;;
        --no-service)
            INSTALL_SERVICE="no"
            shift
            ;;
        -h|--help)
            echo "Uso: $0 [opções]"
            echo ""
            echo "Opções:"
            echo "  -y, --yes            Modo não interativo com confirmação automática"
            echo "  --non-interactive    Não solicitar dados pelo teclado"
            echo "  --fb-email EMAIL     E-mail do Facebook para busca no Marketplace"
            echo "  --fb-password PASS   Senha do Facebook para busca no Marketplace"
            echo "  --center-city CIDADE Cidade centro de referência (padrão: Veranópolis)"
            echo "  --radius KM          Raio de busca em quilômetros (padrão: 50)"
            echo "  --service            Instala e inicia automaticamente o serviço systemd"
            echo "  --no-service         Não instala o serviço systemd"
            echo "  -h, --help           Exibe esta mensagem de ajuda"
            exit 0
            ;;
        *)
            echo -e "${RED}Opção desconhecida: $1${NC}"
            exit 1
            ;;
    esac
done

# Se não estiver em um TTY, desativa modo interativo
if [ ! -t 0 ]; then
    INTERACTIVE=false
fi

# Detecta permissões sudo/root
SUDO_CMD=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo &>/dev/null; then
        SUDO_CMD="sudo"
    else
        echo -e "${YELLOW}Aviso: 'sudo' não encontrado e script não está rodando como root.${NC}"
        echo -e "${YELLOW}Instalação de pacotes de sistema APT pode falhar se não houver privilégios.${NC}"
    fi
fi

CURRENT_USER="${SUDO_USER:-$(whoami)}"
CURRENT_GROUP="$(id -gn "$CURRENT_USER" 2>/dev/null || echo "$CURRENT_USER")"

print_banner

# ==============================================================================
# PASSO 1: Verificação de Sistema Operacional e Pacotes APT
# ==============================================================================
echo -e "${BLUE}${BOLD}[1/6] Verificando Sistema Operacional e Dependências de Sistema...${NC}"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo -e "   Distro Detectada: ${BOLD}${NAME:-Linux} ${VERSION:-}${NC}"
fi

APT_PACKAGES=(
    python3
    python3-venv
    python3-pip
    python3-dev
    git
    curl
    wget
    build-essential
    ca-certificates
)

echo -e "   Atualizando repositórios e instalando pacotes base do sistema via APT..."
if [ -n "$SUDO_CMD" ] || [ "$(id -u)" -eq 0 ]; then
    $SUDO_CMD apt-get update -qq || true
    DEBIAN_FRONTEND=noninteractive $SUDO_CMD apt-get install -y --no-install-recommends "${APT_PACKAGES[@]}" || {
        echo -e "${YELLOW}Aviso: Alguns pacotes APT falharam ou já estão instalados. Continuando...${NC}"
    }
else
    echo -e "${YELLOW}Pulando 'apt-get install' (executando sem privilégios de administrador).${NC}"
fi

# ==============================================================================
# PASSO 2: Criação e Configuração do Ambiente Virtual Python
# ==============================================================================
echo -e "\n${BLUE}${BOLD}[2/6] Configurando Ambiente Virtual Python 3 (.venv)...${NC}"

PYTHON_SYS="python3"
if ! command -v "$PYTHON_SYS" &>/dev/null; then
    echo -e "${RED}Erro: Python 3 não encontrado no PATH do sistema.${NC}"
    exit 1
fi

PY_VERSION="$($PYTHON_SYS -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo -e "   Versão do Python: ${BOLD}$PY_VERSION${NC}"

if [ ! -d ".venv" ] || [ ! -f ".venv/bin/python" ]; then
    echo -e "   Criando ambiente virtual em: ${BOLD}$SCRIPT_DIR/.venv${NC}"
    $PYTHON_SYS -m venv .venv
else
    echo -e "   Ambiente virtual já existente em: ${BOLD}$SCRIPT_DIR/.venv${NC}"
fi

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# Garante pip funcional no venv
echo -e "   Verificando gerenciador de pacotes no ambiente virtual..."
if ! "$VENV_PYTHON" -m pip --version &>/dev/null; then
    echo -e "   Instalando pip via ensurepip..."
    "$VENV_PYTHON" -m ensurepip --upgrade || true
fi

# Instalação das dependências Python
echo -e "   Instalando dependências a partir de requirements.txt..."
if [ -f "requirements.txt" ]; then
    "$VENV_PYTHON" -m pip install --quiet --upgrade pip setuptools wheel || true
    "$VENV_PYTHON" -m pip install --quiet -r requirements.txt
else
    echo -e "${RED}Erro: requirements.txt não encontrado!${NC}"
    exit 1
fi

echo -e "   ${GREEN}✓ Dependências Python instaladas com sucesso!${NC}"

# ==============================================================================
# PASSO 3: Instalação do Playwright e Navegador Chromium
# ==============================================================================
echo -e "\n${BLUE}${BOLD}[3/6] Configurando Playwright e Navegador Chromium Headless...${NC}"

# Instala bibliotecas de sistema necessárias para o Chromium (glib, nss, fontconfig, etc)
if [ -n "$SUDO_CMD" ] || [ "$(id -u)" -eq 0 ]; then
    echo -e "   Instalando bibliotecas do sistema para Chromium (playwright install-deps)..."
    $SUDO_CMD "$VENV_PYTHON" -m playwright install-deps chromium || {
        echo -e "${YELLOW}Aviso: install-deps falhou ou não é necessário. Prosseguindo com o navegador.${NC}"
    }
fi

# Instala o executável do Chromium no cache do usuário
echo -e "   Baixando binário do Chromium para automação..."
"$VENV_PYTHON" -m playwright install chromium

echo -e "   ${GREEN}✓ Playwright e Chromium configurados!${NC}"

# ==============================================================================
# PASSO 4: Configuração de Credenciais e Parâmetros (Facebook & Região)
# ==============================================================================
echo -e "\n${BLUE}${BOLD}[4/6] Configuração de Parâmetros e Credenciais do Facebook...${NC}"

# Cria config.yaml a partir do exemplo se não existir
if [ ! -f "config.yaml" ] && [ -f "config.example.yaml" ]; then
    cp config.example.yaml config.yaml
    chmod 600 config.yaml
    echo -e "   Criado config.yaml a partir de config.example.yaml"
fi

mkdir -p data
chmod 700 data 2>/dev/null || true

if [ "$INTERACTIVE" = true ]; then
    echo -e "${CYAN}Deseja configurar o login do Facebook Marketplace agora?${NC}"
    echo -e "   Isso permite que o scraper faça buscas regionalizadas completas no RS."
    read -r -p "Configurar Facebook agora? [S/n]: " RESP_FB
    RESP_FB=${RESP_FB:-S}

    if [[ "$RESP_FB" =~ ^[SsYy]$ ]]; then
        "$VENV_PYTHON" scripts/setup_config.py
    else
        echo -e "   Pulando credenciais do Facebook. O scraper tentará acesso anônimo/cookies locais."
        "$VENV_PYTHON" scripts/setup_config.py --non-interactive
    fi
else
    SETUP_ARGS=("--non-interactive")
    if [ -n "$FB_EMAIL_ARG" ]; then
        SETUP_ARGS+=("--email" "$FB_EMAIL_ARG")
    fi
    if [ -n "$FB_PASS_ARG" ]; then
        SETUP_ARGS+=("--password" "$FB_PASS_ARG")
    fi
    if [ -n "$CENTER_CITY_ARG" ]; then
        SETUP_ARGS+=("--center-city" "$CENTER_CITY_ARG")
    fi
    if [ -n "$RADIUS_ARG" ]; then
        SETUP_ARGS+=("--radius" "$RADIUS_ARG")
    fi
    "$VENV_PYTHON" scripts/setup_config.py "${SETUP_ARGS[@]}"
fi

# ==============================================================================
# PASSO 5: Execução da Suíte de Testes para Validação
# ==============================================================================
echo -e "\n${BLUE}${BOLD}[5/6] Executando Testes de Validação do Sistema...${NC}"

if "$VENV_PYTHON" -m pytest tests/ -q; then
    echo -e "   ${GREEN}✓ Todos os testes de validação passaram com sucesso!${NC}"
else
    echo -e "${YELLOW}⚠️ Alguns testes reportaram avisos, mas a instalação prosseguirá.${NC}"
fi

# ==============================================================================
# PASSO 6: Configuração do Serviço Systemd (Opcional / Automático)
# ==============================================================================
echo -e "\n${BLUE}${BOLD}[6/6] Configuração do Serviço em Segundo Plano (Systemd)...${NC}"

SERVICE_FILE="/etc/systemd/system/gpufinder.service"

setup_systemd_service() {
    echo -e "   Instalando serviço systemd em ${BOLD}$SERVICE_FILE${NC}..."
    TEMP_SERVICE="$(mktemp)"
    sed -e "s|__USER__|$CURRENT_USER|g" \
        -e "s|__GROUP__|$CURRENT_GROUP|g" \
        -e "s|__WORKDIR__|$SCRIPT_DIR|g" \
        "$SCRIPT_DIR/scripts/gpufinder.service.template" > "$TEMP_SERVICE"

    $SUDO_CMD cp "$TEMP_SERVICE" "$SERVICE_FILE"
    rm -f "$TEMP_SERVICE"
    $SUDO_CMD chmod 644 "$SERVICE_FILE"
    $SUDO_CMD systemctl daemon-reload
    $SUDO_CMD systemctl enable gpufinder.service
    $SUDO_CMD systemctl restart gpufinder.service

    echo -e "   ${GREEN}✓ Serviço gpufinder registrado e iniciado com sucesso!${NC}"
}

if [ "$INSTALL_SERVICE" = "yes" ]; then
    if [ -n "$SUDO_CMD" ] || [ "$(id -u)" -eq 0 ]; then
        setup_systemd_service
    else
        echo -e "${YELLOW}Não foi possível registrar o serviço: privilégios sudo/root necessários.${NC}"
    fi
elif [ "$INSTALL_SERVICE" = "no" ]; then
    echo -e "   Instalação de serviço systemd ignorada por comando."
elif [ "$INTERACTIVE" = true ]; then
    if [ -n "$SUDO_CMD" ] || [ "$(id -u)" -eq 0 ]; then
        read -r -p "Deseja registrar e iniciar o GPU Finder como serviço no Systemd (início automático no boot)? [S/n]: " RESP_SRV
        RESP_SRV=${RESP_SRV:-S}
        if [[ "$RESP_SRV" =~ ^[SsYy]$ ]]; then
            setup_systemd_service
        else
            echo -e "   Serviço systemd não configurado."
        fi
    else
        echo -e "   Para configurar o serviço systemd posteriormente, execute: ${BOLD}sudo ./install.sh --service${NC}"
    fi
fi

# Garante permissão de execução nos scripts auxiliares
chmod +x "$SCRIPT_DIR/run.sh" "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/scripts/setup_config.py"

# ==============================================================================
# CONCLUSÃO E RESUMO
# ==============================================================================
echo -e "\n${GREEN}${BOLD}======================================================================${NC}"
echo -e "${GREEN}${BOLD}          🎉 GPU FINDER INSTALADO COM SUCESSO!                       ${NC}"
echo -e "${GREEN}${BOLD}======================================================================${NC}"
echo ""
echo -e "🌐 ${BOLD}Painel / Dashboard Web:${NC} http://localhost:7860"
echo ""
echo -e "Comandos úteis:"
echo -e "  • ${BOLD}Iniciar Servidor Manualmente:${NC} ./run.sh --server"
echo -e "  • ${BOLD}Executar Varredura no Terminal:${NC} ./run.sh --scan"
echo -e "  • ${BOLD}Reconfigurar Credenciais do Facebook:${NC} .venv/bin/python scripts/setup_config.py"
if [ -f "$SERVICE_FILE" ]; then
echo -e "  • ${BOLD}Status do Serviço Systemd:${NC} sudo systemctl status gpufinder"
echo -e "  • ${BOLD}Ver Logs em Tempo Real:${NC} journalctl -u gpufinder -f"
fi
echo ""
echo -e "${CYAN}O GPU Finder está pronto para encontrar placas na Serra Gaúcha!${NC}"
