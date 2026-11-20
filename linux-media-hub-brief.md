# Projektbrief: Linux Media Hub

## 1. Målsättning

Bygg en fristående, lokal HTPC-launcher för Linux som ersätter Flex Launcher. Gränssnittet ska vara inspirerat av PlayStation 4 och moderna Smart TV-system: snabbt, visuellt genomarbetat och fullt användbart från TV-soffan med en Xbox 360-handkontroll. Ingen fysisk mus eller tangentbord ska behövas i normal användning.

Användaren prioriterar egen kontroll, öppenhet och möjlighet att utveckla systemet vidare. Lösningen ska inte kräva Kodi eller en Android TV-enhet.

## 2. Befintlig miljö

- Ubuntu MATE 24.04 LTS, X11.
- Intel Core i5-3570, 8 GB RAM, SSD och gigabit-Ethernet.
- Nvidia GTX 660 Ti med drivrutin 470. HDMI är begränsat till 4K/30 Hz; optimera därför även för 1080p/60 Hz.
- Xbox 360-handkontroll.
- Firefox med uBlock Origin och SponsorBlock, befintlig användarprofil.
- AntiMicroX 3.1.4 för mus- och tangentbordsemulering.
- Snes9x via Flatpak (`com.snes9x.Snes9x`).
- SNES-ROM-filer i `~/snes`, inklusive Super Mario All-Stars.
- Flex Launcher i `~/.config/flex-launcher/`, med befintliga ikoner och menyer.
- Utveckling och konfiguration sker gärna via terminal/SSH.

## 3. Funktionella krav

Launchern ska kunna starta YouTube, Netflix, Disney+, Prime Video, SVT Play, Steam, emulatorer, enskilda spel och andra konfigurerbara Linuxprogram.

- Streaming öppnas i separata Firefox-fönster med den befintliga Firefox-profilen och dess tillägg, utan att radera eller ersätta användardata.
- Spel startas direkt från ett spelbibliotek, utan att användaren behöver navigera i emulatorns egna menyer.
- 4K ska stödjas där hårdvaran och respektive tjänst tillåter det. Linuxbaserad browseruppspelning kan vara DRM-begränsad; launchern ska inte utlova 4K för alla tjänster.
- Stöd för återgång till MATE-skrivbordet, systemmeny, avstängning och viloläge.

## 4. Visuell design

- Helskärmsgränssnitt, stort och läsbart på flera meters avstånd.
- Stora appikoner och spelomslag, tydligt markerat aktivt menyval.
- Kontinuerliga, mycket långsamma gradient-/färgövergångar, utan ryckiga bildbyten.
- Diskret sken och mjuk förstoring av markerade ikoner.
- Mjuka meny- och kategoriövergångar, klocka och datum.
- GPU-accelererad rendering med målsättning 60 FPS, konfigurerbart 30 FPS-läge och möjlighet att reducera animationer.
- Pausa eller minimera rendering när en extern applikation används.

## 5. Xbox 360-handkontroll

Använd SDL2 eller motsvarande standardiserat gamepad-API med hotplugging. Handkontrollen är den primära inmatningsenheten. Stöd även mus och tangentbord.

| Kontroll | Funktion i launchern |
|---|---|
| D-pad/vänster spak | Navigering |
| A | Välj/starta |
| B | Tillbaka |
| LB/RB | Byt kategori |
| Start | Systemmeny |
| Xbox Guide | Hem/återgång, om knappen kan registreras |

Implementera deadzone, kontrollerad knapprepetition och skydd mot dubbla aktiveringar. Reservera en konfigurerbar alternativ knappkombination för återgång om Guide-knappen inte kan användas.

## 6. Handover till externa applikationer (kritiskt)

Användaren ska aldrig behöva byta från Xbox-kontrollen. Hantera överlämning och återgång som en uttrycklig livscykel: launcher → startar → extern app aktiv → återgång → launcher. Upptäck fönster, hantera fokus, timeout, krasch och avslut. Undvik att både AntiMicroX och launchern behandlar samma knapptryckning.

### Firefox

Ladda befintlig AntiMicroX-profil `~/.config/antimicrox/firefox.gamecontroller.amgp` när browsern används.

| Kontroll | Befintlig funktion |
|---|---|
| Vänster spak | Muspekare (hastighet omkring 45) |
| Höger spak | Scroll |
| D-pad | Piltangenter |
| A | Vänsterklick |
| B | Escape |
| X | Enter |
| Y | Mellanslag/play-paus |
| LB/RB | Shift+Tab/Tab |
| Start | F11, browserns helskärm |
| RT | F, videons helskärm där tjänsten stödjer det |
| Select/View | Alt+F4, stäng fönster |
| LT | Reserverad för skärmtangentbord |

Observera att Firefox kan återanvända en redan körande process; övervaka därför det skapade fönstret och inte enbart startprocessen. Stäng inte andra Firefox-fönster. Återställ launcherfokus och tidigare menyval när användaren avslutar.

### Emulatorer

- Spelkontrollen ska få oförändrade gamepad-signaler; AntiMicroX:s vanliga mus- och tangentbordsmappningar ska inte vara aktiva under spel.
- En reserverad Guide-knapp eller alternativ knappkombination ska avsluta emulatorn kontrollerat så att sparfiler kan skrivas.
- Återgå till föregående spelmeny med samma spel markerat.
- Snes9x ska använda helskärm vid ROM-start.
- Starta exempelvis `flatpak run --filesystem=/home/user/snes com.snes9x.Snes9x '/home/user/snes/<ROM-fil>'`; använd rätt katalog och argument för varje spel. Konfigurera Flatpak-åtkomst vid behov utan att ge onödiga breda behörigheter.

### AntiMicroX-integration

Aktuell konfigurationskatalog: `~/.config/antimicrox/`.

- `firefox.gamecontroller.amgp`: mus-/webbläsarprofil och normal skrivbordsstyrning.
- `flex.gamecontroller.amgp`: tom profil för launcherns inbyggda gamepad-styrning.
- `snes9x.gamecontroller.amgp`: spelprofil, normalt utan mappningar förutom avslut.
- `antimicrox_settings.ini`: automatiska profiler under X11.

Befintliga observerade X11 WM_CLASS-värden: `Navigator firefox_firefox`, `flex-launcher flex-launcher` och `snes9x-gtk Snes9x-gtk`. Det nya programmets klass ska vara stabil och dokumenterad. Verifiera faktisk profilväxling i AntiMicroX 3.1.4; utgå inte från att nyare CLI- eller D-Bus-funktioner finns. Automatiska profiler eller explicit profilväxling får användas, men återgången ska fungera även efter fel. Se även till att skärmtangentbord eller dialogrutor inte gör gamepaden oanvändbar vid tillfälliga fokusbyten.

## 7. Utbyggbarhet och konfiguration

Launchern ska vara en generell plattform, inte en hårdkodad samling streamingtjänster. Nya appar, kategorier, undermenyer, emulatorer, spel och teman ska kunna läggas till utan ändringar i källkoden.

Använd ett dokumenterat JSON- eller TOML-format med validering och tydliga felmeddelanden. Konfigurationen ska stödja:

- Menyer, kategorier, ordning, ikoner och spelomslag.
- Startkommandon och argument som separata värden, arbetskatalog och vid behov miljövariabler.
- Emulatorer, ROM-kataloger, filändelser och helskärmsalternativ.
- Individuella handover-profiler, start-/avslutsstrategier och fönsterklassmatchning.
- Handkontrollsmappningar, tema, bildfrekvens och animationstider.
- Individuella teman per kategori och användarens egna genvägar.

### Spelbibliotek och emulatorer

- Skanna konfigurerbara ROM-kataloger automatiskt.
- Stöd flera emulatorer, till exempel Snes9x, Dolphin, PCSX2, DuckStation och RetroArch.
- Visa spelomslag, metadata och fallback-ikoner för saknade bilder.
- Separata startkommandon och kontrollprofiler per emulator.
- Stöd Steam Big Picture samt direktstart av enskilda Steam-spel där det är möjligt.
- Steam och emulatorer måste kunna ta emot handkontrollen direkt utan störande AntiMicroX-mappningar.

### Skärmsläckare

- Konfigurerbar inaktivitetstid i launchern.
- Lugn helskärms-slideshow av fotografier i valda lokala kataloger.
- Långa, mjuka övertoningar och diskret panorering/zoomning (Ken Burns), med val att stänga av rörelsen.
- Slumpmässig eller sekventiell ordning, bildvisnings- och övergångstid ska kunna ställas oberoende.
- Bevara bildernas proportioner, undvik distraherande element och hantera trasiga bildfiler.
- Första handkontrollsaktiviteten väcker skärmen utan att samtidigt aktivera ett menyval.
- Skärmsläckaren ska inte aktiveras över externa applikationer.

## 8. Teknisk rekommendation

Qt/QML är förstahandsval för visuellt gränssnitt och animationer, tillsammans med Python eller C++ samt SDL2. Alternativ teknik är acceptabel om den motiveras med stabilitet och prestanda på målmaskinen.

Separera UI, gamepad-hantering, app-/fönsterövervakning, profilväxling, spelbibliotek, skärmsläckare, teman och konfigurationsvalidering. Undvik att göra hela systemet beroende av en specifik emulator eller webbläsarimplementering.

Lägg användarkonfiguration under `~/.config/` och återanvänd befintliga ikoner där lämpligt. Programmet ska fungera lokalt och inte kräva molnanslutning för grundfunktionerna. Installera utan att modifiera Flex Launcher eller skriva över befintliga AntiMicroX-profiler utan säkerhetskopia. Tillhandahåll enkel återställning och loggar som underlättar SSH-felsökning.

## 9. Prioriterad leverans

1. Grundläggande helskärmsgränssnitt med streamingappar och konfigurationsformat.
2. Stabil Xbox 360-navigering, inklusive frånkoppling och återanslutning.
3. Robust handover till Firefox och tillbaka.
4. ROM-bibliotek med Snes9x samt direktstart och kontrollerat spelavslut.
5. Steam Big Picture och generell emulatorintegration.
6. Dynamiska gradienter, visuella animationer och foto-skärmsläckare.

### Framtida funktioner

- Eget svenskt TV-anpassat skärmtangentbord med D-pad-navigering.
- Hermes Agent för röststyrning och godkända appkommandon.
- Lokal mediaspelare, musik och eventuellt DVD med fungerande extern läsare.

## 10. Acceptanskriterier och testning

- Från ett inloggat skrivbord ska en användare med enbart Xbox 360-handkontrollen kunna starta launchern, öppna en streamingtjänst, navigera, spela video och återgå.
- En användare ska kunna välja ett SNES-spel, spela i helskärm och avsluta med handkontrollen, utan oönskade mus-/tangentbordsinsignaler i spelet.
- Steam Big Picture ska kunna startas och avslutas utan att kontrollen behöver bytas ut.
- Ett misslyckat appstartförsök eller en krasch får inte lämna användaren utan fungerande styrning.
- Skärmsläckaren ska visa foton lugnt och kunna väckas utan oavsiktlig aktivering.
- En ny emulator och ett nytt program ska kunna läggas till enbart via konfiguration.
- Verifiera prestanda på den gamla testdatorn, inte enbart en modern utvecklingsmaskin.
- Leverera källkod, komplett installationsskript, exempelkonfiguration, dokumentation, testinstruktioner och återställningsinstruktioner. Befintlig Flex Launcher ska förbli användbar tills den nya lösningen har verifierats.
