# Manuale d'Uso: TuneUp

Questo documento ti guiderà passo passo all'utilizzo dell'applicazione `TuneUp` tramite la sua interfaccia grafica.

## A Cosa Serve Questo Programma?

**TuneUp** ti aiuta a fare ordine nella tua collezione di musica digitale (file MP3). Svolge tre compiti principali:

1.  **Pulisce i file "spazzatura"**: Sposta in una cartella apposita i file che non sono vere e proprie canzoni, come l'audio scaricato da video musicali o formati non supportati.
2.  **Elimina i duplicati**: Trova le canzoni identiche, tiene solo la versione migliore (quella che occupa più spazio, quindi di qualità superiore) e sposta le altre copie.
3.  **Raggruppa le versioni**: Se hai più versioni della stessa canzone (es. una normale, una live, un remix), le raggruppa in una cartella per permetterti di decidere quali tenere.

**Importante**: il programma non cancella mai i file. Li sposta in cartelle dedicate, così puoi sempre controllarli e recuperarli se necessario.

## Come si Usa

### 1. Avvio dell'Applicazione

Fai doppio clic sul file eseguibile del programma. Si aprirà la finestra principale.

![Finestra Principale](https://i.imgur.com/placeholder.png) <!-- Immagine placeholder -->

### 2. Selezione delle Cartelle

La prima cosa da fare è dire al programma dove si trova la tua musica.

-   **Cartella Musicale**: Clicca sul pulsante **"Sfoglia..."** accanto a questo campo e seleziona la cartella principale che contiene tutti i tuoi file musicali (es. `C:\Users\TuoNome\Musica`).
-   **Cartella Duplicati** e **Cartella Non Conformi**: Una volta scelta la cartella musicale, questi campi verranno riempiti automaticamente. Per impostazione predefinita, il programma creerà le cartelle `DOPPIONI` e `NON CONFORMI` all'interno della tua cartella musicale. Puoi cambiarle se vuoi, ma solitamente l'impostazione predefinita va benissimo.

### 3. Avviare l'Analisi

Una volta impostata la cartella musicale, clicca sul pulsante **"Avvia Analisi"**.

Il programma inizierà a scansionare tutti i tuoi file. Vedrai due cose:
-   La **barra di progresso** in basso si riempirà, mostrandoti a che punto è la scansione.
-   L'area di **Log Operazioni** si popolerà di testo, descrivendo in dettaglio cosa sta facendo il programma.

Durante questa fase, i pulsanti e i campi verranno disabilitati.

### 4. La Finestra di Anteprima

Una volta terminata l'analisi, succederà una di queste due cose:

-   **Se non ci sono file da spostare**: Apparirà un piccolo messaggio che ti informa che la tua libreria è già in ordine.
-   **Se ci sono file da spostare**: Apparirà una nuova finestra, l'**Anteprima Spostamenti**.

![Finestra Anteprima](https://i.imgur.com/placeholder.png) <!-- Immagine placeholder -->

Questa finestra è il cuore del programma. Ti mostra una tabella con tutte le operazioni che il programma *propone* di fare. Le colonne sono:
-   **File Originale**: Il file che verrà spostato.
-   **Nuova Posizione**: La cartella in cui verrà spostato.
-   **Motivazione**: Il motivo dello spostamento. Può essere:
    -   `Duplicato`: Il file è una copia di un'altra canzone che verrà mantenuta.
    -   `Versione da Verificare`: Il file è una versione diversa (live, remix, etc.) di un'altra canzone. Viene raggruppato con le altre versioni per una tua revisione.

### 5. Decisione Finale: Eseguire o Annullare

A questo punto, hai il pieno controllo.

-   **Per confermare e spostare i file** come proposto, clicca sul pulsante **"Esegui Spostamenti"**. Il programma eseguirà tutte le operazioni e poi si chiuderà la finestra di anteprima.
-   **Per non fare nulla** e lasciare tutti i file dove sono, clicca su **"Annulla"**. La finestra si chiuderà e nessuna modifica verrà apportata.

### 6. Controllo del Risultato

Dopo aver eseguito gli spostamenti, puoi andare a controllare le cartelle create dal programma (`DOPPIONI`, `NON CONFORMI`, `DA_VERIFICARE`) per vedere i file che sono stati spostati.

Puoi anche leggere il **Log Operazioni** nella finestra principale per un resoconto dettagliato di ogni singolo spostamento.

---
Hai finito! La tua libreria musicale ora è più pulita e ordinata.
