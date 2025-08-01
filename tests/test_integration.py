import pytest
from pathlib import Path
import shutil
from gestore_duplicati_musicali import avvia_gestione_duplicati

# Helper per creare file fittizi
def crea_file_fittizio(path: Path, contenuto: str = "data"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contenuto)

# Mock per la lettura dei tag ID3 per questo test specifico
class MockEasyID3Integration:
    def __init__(self, file_path):
        self.path = file_path
        self.tags = {
            'Traccia Buona.mp3': {'artist': ['Artista 1'], 'title': ['Traccia Buona']},
            'Traccia Buona (Copia).mp3': {'artist': ['Artista 1'], 'title': ['Traccia Buona']},
            'Traccia Buona (Live).mp3': {'artist': ['Artista 1'], 'title': ['Traccia Buona (Live)']},
            'Traccia Altro Artista.mp3': {'artist': ['Artista 2'], 'title': ['Traccia Altro Artista']},
            'File Video.mp4': {},
        }
        # Il nome del file è la chiave per ottenere i tag
        self.file_tags = self.tags.get(Path(file_path).name, {})

    def get(self, key, default):
        return self.file_tags.get(key, default)

@pytest.fixture
def libreria_musicale_test(tmp_path):
    """Crea una struttura di cartelle e file per il test di integrazione."""
    cartella_musicale = tmp_path / "musica"

    # Crea file
    crea_file_fittizio(cartella_musicale / "Traccia Buona.mp3", "dati di qualità superiore") # Da mantenere
    crea_file_fittizio(cartella_musicale / "sottocartella" / "Traccia Buona (Copia).mp3", "dati") # Duplicato
    crea_file_fittizio(cartella_musicale / "Traccia Buona (Live).mp3", "dati live") # Versione
    crea_file_fittizio(cartella_musicale / "Traccia Altro Artista.mp3", "dati2") # Unico
    crea_file_fittizio(cartella_musicale / "File Video (official video).mp4", "video") # Non conforme
    crea_file_fittizio(cartella_musicale / "documento.txt", "testo") # Non supportato

    return cartella_musicale

def test_flusso_completo_integrazione(libreria_musicale_test, mocker):
    """
    Testa l'intero flusso di lavoro: scansione, pianificazione ed esecuzione.
    """
    # Mock di EasyID3 per usare la nostra classe di mock specifica per l'integrazione
    mocker.patch('gestore_duplicati_musicali.EasyID3', MockEasyID3Integration)

    cartella_musicale = libreria_musicale_test
    cartella_doppioni = cartella_musicale / "DOPPIONI"
    cartella_non_conformi = cartella_musicale / "NON CONFORMI"
    cartella_da_verificare = cartella_doppioni / "DA_VERIFICARE"

    # Esegui la funzione principale
    avvia_gestione_duplicati(
        cartella_musicale,
        cartella_doppioni,
        cartella_non_conformi,
        cartella_da_verificare,
        logger=lambda msg, flush=True: None # Logger silenzioso per il test
    )

    # --- VERIFICHE ---

    # 1. File non conformi
    assert (cartella_non_conformi / "File Video (official video).mp4").exists()
    assert (cartella_non_conformi / "documento.txt").exists()
    assert not (cartella_musicale / "File Video (official video).mp4").exists()

    # 2. Duplicati
    assert (cartella_doppioni / "Traccia Buona (Copia).mp3").exists()
    assert not (cartella_musicale / "sottocartella" / "Traccia Buona (Copia).mp3").exists()

    # 3. File mantenuto (non è un duplicato esatto e non ha altre versioni "base")
    assert (cartella_musicale / "Traccia Altro Artista.mp3").exists()

    # 4. File da verificare (gruppo di versioni)
    # Poiché "Traccia Buona" e "Traccia Buona (Live)" hanno lo stesso titolo base,
    # entrambi dovrebbero essere spostati in DA_VERIFICARE per la revisione.
    cartella_gruppo_da_verificare = cartella_da_verificare / "artista 1" / "traccia buona"
    assert (cartella_gruppo_da_verificare / "Traccia Buona.mp3").exists()
    assert (cartella_gruppo_da_verificare / "Traccia Buona (Live).mp3").exists()
    assert not (cartella_musicale / "Traccia Buona.mp3").exists()
    assert not (cartella_musicale / "Traccia Buona (Live).mp3").exists()
