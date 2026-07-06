#!/usr/bin/env bash
# Smoke test do ambiente Python (Linux/Cloud).
# Uso: ./scripts/smoke_test_env.sh [python3.14]
# Valida: pip install, py_compile, pytest, imports críticos (barcodes).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${1:-python3}"
VENV="${TMPDIR:-/tmp}/artemis-smoke-venv"

echo "== ArtemiS smoke test =="
echo "Python: $($PYTHON --version)"
echo "Root:   $ROOT"
echo

rm -rf "$VENV"
"$PYTHON" -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install -q -U pip setuptools wheel
pip install -q -r "$ROOT/requirements-linux.txt" pytest

echo "[1/4] py_compile"
python -m py_compile "$ROOT/Main.py" "$ROOT/app/bootstrap.py"

echo "[2/4] font symlinks (Linux)"
for pair in "Arial.ttf:arial.ttf" "arialn.ttf:ARIALN.TTF" "arialnb.ttf:ARIALNB.TTF" "Morganite-Semibold.ttf:Morganite-SemiBold.ttf"; do
  link="${pair%%:*}"
  target="${pair##*:}"
  if [[ -f "$ROOT/fontes/$target" ]]; then
    ln -sf "$target" "$ROOT/fontes/$link"
  fi
done

echo "[3/4] pytest"
PYTHONPATH="$ROOT/dev_stubs:$ROOT" python -m pytest "$ROOT/tests/" -q

echo "[4/4] barcode imports"
PYTHONPATH="$ROOT/dev_stubs:$ROOT" python - <<'PY'
from app.utils.barcode_generator import (
    create_barcode_bytes,
    create_datamatrix_bytes,
    create_qrcode_bytes,
)
create_barcode_bytes('1234567890', 0.3, 8)
create_datamatrix_bytes('12345')
create_qrcode_bytes('test')
print('barcodes OK')
PY

echo
echo "OK: ambiente validado com $($PYTHON --version)"
