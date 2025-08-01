import os
import shutil
import argparse
import re
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen import MutagenError
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Set

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

@dataclass(frozen=True)
class MusicFile:
    """Rappresenta un singolo file musicale e i suoi metadati."""
    path: Path
    artista_norm: str
    titolo_norm: str
    titolo_base_norm: str
    tag_versione: Optional[str]
    dimensione: int
    sorgente_info: str


@dataclass(frozen=True)
class SpostaFileAzione:
    """Rappresenta una singola operazione di spostamento file."""
    sorgente: Path
    destinazione: Path
    motivazione: str # Es. "Duplicato", "Versione da Verificare"


def _default_logger(messaggio, flush=True):
    print(messaggio, flush=flush)


def _estrai_info_file(file_path: Path, logger=_default_logger) -> Optional[MusicFile]:
    """
    Estrae, normalizza e struttura le informazioni di un singolo file musicale.
    Restituisce un oggetto MusicFile o None se le informazioni sono insufficienti.
    """
    # 1. Estrazione Raw
    titolo_id3_raw, artista_id3_raw = estrai_info_id3(file_path)
    artista_nomefile_raw, titolo_nomefile_raw = estrai_info_da_nome_file(file_path.stem)

    artista_finale, titolo_finale, sorgente_info = None, None, "Nessuna"

    if artista_id3_raw and titolo_id3_raw:
        artista_finale = artista_id3_raw
        titolo_finale = titolo_id3_raw
        sorgente_info = "ID3"
    elif artista_nomefile_raw and titolo_nomefile_raw:
        artista_finale = artista_nomefile_raw
        titolo_finale = titolo_nomefile_raw
        sorgente_info = "Nome File"
    else:
        logger(f"    Info insufficienti (ID3/Nome File) per: {file_path.name}")
        return None

    # 2. Normalizzazione
    artista_normalizzato = normalizza_testo(artista_finale)
    titolo_normalizzato = normalizza_testo(titolo_finale)

    if not (artista_normalizzato and titolo_normalizzato):
        logger(f"    Info insufficienti post-normalizzazione per: {file_path.name}")
        return None

    # 3. Estrazione Titolo Base e Versione
    titolo_base, tag_versione = estrai_titolo_base_e_versione(titolo_normalizzato, logger)

    # 4. Recupero Metadati Aggiuntivi
    try:
        dimensione = file_path.stat().st_size
    except FileNotFoundError:
        logger(f"    ATTENZIONE: File {file_path.name} non trovato durante lettura dimensione.")
        return None

    return MusicFile(
        path=file_path,
        artista_norm=artista_normalizzato,
        titolo_norm=titolo_normalizzato,
        titolo_base_norm=titolo_base,
        tag_versione=tag_versione,
        dimensione=dimensione,
        sorgente_info=sorgente_info
    )


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

def scansiona_cartella(cartella_path: Path, cartella_non_conformi_path: Path, logger=_default_logger, progress_callback=None) -> Tuple[List[MusicFile], int]:
    """
    Scansiona la cartella, sposta i file video/non-conformi e restituisce una lista
    di oggetti MusicFile per i file audio validi.
    """
    file_musicali_validi: List[MusicFile] = []
    file_supportati = ['.mp3']
    contatore_non_conformi = 0
    contatore_file_audio_analizzati = 0

    logger(f"Inizio pre-scansione per conteggio file in: {cartella_path}")
    # Usiamo un generatore per efficienza, ma lo convertiamo a lista per il conteggio
    tutti_i_file_nella_cartella = list(cartella_path.rglob('*'))
    file_audio_da_elaborare_lista = [f for f in tutti_i_file_nella_cartella if f.is_file() and f.suffix.lower() in file_supportati]
    totale_file_audio_da_elaborare = len(file_audio_da_elaborare_lista)
    
    logger(f"Trovati {totale_file_audio_da_elaborare} file audio ({', '.join(file_supportati)}) da analizzare.")
    logger(f"I file non audio o identificati come 'video' verranno spostati in: {cartella_non_conformi_path}")

    if not tutti_i_file_nella_cartella:
        logger("Nessun file trovato nella cartella. Termino la scansione.")
        return [], 0

    for file_path in tutti_i_file_nella_cartella:
        if not file_path.is_file():
            continue

        # Fase 1: Identificazione e spostamento file non conformi/video
        is_video = identifica_come_video(file_path.stem)
        is_audio_supportato = file_path.suffix.lower() in file_supportati

        if is_video or not is_audio_supportato:
            if is_video:
                logger(f"  -> Identificato come file di tipo video/non conforme: '{file_path.name}'")
            else: # File non supportato
                logger(f"  -> File non supportato, trattato come non conforme: '{file_path.name}'")

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
                logger(f"    ERRORE durante lo spostamento di {file_path.name}: {e}")
            continue # Passa al file successivo

        # Fase 2: Processamento file audio
        contatore_file_audio_analizzati += 1
        logger(f"\n  Analizzo file audio {contatore_file_audio_analizzati}/{totale_file_audio_da_elaborare} (Nome: {file_path.name})", flush=True)
        if progress_callback:
            progress_callback(contatore_file_audio_analizzati, totale_file_audio_da_elaborare)

        info_file = _estrai_info_file(file_path, logger)
        if info_file:
            logger(f"    Normalizzati ({info_file.sorgente_info}): Artista='{info_file.artista_norm}', Titolo='{info_file.titolo_norm}'")
            file_musicali_validi.append(info_file)
        else:
            # Il logger dentro _estrai_info_file ha già dato dettagli
            logger(f"    File {file_path.name} scartato per info insufficienti.")
    
    logger(f"\nScansione file completata. Analizzati {contatore_file_audio_analizzati} file audio.")
    if contatore_non_conformi > 0:
        logger(f"Spostati {contatore_non_conformi} file non conformi in '{cartella_non_conformi_path}'.")
    else:
        logger("Nessun file non conforme è stato spostato.")

    return file_musicali_validi, contatore_non_conformi

def pianifica_spostamento_duplicati(file_musicali: List[MusicFile], cartella_duplicati_path: Path, logger=_default_logger) -> Tuple[List[SpostaFileAzione], Set[MusicFile]]:
    """
    Analizza una lista di MusicFile e pianifica lo spostamento dei duplicati.
    NON esegue lo spostamento, ma restituisce una lista di azioni da compiere.
    """
    logger("\n--- Inizio Pianificazione Spostamento Duplicati ---")
    azioni: List[SpostaFileAzione] = []
    file_mantenuti: Set[MusicFile] = set()

    brani_identificati: Dict[Tuple[str, str], List[MusicFile]] = defaultdict(list)
    for mf in file_musicali:
        brani_identificati[(mf.artista_norm, mf.titolo_norm)].append(mf)

    for (artista, titolo), files_in_gruppo in brani_identificati.items():
        if len(files_in_gruppo) == 1:
            file_mantenuti.add(files_in_gruppo[0])
            continue

        logger(f"Brano: Artista='{artista}', Titolo='{titolo}' - Trovati {len(files_in_gruppo)} file (potenziali duplicati).")
        
        file_da_mantenere = max(files_in_gruppo, key=lambda mf: mf.dimensione, default=None)

        if file_da_mantenere:
            file_mantenuti.add(file_da_mantenere)
            logger(f"    -> Da Mantenere: {file_da_mantenere.path.name} (Dimensione: {file_da_mantenere.dimensione} bytes)")

            for mf_da_spostare in files_in_gruppo:
                if mf_da_spostare != file_da_mantenere:
                    # La gestione di nomi duplicati nella destinazione verrà fatta dall'esecutore del piano
                    destinazione_proposta = cartella_duplicati_path / mf_da_spostare.path.name
                    azione = SpostaFileAzione(
                        sorgente=mf_da_spostare.path,
                        destinazione=destinazione_proposta,
                        motivazione="Duplicato"
                    )
                    azioni.append(azione)
                    logger(f"    -> Da Spostare: {mf_da_spostare.path.name} -> {destinazione_proposta}")
        else:
            logger(f"    ATTENZIONE: Non è stato possibile determinare un file da mantenere per '{artista} - {titolo}'.")
            file_mantenuti.update(files_in_gruppo)

    logger(f"Pianificate {len(azioni)} azioni di spostamento per duplicati.")
    return azioni, file_mantenuti

def pianifica_spostamento_da_verificare(file_da_considerare: Set[MusicFile], cartella_base_da_verificare_path: Path, logger=_default_logger) -> List[SpostaFileAzione]:
    """
    Analizza un set di MusicFile e pianifica lo spostamento di gruppi di versioni
    dello stesso brano per una revisione manuale.
    """
    logger("\n--- Inizio Pianificazione File DA VERIFICARE ---")
    azioni: List[SpostaFileAzione] = []
    if not file_da_considerare:
        logger("Nessun file candidato per l'analisi DA VERIFICARE.")
        return azioni

    brani_per_base: Dict[Tuple[str, str], List[MusicFile]] = defaultdict(list)
    for mf in file_da_considerare:
        brani_per_base[(mf.artista_norm, mf.titolo_base_norm)].append(mf)

    for (artista_norm, titolo_base), lista_brani in brani_per_base.items():
        if len(lista_brani) > 1:
            logger(f"  Gruppo DA VERIFICARE per Artista='{artista_norm}', Titolo Base='{titolo_base}' ({len(lista_brani)} file):")
            
            nome_cartella_artista = "".join(c for c in artista_norm if c.isalnum() or c in (' ', '_')).strip() or "ArtistaSconosciuto"
            nome_cartella_titolo = "".join(c for c in titolo_base if c.isalnum() or c in (' ', '_')).strip() or "TitoloSconosciuto"
            cartella_destinazione_gruppo = cartella_base_da_verificare_path / nome_cartella_artista / nome_cartella_titolo

            for mf_da_spostare in lista_brani:
                destinazione_proposta = cartella_destinazione_gruppo / mf_da_spostare.path.name
                azione = SpostaFileAzione(
                    sorgente=mf_da_spostare.path,
                    destinazione=destinazione_proposta,
                    motivazione="Versione da Verificare"
                )
                azioni.append(azione)
                logger(f"    - Pianificato spostamento per '{mf_da_spostare.path.name}' in '{cartella_destinazione_gruppo}'")

    logger(f"Pianificate {len(azioni)} azioni di spostamento per file DA VERIFICARE.")
    return azioni


def esegui_piano_azioni(piano: List[SpostaFileAzione], logger=_default_logger) -> int:
    """
    Esegue una lista di azioni di spostamento, gestendo la creazione di cartelle
    e i conflitti di nomi.
    """
    logger("\n--- Inizio Esecuzione Piano di Spostamento ---")
    contatore_spostati = 0
    if not piano:
        logger("Piano di azioni vuoto. Nessun file da spostare.")
        return 0

    for azione in piano:
        try:
            # Assicura che la cartella di destinazione esista
            azione.destinazione.parent.mkdir(parents=True, exist_ok=True)

            # Gestisci conflitti di nomi
            nome_file_dest = azione.destinazione
            counter = 1
            while nome_file_dest.exists():
                nome_file_dest = azione.destinazione.parent / f"{azione.destinazione.stem}_{counter}{azione.destinazione.suffix}"
                counter += 1

            shutil.move(str(azione.sorgente), str(nome_file_dest))
            logger(f"  -> Spostato: '{azione.sorgente.name}' in '{nome_file_dest.parent}' ({azione.motivazione})")
            contatore_spostati += 1

        except FileNotFoundError:
            logger(f"    ATTENZIONE: File sorgente non trovato, impossibile spostare: {azione.sorgente}")
        except Exception as e:
            logger(f"    ERRORE durante lo spostamento di {azione.sorgente.name}: {e}")

    logger(f"Esecuzione completata. Spostati {contatore_spostati} file.")
    return contatore_spostati


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

    # Assicura che le cartelle di destinazione esistano prima di ogni operazione
    for p in [cartella_duplicati_path_abs, cartella_non_conformi_path_abs, cartella_da_verificare_path_abs]:
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger(f"Errore critico durante la creazione della cartella '{p}': {e}")
            return
    
    # 1. Scansiona la cartella, sposta i non conformi e ottieni una lista di file audio validi
    logger("\n--- Fase 1: Scansione e Analisi File ---")
    file_musicali_validi, _ = scansiona_cartella(
        cartella_musicale_path_abs,
        cartella_non_conformi_path_abs,
        logger,
        progress_callback
    )

    if not file_musicali_validi:
        logger("Nessun file audio valido trovato da processare. Operazione completata.")
        return

    # 2. Pianifica lo spostamento dei duplicati e ottieni la lista dei file unici mantenuti
    azioni_duplicati, file_mantenuti = pianifica_spostamento_duplicati(
        file_musicali_validi,
        cartella_duplicati_path_abs,
        logger
    )

    # 3. Pianifica lo spostamento delle diverse versioni dai file rimasti
    azioni_da_verificare = pianifica_spostamento_da_verificare(
        file_mantenuti,
        cartella_da_verificare_path_abs,
        logger
    )

    # 4. Combina ed esegui il piano completo di azioni
    piano_completo = azioni_duplicati + azioni_da_verificare
    esegui_piano_azioni(piano_completo, logger)

    logger("\n--- Operazione Completata ---")

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