#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
    PYTHON_EXEC=".venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
else
    echo "Python não encontrado. Instale o Python 3.10+ para continuar."
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"


echo "Iniciando GPU Hunter..."
$PYTHON_EXEC run.py "$@"
