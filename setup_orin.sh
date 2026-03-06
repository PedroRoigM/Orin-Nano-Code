#!/usr/bin/env bash
# setup_orin.sh
# Crea/activa el entorno virtual ~/venv_cuda, comprueba las librerías del proyecto
# y lanza tensor_rt_orin.py en la Jetson Orin Nano.
#
# Uso:
#   chmod +x setup_orin.sh
#   ./setup_orin.sh

set -euo pipefail

PROJECT_DIR="/home/jetson/prueba"
VENV_DIR="$HOME/venv_cuda"
MAIN_SCRIPT="core/tensor_rt_orin.py"

RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GRN}[OK]${NC}  $*"; }
warn() { echo -e "${YEL}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; }

# ─────────────────────────────────────────────────────────────────────────────
# 1. Entorno virtual
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Entorno virtual: $VENV_DIR ==="

if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV_DIR" --system-site-packages
    ok "Entorno virtual creado (con --system-site-packages para acceder a TensorRT/PyCUDA/PyTorch del sistema)"
else
    ok "Entorno virtual ya existe"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
ok "Entorno virtual activado: $(python3 --version)"

# ─────────────────────────────────────────────────────────────────────────────
# 2. Actualizar pip
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Actualizando pip ==="
pip install --quiet --upgrade pip
ok "pip actualizado: $(pip --version)"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Librerías del sistema (JetPack) — solo verificar importabilidad
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Librerías del sistema (JetPack / CUDA) ==="

check_system_lib() {
    local module="$1"
    local label="$2"
    if python3 -c "import $module" 2>/dev/null; then
        ok "$label"
    else
        fail "$label — no encontrada. Instala JetPack o verifica PYTHONPATH."
        MISSING_SYSTEM=1
    fi
}

MISSING_SYSTEM=0
check_system_lib "tensorrt"    "tensorrt (JetPack)"
check_system_lib "torch"       "torch/PyTorch (JetPack)"
check_system_lib "torchvision" "torchvision (JetPack)"

# pycuda: puede no estar como paquete del sistema → compilar vía pip
if python3 -c "import pycuda" 2>/dev/null; then
    ok "pycuda"
else
    echo "  pycuda no encontrada, buscando cabeceras CUDA..."

    # Buscar cuda.h — en JetPack están bajo targets/aarch64-linux/include/
    CUDA_INC=""
    CUDA_ROOT_CANDIDATE=""
    for versioned in /usr/local/cuda /usr/local/cuda-*; do
        if [ -f "$versioned/include/cuda.h" ]; then
            CUDA_ROOT_CANDIDATE="$versioned"
            CUDA_INC="$versioned/include"
            break
        fi
        if [ -f "$versioned/targets/aarch64-linux/include/cuda.h" ]; then
            CUDA_ROOT_CANDIDATE="$versioned"
            CUDA_INC="$versioned/targets/aarch64-linux/include"
            break
        fi
    done

    if [ -z "$CUDA_INC" ]; then
        fail "pycuda — no se encontró cuda.h. Verifica que JetPack esté instalado."
        MISSING_SYSTEM=1
    else
        echo "  Cabeceras CUDA: $CUDA_INC"

        # Añadir nvcc al PATH (pycuda lo necesita para auto-detectar CUDA)
        NVCC_BIN="$CUDA_ROOT_CANDIDATE/bin"
        if [ -f "$NVCC_BIN/nvcc" ]; then
            export PATH="$NVCC_BIN:$PATH"
            echo "  nvcc: $NVCC_BIN/nvcc"
        else
            warn "  nvcc no encontrado en $NVCC_BIN — la compilación puede fallar"
        fi

        if pip install --quiet pycuda; then
            ok "pycuda (instalada vía pip)"
        else
            fail "pycuda — falló la compilación."
            warn "Prueba manualmente:"
            warn "  export PATH=/usr/local/cuda-12.6/bin:\$PATH"
            warn "  pip install pycuda"
            MISSING_SYSTEM=1
        fi
    fi
fi

if [ "$MISSING_SYSTEM" -ne 0 ]; then
    warn "Algunas librerías del sistema faltan. Continúa bajo tu responsabilidad."
fi

# ─────────────────────────────────────────────────────────────────────────────
# 4. Librerías pip — instalar si faltan
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Librerías pip ==="

install_if_missing() {
    local module="$1"
    local package="${2:-$1}"   # nombre pip (default = nombre de módulo)
    local label="${3:-$package}"

    if python3 -c "import $module" 2>/dev/null; then
        ok "$label"
    else
        echo "  Instalando $package..."
        if pip install --quiet "$package"; then
            ok "$label (instalada)"
        else
            fail "$label — error al instalar '$package'"
        fi
    fi
}

install_if_missing "cv2"            "opencv-python"          "opencv-python (cv2)"
install_if_missing "numpy"          "numpy"                  "numpy"
install_if_missing "serial"         "pyserial"               "pyserial"
install_if_missing "spidev"         "spidev"                 "spidev"
# Jetson.GPIO: siempre instalar en el venv para que la versión pip
# (con soporte Orin Nano) tome prioridad sobre la del sistema (/usr/lib/...)
echo "  Instalando/actualizando Jetson.GPIO en el venv..."
if pip install --quiet --force-reinstall Jetson.GPIO; then
    ok "Jetson.GPIO (versión pip en venv)"
else
    fail "Jetson.GPIO — error al instalar"
fi
install_if_missing "facenet_pytorch" "facenet-pytorch"       "facenet-pytorch"
install_if_missing "sounddevice"    "sounddevice"            "sounddevice"
install_if_missing "PIL"            "Pillow"                 "Pillow (PIL)"

# ─────────────────────────────────────────────────────────────────────────────
# 5. Permisos GPIO (aviso, no bloquea)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Permisos ==="

if groups | grep -qw gpio; then
    ok "Usuario en grupo 'gpio'"
else
    warn "Usuario NO está en el grupo 'gpio'."
    warn "Si falla Jetson.GPIO, ejecuta: sudo usermod -aG gpio \$USER && (vuelve a loguear)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 6. Verificar que el script principal existe
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== Proyecto ==="

if [ ! -d "$PROJECT_DIR" ]; then
    fail "Directorio del proyecto no encontrado: $PROJECT_DIR"
    exit 1
fi
ok "Directorio del proyecto: $PROJECT_DIR"

if [ ! -f "$PROJECT_DIR/$MAIN_SCRIPT" ]; then
    fail "Script principal no encontrado: $PROJECT_DIR/$MAIN_SCRIPT"
    exit 1
fi
ok "Script principal: $MAIN_SCRIPT"

# ─────────────────────────────────────────────────────────────────────────────
# 7. Lanzar
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "================================================================="
echo "  Lanzando tensor_rt_orin.py — Ctrl+C para detener"
echo "================================================================="
echo ""

cd "$PROJECT_DIR"
exec python3 "$MAIN_SCRIPT"
