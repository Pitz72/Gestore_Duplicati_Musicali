import pytest
from gestore_duplicati_musicali import normalizza_testo, estrai_titolo_base_e_versione, identifica_come_video

# --- Test per normalizza_testo ---

def test_normalizza_testo_minuscolo_e_trim():
    assert normalizza_testo("  Testo con Spazi  ") == "testo con spazi"

def test_normalizza_testo_punteggiatura():
    assert normalizza_testo("Testo, con. punteggiatura!?'#*:") == "testo con punteggiatura"

def test_normalizza_testo_parentesi_conservate():
    assert normalizza_testo("Titolo (Live) [Remix]") == "titolo (live) [remix]"

def test_normalizza_testo_spazi_interni_parentesi():
    assert normalizza_testo("Titolo ( Live ) [ Remix ]") == "titolo (live) [remix]"

def test_normalizza_testo_and_commerciale():
    assert normalizza_testo("Artista & Altro") == "artista and altro"

def test_normalizza_testo_spazi_multipli():
    assert normalizza_testo("Testo   con   spazi   multipli") == "testo con spazi multipli"

def test_normalizza_testo_nullo():
    assert normalizza_testo(None) is None

def test_normalizza_testo_stringa_vuota():
    assert normalizza_testo("") == ""


# --- Test per estrai_titolo_base_e_versione ---

def test_estrai_versione_live():
    titolo = "some great song (live at wembley)"
    base, versione = estrai_titolo_base_e_versione(titolo)
    assert base == "some great song"
    assert versione == "(live at wembley)"

def test_estrai_versione_remix_quadre():
    titolo = "another song [dj something remix]"
    base, versione = estrai_titolo_base_e_versione(titolo)
    assert base == "another song"
    assert versione == "[dj something remix]"

def test_estrai_versione_remastered_con_anno():
    titolo = "classic hit (2023 remaster)"
    base, versione = estrai_titolo_base_e_versione(titolo)
    assert base == "classic hit"
    assert versione == "(2023 remaster)"

def test_estrai_nessuna_versione():
    titolo = "un titolo normale senza versioni"
    base, versione = estrai_titolo_base_e_versione(titolo)
    assert base == "un titolo normale senza versioni"
    assert versione is None

def test_estrai_versione_pulisce_trattino_finale():
    titolo = "song title - (acoustic)"
    base, versione = estrai_titolo_base_e_versione(titolo)
    assert base == "song title"
    assert versione == "(acoustic)"

def test_estrai_versione_con_solo_spazio_e_parentesi():
    titolo = "titolo (unplugged)"
    base, versione = estrai_titolo_base_e_versione(titolo)
    assert base == "titolo"
    assert versione == "(unplugged)"

# --- Test per identifica_come_video ---

@pytest.mark.parametrize("nome_file, expected", [
    ("Artista - Titolo (Official Video)", True),
    ("Artista - Titolo [Official Music Video]", True),
    ("Artista - Titolo (Lyrics Video)", True),
    ("Artista - Titolo (lyric video)", True),
    ("Artista - Titolo (Visualizer)", True),
    ("Artista - Titolo (official_video)", False), # underscore non matcha
    ("Artista - Titolo", False),
    ("Artista - Titolo (Live)", False)
])
def test_identifica_come_video_parametri(nome_file, expected):
    assert identifica_come_video(nome_file) == expected

def test_estrai_versione_remastered_con_anno_quadre():
    titolo = "classic hit [2023 remaster]"
    base, versione = estrai_titolo_base_e_versione(titolo)
    assert base == "classic hit"
    assert versione == "[2023 remaster]"
