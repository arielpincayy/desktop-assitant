#!/bin/sh
# Instala el lanzador "ULU" (menú de aplicaciones) con rutas de este checkout.
set -eu
dir="$(cd "$(dirname "$0")" && pwd)"
dest="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$dest"
cat > "$dest/ulu.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ULU
Comment=Recordatorios con ULU
Exec=$dir/mostrar-recordatorios.sh
Icon=$dir/assets/fantasmita.svg
Terminal=false
Categories=Utility;
StartupWMClass=ulu
EOF
update-desktop-database "$dest" 2>/dev/null || true
echo "Instalado: $dest/ulu.desktop"
