#!/bin/bash
set -e

echo "=== Configurando cámara en Jetson Orin Nano ==="

# Verificar que jetson-io existe
if [ ! -f /opt/nvidia/jetson-io/jetson-io.py ]; then
    echo "ERROR: No se encuentra /opt/nvidia/jetson-io/jetson-io.py"
    exit 1
fi

# Lanzar la herramienta de configuración
sudo python3 /opt/nvidia/jetson-io/jetson-io.py

echo "=== Configuración completada ==="
echo "Reinicia el sistema para aplicar los cambios:"
echo "  sudo reboot"