import os
import shutil
import argparse
import re
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen import MutagenError
from collections import defaultdict # Aggiunto per raggruppare i file da verificare

VIDEO_PATTERNS = [
    r'\(official video\)', r'\[official video\]',
    r'\(official music video\)', r'\[official music video\]',
    r'\(lyrics? video\)', r'\[lyrics? video\]',
    r'\(visualizer\)', r'\[visualizer\]',
    # Aggiungere altri pattern specifici per video qui
]

VERSION_PATTERNS = [
    # Pattern comuni per versioni, da usare per estrarre il titolo base
    # L'ordine è importante: i più specifici (es. 'radio edit') prima dei più generici (es. 'edit')
    r'\s*\([^)]*radio edit[^)]*\)', r'\s*\[[^]]*radio edit[^]]*\]',
    r'\s*\([^)]*album version[^)]*\)', r'\s*\[[^]]*album version[^]]*\]',
    r'\s*\([^)]*extended[^)]*\)', r'\s*\[[^]]*extended[^]]*\]',
    r'\s*\([^)]*instrumental[^)]*\)', r'\s*\[[^]]*instrumental[^]]*\]',
    r'\s*\([^)]*unplugged[^)]*\)', r'\s*\[[^]]*unplugged[^]]*\]',
    # Pattern che includono anni, spesso usati per remaster/riedizioni
    r'\s*\(\d{4}[^)]*(version|mix|edit|remaster)[^)]*\)',
    r'\s*\[\d{4}[^]]*(version|mix|edit|remaster)[^]]*\]', # Corretto doppio backslash e reso più generico
    # Pattern generici per parole chiave
    r'\s*\([^)]*live[^)]*\)', r'\s*\[[^]]*live[^]]*\]',
    r'\s*\([^)]*remastered[^)]*\)', r'\s*\[[^]]*remastered[^]]*\]',
    r'\s*\([^)]*acoustic[^)]*\)', r'\s*\[[^]]*acoustic[^]]*\]',
    r'\s*\([^)]*remix[^)]*\)', r'\s*\[[^]]*remix[^]]*\]',
    # Pattern semplici per tag esatti
    r'\s*\(edit\)', r'\s*\[edit\]',
    r'\s*\(mono\)', r'\s*\[mono\]',
    r'\s*\(stereo\)', r'\s*\[stereo\]',
    r'\s*\(clean\)', r'\s*\[clean\]',
    r'\s*\(explicit\)', r'\s*\[explicit\]',
]

def _default_logger(messaggio, flush=True):
    print(messaggio, flush=flush)

def normalizza_testo(testo):
    """Normalizza il testo per il confronto: minuscolo, trim, rimozione punteggiatura base."""
    if testo is None:
        return None
    testo = testo.lower()
    testo = testo.strip()
    # Ora NON rimuoviamo le parentesi tonde () e quadre [] per preservare tag come (Live), (Remastered)
    testo = re.sub(r'[\.,!?"\'\{\}#*:]', '', testo) # Rimossa \(\) e \[\] dalla classe
    testo = testo.replace('&', 'and') # Esempio, si può espandere
    testo = re.sub(r'\s+', ' ', testo) # Rimuove spazi multipli
    # Rimuove spazi extra che potrebbero essere rimasti attorno a parentesi conservate
    testo = testo.replace('( ', '(').replace(' )', ')')
    testo = testo.replace('[ ', '[').replace(' ]', ']')
    return testo.strip() # Trim finale

def estrai_titolo_base_e_versione(titolo_normalizzato, logger=_default_logger):
    """
    Tenta di estrarre un 'titolo base' e l'eventuale 'tag di versione' da un titolo normalizzato.
    Restituisce (titolo_base, tag_versione_trovato) o (titolo_originale, None) se nessun pattern matcha.
    """
    titolo_da_lavorare = titolo_normalizzato
    versione_trovata = None

    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, titolo_da_lavorare, flags=re.IGNORECASE)
        if match:
            versione_trovata = match.group(0).strip() # Il tag di versione include le parentesi
            # Rimuove il tag di versione dal titolo per ottenere il titolo base
            # Usiamo re.escape sul tag trovato per sicurezza se contiene caratteri speciali regex
            titolo_da_lavorare = re.sub(re.escape(versione_trovata), '', titolo_da_lavorare, flags=re.IGNORECASE).strip()
            # Rimuove eventuali doppi spazi o spazi all'inizio/fine creati dalla rimozione
            titolo_da_lavorare = re.sub(r'\s+', ' ', titolo_da_lavorare).strip()
            #logger(f"      Pattern versione '{pattern}' matchato: tag='{versione_trovata}', titolo base preliminare='{titolo_da_lavorare}'")
            break # Trovato un pattern, usiamo questo

    if versione_trovata:
        # A volte la rimozione può lasciare " - " o simili alla fine, puliamo
        titolo_da_lavorare = re.sub(r'\s*-\s*$', '', titolo_da_lavorare).strip()
        return titolo_da_lavorare, versione_trovata
    else:
        return titolo_normalizzato, None

def identifica_come_video(nome_file_stem):
    """Verifica se il nome del file suggerisce un contenuto video."""
    nome_lower = nome_file_stem.lower()
    for pattern in VIDEO_PATTERNS:
        if re.search(pattern, nome_lower):
            return True
    return False

def estrai_info_da_nome_file(nome_file_stem):
    """Tenta di estrarre Artista e Titolo dal nome del file (senza estensione)."""
    # Lista di pattern da rimuovere (es. numeri traccia, tag vari)
    # Questa lista può essere espansa significativamente
    pattern_da_rimuovere = [
        r'^\s*\d+[\s.-]*',              # Numeri traccia all'inizio (es. "01.", "02 - ")
        r'\s*\(hd\)', r'\s*\[hd\]',
        r'\s*\(hq\)', r'\s*\[hq\]',
        r'\s*\(explicit\)', r'\s*\[explicit\]',
        r'\s*\(clean\)', r'\s*\[clean\]',
        r'\s*\(www\..*?\..*?\)',      # Indirizzi web semplici
        # Aggiungere altri pattern specifici osservati nei propri file
    ]

    nome_pulito = nome_file_stem
    for pattern in pattern_da_rimuovere:
        nome_pulito = re.sub(pattern, '', nome_pulito, flags=re.IGNORECASE)
    
    nome_pulito = nome_pulito.strip()

    # Tentativo di separare Artista - Titolo
    match = re.match(r'(.+?) - (.+)', nome_pulito)
    if match:
        artista = match.group(1).strip()
        titolo = match.group(2).strip()
        if artista and titolo: # Assicurati che entrambi siano non vuoti dopo lo strip
             return artista, titolo
    
    # Fallback: se non c'è " - ", ma ci sono spazi, potremmo provare a dividere
    # Questo è più euristico e potrebbe necessitare di affinamenti
    # parts = nome_pulito.split()
    # if len(parts) >= 2: # Richiede almeno due parole
    #    # Qui si potrebbe tentare di indovinare, es. la prima parte è l'artista
    #    pass

    return None, None # Se non si riesce a separare chiaramente

def estrai_info_id3(file_path):
    """Estrae titolo e artista dai tag ID3 di un file MP3."""
    try:
        audio = EasyID3(file_path)
        titolo = audio.get('title', [None])[0]
        artista = audio.get('artist', [None])[0]
        return titolo, artista # La normalizzazione avverrà dopo
    except MutagenError:
        return None, None
    except Exception:
        return None, None

def scansiona_cartella(cartella_path, cartella_non_conformi_path, logger=_default_logger, progress_callback=None):
    """Scansiona la cartella, sposta i file video e raccoglie info sui file audio."""
    file_musicali_info = {}
    file_supportati = ['.mp3'] # Mantenere come lista per future estensioni
    contatore_non_conformi = 0
    contatore_file_audio_analizzati = 0 # Contatore specifico per file audio elaborati

    logger(f"Inizio pre-scansione per conteggio file audio in: {cartella_path}")
    tutti_i_file_nella_cartella = list(cartella_path.rglob('*'))
    file_audio_da_elaborare_lista = [f for f in tutti_i_file_nella_cartella if f.is_file() and f.suffix.lower() in file_supportati]
    totale_file_audio_da_elaborare = len(file_audio_da_elaborare_lista)
    
    logger(f"Trovati {totale_file_audio_da_elaborare} file audio ({', '.join(file_supportati)}) da analizzare.")
    logger(f"I file identificati come 'video' o non conformi verranno spostati in: {cartella_non_conformi_path}")
    if totale_file_audio_da_elaborare == 0 and not any(identifica_come_video(f.stem) for f in tutti_i_file_nella_cartella if f.is_file()):
        logger("Nessun file audio supportato trovato e nessun file video identificato. Termino la scansione.")
        return file_musicali_info, contatore_non_conformi, 0, 0

    # Ora iteriamo sulla lista pre-filtrata dei file audio e su tutti per i video
    # Questo approccio è un po' inefficiente perché rglob potrebbe essere chiamato due volte indirettamente
    # o filtriamo tutti i file. Per ora, privilegiamo la chiarezza del conteggio.
    
    contatore_generale_file_processati = 0

    for i, file_path in enumerate(tutti_i_file_nella_cartella):
        contatore_generale_file_processati +=1 # Contatore per feedback generale, anche se non è un file audio

        if file_path.is_file():
            if file_path.suffix.lower() in file_supportati:
                contatore_file_audio_analizzati += 1
                logger(f"\n  Analizzo file audio {contatore_file_audio_analizzati}/{totale_file_audio_da_elaborare} (Nome: {file_path.name})", flush=True) # flush=True qui è utile
                if progress_callback:
                    progress_callback(contatore_file_audio_analizzati, totale_file_audio_da_elaborare)

                # Se è un file audio, non può essere un video da spostare subito (la logica video è sotto)
                # Questa parte rimane per i file audio
                titolo_id3_raw, artista_id3_raw = estrai_info_id3(file_path)
                titolo_nomefile_raw, artista_nomefile_raw = estrai_info_da_nome_file(file_path.stem)
                titolo_finale, artista_finale, sorgente_info = None, None, "Nessuna"

                if artista_id3_raw and titolo_id3_raw:
                    artista_finale, titolo_finale, sorgente_info = artista_id3_raw, titolo_id3_raw, "ID3"
                    logger(f"    Info da ID3: Artista='{artista_finale}', Titolo='{titolo_finale}'")
                    if artista_nomefile_raw and titolo_nomefile_raw and (normalizza_testo(artista_id3_raw) != normalizza_testo(artista_nomefile_raw) or normalizza_testo(titolo_id3_raw) != normalizza_testo(titolo_nomefile_raw)):
                        logger(f"      (Nome file suggerisce info diverse: Artista='{artista_nomefile_raw}', Titolo='{titolo_nomefile_raw}')")
                elif artista_nomefile_raw and titolo_nomefile_raw:
                    artista_finale, titolo_finale, sorgente_info = artista_nomefile_raw, titolo_nomefile_raw, "Nome File"
                    logger(f"    Info da Nome File (ID3 mancanti/incompleti): Artista='{artista_finale}', Titolo='{titolo_finale}'")
                else:
                    logger(f"    Info insufficienti da ID3 e Nome File per: {file_path.name} per classificazione audio.")
                    if artista_id3_raw or titolo_id3_raw: logger(f"      (ID3 parziali: Artista='{artista_id3_raw}', Titolo='{titolo_id3_raw}')")
                    if artista_nomefile_raw or titolo_nomefile_raw: logger(f"      (Nome file parziali: Artista='{artista_nomefile_raw}', Titolo='{titolo_nomefile_raw}')")
                    continue # Prossimo file audio
            
                artista_normalizzato = normalizza_testo(artista_finale)
                titolo_normalizzato = normalizza_testo(titolo_finale)

                if artista_normalizzato and titolo_normalizzato and artista_normalizzato != "" and titolo_normalizzato != "":
                    logger(f"    Normalizzati ({sorgente_info}): Artista='{artista_normalizzato}', Titolo='{titolo_normalizzato}'")
                    chiave_brano = (artista_normalizzato, titolo_normalizzato)
                    if chiave_brano not in file_musicali_info:
                        file_musicali_info[chiave_brano] = []
                    file_musicali_info[chiave_brano].append(str(file_path))
                else:
                    logger(f"    Info insufficienti dopo normalizzazione per: {file_path.name} (Artista: '{artista_normalizzato}', Titolo: '{titolo_normalizzato}')")
            
            # Gestione file video (potrebbe essere un file non audio o anche un file audio che matcha i pattern video)
            # Questa logica viene eseguita per TUTTI i file, inclusi quelli già processati come audio.
            # Dobbiamo assicurarci che un file audio non venga spostato come video se è già stato aggiunto a file_musicali_info.
            # Tuttavia, la logica attuale di `identifica_come_video` e il `continue` nello script originale 
            # facevano sì che un file identificato come video venisse spostato e basta.
            # Manteniamo quel comportamento: se è video, è solo video.
            if identifica_come_video(file_path.stem):
                # Se un file audio è stato appena processato e aggiunto a file_musicali_info
                # e ORA viene identificato come video, dobbiamo rimuoverlo da file_musicali_info.
                # Questo scenario è meno probabile se VIDEO_PATTERNS è ben distinto da nomi di file audio validi.
                chiave_da_rimuovere = None
                for chiave, lista_path in file_musicali_info.items():
                    if str(file_path) in lista_path:
                        logger(f"    ATTENZIONE: Il file {file_path.name} era stato considerato audio ma ora è identificato come video. Verrà rimosso dall'analisi duplicati audio.")
                        lista_path.remove(str(file_path))
                        if not lista_path: # se la lista diventa vuota
                            chiave_da_rimuovere = chiave
                        break
                if chiave_da_rimuovere:
                    del file_musicali_info[chiave_da_rimuovere]
                    # Non decrementare contatore_file_audio_analizzati perché era stato contato come audio prima

                logger(f"    -> Identificato come file di tipo video/non conforme: '{file_path.name}'")
                try:
                    nome_file_destinazione = cartella_non_conformi_path / file_path.name
                    counter = 1
                    while nome_file_destinazione.exists():
                        nome_file_destinazione = cartella_non_conformi_path / f"{file_path.stem}_{counter}{file_path.suffix}"
                        counter += 1
                    shutil.move(str(file_path), str(nome_file_destinazione))
                    logger(f"    -> Spostato in: {nome_file_destinazione}")
                    contatore_non_conformi += 1
                except Exception as e:
                    logger(f"    ERRORE durante lo spostamento di {file_path.name} in {cartella_non_conformi_path}: {e}")
                # Non fare continue qui se era un file audio, perché il progress callback deve averlo contato.
                # Ma se era un file audio e viene spostato come video, non dovrebbe più essere nei duplicati audio.
                # La rimozione da file_musicali_info gestisce questo.
    
    logger(f"\nScansione file completata. Analizzati {contatore_file_audio_analizzati} file audio effettivi su {totale_file_audio_da_elaborare} trovati.")
    if contatore_non_conformi > 0:
        logger(f"Spostati {contatore_non_conformi} file non conformi/video in '{cartella_non_conformi_path}'.")
    else:
        logger("Nessun file non conforme/video è stato spostato.")
    return file_musicali_info, contatore_non_conformi, contatore_file_audio_analizzati, totale_file_audio_da_elaborare

def sposta_duplicati(brani_identificati, cartella_duplicati_path, logger=_default_logger):
    """Sposta i file duplicati, mantenendo quello con la dimensione maggiore."""
    logger("\n--- Inizio Gestione Duplicati Audio ---")
    contatore_spostati = 0
    for (artista, titolo), files_originali in brani_identificati.items():
        if len(files_originali) > 1:
            logger(f"Brano: Artista='{artista}', Titolo='{titolo}' - Trovati {len(files_originali)} file.")
            
            file_da_mantenere = None
            dimensione_massima = -1

            # Converti i percorsi stringa in oggetti Path per facilitare l'accesso alle proprietà
            files = [Path(f) for f in files_originali]

            # Trova il file con la dimensione maggiore
            for file_path_obj in files:
                try:
                    dimensione_file = file_path_obj.stat().st_size
                    logger(f"  - File: {file_path_obj.name}, Dimensione: {dimensione_file} bytes")
                    if dimensione_file > dimensione_massima:
                        dimensione_massima = dimensione_file
                        file_da_mantenere = file_path_obj
                except FileNotFoundError:
                    logger(f"    ATTENZIONE: File {file_path_obj} non trovato durante il controllo della dimensione. Sarà ignorato.")
                    continue # Passa al prossimo file se questo non esiste più
            
            if file_da_mantenere:
                logger(f"    -> Mantenuto: {file_da_mantenere.name} (Dimensione: {dimensione_massima} bytes)")
                # Sposta gli altri file
                for file_path_obj in files:
                    if file_path_obj != file_da_mantenere:
                        try:
                            nome_file_destinazione = cartella_duplicati_path / file_path_obj.name
                            # Gestione di eventuali conflitti di nomi nella cartella duplicati
                            counter = 1
                            while nome_file_destinazione.exists():
                                nome_file_destinazione = cartella_duplicati_path / f"{file_path_obj.stem}_{counter}{file_path_obj.suffix}"
                                counter += 1
                            
                            shutil.move(str(file_path_obj), str(nome_file_destinazione))
                            logger(f"    -> Spostato: {file_path_obj.name} in {cartella_duplicati_path}")
                            contatore_spostati += 1
                        except FileNotFoundError:
                             logger(f"    ATTENZIONE: File {file_path_obj.name} non trovato durante tentativo di spostamento.")
                        except Exception as e:
                            logger(f"    ERRORE durante lo spostamento di {file_path_obj.name}: {e}")
            else:
                logger(f"    ATTENZIONE: Non è stato possibile determinare un file da mantenere per {artista} - {titolo}. Nessun file spostato.")
        
    logger("\n--- Gestione Duplicati Audio Completata ---")
    if contatore_spostati > 0:
        logger(f"Spostati {contatore_spostati} file audio duplicati in '{cartella_duplicati_path}'.")
    else:
        logger("Nessun file audio duplicato è stato spostato.")
    # Restituiamo l'elenco dei file che sono stati mantenuti (non spostati come duplicati)
    file_mantenuti = set()
    for _, files_originali in brani_identificati.items():
        if not files_originali: continue
        files_obj = [Path(f) for f in files_originali]
        if len(files_obj) == 1:
            file_mantenuti.add(str(files_obj[0])) # Unico file, quindi mantenuto
        elif len(files_obj) > 1:
            # Identifica di nuovo il file da mantenere basato sulla dimensione
            # Questa logica è duplicata da sopra, potrebbe essere rifattorizzata
            file_da_mantenere_obj = None
            dimensione_massima = -1
            for file_path_obj in files_obj:
                try:
                    dimensione_file = file_path_obj.stat().st_size
                    if dimensione_file > dimensione_massima:
                        dimensione_massima = dimensione_file
                        file_da_mantenere_obj = file_path_obj
                except FileNotFoundError:
                    continue # Ignora se non trovato
            if file_da_mantenere_obj:
                file_mantenuti.add(str(file_da_mantenere_obj))
    return contatore_spostati, file_mantenuti

def sposta_file_da_verificare(file_da_considerare, cartella_base_da_verificare_path, logger=_default_logger):
    """
    Analizza i file specificati (presumibilmente quelli non spostati come duplicati o non conformi)
    per identificare gruppi di versioni dello stesso brano e li sposta in una sottocartella DA_VERIFICARE.
    """
    logger("\n--- Inizio Analisi per File DA VERIFICARE ---")
    if not file_da_considerare:
        logger("Nessun file candidato per l'analisi DA VERIFICARE.")
        return 0

    brani_con_versioni = defaultdict(lambda: {'artista_norm': None, 'titolo_base': None, 'files': []})
    file_processati_per_versione = set() # Per evitare di processare due volte lo stesso file originale

    # 1. Estrai info, normalizza e identifica titolo base per ogni file
    logger("Fase 1: Estrazione info e identificazione titolo base...")
    temp_info_file = [] # Lista di tuple (path_originale, artista_norm, titolo_norm, titolo_base, tag_versione)
    
    for file_path_str in file_da_considerare:
        file_path = Path(file_path_str)
        if not file_path.exists() or not file_path.is_file(): # Controllo extra
            logger(f"  File {file_path.name} non trovato o non è un file, skippo per DA VERIFICARE.")
            continue

        #logger(f"  Considero per DA VERIFICARE: {file_path.name}")
        titolo_id3, artista_id3 = estrai_info_id3(file_path)
        titolo_fn, artista_fn = estrai_info_da_nome_file(file_path.stem)

        artista_finale, titolo_finale = None, None
        if artista_id3 and titolo_id3:
            artista_finale, titolo_finale = artista_id3, titolo_id3
        elif artista_fn and titolo_fn:
            artista_finale, titolo_finale = artista_fn, titolo_fn
        else:
            #logger(f"    Info insufficienti (artista/titolo) per {file_path.name}. Skippato per DA VERIFICARE.")
            continue
            
        artista_normalizzato = normalizza_testo(artista_finale)
        titolo_normalizzato = normalizza_testo(titolo_finale)

        if not (artista_normalizzato and titolo_normalizzato):
            #logger(f"    Info insufficienti post-normalizzazione per {file_path.name}. Skippato.")
            continue

        titolo_base, tag_versione = estrai_titolo_base_e_versione(titolo_normalizzato, logger)
        temp_info_file.append({
            "path_originale": file_path,
            "artista_norm": artista_normalizzato,
            "titolo_norm": titolo_normalizzato, # Titolo completo normalizzato
            "titolo_base": titolo_base,         # Titolo senza tag versione
            "tag_versione": tag_versione       # Es. "(live)", "(remix)"
        })

    # 2. Raggruppa per (artista_norm, titolo_base)
    logger("Fase 2: Raggruppamento per artista e titolo base...")
    brani_per_base = defaultdict(list)
    for info in temp_info_file:
        chiave_base = (info["artista_norm"], info["titolo_base"])
        brani_per_base[chiave_base].append(info)

    # 3. Identifica i gruppi che necessitano verifica (più di un file per titolo base o un file con versione esplicita)
    #    e sposta i file relativi
    contatore_spostati_da_verificare = 0
    file_effettivamente_spostati_o_da_non_toccare_piu = set()

    logger("Fase 3: Identificazione gruppi da verificare e spostamento...")
    if not cartella_base_da_verificare_path.exists():
        try:
            cartella_base_da_verificare_path.mkdir(parents=True, exist_ok=True)
            logger(f"Creata cartella DA_VERIFICARE base: {cartella_base_da_verificare_path}")
        except OSError as e:
            logger(f"ERRORE: Impossibile creare la cartella DA_VERIFICARE base '{cartella_base_da_verificare_path}': {e}. La funzionalità DA VERIFICARE sarà saltata.")
            return 0

    for (artista_norm, titolo_b), lista_info_brani in brani_per_base.items():
        if len(lista_info_brani) > 1: # Trovate più versioni (o l'originale + versioni)
            logger(f"  Gruppo DA VERIFICARE per Artista='{artista_norm}', Titolo Base='{titolo_b}' ({len(lista_info_brani)} file):")
            
            # Crea una sottocartella specifica per questo gruppo
            # Pulisci artista e titolo base per usarli come nomi di cartelle
            nome_cartella_artista = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in artista_norm).strip() or "ArtistaSconosciuto"
            nome_cartella_titolo = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in titolo_b).strip() or "TitoloSconosciuto"
            
            cartella_destinazione_gruppo = cartella_base_da_verificare_path / nome_cartella_artista / nome_cartella_titolo
            try:
                cartella_destinazione_gruppo.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger(f"    ERRORE: Impossibile creare sottocartella DA_VERIFICARE '{cartella_destinazione_gruppo}': {e}. Skippo questo gruppo.")
                continue

            for info_brano in lista_info_brani:
                file_path_originale = info_brano["path_originale"]
                logger(f"    - '{info_brano['titolo_norm']}' (File: {file_path_originale.name})")
                try:
                    # Il nome del file nella destinazione rimane lo stesso del file originale
                    nome_file_dest = cartella_destinazione_gruppo / file_path_originale.name
                    
                    # Gestione conflitti (improbabile se i file sono già unici, ma per sicurezza)
                    counter = 1
                    stem, suffix = file_path_originale.stem, file_path_originale.suffix
                    while nome_file_dest.exists():
                        nome_file_dest = cartella_destinazione_gruppo / f"{stem}_{counter}{suffix}"
                        counter += 1
                        
                    shutil.move(str(file_path_originale), str(nome_file_dest))
                    logger(f"      -> Spostato in: {nome_file_dest}")
                    contatore_spostati_da_verificare += 1
                    file_effettivamente_spostati_o_da_non_toccare_piu.add(str(file_path_originale))
                except FileNotFoundError:
                    logger(f"      ATTENZIONE: File {file_path_originale.name} non trovato durante tentativo di spostamento in DA_VERIFICARE.")
                except Exception as e:
                    logger(f"      ERRORE durante lo spostamento di {file_path_originale.name} in DA_VERIFICARE: {e}")
        # else:
            # logger(f"  Gruppo con 1 solo file per Artista='{artista_norm}', Titolo Base='{titolo_b}'. Nessuna azione DA VERIFICARE.")
            # # Aggiungiamo comunque il file a quelli "processati" per questa fase, così non viene ricontrollato
            # file_effettivamente_spostati_o_da_non_toccare_piu.add(str(lista_info_brani[0]["path_originale"]))


    logger("\n--- Analisi per File DA VERIFICARE Completata ---")
    if contatore_spostati_da_verificare > 0:
        logger(f"Spostati {contatore_spostati_da_verificare} file nella cartella '{cartella_base_da_verificare_path}' per revisione manuale.")
    else:
        logger("Nessun file è stato spostato nella cartella DA VERIFICARE.")
    return contatore_spostati_da_verificare, file_effettivamente_spostati_o_da_non_toccare_piu

def avvia_gestione_duplicati(cartella_musicale_path_abs: Path, cartella_duplicati_path_abs: Path, cartella_non_conformi_path_abs: Path, cartella_da_verificare_path_abs: Path, logger=_default_logger, progress_callback=None):
    """
    Funzione principale per orchestrare la scansione e lo spostamento dei duplicati.
    Accetta percorsi assoluti (oggetti Path) e un logger personalizzato.
    """
    logger(f"Cartella musicale da analizzare: {cartella_musicale_path_abs}")
    logger(f"Cartella per i duplicati audio: {cartella_duplicati_path_abs}")
    logger(f"Cartella per i file non conformi/video: {cartella_non_conformi_path_abs}")
    logger(f"Cartella per i file da verificare: {cartella_da_verificare_path_abs}")

    if not cartella_musicale_path_abs.is_dir():
        logger(f"Errore: La cartella musicale '{cartella_musicale_path_abs}' non esiste o non è una directory.")
        return

    # Crea le cartelle di destinazione se non esistono
    # Questa logica è già assunta essere gestita da chi chiama avvia_gestione_duplicati,
    # ma una doppia verifica non fa male, specialmente per la GUI.
    for p in [cartella_duplicati_path_abs, cartella_non_conformi_path_abs, cartella_da_verificare_path_abs]:
        try:
            p.mkdir(parents=True, exist_ok=True)
            logger(f"Assicurata esistenza cartella: {p}")
        except OSError as e:
            logger(f"Errore durante la creazione o verifica della cartella '{p}': {e}")
            return
    
    logger("\nInizio scansione...")
    # Modifica per ricevere i nuovi valori da scansiona_cartella
    risultato_scansione = scansiona_cartella(cartella_musicale_path_abs, cartella_non_conformi_path_abs, logger, progress_callback)
    brani_identificati = risultato_scansione[0]
    # contatore_non_conformi_restituito = risultato_scansione[1]
    # contatore_audio_analizzati_restituito = risultato_scansione[2]
    # totale_audio_restituito = risultato_scansione[3]

    logger("\n--- Riepilogo Brani Audio Identificati (pre-duplicati) ---")
    if not brani_identificati:
        logger("Nessun brano audio identificato per l'analisi dei duplicati.")
    else:
        for (artista, titolo), files in brani_identificati.items():
            logger(f"Brano: Artista='{artista}', Titolo='{titolo}'")
            for f_path in files:
                logger(f"  - File: {Path(f_path).name} (Percorso: {f_path})")
            if len(files) > 1:
                logger(f"    -> TROVATI {len(files)} file per questo brano (potenziali duplicati)")

    # Colleziona tutti i file originali prima della gestione duplicati
    tutti_i_file_audio_originali_scannerizzati = set()
    for _, files_list in brani_identificati.items():
        for f_path_str in files_list:
            tutti_i_file_audio_originali_scannerizzati.add(f_path_str)

    # Ora, i file in 'file_mantenuti_post_duplicati' sono quelli che NON sono stati spostati in DOPPIONI.
    # Questi sono i candidati per l'analisi "DA VERIFICARE".
    # Dobbiamo essere sicuri che questi file esistano ancora e non siano stati spostati come "NON CONFORMI".
    # I file non conformi sono già stati gestiti in scansiona_cartella e non dovrebbero essere in brani_identificati.
    
    # La logica di sposta_file_da_verificare prenderà i percorsi da file_mantenuti_post_duplicati
    # e li sposterà DALLA LORO POSIZIONE ATTUALE (nella libreria musicale originale)
    # ALLA cartella_da_verificare_path_abs.

    # ---- CORREZIONE BUG CRITICO: Chiamare `sposta_duplicati` e catturare i file mantenuti ----
    contatore_spostati, file_mantenuti_post_duplicati = sposta_duplicati(brani_identificati, cartella_duplicati_path_abs, logger)
    # -----------------------------------------------------------------------------------------

    sposta_file_da_verificare(file_mantenuti_post_duplicati, cartella_da_verificare_path_abs, logger)

    logger("\nOperazione completata.")

def main_cli():
    parser = argparse.ArgumentParser(description="Identifica e sposta i file musicali duplicati e non conformi.")
    parser.add_argument("cartella_musicale", type=str, help="La cartella musicale da analizzare.")
    parser.add_argument("--cartella-duplicati", type=str, default="DOPPIONI",
                        help="La cartella dove spostare i file audio duplicati (default: DOPPIONI).")
    parser.add_argument("--cartella-non-conformi", type=str, default="NON CONFORMI",
                        help="La cartella dove spostare i file non conformi/video (default: NON CONFORMI).")
    parser.add_argument("--cartella-da-verificare", type=str, default="DA_VERIFICARE",
                        help="Sottocartella (relativa a --cartella-duplicati) per file che necessitano revisione (default: DA_VERIFICARE).")
    
    args = parser.parse_args()

    cartella_musicale_path = Path(args.cartella_musicale)
    
    cartella_duplicati_path_arg = Path(args.cartella_duplicati)
    if not cartella_duplicati_path_arg.is_absolute():
        cartella_duplicati_path_abs = (cartella_musicale_path / cartella_duplicati_path_arg).resolve()
    else:
        cartella_duplicati_path_abs = cartella_duplicati_path_arg.resolve()

    cartella_non_conformi_path_arg = Path(args.cartella_non_conformi)
    if not cartella_non_conformi_path_arg.is_absolute():
        cartella_non_conformi_path_abs = (cartella_musicale_path / cartella_non_conformi_path_arg).resolve()
    else:
        cartella_non_conformi_path_abs = cartella_non_conformi_path_arg.resolve()

    # Gestione cartella DA_VERIFICARE (come sottocartella di cartella_duplicati_path_abs)
    cartella_da_verificare_nome_sottocartella = Path(args.cartella_da_verificare)
    cartella_da_verificare_path_abs = (cartella_duplicati_path_abs / cartella_da_verificare_nome_sottocartella).resolve()

    # Definisco un logger specifico per la CLI che usa print con flush=True
    def cli_logger(messaggio):
        print(messaggio, flush=True)

    # Definisco un callback per la progress bar per la CLI
    ultimo_percentuale_stampata = -1
    def cli_progress_callback(corrente, totale):
        nonlocal ultimo_percentuale_stampata
        if totale > 0:
            percentuale = int((corrente / totale) * 100)
            if percentuale > ultimo_percentuale_stampata:
                 # Stampa sulla stessa riga sovrascrivendo
                print(f"Progresso scansione: {corrente}/{totale} ({percentuale}%)          \r", end="", flush=True)
                ultimo_percentuale_stampata = percentuale
        if corrente == totale: # A fine scansione, vai a nuova riga
            print() 

    # Creazione iniziale delle cartelle qui, prima di chiamare la logica principale
    # così avvia_gestione_duplicati può assumerle esistenti (o tentare di ricrearle).
    if not cartella_musicale_path.is_dir():
        cli_logger(f"Errore: La cartella musicale '{cartella_musicale_path}' non esiste o non è una directory.")
        return

    for p in [cartella_duplicati_path_abs, cartella_non_conformi_path_abs, cartella_da_verificare_path_abs]:
        if not p.exists():
            cli_logger(f"Creo la cartella: {p}")
            try:
                p.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                cli_logger(f"Errore durante la creazione della cartella '{p}': {e}")
                return
    
    avvia_gestione_duplicati(
        cartella_musicale_path.resolve(), 
        cartella_duplicati_path_abs, 
        cartella_non_conformi_path_abs,
        cartella_da_verificare_path_abs,
        logger=cli_logger,
        progress_callback=cli_progress_callback
    )

if __name__ == "__main__":
    main_cli() 