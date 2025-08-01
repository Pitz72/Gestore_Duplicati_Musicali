import pytest
from pathlib import Path
from gestore_duplicati_musicali import _estrai_info_file, MusicFile

# Mock per EasyID3, per non dipendere da file reali
class MockEasyID3:
    def __init__(self, tags=None):
        self.tags = tags if tags is not None else {}

    def get(self, key, default):
        return self.tags.get(key, default)

# Test per la nuova funzione _estrai_info_file
def test_estrai_info_file_con_id3_validi(mocker):
    """
    Testa l'estrazione quando i tag ID3 sono presenti e validi.
    """
    # Mock delle dipendenze esterne
    mocker.patch('gestore_duplicati_musicali.EasyID3', return_value=MockEasyID3({
        'artist': ['Artista ID3'],
        'title': ['Titolo ID3 (Live)']
    }))
    mocker.patch('pathlib.Path.stat', return_value=mocker.Mock(st_size=12345))
    mock_path = Path('/fake/dir/Artista ID3 - Titolo ID3 (Live).mp3')
    mocker.patch('gestore_duplicati_musicali.estrai_info_da_nome_file', return_value=('Artista NomeFile', 'Titolo NomeFile'))

    # Esecuzione
    result = _estrai_info_file(mock_path)

    # Asserzioni
    assert result is not None
    assert isinstance(result, MusicFile)
    assert result.artista_norm == 'artista id3'
    assert result.titolo_norm == 'titolo id3 (live)'
    assert result.titolo_base_norm == 'titolo id3'
    assert result.tag_versione == '(live)'
    assert result.sorgente_info == 'ID3'
    assert result.dimensione == 12345
    assert result.path == mock_path

def test_estrai_info_file_fallback_su_nome_file(mocker):
    """
    Testa il fallback all'analisi del nome del file quando i tag ID3 mancano.
    """
    # Mock delle dipendenze
    mocker.patch('gestore_duplicati_musicali.EasyID3', return_value=MockEasyID3({})) # ID3 vuoti
    mocker.patch('pathlib.Path.stat', return_value=mocker.Mock(st_size=54321))
    mock_path = Path('/fake/dir/Artista NomeFile - Titolo NomeFile [Remix].mp3')
    # Assicuriamo che la funzione vera sia chiamata, ma la mockiamo per isolare il test se necessario
    mocker.patch('gestore_duplicati_musicali.estrai_info_da_nome_file', return_value=('Artista NomeFile', 'Titolo NomeFile [Remix]'))

    # Esecuzione
    result = _estrai_info_file(mock_path)

    # Asserzioni
    assert result is not None
    assert result.artista_norm == 'artista nomefile'
    assert result.titolo_norm == 'titolo nomefile [remix]'
    assert result.titolo_base_norm == 'titolo nomefile'
    assert result.tag_versione == '[remix]'
    assert result.sorgente_info == 'Nome File'
    assert result.dimensione == 54321

def test_estrai_info_file_info_insufficienti_id3_parziali(mocker):
    """
    Testa che il file venga scartato se i tag ID3 sono incompleti e il nome file non è parsabile.
    """
    mocker.patch('mutagen.easyid3.EasyID3', return_value=MockEasyID3({'artist': ['Artista ID3']})) # Manca il titolo
    mocker.patch('gestore_duplicati_musicali.estrai_info_da_nome_file', return_value=(None, None)) # Nome file non valido
    mock_path = Path('/fake/dir/file_invalido.mp3')

    result = _estrai_info_file(mock_path)
    assert result is None

def test_estrai_info_file_info_insufficienti_post_normalizzazione(mocker):
    """
    Testa che il file venga scartato se le info post-normalizzazione sono vuote.
    """
    mocker.patch('mutagen.easyid3.EasyID3', return_value=MockEasyID3({'artist': [' '], 'title': [' ']}))
    mock_path = Path('/fake/dir/empty.mp3')

    result = _estrai_info_file(mock_path)
    assert result is None
