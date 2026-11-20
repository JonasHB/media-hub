# Media Hub – agentinstruktioner

Lokal HTPC-launcher för Linux: Python 3.11+ med PySide6/QML (Qt 6) och SDL2.
Ersätter Flex Launcher. Svensk UI-text, engelska identifierare.

## Git

- **Committa alltid ändringar i detta repo** när ett sammanhängande arbete är
  klart och testerna är gröna. Användaren behöver inte be om det.
- Conventional Commits, engelska, imperativ, ämnesrad ≤ 50 tecken, body
  radbryten vid 72. Ingen `Co-Authored-By`.
- Committa inte hemligheter, `.venv/`, `__pycache__/` eller skärmdumpar.
- Committa inte om testerna faller; fixa först.

## Miljö

- Utveckling sker i WSL2. Målmaskinen är en separat HTPC (Ubuntu MATE 24.04,
  X11, i5-3570, GTX 660 Ti med driver 470, Xbox 360-handkontroll).
- Hårdvaruspecifikt (handkontroll, Firefox-handover, Snes9x, AntiMicroX, FPS,
  1080p/60 och 4K/30) verifieras på målmaskinen – checklista i README.
- Python finns i `.venv`:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

- Handover-testerna kräver `DISPLAY`; övriga tester är headless.
- Använd aldrig sudo. Rör inte Flex Launcher eller befintliga AntiMicroX-profiler
  utan säkerhetskopia. Användarkonfiguration ligger i `~/.config/media-hub/`.

## UI-verifiering

Kör offscreen med mjukvarurendering och ta skärmdumpar:

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  .venv/bin/python -m mediahub --config /tmp/cfg.json --windowed \
  --size 1920x1080 --no-log-file --keys S \
  --screenshot /tmp/x.png --screenshot-delay 3000
```

- Spara granskningsbara skärmdumpar i
  `"/mnt/c/Lokala Filer/screenshots/opencode_workspace"`.
- Modellen kan inte se bilder: delegera bildläsning till `vision`-agenten.
- `--keys` skickar tangenter 600 ms efter start, sedan en per 350 ms.

## Struktur

- `mediahub/` – `config.py` (strikt JSON-validering, version 1), `gamepad.py`
  (SDL2), `handover.py` (X11-fönsterövervakning), `library.py` (ROM),
  `photos.py` (skärmsläckare), `main.py` (start och CLI).
- `qml/Main.qml` samt `qml/components/` och `qml/assets/`.
- `tests/` – pytest.
- `config/example.json` ska alltid vara giltig och hållas i synk med
  valideringen; nya inställningar ska dokumenteras i README.

## Kodstil

- Inga kommentarer om de inte behövs; tydliga namn i stället.
- Nya inställningar: validera med tydliga felmeddelanden inklusive sökväg och
  lägg till test.
- Skärmsläckare och animationer får inte aktiveras över externa applikationer.
- Textfiler är LF enligt `.gitattributes`; ändra inte radslut.
