#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".venv/bin/python" ]; then
    echo "⚠️ Ambiente virtual (.venv) não encontrado."
    echo "Execute o instalador automático primeiro:"
    echo "    ./install.sh"
    exit 1
fi

if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        echo "ℹ️ config.yaml não encontrado. Criando a partir de config.example.yaml..."
        cp config.example.yaml config.yaml
        chmod 600 config.yaml
    fi
fi

PYTHON_EXEC=".venv/bin/python"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

echo "Iniciando GPU Finder..."
exec $PYTHON_EXEC run.py "$@"
