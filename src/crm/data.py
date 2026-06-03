import os
import re
from datetime import date
from pathlib import Path

PRODUCTS_HEADER = "| Code | Name | Price |\n|------|------|-------|\n"
REMINDERS_HEADER = (
    "| Due | Contact | Description | Done |\n|-----|---------|-------------|------|\n"
)

CONTACT_TEMPLATE = """# {name}
- **Email**: {email}
- **Company**: {company}
- **Product**: {product}

## Notes
"""
DEFAULT_INITIALS = "xx"


def crm_data() -> Path:
    return Path(os.environ.get("CRM_DATA", Path.home() / "crm_data"))


def contacts_dir() -> Path:
    return crm_data() / "contacts"


def products_path() -> Path:
    return crm_data() / "products.md"


def load_products() -> list[dict[str, str]]:
    path = products_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines()[2:]:
        if not line.strip():
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3:
            rows.append(dict(zip(["Code", "Name", "Price"], cells)))
    return rows


def add_product(code: str, name: str, price: str) -> None:
    if any(p["Code"] == code for p in load_products()):
        raise ValueError(f"Product {code} already exists")
    if "|" in code + name + price:
        raise ValueError("'|' is not allowed in product fields")
    path = products_path()
    if not path.exists():
        path.write_text(PRODUCTS_HEADER)
    path.write_text(path.read_text().rstrip() + f"\n| {code} | {name} | {price} |\n")


def contact_path(code: str) -> Path:
    return contacts_dir() / f"{code}.md"


def next_code(name: str) -> str:
    initials = "".join(w[0].lower() for w in name.split()[:2]) or DEFAULT_INITIALS
    pattern = re.compile(rf"^{re.escape(initials)}(\d+)$")
    used = [
        int(m.group(1))
        for f in contacts_dir().glob(f"{initials}*.md")
        if (m := pattern.match(f.stem))
    ]
    return f"{initials}{max(used, default=0) + 1}"


def create_contact(name, email="", company="", product="") -> str:
    contacts_dir().mkdir(parents=True, exist_ok=True)
    code = next_code(name)
    path = contact_path(code)
    if path.exists():
        raise FileExistsError(f"Contact {code} already exists")
    path.write_text(
        CONTACT_TEMPLATE.format(
            name=name, email=email, company=company, product=product
        )
    )
    return code


def read_contact(code: str) -> str:
    path = contact_path(code)
    if not path.exists():
        raise FileNotFoundError(f"Contact {code} not found")
    return path.read_text()


def parse_header(text: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for line in text.splitlines():
        title = re.match(r"^#\s+(.+)$", line)
        if title:
            info["name"] = title.group(1).strip()
            continue
        field = re.match(r"^-\s+\*\*(\w+)\*\*:\s*(.*)$", line)
        if field:
            info[field.group(1).lower()] = field.group(2).strip()
    return info


def add_note(code: str, content: str) -> None:
    path = contact_path(code)
    if not path.exists():
        raise FileNotFoundError(f"Contact {code} not found")
    today = date.today().isoformat()
    path.write_text(path.read_text().rstrip() + f"\n- {today} — {content}\n")


def load_reminders() -> list[dict[str, str]]:
    path = crm_data() / "reminders.md"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines()[2:]:
        if not line.strip():
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            print(f"Skipping invalid reminder line: {line}")
        else:
            rows.append(dict(zip(["Due", "Contact", "Description", "Done"], cells)))
    return rows


def add_reminder(contact: str, description: str, due: date) -> None:
    if "|" in description:
        raise ValueError("'|' is not allowed in reminder description")
    rows = load_reminders()
    rows.append(
        {
            "Due": due.isoformat(),
            "Contact": contact,
            "Description": description,
            "Done": "no",
        }
    )
    rows.sort(key=lambda r: r["Due"])
    _write_reminders(rows)


def _write_reminders(rows: list[dict[str, str]]) -> None:
    lines: list[str] = [REMINDERS_HEADER.rstrip()]
    for r in rows:
        lines.append(
            f"| {r['Due']} | {r['Contact']} | {r['Description']} | {r['Done']} |"
        )
    (crm_data() / "reminders.md").write_text("\n".join(lines) + "\n")
