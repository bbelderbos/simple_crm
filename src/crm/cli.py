from datetime import date, datetime, timedelta

import typer
from rich.console import Console
from rich.table import Table

from . import data

cli = typer.Typer(help="A tiny CLI CRM backed by Markdown files.")
product_app = typer.Typer(help="Manage the product catalog.")
cli.add_typer(product_app, name="product")
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


@product_app.command("add")
def product_add(code: str, name: str, price: str) -> None:
    try:
        data.add_product(code, name, price)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"Added product {code}")


@product_app.command("list")
def product_list() -> None:
    products = data.load_products()
    if not products:
        console.print("No products.")
        return
    table = Table(title="Products")
    table.add_column("Code", style="cyan")
    table.add_column("Name")
    table.add_column("Price", justify="right")
    for p in products:
        table.add_row(p["Code"], p["Name"], p["Price"])
    console.print(table)


@cli.command()
def add(
    name: str = typer.Option(..., prompt=True),
    email: str = typer.Option("", prompt=True),
    company: str = typer.Option("", prompt=True),
) -> None:
    codes = [p["Code"] for p in data.load_products()]
    product = ""
    if codes:
        product = typer.prompt(f"Product [{', '.join(codes)}]", default="")
        if product and product not in codes:
            console.print(f"[red]Unknown product: {product}[/red]")
            raise typer.Exit(1)
    code = data.create_contact(name, email=email, company=company, product=product)
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
    table.add_column("Product")
    for f in sorted(cdir.glob("*.md")):
        info = data.parse_header(f.read_text())
        table.add_row(
            f.stem,
            info.get("name", ""),
            info.get("company", ""),
            info.get("product", ""),
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
    if in_days < 0:
        console.print("[red]Days must be non-negative[/red]")
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
        due_str = r["Due"]
        try:
            due = datetime.strptime(r["Due"], "%Y-%m-%d").date()
            style = "red" if due <= today else None
        except ValueError:
            due_str = "Invalid date"
            style = None
        table.add_row(due_str, r["Contact"], r["Description"], style=style)
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    cli()
