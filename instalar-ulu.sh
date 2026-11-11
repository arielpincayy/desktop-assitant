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

# Al iniciar sesión: anuncia los recordatorios que se perdieron con la PC apagada.
auto="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
mkdir -p "$auto"
cat > "$auto/ulu-pendientes.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ULU pendientes
Exec=$dir/.venv/bin/python $dir/recordar.py --pendientes
Terminal=false
EOF
echo "Instalado: $auto/ulu-pendientes.desktop"
