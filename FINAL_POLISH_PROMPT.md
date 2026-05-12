# Final Polish Before Push

Paste this whole document into Claude Code with working directory set to
`Analysis_securities/`. The user just tried to push to GitHub but the placeholder
URL `https://github.com/yourname/...` was used literally, plus several `<user>/<repo>`
placeholders remain in source files. This prompt handles all file-level cleanup;
the user does the interactive push themselves at the end.

## Inputs the user must provide before this prompt runs

Ask for both via AskUserQuestion (single question, free-text) if not already provided:

- **GITHUB_USERNAME** — the user's GitHub handle (e.g. `alexeyklek`).
- **REPO_NAME** — the GitHub repo name (e.g. `Analysis_securities`).

Do not proceed without both.

## Context (what's already true)

The repo is local-only, committed once, branch is `main`. The previous attempt at
`git remote add origin https://github.com/yourname/Analysis_securities.git` set a
broken remote. `_fix_notebooks.py` was committed at root as a one-time fix script
and should not ship. Three files still contain `<user>` and `<repo>` placeholders
in Colab-badge URLs.

## Tasks (execute in order, halt on any failure)

### 1. Replace placeholders in README.md

Find every `<user>` → replace with `GITHUB_USERNAME`. Find every `<repo>` → replace
with `REPO_NAME`. Two Colab-badge URLs near the "How to run" section.

### 2. Replace placeholders in both notebooks

Edit `notebooks/Correlation_Analysis.ipynb` and `notebooks/Volatility_Analysis.ipynb`
directly as JSON. In each, find the first markdown cell (cell index 0, `cell_type ==
"markdown"`) and replace `<user>` → `GITHUB_USERNAME`, `<repo>` → `REPO_NAME` inside
its `source` array. Use string replacement on the cell's source strings, not regex
on the file as a whole — keeps the rest of the JSON untouched.

After saving, verify both notebooks still parse as strict JSON:
```python
import json
for p in ['notebooks/Correlation_Analysis.ipynb', 'notebooks/Volatility_Analysis.ipynb']:
    with open(p, 'rb') as f:
        json.loads(f.read().decode('utf-8'))
    print(f'{p}: OK')
```

### 3. Verify no placeholders remain

Run these greps; all three must return zero matches:
```bash
grep -r '<user>' README.md notebooks/
grep -r '<repo>' README.md notebooks/
grep -r 'yourname' README.md notebooks/
```

If any match, halt and report.

### 4. Remove the one-time fix script

```bash
git rm _fix_notebooks.py
```

And update `.gitignore` — add a new line `_fix_*.py` next to the existing
`_*_work.py` and `_gate_*.py` entries so future fix-shaped scratch scripts
don't accidentally get committed.

### 5. Verify tests still pass

```bash
pytest tests/
```

Must report 7 passed. Halt if not.

### 6. Fix the broken git remote

The current remote is the literal placeholder URL. Replace it with the real one:
```bash
git remote set-url origin https://github.com/GITHUB_USERNAME/REPO_NAME.git
```

Then verify:
```bash
git remote -v
```
Should show `origin` pointing at the new URL.

### 7. Amend the existing commit with these changes

```bash
git add .
git commit --amend --no-edit
```

Keeps the single "Initial publishable version" commit clean.

### 8. Print the final manual step for the user

Print this and stop — do NOT run it (it requires interactive browser auth):

```
Ready to push. From your PowerShell prompt, run:

    git push -u origin main

The first push will open a browser to authenticate with GitHub. Approve it,
wait for the upload, then refresh github.com/GITHUB_USERNAME/REPO_NAME — your
repo will be live with README rendered, both notebooks renderable, all 118
PNGs in place, and working Colab badges.
```

## Hard constraints

- Don't `git push` — that's the user's interactive step.
- Don't create the GitHub repo — the user does that manually on github.com.
- Don't modify the analysis code, README methodology, or any notebook code cells —
  only the badge-URL placeholders in the first markdown cells.
- Don't `pip install` anything; the venv is already correct.
- Strict halt on any verification failure with a clear single-line reason.
