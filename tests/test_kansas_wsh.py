import copy
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "server"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import kansas_wsh


class _FakeCachingLoader(dict):
    def __init__(self, values):
        super().__init__(copy.deepcopy(values))


def _sample_deck(prefix):
    return {
        "deck_name": f"{prefix}.txt",
        "resource_prefix": "https://example.invalid/scans/en/",
        "default_back_url": "/third_party/images/mtg_detail.jpg",
        "urls": {0: f"{prefix}/1.jpg", 1: f"{prefix}/2.jpg"},
    }


def test_combine_decks_appends_second_deck_urls():
    d1 = _sample_deck("a")
    d2 = _sample_deck("b")

    combined = kansas_wsh.combine_decks(d1, d2)

    assert combined["urls"][0] == "a/1.jpg"
    assert combined["urls"][1] == "a/2.jpg"
    assert combined["urls"][2] == "b/1.jpg"
    assert combined["urls"][3] == "b/2.jpg"


def test_move_card_updates_index_and_destination(monkeypatch):
    monkeypatch.setattr(kansas_wsh, "CachingLoader", _FakeCachingLoader)
    monkeypatch.setattr(kansas_wsh.decks, "decklist", [_sample_deck("a"), _sample_deck("b")])

    state = kansas_wsh.KansasGameState(0, 1)

    src_type, src_key = state.moveCard(card=0, dest_type="hands", dest_key="alice", dest_orient=1)

    assert src_type == "board"
    assert isinstance(src_key, int)
    assert state.index[0] == ("hands", "alice")
    assert 0 in state.data["hands"]["alice"]
    assert state.data["orientations"][0] == 1
