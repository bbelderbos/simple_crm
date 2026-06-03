from datetime import date

import pytest
from freezegun import freeze_time

from crm import data


@pytest.fixture(autouse=True)
def crm_data(tmp_path, monkeypatch):
    monkeypatch.setenv("CRM_DATA", str(tmp_path))
    (tmp_path / "contacts").mkdir()
    return tmp_path


def test_codes_increment_per_initials():
    assert data.create_contact("Jane Doe") == "jd1"
    assert data.create_contact("John Davis") == "jd2"
    assert data.create_contact("Alice Smith") == "as1"


def test_code_falls_back_when_name_has_no_letters():
    assert data.next_code("") == "xx1"


def test_create_and_read_contact():
    code = data.create_contact("Jane Doe", email="j@co.com", company="Acme")
    info = data.parse_header(data.read_contact(code))
    assert info["name"] == "Jane Doe"
    assert info["email"] == "j@co.com"
    assert info["company"] == "Acme"


def test_read_missing_contact_raises():
    with pytest.raises(FileNotFoundError):
        data.read_contact("zz9")


@freeze_time("2026-06-02")
def test_add_note_appends_dated_line():
    code = data.create_contact("Jane Doe")
    data.add_note(code, "called, left voicemail")
    notes = [
        line for line in data.read_contact(code).splitlines() if line.startswith("- ")
    ]
    assert notes[-1].endswith("called, left voicemail")
    assert "2026-06-02" in notes[-1]


def test_add_note_to_missing_contact_raises():
    with pytest.raises(FileNotFoundError):
        data.add_note("zz9", "nope")


def test_add_and_load_products():
    data.add_product("pro", "Pro Plan", "49")
    data.add_product("ent", "Enterprise", "299")
    products = data.load_products()
    assert [p["Code"] for p in products] == ["pro", "ent"]
    assert products[0]["Name"] == "Pro Plan"
    assert products[1]["Price"] == "299"


def test_add_duplicate_product_raises():
    data.add_product("pro", "Pro Plan", "49")
    with pytest.raises(ValueError):
        data.add_product("pro", "Dup", "1")


def test_create_contact_stores_product():
    code = data.create_contact("Jane Doe", product="pro")
    assert data.parse_header(data.read_contact(code))["product"] == "pro"


def test_reminders_roundtrip_sorted_by_due():
    data.create_contact("Jane Doe")
    data.add_reminder("jd1", "follow up", date(2026, 6, 10))
    data.add_reminder("jd1", "send proposal", date(2026, 6, 1))
    rows = data.load_reminders()
    assert [r["Due"] for r in rows] == ["2026-06-01", "2026-06-10"]


def test_single_word_names_do_not_collide():
    first = data.create_contact("Cher")
    second = data.create_contact("Carlos")
    assert first != second
    assert "Cher" in data.read_contact(first)
    assert "Carlos" in data.read_contact(second)


def test_next_code_increments_for_single_word_name():
    data.create_contact("Cher")
    assert data.next_code("Carlos") == "c2"


# C2: load_reminders filters out Done==yes, and add_reminder round-trips through
# it, so completed reminders are dropped on the next add.
def test_completed_reminder_survives_adding_another(crm_data):
    path = crm_data / "reminders.md"
    path.write_text(data.REMINDERS_HEADER + "| 2026-06-01 | jd1 | done task | yes |\n")
    data.add_reminder("jd1", "new task", date(2026, 6, 5))
    assert "done task" in path.read_text()


# M1: add_reminder's return is len(rows) — not an id, never consumed. Drop it.
def test_add_reminder_returns_none():
    data.create_contact("Jane Doe")
    assert data.add_reminder("jd1", "x", date(2026, 6, 5)) is None


# M2: a hand-typed '|' in a field breaks the Markdown-table round-trip; reject
# it on the write path.
def test_add_product_rejects_pipe_in_field():
    with pytest.raises(ValueError):
        data.add_product("pro", "Pro | Plus", "49")


def test_add_reminder_rejects_pipe_in_description():
    data.create_contact("Jane Doe")
    with pytest.raises(ValueError):
        data.add_reminder("jd1", "call | email", date(2026, 6, 5))
