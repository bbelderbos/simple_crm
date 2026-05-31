from datetime import date, datetime, timedelta

import typer
from rich.console import Console
from rich.table import Table

from . import data

cli = typer.Typer(help="A tiny CLI CRM backed by Markdown files.")
console = Console()


@cli.command()
def init() -> None:
    data.crm_data().mkdir(parents=True, exist_ok=True)
    products = data.crm_data() / "products.md"
    if not products.exists():
        products.write_text(data.PRODUCTS_HEADER)
    data.contacts_dir().mkdir(exist_ok=True)
    reminders = data.crm_data() / "reminders.md"
    if not reminders.exists():
        reminders.write_text(data.REMINDERS_HEADER)
    console.print(f"Initialized CRM data at {data.crm_data()}")


@cli.command()
def add(
    name: str = typer.Option(..., prompt=True),
    email: str = typer.Option("", prompt=True),
    company: str = typer.Option("", prompt=True),
) -> None:
    code = data.create_contact(name, email=email, company=company)
    console.print(f"Created contact [bold]{code}[/bold]")


@cli.command(name="list")
def list_contacts() -> None:
    cdir = data.contacts_dir()
    if not cdir.exists():
        console.print("No contacts. Run `crm init` first.")
        raise typer.Exit(1)
    table = Table(title="Contacts")
    table.add_column("Code", style="cyan")
    table.add_column("Name")
    table.add_column("Company")
    table.add_column("Stage", style="green")
    for f in sorted(cdir.glob("*.md")):
        text = f.read_text()
        if not data.is_active(text):
            continue
        info = data.parse_header(text)
        table.add_row(
            f.stem, info.get("name", ""), info.get("company", ""), info.get("stage", "")
        )
    console.print(table)


@cli.command()
def get(code: str) -> None:
    try:
        console.print(data.read_contact(code))
    except FileNotFoundError:
        console.print(f"[red]Contact {code} not found[/red]")
        raise typer.Exit(1)


@cli.command()
def note(code: str, text: str) -> None:
    try:
        data.add_note(code, text)
    except FileNotFoundError:
        console.print(f"[red]Contact {code} not found[/red]")
        raise typer.Exit(1)
    console.print(f"Note added to {code}")


@cli.command()
def remind(
    code: str,
    text: str,
    in_days: int = typer.Option(..., "--in", help="Days from now"),
) -> None:
    try:
        data.read_contact(code)
    except FileNotFoundError:
        console.print(f"[red]Contact {code} not found[/red]")
        raise typer.Exit(1)
    due = date.today() + timedelta(days=in_days)
    data.add_reminder(code, text, due)
    console.print(f"Reminder set for {code} on {due}")


@cli.command()
def reminders() -> None:
    rows = data.load_reminders()
    if not rows:
        console.print("No reminders.")
        return
    table = Table(title="Reminders")
    table.add_column("Due", style="cyan")
    table.add_column("Contact")
    table.add_column("Description")
    today = date.today()
    for r in rows:
        due = datetime.strptime(r["Due"], "%Y-%m-%d").date()
        style = "red" if due <= today else None
        table.add_row(r["Due"], r["Contact"], r["Description"], style=style)
    console.print(table)


if __name__ == "__main__":
    cli()
