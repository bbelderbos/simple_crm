# simple_crm

A tiny CLI CRM backed by Markdown files. Two Python files, two dependencies
([Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/)),
and a folder of Markdown. No database, no web UI, no deployment.

This is the minimal companion to the article
[Build the Simplest Thing That Works](https://belderbos.dev/blog/build-the-simplest-thing-that-works/).

## Install

```bash
git clone https://github.com/bbelderbos/simple_crm
cd simple_crm
uv sync
```

## Data location

All data lives in one folder, set via an environment variable:

```bash
export CRM_DATA=/path/to/your/crm
```

If unset, it defaults to `~/crm_data`.

## Usage

```bash
uv run crm init                          # create the data folder + files
uv run crm add                           # add a contact (prompts for name/email/company)
uv run crm list                          # active contacts
uv run crm get jd1                       # show one contact
uv run crm note jd1 "had intro call"     # append a dated note
uv run crm remind jd1 "follow up" --in 7 # set a reminder N days out
uv run crm reminders                     # due/overdue reminders (overdue in red)
```

## Data layout

```
$CRM_DATA/
  products.md        # hand-edited table: code, name, price
  reminders.md       # table: due date, contact, description, done
  contacts/
    jd1.md           # Jane Doe (unique code: initials + number)
    bs2.md           # Bob Smith
```

Each contact is plain Markdown you can open in any editor:

```markdown
# Jane Doe
- **Email**: j@co.com
- **Company**: Acme
- **Stage**: open

## Notes
- 2026-05-28 — had intro call
```

A contact is **active** until its `Stage` is `won` or `archived`. Edit the file
by hand to change it.

## Shell glue (optional)

The CLI does the CRM-specific logic; Unix tools handle search and editing. The
trick is piping `crm list` into [`fzf`](https://github.com/junegunn/fzf) to pick
a contact, then acting on it:

```bash
# run crm from anywhere
alias crm='uv run --project /path/to/simple_crm crm'

# interactive picker -> open in vim
crme() {
  local code
  code=$(crm list "$@" | grep '│' | fzf --ansi | awk -F '│' '{gsub(/ /, "", $2); print $2}')
  [[ -n "$code" ]] && vim "$CRM_DATA/contacts/${code}.md"
}

# interactive picker -> add a reminder
crma() {
  local code
  code=$(crm list | grep '│' | fzf --ansi | awk -F '│' '{gsub(/ /, "", $2); print $2}')
  [[ -n "$code" ]] && crm remind "$code" "$1" --in "$2"
}
```

A handy Vim mapping to add a dated note line:

```vim
nnoremap <Leader>da o- <C-R>=strftime('%Y-%m-%d')<CR> —
```

## Tests

```bash
uv run pytest -q
```

## Scope

Single user, local files, small data. The day you need multi-user access or real
concurrency, this design is the wrong one and you should reach for a database and
a framework. That is the whole point: match the tool to the problem in front of you.
