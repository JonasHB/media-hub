#!/usr/bin/env bash
set -euo pipefail

PREFIX="${MEDIAHUB_PREFIX:-$HOME/.local/share/media-hub}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/media-hub"
APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
ASSUME_YES=0

for arg in "$@"; do
    case "$arg" in
        --yes) ASSUME_YES=1 ;;
        -h|--help)
            echo "Användning: $0 [--yes]"
            echo "Tar bort programmet men behåller konfigurationen i $CONFIG_DIR."
            exit 0
            ;;
        *) echo "Okänt argument: $arg" >&2; exit 2 ;;
    esac
done

if [ "$ASSUME_YES" -eq 0 ]; then
    read -r -p "Ta bort Media Hub från $PREFIX? [j/N] " answer
    case "$answer" in
        j|J|ja|Ja) ;;
        *) echo "Avbrutet."; exit 0 ;;
    esac
fi

rm -rf "$PREFIX"
rm -f "$APPLICATIONS_DIR/media-hub.desktop"
rm -f "$AUTOSTART_DIR/media-hub.desktop"

cat <<EOF
Media Hub borttaget.
Kvar (ta bort manuellt om du vill): $CONFIG_DIR
Loggar: ${XDG_STATE_HOME:-$HOME/.local/state}/media-hub/
AntiMicroX-backuper heter *.amgp.bak i ~/.config/antimicrox/ om sådana skapades.
EOF
