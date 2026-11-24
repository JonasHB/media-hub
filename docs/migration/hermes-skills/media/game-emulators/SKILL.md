---
name: game-emulators
description: "Use when managing console emulators. Import and verify ROMs."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [emulation, snes, roms]
    related_skills: [media-hub-config]
---

# Tv-spelsemulatorer

## When to Use

Använd för att hantera ROM-bibliotek, emulatorsparningar och handkontrollens genvägar. Läs `media-hub-config` när uppgiften gäller Media Hub.

Föredra spelets egna sparfiler framför emulatorns save states. När användaren säger ”slot”, skilj på spelets sparfil och emulatorns QuickSave innan du föreslår en bindning. Förklara när spelet självt sparar och hur man därefter avslutar normalt; bind inte sparning till avslut. I Super Mario World: välj ”Continue and Save” när spelet erbjuder det, avsluta sedan och välj samma sparfil nästa gång.

## Källor och nedladdning

- Leta först efter spelet i det aktiva ROM-biblioteket och de lokala hämtningsmapparna så att du inte laddar ner en dubblett. Föredra auktoriserade utgåvor, homebrew och egna dumpar när de finns. Planet Emulation (`planetemu.net`) är en beprövad källa att kontrollera för både NES och SNES. Använd spelsidans vanliga nedladdningsknapp i webbläsaren och vänta tills den är aktiverad; knappen kan vara inaktiverad i sidans ursprungliga HTML.
- Sök på rätt konsol, titel och region. Läs vad arkivet ska innehålla innan nedladdning. På en nedladdningssida med formulär kan knappen vara ett `input[type=submit]`: kontrollera dess `value` och att `disabled` är falskt innan du klickar, eftersom en sökning efter synlig länk- eller knapptext kan missa den. Kontrollera att en färdig fil faktiskt sparats; en knapp eller lyckad sidladdning räcker inte. På den här datorn kan webbläsaren spara i `~/Hämtningar` snarare än `~/Downloads`.
- Byt källa om sajten fortsätter ge tomma svar eller fastnar i robotkontroll. Emu-Land har valts bort av användaren; RomsFun fastnade i Cloudflare-verifiering. Förväxla inte en katalogträff med en fungerande nedladdning.

## Hitta spellogotyper

- Sök efter konsol och titel i LaunchBox Games Database och välj **Clear Logo** på spelets bildsida. Kontrollera regionen; använd World om en passande regional version saknas. För otydligt namngivna råa GameCube-/Wii-ISO-filer, läs skiv-ID:t med `xxd -l 6` och slå upp titel, konsol och region innan du väljer bilden; bibliotekets kategorinamn kan skilja sig från skivans faktiska konsol. Följ bildkortets länk till original-PNG i stället för att spara miniatyren. Om en direkt hämtning ger 403, försök med webbläsarens `User-Agent` och `Referer: https://gamesdb.launchbox-app.com/`, eller öppna länken i den vanliga webbläsaren. Verifiera att resultatet är en läsbar PNG med transparens, inte en felsida. I webbläsaren finns regionen i bildkortets `data-title` och originalet i länkens `href`; `img.src` kan vara en miniatyr. Om bilden bara går att öppna i webbläsaren, spara den därifrån eller exportera den öppnade bilden som PNG via canvas. Behåll proportioner och alfakanal; skala bara ned vid behov (1200 px bredd räckte för spelkaklen). Skriv inte över en befintlig bild. Läs tillbaka filen med `QImage` och kör `apply_library` med den installerade appens aktiva konfiguration för att bekräfta att rätt kakel använder den.
- Om användaren skickar en bildlänk, kontrollera vilket motiv den faktiskt visar. Om originalet är otillgängligt eller länken bara ger en liten miniatyr, jämför med regionmatchade `Named_Boxarts` från Libretro Thumbnails och använd ett skarpare exemplar bara om motivet stämmer. Säkerhetskopiera tidigare bild när användaren ber om ett byte, och verifiera vilken fil Media Hub faktiskt väljer.

## Xbox-knappen för att återgå

- Kontrollera först om spelet startas via Media Hub eller fristående. Återanvänd Media Hubs befintliga avslutsgest i stället för att lägga till en överlappande bindning. För fristående Snes9x (Flatpak), inspektera `GTK_quit` i `~/.var/app/com.snes9x.Snes9x/config/snes9x/snes9x.conf`; `QuickSave*` är separata save state-bindningar.
- Media Hub lyssnar redan på Xbox Guide under extern handover och begär kontrollerad stängning. Om Steam tar fokus, kontrollera Steam Settings → Controller → Show Advanced Settings → Guide button focuses Steam och stäng av just det reglaget. Läs tillbaka reglagets läge i UI:t; ändra inte Steam Input eller Guide Button Chords i onödan. Verifiera den fysiska knappen separat. `settings.exit_combo` (normalt LB + RB) fungerar som reserv.

## Testa knappfördröjning

- Skilj knapprespons från ojämn scrollning. Jämför exakt samma ROM och region, bana, handkontroll och skärm; olika spel kan ha olika inbyggd timing. Ändra en inställning i taget och börja utan Run-Ahead. Använd spelets egna sparfiler, inte save states. Se `references/input-latency.md` för Snes9x-inställningar och ett isolerat jämförelsetest i bsnes.

## NES på Media Hub

- Nestopia UE fungerar på den här datorn som användar-Flatpak `ca._0ldsk00l.Nestopia`. Använd `flatpak run ca._0ldsk00l.Nestopia {rom}`, `.nes`, `~/nes` och kategori `nes`. Verifierad X11-klass är `nestopia Nestopia`. Kontrollera fönstrets titel med en riktig ROM och `xprop`, och stäng testfönstret normalt. Flatpaken hade redan läsrätt till hemkatalogen; kontrollera `flatpak info --show-permissions` innan du lägger till undantag.

- Håll Xbox-musens mappning och muspekarens synlighet isär. För mappningen: säkerhetskopiera `~/.config/antimicrox/antimicrox_settings.ini`, ge `nestopia Nestopia` en aktiv automatisk profil utan mappningar, starta om AntiMicroX när det inte stör ett spel och läs tillbaka regeln. Bevara standardprofilen och andra emulatorregler. Filkontroll bevisar inte att profilväxlingen fungerar under spel.
- För muspekarens synlighet använder Nestopia **Hide Cursor** (`m_hidecursor = 1` i `~/.var/app/ca._0ldsk00l.Nestopia/config/nestopia/nestopia.conf`). Ändra det via emulatorn eller när den är stängd, så att den pågående instansen inte skriver över filen. Avbryt inte ett pågående spel utan godkännande. Verifiera att värdet består efter omstart och skilj det från ett visuellt test.

## Wii på Media Hub

- Installera Dolphin som användar-Flatpak med `flatpak install --user flathub org.DolphinEmu.dolphin-emu`, verifiera med `flatpak info` och öppna GUI:t i skrivbordssessionen. Kontrollera eventuella förstagångsdialoger innan du testar start från ett kakel; välj inte telemetri åt användaren. Läs ut X11-klassen med `wmctrl -lx` eller `xprop`; huvudfönstret använder `dolphin-emu dolphin-emu` på den här datorn.
- Kontrollera spelets styrkrav innan du rekommenderar eller hämtar Wii-spel för det här Xbox-biblioteket. Föredra spel som stöder vanlig handkontroll utan emulerad pekare, skakning eller MotionPlus; användaren vill inte behöva mappa sådana rörelser som standard. En fungerande Xbox-mappning i `GCPadNew.ini` gäller GameCube-porten, inte den emulerade Wii-fjärren i `WiimoteNew.ini`. Om användaren uttryckligen vill prova rörelseemulering, håll ändringen spelspecifik och skilj fungerande mappning från provspelning.
- Lägg Wii under Spel i Media Hub med `~/wii`, `.rvz`/`.iso`/`.wbfs` och fönsteröverlämning. `flatpak run org.DolphinEmu.dolphin-emu --batch --exec {rom}` är CLI-upplägget; verifiera fönsterklass, helskärm och kontrollerad stängning igen med ett riktigt spel i batchläge. Ett öppnat huvudfönster verifierar bara emulatorstart, inte spelstart eller handkontroll.

- Om en svart rad visar Dolphin-versionen, använd spelfönstrets titel och `xprop -id "$wid" _NET_WM_STATE _NET_FRAME_EXTENTS` för att skilja fönsterdekoration från en rad inuti spelet. Identifiera rätt fönster med `wmctrl -lpGx` i den aktiva X11-sessionen; en modal dialog kan ha samma fönsterklass. Om helskärmsflaggan saknas, kör `wmctrl -ir "$wid" -b add,fullscreen` för att rätta det öppna fönstret utan omstart. Läs tillbaka `_NET_WM_STATE_FULLSCREEN`, nollställda ramkanter och skärmtäckande geometri (`xwininfo -id "$wid"`). Lita inte på sparad `Fullscreen = True`, Media Hubs `handover.fullscreen: true` eller loggad fönsteröverlämning som bevis för att fönsterhanteraren faktiskt gick till helskärm. Om raden återkommer vid spelstart, jämför samma `flatpak run … --batch --exec …` direkt i skrivbordssessionen och via Media Hub, med samma ROM. Om Dolphin själv går till verifierad helskärm, testa att behålla `[Display] Fullscreen = True` i Dolphin och inaktivera endast Dolphins `handover.fullscreen` i Media Hub, så att bara Dolphin begär helskärm. Behåll fönsteröverlämning och kontrollerad stängning. Ett lyckat direktstartstest verifierar inte ändringen i Media Hub: starta om launchern med godkännande och prova ett nytt spel från kaklet innan du kallar lösningen permanent.
- Om Xbox Guide öppnar Dolphins stoppdialog men handkontrollen inte kan välja Ja eller Nej, behåll Media Hubs kontrollerade stängning. Kontrollera med `flatpak ps` att Dolphin är stängt, säkerhetskopiera `~/.var/app/org.DolphinEmu.dolphin-emu/config/dolphin-emu/Dolphin.ini` och sätt `ConfirmStop = False` i `[Interface]` (uppdatera befintlig sektion eller skapa den om den saknas). Läs tillbaka värdet. Testa sedan Guide från ett riktigt spel startat via Media Hub när det är möjligt; filkontroll räcker inte för att bekräfta återgång utan dialog.

## Avinstallera en testemulator

- Kontrollera installationens scope med `flatpak info --user APP-ID` och körstatus med `flatpak ps`. Stäng vid behov rätt emulator normalt och avinstallera bara den valda appen med `flatpak uninstall --user APP-ID` för en användarinstallation. Använd inte `--delete-data` om användaren inte uttryckligen ber om att radera emulatorns data. Verifiera med `flatpak info APP-ID` att appen är borta och kontrollera att den ordinarie emulatorn, spelet och dess sparfil finns kvar.

## Import till Media Hub

1. Läs emulatorns `rom_dirs` och `extensions` i den aktiva konfigurationen. Snes9x på den här datorn var konfigurerad för `/home/jonas/snes` och `.sfc`/`.smc`, inte ZIP.
2. Lista innehållet med `unzip -l` eller `ZipFile.infolist()` och läs bara den förväntade posten med `ZipFile.read(exakt_namn)`. Ignorera medföljande README och andra filer; packa inte upp hela arkivet i biblioteket. Validera ROM-filer och logotyper för hela gruppen före skrivning, så att ett fel inte lämnar en halv import. Spara ROM-filens basnamn och använd exklusiv filskapning (`open("xb")`) så att en befintlig fil inte skrivs över.
3. Kontrollera formatet före import där det går (för en iNES/NES 2.0-fil ska de första fyra byten vara `NES\x1a`); filändelsen ensam räcker inte. För flergigabytefiler som Wii-RVZ: kontrollera ledigt utrymme och strömma enbart vald post från `ZipFile.open()` till en temporär fil i målkatalogen, inte `ZipFile.read()` till RAM. Kontrollera formatets signatur (`RVZ\x01` för RVZ), läs till EOF för ZIP:s CRC-kontroll, jämför storleken med arkivposten och publicera utan att skriva över en befintlig ROM. Läs tillbaka målfilen och jämför med arkivets ROM-data; använd strömmande hash för stora filer. Varken filsignaturen eller en kontrollsumma utan betrodd referens bevisar äkthet eller spelbarhet.
4. Lägg även till en spellogotyp för varje nytt spel som importeras till Media Hub. Välj rätt titel och region, och återanvänd en befintlig korrekt bild om det finns en. Föredra en tydlig logotyp; använd omslagsbild om en bra logotyp inte går att hitta och säg i så fall till. Spara bilden bredvid ROM-filen med exakt samma basnamn (t.ex. `Harvest Moon (USA).png` bredvid `Harvest Moon (USA).sfc`), i `media/covers` under ROM-filens katalog eller i emulatorns konfigurerade `cover_dir`. Stödda format: PNG, JPG, JPEG, WebP och SVG. Kontrollera att bilden går att läsa och att `mediahub.library.find_cover` väljer rätt fil.
5. Vid borttagning eller ersättning, identifiera spelet i den efterfrågade konsolkategorin först; liknande titlar på andra konsoler ska lämnas orörda. Flytta ROM-filen och dess matchande logotyp till papperskorgen eller en återställningsbar katalog utanför alla skannade rötter. Flytta även ett matchande källarkiv om användaren vill ha bort hela spelet från konsolmappen. Lämna sparfiler orörda. Läs tillbaka de flyttade filerna och verifiera att det gamla kaklet saknas och att eventuell ersättare hittas.
6. Kör installerade `apply_library(load_config(...))` före omstart. I emulatorns kategori, matcha varje nytt kakel mot den exakta ROM-sökvägen i `launch.command` och den förväntade logotypen i `icon`; titeln ensam kan matcha en annan region eller dubblett. Media Hub skannar vid start. Starta inte om utan godkännande; skilj på verifierad biblioteksimport, synlighet i den körande appen och faktisk provspelning. Om ROM-filen syns men inte går att öppna, kontrollera att Snes9x har läsåtkomst till katalogen, särskilt vid Flatpak-installation.
