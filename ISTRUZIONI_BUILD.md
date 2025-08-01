# Guida per Sviluppatori: Build e Test

Questo documento fornisce le istruzioni tecniche per configurare l'ambiente di sviluppo, eseguire la suite di test e creare gli eseguibili standalone dell'applicazione **TuneUp**.

## 1. Configurazione dell'Ambiente di Sviluppo

È fortemente consigliato utilizzare un ambiente virtuale per isolare le dipendenze del progetto.

### Prerequisiti
- Python 3.8 o superiore
- `pip` e `venv` (solitamente inclusi con Python)

### Passaggi
1.  **Clona il repository:**
    ```bash
    git clone https://github.com/tuo-username/tuo-repository.git
    cd tuo-repository
    ```

2.  **Crea e attiva l'ambiente virtuale:**
    -   Su **macOS/Linux**:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    -   Su **Windows**:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Installa le dipendenze:**
    Tutte le dipendenze necessarie per l'esecuzione e lo sviluppo (incluso `pyinstaller`) sono elencate nel file `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

## 2. Esecuzione dei Test

Il progetto è dotato di una suite di test automatici basata su `pytest`. È fondamentale eseguire i test dopo ogni modifica per assicurarsi di non aver introdotto regressioni.

Per eseguire l'intera suite di test, lancia il seguente comando dalla cartella principale del progetto:
```bash
python -m pytest
```

Se tutti i test passano, l'output si concluderà con un messaggio di successo che indica il numero di test superati (es. `28 passed`).

## 3. Creazione degli Eseguibili Standalone (Build)

Utilizziamo **PyInstaller** per creare un singolo file eseguibile per ogni piattaforma. Questo eseguibile contiene l'interprete Python e tutte le dipendenze, quindi può essere eseguito su computer dove Python non è installato.

### Comando Base di PyInstaller

Il comando base per creare l'eseguibile si concentra sul file della GUI (`gui_gestore_musicale.py`). Le opzioni chiave sono:
-   `--onefile`: Crea un singolo file eseguibile.
-   `--windowed`: Su Windows e macOS, previene l'apertura di una finestra del terminale in background quando si avvia l'applicazione grafica.
-   `--name`: Specifica il nome dell'eseguibile.
-   `--icon`: Specifica un'icona per l'applicazione. **Nota**: PyInstaller richiede formati specifici per piattaforma (`.ico` per Windows, `.icns` per macOS). Il file `assets/icon.png` fornito dovrà essere convertito in questi formati.

```bash
pyinstaller --name="TuneUp" --onefile --windowed --icon="assets/icon.ico" gui_gestore_musicale.py
```

### Istruzioni Specifiche per Piattaforma

**Importante**: La build deve essere eseguita sulla piattaforma di destinazione. Ad esempio, per creare un `.exe` per Windows, devi eseguire PyInstaller su una macchina Windows.

#### **Windows**
1.  Converti `assets/icon.png` in `assets/icon.ico` usando un tool online o un software di grafica.
2.  Esegui il comando nel prompt dei comandi o PowerShell:
    ```bash
    pyinstaller --name="TuneUp" --onefile --windowed --icon="assets/icon.ico" gui_gestore_musicale.py
    ```
3.  L'eseguibile `TuneUp.exe` si troverà nella cartella `dist`.

#### **macOS**
1.  Converti `assets/icon.png` in `assets/icon.icns` usando un tool online o l'utility `iconutil` di macOS.
2.  Esegui il comando nel terminale:
    ```bash
    pyinstaller --name="TuneUp" --onefile --windowed --icon="assets/icon.icns" gui_gestore_musicale.py
    ```
3.  L'applicazione `TuneUp.app` verrà creata nella cartella `dist`.

**Considerazioni per Apple Silicon (M1/M2/M3):**
-   Se esegui il comando su un Mac con Apple Silicon, PyInstaller creerà nativamente un'applicazione per l'architettura `arm64`. Questa funzionerà al massimo delle prestazioni sui Mac moderni e sarà comunque eseguibile sui vecchi Mac Intel tramite l'emulatore Rosetta 2.
-   Non sono necessari passaggi aggiuntivi; PyInstaller gestisce l'architettura automaticamente.

#### **Linux**
1.  Su Linux, l'opzione `--windowed` non ha sempre l'effetto desiderato e l'icona potrebbe non essere applicata direttamente all'eseguibile binario. La pratica comune è distribuire l'eseguibile insieme a un file `.desktop`.
2.  Esegui il comando base (l'icona è opzionale qui ma può essere referenziata nel file `.desktop`):
    ```bash
    pyinstaller --name="TuneUp" --onefile gui_gestore_musicale.py
    ```
3.  L'eseguibile `TuneUp` si troverà nella cartella `dist`.
4.  (Opzionale) Crea un file `tuneup.desktop` per una migliore integrazione con gli ambienti desktop:
    ```ini
    [Desktop Entry]
    Name=TuneUp
    Exec=/path/completo/alla/dist/TuneUp
    Icon=/path/completo/assets/icon.png
    Terminal=false
    Type=Application
    Categories=AudioVideo;Audio;
    ```

### Pulizia dei File di Build
Dopo la build, PyInstaller lascia una cartella `build` e un file `.spec`. Possono essere cancellati tranquillamente:
```bash
rm -rf build
rm TuneUp.spec
```
