import pytest
from typer.testing import CliRunner

from crm import data
from crm.cli import cli

runner = CliRunner()


@pytest.fixture(autouse=True)
def crm_data(tmp_path, monkeypatch):
    monkeypatch.setenv("CRM_DATA", str(tmp_path))
    return tmp_path


def _add_jane() -> None:
    result = runner.invoke(cli, ["add"], input="Jane Doe\nj@co.com\nAcme\n")
    assert result.exit_code == 0


def test_product_add_then_list():
    runner.invoke(cli, ["init"])
    result = runner.invoke(cli, ["product", "add", "pro", "Pro Plan", "49"])
    assert result.exit_code == 0
    listed = runner.invoke(cli, ["product", "list"])
    assert "pro" in listed.output
    assert "Pro Plan" in listed.output


def test_product_add_duplicate_errors():
    runner.invoke(cli, ["init"])
    runner.invoke(cli, ["product", "add", "pro", "Pro Plan", "49"])
    result = runner.invoke(cli, ["product", "add", "pro", "Dup", "1"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_product_list_empty():
    runner.invoke(cli, ["init"])
    result = runner.invoke(cli, ["product", "list"])
    assert result.exit_code == 0
    assert "No products" in result.output


def test_add_with_product_shows_in_list():
    runner.invoke(cli, ["init"])
    runner.invoke(cli, ["product", "add", "pro", "Pro Plan", "49"])
    result = runner.invoke(cli, ["add"], input="Jane Doe\nj@co.com\nAcme\npro\n")
    assert result.exit_code == 0
    listed = runner.invoke(cli, ["list"])
    assert "pro" in listed.output


def test_add_with_unknown_product_errors():
    runner.invoke(cli, ["init"])
    runner.invoke(cli, ["product", "add", "pro", "Pro Plan", "49"])
    result = runner.invoke(cli, ["add"], input="Jane Doe\nj@co.com\nAcme\nzz\n")
    assert result.exit_code == 1
    assert "Unknown product" in result.output


def test_init_creates_files(crm_data):
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert (crm_data / "contacts").is_dir()
    assert (crm_data / "products.md").exists()
    assert (crm_data / "reminders.md").exists()


def test_add_then_list_shows_contact():
    runner.invoke(cli, ["init"])
    _add_jane()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "jd1" in result.output
    assert "Jane Doe" in result.output


def test_list_without_init_errors():
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 1
    assert "init" in result.output


def test_get_contact():
    runner.invoke(cli, ["init"])
    _add_jane()
    result = runner.invoke(cli, ["get", "jd1"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output


def test_get_missing_contact_errors():
    runner.invoke(cli, ["init"])
    result = runner.invoke(cli, ["get", "zz9"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_note_appends_to_contact():
    runner.invoke(cli, ["init"])
    _add_jane()
    result = runner.invoke(cli, ["note", "jd1", "had intro call"])
    assert result.exit_code == 0
    assert "had intro call" in runner.invoke(cli, ["get", "jd1"]).output


def test_note_missing_contact_errors():
    runner.invoke(cli, ["init"])
    result = runner.invoke(cli, ["note", "zz9", "nope"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_remind_then_reminders_lists_it():
    runner.invoke(cli, ["init"])
    _add_jane()
    result = runner.invoke(cli, ["remind", "jd1", "follow up", "--in", "7"])
    assert result.exit_code == 0
    listed = runner.invoke(cli, ["reminders"])
    assert "follow up" in listed.output
    assert "jd1" in listed.output


def test_remind_missing_contact_errors():
    runner.invoke(cli, ["init"])
    result = runner.invoke(cli, ["remind", "zz9", "nope", "--in", "3"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_reminders_empty():
    runner.invoke(cli, ["init"])
    result = runner.invoke(cli, ["reminders"])
    assert result.exit_code == 0
    assert "No reminders" in result.output


# --- Bug repros (see ~/reviews/simple_crm-full-2026-06-03.md) ---


# m1: a hand-edited, unparseable Due date makes `reminders` crash with a raw
# ValueError traceback instead of skipping the bad row.
def test_reminders_survives_malformed_date(crm_data):
    runner.invoke(cli, ["init"])
    path = crm_data / "reminders.md"
    path.write_text(data.REMINDERS_HEADER + "| not-a-date | jd1 | bad row | no |\n")
    result = runner.invoke(cli, ["reminders"])
    assert result.exit_code == 0


# m4: --in accepts negatives, silently creating a reminder in the past.
def test_remind_rejects_negative_days():
    runner.invoke(cli, ["init"])
    _add_jane()
    result = runner.invoke(cli, ["remind", "jd1", "past", "--in", "-3"])
    assert result.exit_code == 1
