#!/usr/bin/env bash
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${MEDIAHUB_PREFIX:-$HOME/.local/share/media-hub}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/media-hub"
APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
WITH_AUTOSTART=0
WITH_FLATPAK=0

usage() {
    cat <<EOF
Användning: $0 [--autostart] [--flatpak]

  --autostart   skapa ~/.config/autostart/media-hub.desktop
  --flatpak     ge Snes9x-flatpaken läsåtkomst till ~/snes (användarnivå)

Installationskatalog: $PREFIX (ändra med MEDIAHUB_PREFIX)
EOF
}

for arg in "$@"; do
    case "$arg" in
        --autostart) WITH_AUTOSTART=1 ;;
        --flatpak) WITH_FLATPAK=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Okänt argument: $arg" >&2; usage; exit 2 ;;
    esac
done

if [ "$(id -u)" -eq 0 ]; then
    echo "Kör som vanlig användare, inte med sudo." >&2
    exit 1
fi

command -v python3 >/dev/null || { echo "python3 saknas" >&2; exit 1; }

echo "Installerar Media Hub i $PREFIX"
mkdir -p "$PREFIX"
tar -C "$SRC" \
    --exclude=.git \
    --exclude=.venv \
    --exclude=__pycache__ \
    --exclude=screenshots \
    -cf - . | tar -C "$PREFIX" -xf -

python3 -m venv "$PREFIX/.venv"
"$PREFIX/.venv/bin/pip" install --quiet --upgrade pip
"$PREFIX/.venv/bin/pip" install --quiet -r "$PREFIX/requirements.txt"

mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cp "$SRC/config/example.json" "$CONFIG_DIR/config.json"
    echo "Skapade $CONFIG_DIR/config.json - anpassa sökvägar, ikoner och ROM-kataloger."
else
    echo "Behåller befintlig konfiguration: $CONFIG_DIR/config.json"
fi

mkdir -p "$APPLICATIONS_DIR"
cat > "$APPLICATIONS_DIR/media-hub.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Media Hub
Comment=Local HTPC launcher
Exec="$PREFIX/.venv/bin/python" -m mediahub
Path=$PREFIX
Terminal=false
StartupWMClass=media-hub
Categories=AudioVideo;
EOF

if [ "$WITH_AUTOSTART" -eq 1 ]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$APPLICATIONS_DIR/media-hub.desktop" "$AUTOSTART_DIR/media-hub.desktop"
    echo "Autostart skapad: $AUTOSTART_DIR/media-hub.desktop"
fi

if [ "$WITH_FLATPAK" -eq 1 ]; then
    if flatpak list --app --columns=application 2>/dev/null | grep -qx com.snes9x.Snes9x; then
        flatpak override --user --filesystem="$HOME/snes" com.snes9x.Snes9x
        echo "Snes9x har fått läsåtkomst till $HOME/snes"
    else
        echo "Varning: com.snes9x.Snes9x är inte installerad, hoppar över flatpak-override." >&2
    fi
fi

cat <<EOF

Klart. Flex Launcher och AntiMicroX-profiler är orörda.

Starta:      "$PREFIX/.venv/bin/python" -m mediahub
Testläge:    "$PREFIX/.venv/bin/python" -m mediahub --windowed
Felsökning:  loggar skrivs till ${XDG_STATE_HOME:-$HOME/.local/state}/media-hub/media-hub.log

Verifiera på den riktiga HTPC:n: handkontroll, Firefox-handover, Snes9x och Guide-knappen.
Se README.md för testinstruktioner.
EOF
