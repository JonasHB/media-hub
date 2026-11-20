# Media Hub

Lokal HTPC-launcher för Linux, byggd med Python + QML (Qt 6) och SDL2.
Ersätter Flex Launcher: helskärmsgränssnitt, Xbox 360-navigering, handover till
Firefox/spel och ett konfigurationsdrivet app- och ROM-bibliotek.

## Status

MVP enligt briefens prioriterade leverans steg 1–4:

1. Helskärmsgränssnitt med streamingappar och validerat konfigurationsformat.
2. Xbox 360-navigering via SDL2, inklusive frånkoppling/återanslutning.
3. Handover till Firefox och tillbaka.
4. ROM-bibliotek med Snes9x, direktstart och kontrollerat avslut.

Steam Big Picture finns som konfigurerad post och startar som vanligt program.
Animerad bakgrund (mjuka glödpartiklar och långsamma färgskiftningar), per-kategori
accentfärg, skalning upp till 4K och foto-skärmsläckare är klart.
Eget skärmtangentbord och röststyrning återstår.

## Krav

- Linux med X11 (utvecklad mot Ubuntu MATE 24.04).
- Python 3.11+ och `python3-venv`.
- Fungerande OpenGL. Testat med mjukvarurendering; målet är 60 FPS.
- Valfritt: Xbox 360-handkontroll, Firefox, Snes9x via Flatpak, AntiMicroX 3.1.4.

## Installation

```bash
./install.sh                 # program + menyikon, behåller befintlig config
./install.sh --autostart     # + start vid inloggning
./install.sh --flatpak       # + låt Snes9x läsa ~/snes (användarnivå)
```

Installeras i `~/.local/share/media-hub` (ändra med `MEDIAHUB_PREFIX`).
Konfigurationen hamnar i `~/.config/media-hub/config.json` och skapas bara om
den saknas. Flex Launcher och AntiMicroX rörs inte.

Uppdatera en befintlig installation genom att köra `./install.sh` igen –
källkoden skrivs över men konfigurationen och ikonerna bevaras.

Utveckling direkt i repot:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m mediahub --config config/example.json --windowed
```

## Köra

Starta via menyikonen, eller från terminalen (installationskatalogen måste vara
aktuell katalog):

```bash
cd ~/.local/share/media-hub && .venv/bin/python -m mediahub
```

Flaggor:

```bash
--windowed              fönsterläge för felsökning
--size 1920x1080        fönsterstorlek i windowed-läge (test av hög upplösning)
--config PATH           annan konfigurationsfil
--screenshot PATH       spara skärmdump och avsluta (test)
--screenshot-delay MS   vänta innan skärmdumpen
--keys Down,Right,Return  skicka tangenter efter start (test)
--log-file PATH         extra loggfil
--no-log-file           ingen loggfil
```

Loggar skrivs till `~/.local/state/media-hub/media-hub.log` (roterande) och till
stderr. `tail -f` över SSH räcker för felsökning.

## Konfiguration

JSON med `version: 1`. Okända nycklar och typfel ger tydliga felmeddelanden med
sökväg, t.ex. `categories[0].items[2].launch.command: ...`. Alla fel rapporteras
samtidigt. Relativa sökvägar tolkas relativt konfigurationsfilen, `~` expanderas.

```json
{
  "version": 1,
  "settings": {
    "fps": 60,
    "animations": true,
    "language": "sv",
    "exit_combo": ["left_shoulder", "right_shoulder"]
  },
  "categories": [
    {
      "id": "streaming",
      "title": "Streaming",
      "items": [
        {
          "id": "youtube",
          "title": "YouTube",
          "subtitle": "Valfri undertext",
          "icon": "icons/youtube.png",
          "launch": {
            "command": ["firefox", "--new-window", "https://www.youtube.com/"],
            "cwd": null,
            "env": {}
          },
          "handover": {
            "type": "window",
            "window_class": "Navigator firefox_firefox",
            "profile": "firefox",
            "start_timeout_ms": 20000,
            "restore_focus": true,
            "close_strategy": "graceful",
            "fullscreen": false
          }
        }
      ]
    }
  ],
  "emulators": [
    {
      "id": "snes9x",
      "title": "Super Nintendo",
      "category": "games",
      "rom_dirs": ["/home/user/snes"],
      "extensions": [".sfc", ".smc"],
      "command": ["flatpak", "run", "com.snes9x.Snes9x", "{rom}"],
      "extra_args": [],
      "handover": {
        "type": "window",
        "window_class": "snes9x-gtk Snes9x-gtk",
        "profile": "snes9x",
        "start_timeout_ms": 15000,
        "close_strategy": "graceful",
        "fullscreen": true
      }
    }
  ]
}
```

- `command` är en array: program och varje argument som egna värden.
- `handover.type: "window"` kräver `window_class` (WM_CLASS, skiftlägesokänsligt).
  Fönstret övervakas; launchern läggs under det externa fönstret (inget skrivbord
  blinkar fram) och lyfts tillbaka när fönstret stängs. Animationerna pausas
  medan det externa fönstret är aktivt.
- `fullscreen: true` skickar en EWMH-begäran om helskärm när fönstret dyker upp
  (används för Snes9x).
- `close_strategy`: `graceful` skickar WM_DELETE_WINDOW och väntar, därefter
  SIGTERM/SIGKILL. `kill` skickar SIGTERM direkt.
- `emulators` skannar `rom_dirs` efter `extensions`, skapar en post per ROM i
  angiven kategori och ersätter `{rom}` i kommandot. Omslag letas efter som
  `<romnamn>.png|jpg|jpeg|webp` bredvid ROM-filen eller i `cover_dir`.
  Saknade bilder ger en bokstavsikon som fallback.
- `exit_combo` är de handkontrollsknappar som tillsammans stänger en pågående
  extern applikation (Guide-knappen fungerar också när den kan läsas).
- `theme` per kategori är en accentfärg (`#4d9dff`, `#f2a54a`, ...) som styr
  fokusram, glöd och kategoristreck. Utan tema används blått.
- `screensaver` styr foto-skärmsläckaren, se nedan.
- `settings.animations: false` stänger av rörliga partiklar och övergångar;
  `settings.fps: 30` ger färre partiklar och lämpar sig för 4K/30 Hz-läget.

### Underkategorier för spel

`subcategories` är en valfri lista under en huvudkategori. Varje
underkategori har ett unikt `id` (även jämfört med huvudkategorier), en `title`
och valfria `items` och `theme`. En underkategori kan vara tom.

Exempelkonfigurationen visar **Super Nintendo** (`snes`) och **Nintendo 8-bit**
(`nes`) under **Spel**, där Steam ligger kvar. Snes9x har `"category": "snes"`,
så SNES-spelen visas där. Nintendo 8-bit är tom tills du lägger till en
NES-emulator med `"category": "nes"`, rätt startkommando och `.nes` som filändelse.
Öppna en underkategori med A/Enter och gå tillbaka med B/Esc eller den runda
tillbakapilen.

Befintliga installationer behåller sin konfiguration. För att använda den nya
indelningen, kopiera `subcategories` från exemplet till kategorin `games` i din
konfiguration och ändra Snes9x-postens `category` från `games` till `snes`.
Äldre konfigurationer fungerar oförändrade om du inte gör detta.

### Ikoner och omslag

Lägg bara en bild i `~/.config/media-hub/icons/` med postens `id` som namn,
t.ex. `youtube.png`, `netflix.svg` eller `steam-big-picture.webp`. Inget behöver
ändras i konfigurationen – saknas filen används en snygg bokstavsikon, och
loggen tipsar om exakt filnamn som saknas. Format: png, jpg, jpeg, webp, svg.

Egen `icon`-nyckel fungerar fortfarande för att peka på valfri sökväg.
YouTube, Netflix, Disney+, Prime Video och SVT Play har medföljande
logotyper. En befintlig egen ikon har företräde.

Spelomslag hittas automatiskt, i den här ordningen:

1. `cover_dir` om den är angiven
2. bredvid ROM-filen: `<romnamn>.png|jpg|jpeg|webp|svg`
3. mediakataloger intill ROM-filerna (ES-DE/Pegasus-stil):
   `media/covers`, `media/box2d`, `media/boxart`, `covers`, `box2d`,
   `boxart`, `images`
4. varianter med `-box2d`, `-boxart` eller `-cover` i filnamnet

Så räcker det att lägga `Super Mario All-Stars.png` i
`~/snes/media/covers/`. Saknade omslag får bokstavsikon och loggas.

### Skärmsläckare (bildspel)

```json
"screensaver": {
  "enabled": true,
  "idle_seconds": 300,
  "photo_seconds": 10,
  "transition_ms": 1200,
  "ken_burns": true,
  "order": "random",
  "folders": ["~/Pictures", "/media/foton"],
  "show_filename": false
}
```

- Startar automatiskt efter `idle_seconds` sekunder utan inmatning.
  `0` stänger av auto-start men låter knappen starta manuellt.
- Manuell start: **Y** på handkontrollen eller **S** på tangentbordet.
- `photo_seconds` är visningstid per foto, `transition_ms` mjuk övertoning,
  `ken_burns` ger långsam zoom, `order` är `random` (slumpmässigt urval,
  ny blandning per varv) eller `sequential`.
- `folders` skannas rekursivt efter `jpg`, `jpeg`, `png`, `webp` och `bmp`.
  Videofiler och dolda filer ignoreras. Saknade mappar loggas.
- `show_filename: true` visar även fotots filnamn (utan ändelse) diskret under
  datumet. Av som standard.
- Styrkorset och båda spakarna bläddrar åt vänster/höger; LB/RB visar
  föregående/nästa foto. Upp/ned ökar/minskar visningstiden med en sekund
  (3–600 sekunder) fram till nästa omstart av Media Hub.
- Datum och tid visas diskret nere till höger. Andra knappar som A, B och Y,
  samt tangentbord och mus, väcker launchern utan att aktivera ett menyval.
  Skärmsläckaren startar aldrig ovanpå en extern applikation.
- Hittas inga foton visas en notis med hänvisning till `screensaver.folders`.

## Styrning

| Inmatning | Funktion |
|---|---|
| D-pad/spak vågrätt | Bläddra mellan kakel |
| LB / RB | Byt kategori (endast dessa) |
| A | Starta markerad post |
| B | Tillbaka/stäng meny |
| Y | Starta bildspelet |
| Start / Select | Systemmeny |
| Guide | Begär stängning av extern app |
| Lodrät D-pad/spak | Endast i menyer |

Tangentbord: piltangenter bläddrar, **PgUp/PgDn** byter kategori, Enter startar,
**S** startar bildspelet och **Esc** öppnar menyn.

## Systemmeny

**Start** eller **Select** på handkontrollen (eller **Esc** på tangentbordet) öppnar
systemmenyn: Fortsätt, Viloläge, Starta om, Stäng av och Stäng launcher. Navigera
med D-pad/spak eller piltangenter, välj med **A**/Enter och stäng med **B**/Esc.

- Viloläge, omstart och avstängning körs via `systemctl` som din användare.
  Omstart och avstängning kan kräva polkit-behörighet.
- "Stäng launcher" avslutar bara Media Hub och lämnar skrivbordet kvar.
- Menyn pausar skärmsläckaren och gamepad-navigeringen bakom panelen.

## Handover och AntiMicroX

Launcherns WM_CLASS är `media-hub media-hub` (sätts via applikationsnamn och
desktop-fil). Verifiera på målmaskinen med `xprop WM_CLASS` och välj fönstret.

AntiMicroX 3.1.4 förväntas växla profil automatiskt via
`~/.config/antimicrox/antimicrox_settings.ini` utifrån WM_CLASS:

- `Navigator firefox_firefox` → `firefox.gamecontroller.amgp`
- `snes9x-gtk Snes9x-gtk` → `snes9x.gamecontroller.amgp`
- `media-hub media-hub` → `flex.gamecontroller.amgp` (tom profil; byt gärna namn)

Launchern ändrar aldrig profilerna själv. Om automatiska profiler inte fungerar i
3.1.4: säkerhetskopiera (`cp fil fil.bak`) och konfigurera om i AntiMicroX, eller
verifiera om nyare CLI/D-Bus finns – utgå inte från det.

Under extern applikation är launcherns navigering avstängd så att
handkontrollssignaler inte dubbelaktiverar. Guide och `exit_combo` lyssnar ändå
och begär en kontrollerad stängning. När fönstret försvinner återställs
launchern med samma menyval markerat.

## Felsökning

- Inget händer vid start: kör `--windowed` och läs loggen.
- Fel i konfigurationen: programmet skriver alla fel med sökväg och avslutar.
- Handover fastnar: kontrollera `window_class` med `xprop WM_CLASS`, öka
  `start_timeout_ms` och läs `handover:`-raderna i loggen.
- Långsam start: launchern visar "Startar …" direkt och loggar
  `window ... active after N ms` när fönstret hittas. Är N litet ligger tiden i
  programmets egen uppstart (t.ex. Firefox kallstart med tillägg), inte i
  handovern.
- Ingen gamepad: `ls /dev/input/js*`, testa `SDL_VIDEODRIVER=dummy` vid behov;
  SDL2 hotpluggar automatiskt.
- Återställ allt: `./uninstall.sh` tar bort programmet men behåller
  konfigurationen. Ta bort `~/.config/media-hub` manuellt för nollställning.

## Tester

```bash
.venv/bin/python -m pytest -q
```

Handover-testerna kräver en X-server (`DISPLAY`), i övrigt är testerna headless.
Gamepad testas med SDL:s virtuella handkontroll. Skärmdumpar kan verifieras med
`--screenshot`; `--keys` gör enkla navigeringssmoketester.

## Verifiering på HTPC:n (kvar)

- [ ] Xbox 360-handkontroll: navigering, LB/RB, A/B, urkoppling/inkoppling.
- [ ] Guide-knappen registreras i SDL2; annars fungerar `exit_combo`.
- [ ] Firefox: nytt fönster med befintlig profil, launchern göms, återgår vid stängning.
- [ ] AntiMicroX växlar profil automatiskt för Firefox/Snes9x/media-hub.
- [ ] Snes9x: ROM startar i helskärm och avslutas kontrollerat (sparfiler skrivs).
- [ ] Prestanda: 60 FPS på i5-3570/GTX 660 Ti, 30 FPS-läge och `animations: false`.
- [ ] Hög upplösning: 1080p/60 och 4K/30 (HDMI-begränsning), skarp text och inget avklippt.
- [ ] Bildspel: auto-start efter inställd tid, Y/S-knappen, mjuka byten,
  diskret klocka och väckning utan oavsiktligt menyval.
- [ ] Flex Launcher fungerar fortfarande tills nya launchern är godkänd.
