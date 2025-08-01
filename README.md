# Gestore Duplicati Musicali

Un'applicazione desktop per analizzare una libreria musicale, identificare file duplicati, versioni multiple dello stesso brano e file non conformi, e aiutare l'utente a fare ordine.

![Screenshot GUI](https://i.imgur.com/placeholder.png) <!-- Immagine placeholder, da sostituire con uno screenshot reale -->

## Descrizione

Questo strumento è progettato per chi ha grandi collezioni di file MP3 e desidera:
- **Liberare spazio**: Trovando e spostando i file musicali duplicati.
- **Fare ordine**: Separando file di bassa qualità o estratti da video.
- **Organizzare le versioni**: Raggruppando diverse versioni dello stesso brano (es. Live, Remix, Acoustic) in cartelle dedicate per una facile revisione.

L'applicazione offre sia un'interfaccia a riga di comando (CLI) per l'automazione, sia un'interfaccia grafica (GUI) intuitiva per un facile utilizzo.

## Funzionalità Principali

- **Analisi Ricorsiva**: Scansiona l'intera libreria musicale, incluse tutte le sottocartelle.
- **Identificazione Intelligente**: Utilizza sia i tag ID3 dei file MP3 sia l'analisi del nome del file per identificare artista e titolo.
- **Gestione Duplicati**: Tra i file duplicati esatti, mantiene automaticamente quello con la dimensione maggiore (presumibilmente di qualità superiore) e sposta gli altri.
- **Gestione Versioni**: Isola i gruppi di brani che sono versioni diverse della stessa canzone (es. originale, live, remaster) per una revisione manuale.
- **Pulizia File Non Conformi**: Riconosce e sposta file che non sono tracce musicali standard, come l'audio estratto da video di YouTube (es. nomi contenenti "(official video)").
- **Anteprima Interattiva**: Prima di apportare qualsiasi modifica al filesystem, la GUI mostra una finestra di anteprima con un piano dettagliato di tutti gli spostamenti proposti. L'utente ha il controllo finale e può decidere se procedere o annullare.
- **Logging Dettagliato**: Fornisce un log completo di tutte le operazioni, sia su terminale che nell'interfaccia grafica.

## Installazione e Uso (per Utenti Finali)

Per la versione eseguibile (standalone), non è richiesta alcuna installazione. Basta scaricare il file per il proprio sistema operativo e avviarlo.

1.  Avvia l'applicazione.
2.  Usa il pulsante "Sfoglia..." per selezionare la tua cartella musicale principale. Le cartelle di destinazione verranno suggerite automaticamente.
3.  Clicca su "Avvia Analisi".
4.  Attendi il completamento dell'analisi.
5.  Apparirà una finestra di anteprima: esamina gli spostamenti proposti.
6.  Clicca su "Esegui Spostamenti" per confermare o "Annulla" per non fare nulla.

## Installazione e Sviluppo (per Sviluppatori)

Se desideri eseguire il codice sorgente o contribuire allo sviluppo:

1.  **Clona il repository:**
    ```bash
    git clone https://github.com/tuo-username/tuo-repository.git
    cd tuo-repository
    ```

2.  **Crea un ambiente virtuale (consigliato):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Su Windows: venv\Scripts\activate
    ```

3.  **Installa le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Esegui i test:**
    ```bash
    python -m pytest
    ```

5.  **Avvia l'applicazione:**
    -   GUI: `python gui_gestore_musicale.py`
    -   CLI: `python gestore_duplicati_musicali.py /percorso/della/tua/musica`

## Roadmap Futura

- Migliorare l'interattività dell'anteprima (es. deselezionare singole azioni).
- Supporto per altri formati audio (FLAC, AAC, OGG).
- Criteri di qualità più avanzati per la selezione dei file (bitrate, data).
- Packaging e distribuzione tramite installer nativi.
