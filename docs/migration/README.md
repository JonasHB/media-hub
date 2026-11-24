# Flytta Media Hub till en ny HTPC

Startpunkt för nästa Hermes-agent. Detta är en rekonstruktion av den aktiva setupen på Ubuntu MATE 24.04.5, X11, med Xbox 360-kontroll. Använd repots aktuella kod, inte bara `config/example.json`. `templates/` innehåller granskade, portabla konfigurationsmallar – inte gamla användarprofiler, autentisering, sparfiler eller historik. Inga ROM-filer, emulatorer, nedladdade logotyper, foton eller binärer ingår i migreringspaketet. Redan versionshanterade UI-resurser ligger kvar där de låg.

## 1. Installera beroenden och kontrollera sessionen

- Använd en X11-session och aktivera svensk XKB-layout `se` i MATE. Ha SSH eller tangentbord som reserv innan du testar autostart; den gamla TV-datorn styrs annars bara med handkontrollen. Anpassa grafikdrivrutinen efter **nya** GPU:n; GTX 660 Ti och NVIDIA 470 var specifika för den gamla datorn. Picom körde med `xrender`, vsync och `--unredir-if-possible`; ändra inte hela kompositorn för att fixa OSK (se wrappern).
- Installera Media Hubs Python/Qt-/SDL2- och X11-beroenden enligt repots README. `wmctrl`, `xprop` och `xwininfo` behövs för felsökning. Installera AntiMicroX från en betrodd paketkälla (`antimicrox` är kommandot; på gamla värden ägdes filen av Ubuntu-paketet `antimicro` 3.1.4-2). Installera Firefox och Steam som Snap för att behålla fönsterklass och sökvägar. Historiska revisioner: Firefox 5889, Steam 289; installera en stödd version, inte en gammal Firefox bara för att matcha revisionen.
- Aktivera Flathub för respektive installationsnivå. Kör `flatpak install --user flathub ca._0ldsk00l.Nestopia org.DolphinEmu.dolphin-emu` och installera `com.snes9x.Snes9x` från Flathub på systemnivå (eller välj användarnivå och verifiera åtkomst). Observerat: Nestopia 1.53.2 och Dolphin 2609b på användarnivå, Snes9x 1.63 på systemnivå. Kontrollera med `flatpak info --show-permissions APP-ID`. Snes9x startas dessutom med `--filesystem=<hem>/snes` och hade samma override på användarnivå; den kan återskapas med `flatpak override --user --filesystem="$HOME/snes" com.snes9x.Snes9x`.
- Starta emulatorer och Steam första gången i rätt grafisk session och stäng dem normalt före återställning. Låt användaren välja telemetri och logga in själv i Firefox-/Steam-tjänster. Installera Steam-spelen via Steam; huvudroten var `~/snap/steam/common/.local/share/Steam` och `steamapps/libraryfolders.vdf` innehöll även `~/Games`. Skapa den extra roten via Steam vid behov. Stäng av **Guide button focuses Steam** under Settings → Controller → Show Advanced Settings; ändra inte Steam Input generellt. Autoimport använder manifest. Stardew Valley (413150) har ett manuellt kakel med `detached_launch`, och Untitled Goose Game (837470) har en AntiMicroX-regel. `steam-controller-profiles.json` fanns inte i aktiva Media Hub-katalogen vid inventeringen; skapa inte påhittade val. Xbox X på ett importerat spel öppnar profilväljaren.

## 2. Återställ konfigurationen

Från reporoten: kör `./install.sh --autostart` som vanlig användare. Media Hub installeras i `~/.local/share/media-hub` och autostarten genereras av installationsskriptet. Avsluta eventuella gamla instanser normalt innan du skriver konfiguration; behåll privata säkerhetskopior av alla filer du ersätter. Mallarna förutsätter vanliga XDG-sökvägar (`~/.config`, `~/.local/share`, `~/.local/state`); vid anpassade XDG-sökvägar måste både destinationer och interna referenser uppdateras.

Rendera först till en tom stagingkatalog för granskning; sätt `DEST_HOME` till det verkliga hemmet för kontot på den nya datorn (inte stagingkatalogen). Använd ett vanligt hemnamn utan citattecken, backslash, `$` eller radbrytningar; annars krävs formatspecifik escaping.

```sh
stage=$(mktemp -d)
DEST_HOME="$HOME" STAGE="$stage" python3 - <<'PY'
import os
from pathlib import Path

source = Path('docs/migration/templates')
dest = Path(os.environ['STAGE'])
home = os.environ['DEST_HOME']
assert Path(home).is_absolute() and not any(c in home for c in '\"\\$\n`')
for p in sorted(source.rglob('*')):
    if p.is_file():
        target = dest / p.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(p.read_text().replace('@HOME@', home))
(dest / '.local/bin/gamepad-osk').chmod(0o755)
PY
printf '%s\n' "$stage"
```

Läs diff mot vad som finns på nya datorn. Kopiera de granskade filerna från staging till **motsvarande relativa sökvägar under hemmet** (`.config`, `.local/bin`, `.var/app`), inte stagingkatalogen själv. Behåll körbiten på OSK-wrappern. Skriv inte över hela `.config` eller `.var/app`. Dolphin.ini i mallen är en delmängd: slå samman sektionerna med den nya filen; behåll maskinens egna värden för `[Analytics]` och `[General]`. Övriga Dolphin-filer är de faktiska styr- och grafikinställningarna. Validera Media Hubs slutliga fil med `~/.local/share/media-hub/.venv/bin/python -c 'from mediahub.config import load_config; from pathlib import Path; load_config(Path.home()/".config/media-hub/config.json")'` från reporoten eller installerad katalog. Defaultlogg: `~/.local/state/media-hub/media-hub.log`.

Skapa `~/nes`, `~/snes`, `~/wii` och `~/Pictures`. Slideshow: 120 s inaktivitet, 6 s per foto, 1200 ms övergång, slumpordning, Ken Burns, inga filnamn. I bildspelet bläddrar D-pad/spakar och LB/RB åt sidorna, upp/ned ändrar intervallet 0,5 s och A pausar/återupptar. Flytta privata foton separat om användaren vill.

### Xbox- och fönsterbeteende

- Media Hub tar emot den nativa Xbox-kontrollen; Guide är återgång även under extern handover. Spel ska ta emot kontrollen nativt, utan skrivbordsmus. Firefox Snap (`Navigator firefox_firefox`) använder AntiMicroX standardprofil med LB/RB för Alt+vänster/höger och de exakta mus-/tangentbindningarna i `firefox.gamecontroller.amgp`. Ingen Select-slot i AntiMicroX. Hårdvaru-ID-specifika AntiMicroX-listor har avsiktligt inte kopierats; välj Firefox-profilen manuellt om ny kontroll inte får rätt startprofil. `flex.gamecontroller.amgp` är tom och används för Media Hub också; Flex Launcher behöver inte installeras. bsnes-regeln finns kvar som referens, basen kräver inte bsnes.
- Nestopia döljer muspekaren (`m_hidecursor = 1`). Dolphin sköter själv helskärm (`Fullscreen = True`) och frågar inte vid stopp (`ConfirmStop = False`); Media Hub begär därför inte Dolphin-helskärm. `GCPadNew.ini` mappar Xbox till GameCube-port 1, inte till Wii-fjärren. Snes9x-profilen är inte tom: den har en befintlig Alt+F4-bindning på index 6; bekräfta vilken fysisk knapp det motsvarar på nya enheten och om den krockar med Guide eller spel. Inga regler innebär verifierad profilväxling förrän respektive app testats.
- Kontrollera båda delarna av `WM_CLASS` med `wmctrl -lx` och `xprop`. För skapade Steam-kakel utan dedikerad tom AutoProfile finns ingen garanti att Xbox-musen stängs av. Om en klass förändrats, uppdatera rätt regel i stället för att bredda matchningen.

## 3. Bygg det svenska skärmtangentbordet

Originalkälla: `https://github.com/0x90shell/gamepad-osk.git`, tagg `v2.1.1`, commit `dbdfc168056a316555b42b2d015666e60428f8bf`. Patch och regressionstest under `osk/` är projektets lokala anpassningar. Hämta koden i en separat arbetskatalog, inte i Media Hub-repot. Kör följande med `migration` satt till den absoluta sökvägen till katalogen som innehåller denna README:

```sh
git clone --depth 1 --branch v2.1.1 https://github.com/0x90shell/gamepad-osk.git
cd gamepad-osk
test "$(git rev-parse HEAD)" = dbdfc168056a316555b42b2d015666e60428f8bf
git apply --check "$migration/osk/swedish-layout-v2.1.1.patch"
git apply "$migration/osk/swedish-layout-v2.1.1.patch"
cp "$migration/osk/swedish_layout_test.go" .
pkg-config --cflags --libs sdl3 sdl3-ttf x11 wayland-client
go test ./...
go build -o gamepad-osk .
install -Dm755 gamepad-osk "$HOME/.local/opt/gamepad-osk/gamepad-osk"
```

Byggkrav: Go 1.26.1 (officiell distribution, kontrollera publicerad SHA-256), C-kompilator, pkg-config, SDL3, SDL3_ttf, X11 och Wayland klientbibliotek med utvecklingsfiler. Föredra mål-OS:ets paket. På gamla Ubuntu extraherades Debianpaketen `libsdl3-0_3.2.10+ds-1_amd64.deb`, `libsdl3-dev_3.2.10+ds-1_amd64.deb` ur `pool/main/libs/libsdl3/` samt `libsdl3-ttf0_3.2.2+ds-1_amd64.deb`, `libsdl3-ttf-dev_3.2.2+ds-1_amd64.deb` ur `pool/main/libs/libsdl3-ttf/` på `deb.debian.org/debian`. Använd Debian Snapshot om versionsfilerna flyttats. Extrahera med `dpkg-deb -x` till privat byggrot (installera inte Debianpaketen globalt på Ubuntu), använd dess `usr/lib/<multiarch>/pkgconfig` med `PKG_CONFIG_SYSROOT_DIR` och `PKG_CONFIG_LIBDIR` och håll bygg- och runtimeversioner matchade. Gamla bygget använde även `libx11-dev libwayland-dev x11proto-dev libxcb1-dev libxau-dev libxdmcp-dev` från Noble i samma byggrot. Vid problem föredra ett kompatibelt byggsystem framför att ändra systembibliotek.

Vid privat SDL: kopiera bara runtimefilerna `libSDL3.so.0*` och `libSDL3_ttf.so.0*` med `cp -a` till `~/.local/opt/gamepad-osk/lib/`, så att SONAME-länkarna följer med. Wrappern sätter `GAMEPAD_OSK_LAYOUT=se`, blockerar SDL:s X11 compositor bypass och lägger till den privata sökvägen lokalt. Kontrollera `ldd -r` med samma bibliotekssökväg och `~/.local/bin/gamepad-osk --version`. Kontrollera skrivbordsanvändarens åtkomst till rätt `/dev/input/event*` och `/dev/uinput` med `getfacl` innan någon behörighet ändras. Ändra inte breda behörigheter bara för att ett SSH-test misslyckas.

Skapa `~/.local/state/gamepad-osk/` innan autostarten testas (loggen omdirigeras dit). Starta i MATE-sessionen via `gio launch ~/.config/autostart/gamepad-osk.desktop` när ingen daemon redan kör. Starta inte dessutom upstreams systemd-tjänst. Select öppnar OSK **bara** i Firefox och stänger när det visas. Guide när OSK visas ska först släppa exklusiv kontroll, sedan begära Media Hubs återgång över `$XDG_RUNTIME_DIR/media-hub-return.sock`. OSK behöver inte och ska inte själv stänga Firefox. `toggle_combo` lämnas tom.

## 4. Återskapa bibliotek och logotyper

`library-inventory.json` innehåller exakta filnamn (inga ROM-data), rapporterad historisk källa där belagd och SHA-256 för befintlig logotyp. Källor är proveniens, inte en verifiering av att en nedladdning fungerar idag. Använd egna dumpar eller auktoriserade utgåvor. Planet Emulation användes för flera NES/SNES-titlar; `~/Hämtningar` och konsolkatalogerna innehöll vissa originalarkiv, men ett lokalt filnamn bevisar inte källa. De fyra ISO-filerna fanns redan lokalt under `~/wii`; deras ursprung är okänt. Internet Archive och RomsFun förekom i försök kring andra Wii-titlar, inte som belagda källor för de fyra aktiva ISO-filerna. Emu-Land valdes bort. Namnet `wii` är den befintliga katalogen och menykategorin – betyder inte att varje skiva är Wii. Låt gärna kvarvarande original och sparfiler ligga i en separat privat backup; lägg dem inte i Git.

Spellogotyper: sök efter **Clear Logo** för rätt spel, plattform och region på `gamesdb.launchbox-app.com`; använd original-PNG med alfa. Spara bredvid respektive ROM med exakt samma basnamn (se inventeringen). För de fyra Dolphin-titlarna finns originalbild-URL i inventeringen; det gamla bygget skalade vid behov ned till högst 1200 px bredd med Qt:s smooth transformation. Kontrollera hash för identiska kopior; en ny Qt-kodning kan ge annan hash även om bilden ser likadan ut. För övriga titlar där original-URL inte är belagd används titel/region och checksumma som referens.

För streaming används repots befintliga SVG-fallback när de gamla explicita PNG-sökvägarna saknar filer; källor finns i `config/icons/credits.md`. Cineasterna är ett aktivt lokalt undantag: ta webbplatsens `apple-icon-144x144.png` (historisk källa `https://d3k9jeyu3pq1ex.cloudfront.net/static/frontend/apple-icon-144x144.png`), applicera en kantutjämnad rund alfamask och spara `~/.config/media-hub/icons/cineasterna.png`. Kakel-URL är till Huddinge biblioteks katalog. Stardew Valley-loggan hämtas ur Steam-klientens `appcache/librarycache/413150/logo.png` och sparas som `~/.config/media-hub/icons/stardew-valley.png`. Befintliga kategori-/folder-ikoner ligger redan i `qml/assets/` och ska inte exporteras igen. Se artwork-referensen i den medföljande skillen.

## 5. Hermes-skills och slutkontroll

`hermes-skills/` innehåller `media-hub-config` och `media/game-emulators` inklusive referenser. Kopiera respektive katalog till den aktiva Hermes-profilens `skills/` (bevara `media/` för emulator-skillen). Läs dessa före konfigändringar. `media-hub-config` och gamla exempel utgår från `/home/jonas/repo/media-hub`; använd den faktiska checkouten på den nya datorn. Hela Hermes-konfigurationen, auth, minne, sessioner och loggar ska inte kopieras.

1. Kör repots tester; för X11-handover använd den grafiska sessionens `DISPLAY` och vid behov `XAUTHORITY`. För automatiska tester kan `SDL_GAMECONTROLLER_IGNORE_DEVICES=0x045e/0x028e` hålla den riktiga Xbox 360-kontrollen utanför testet. Kör `load_config` och `apply_library` mot aktiv JSON och kontrollera förväntade ROM-argv, bildvägar och Steam-AppID; installera inget nytt bara för ett test.
2. Testa från Media Hubs kakel på TV:n: Firefox-helskärm, LB/RB i samma flik, Select visar/döljer OSK, svenska å/ä/ö går att skriva, Select gör inget i Media Hub, Guide återgår även när OSK visas. Kontrollera skärmpixlar om OSK är osynligt trots att X11 säger `IsViewable`.
3. Testa ett spel per emulator och per viktigt Steam-profilfall. Kontrollera rätt player slot, inga dubbla mus-/tangentinmatningar, Guide återgår utan stoppdialog och Media Hub återfår kontroll/fokus. I Dolphin: verifiera `_NET_WM_STATE_FULLSCREEN`, noll ramkanter och skärmtäckande geometri vid start från kakel. Direktstart på gamla maskinen verifierade helskärm, men det är inte verifiering av kakelstart på nya maskinen.
4. Bekräfta vid nästa normala skrivbordsinloggning att en instans vardera av Media Hub, AntiMicroX och OSK startar. Prova omslag, bildspel och återgång; dokumentera avvikelser. Inga fysiska acceptanstester på den nya datorn ersätts av filverifiering.
