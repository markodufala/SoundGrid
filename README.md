# SoundGrid - Interaktívna Zvuková Sieť

## Popis projektu
SoundGrid je interaktívna aplikácia, ktorá kombinuje zvukové syntézy, vizualizáciu obrazu a farieb a poskytuje používateľovi možnosť ovládať zvukovú sieť prostredníctvom GUI rozhrania a kamery. Aplikácia umožňuje:

- Hrať rôzne zvukové nástroje ako sínusové, pílové a štvorcové vlny, a predpripravené zvukové vzorky.
- Používať kameru na detekciu farieb a vytváranie dynamických zvukových efektov.
- Vizuálne ovládať a spravovať zvukové efekty pomocou tlačidiel a posuvníkov.

## Inštalácia

1. **Požiadavky:**
   - Python 3.11 alebo vyšší
   - Nasledujúce Python knižnice:
     - `wxPython`
     - `pyo`
     - `opencv-python`
     - `numpy`

2. **Inštalácia závislostí:**
   ```bash
   pip install wxPython pyo opencv-python numpy
   ```

3. **Spustenie aplikácie:**
   ```bash
   python app.py
   ```

## Použitie

### Ovládacie prvky:
- **Tlačidlá siete:** Tlačidlá v mriežke (10x10) umožňujú aktivovať/deaktivovať jednotlivé nástroje.
- **Play/Pause:** Spustí alebo zastaví prehrávanie.
- **Clear All:** Vymaže nastavenia celej mriežky a zastaví všetky nástroje.
- **Posuvníky:**
  - **Volume:** Nastavuje hlasitosť nástrojov.
  - **Hue Volume:** Nastavuje hlasitosť zvukov generovaných na základe farieb.
  - **Hue Reverb:** Nastavuje dozvuk zvuku generovaného na základe farieb.
  - **Speed:** Rýchlosť prehrávania v mriežke.
- **Detekcia farieb:**
  - Aktivujte pomocou tlačidla "Enable Hue Detection".
  - Posuvníky "Hue" a "Sensitivity" umožňujú nastaviť detekciu farieb na základe odtieňa a citlivosti.

### Kamerové panely:
- **Camera Feed:** Zobrazuje obraz z kamery s detekciou farieb.
- **Edge Detection:** Zobrazuje hrany objektov vo videu.
- **Mask Visualization:** Zobrazuje masku detekovaných farieb.

## Hlavné funkcie

1. **Zvuková syntéza:**
   - Rôzne typy oscilátorov a prehrávanie zvukových vzoriek.
2. **Vizualizácia:**
   - Detekcia farieb v reálnom čase a ich mapovanie na zvukové parametre.
3. **Ovládanie mriežky:**
   - Dynamická zmena zvuku v reálnom čase prostredníctvom GUI.

## Štruktúra

SoundGrid/
│
├── app.py               # Hlavný súbor aplikácie
├── sound_synthesis.py   # Zvuková syntéza nástrojov a efekty
├── camera_utils.py      # Zpracovanie obrazu a detekcia farieb
├── samples              # Zložka sample súborov pre nástroj "Sample"
└── README.md            # Tento súbor

## Spolupráca:
s Adamom Štechom na ČVUT   

