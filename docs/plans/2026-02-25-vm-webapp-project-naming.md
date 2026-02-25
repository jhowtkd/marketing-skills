# VM Webapp Project Naming Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce developer confusion by aligning internal naming: rename the ORM model `Product` to `Project` without database migrations, while keeping existing API behavior unchanged.

**Architecture:** Pure refactor. Keep `__tablename__ = "products"` so the DB schema stays the same. Update imports/usages in repo and v1 endpoints that still reference the legacy “product” table. Do not rename DB columns.

**Tech Stack:** Python, SQLAlchemy, FastAPI, pytest, uv.

---

## Pre-flight (recommended)

Create a dedicated worktree + branch for this plan:

```bash
git worktree add .worktrees/vm-webapp-project-naming -b codex/vm-webapp-project-naming
cd .worktrees/vm-webapp-project-naming
```

---

### Task 1: Add a naming contract test (Project maps to products table)

**Files:**
- Create: `09-tools/tests/test_vm_webapp_models_naming.py`

**Step 1: Write the failing test**

Create `09-tools/tests/test_vm_webapp_models_naming.py`:

```python
from vm_webapp.models import Project


def test_project_model_is_backed_by_products_table() -> None:
    assert Project.__tablename__ == "products"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_models_naming.py -v`  
Expected: FAIL with `ImportError` (Project not found).

---

### Task 2: Rename the ORM model `Product` -> `Project` (no schema changes)

**Files:**
- Modify: `09-tools/vm_webapp/models.py`

**Step 1: Implement minimal rename**

In `09-tools/vm_webapp/models.py`, replace:

```python
class Product(Base):
    __tablename__ = "products"
```

with:

```python
class Project(Base):
    __tablename__ = "products"
```

Keep all columns unchanged (including `product_id`).

**Step 2: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_models_naming.py -v`  
Expected: PASS.

**Step 3: Commit**

```bash
git add 09-tools/vm_webapp/models.py 09-tools/tests/test_vm_webapp_models_naming.py
git commit -m "refactor(vm): rename Product ORM model to Project (no migration)"
```

---

### Task 3: Update repo layer imports and type usage

**Files:**
- Modify: `09-tools/vm_webapp/repo.py`

**Step 1: Update imports and annotations**

In `09-tools/vm_webapp/repo.py`:

- Replace `from vm_webapp.models import Product` with `Project`.
- Update function annotations:
  - `list_products_by_brand(...) -> list[Project]`
  - `create_product(...) -> Project`
  - `get_product(...) -> Project | None`

Keep function names as-is for now (API v1 still uses `/products`).

**Step 2: Run focused tests**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_models_naming.py -v
uv run pytest 09-tools/tests/test_vm_webapp_api_v1.py -q || true
uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
```

Expected: PASS for naming + v2. (If there is no `test_vm_webapp_api_v1.py`, ignore that line.)

**Step 3: Commit**

```bash
git add 09-tools/vm_webapp/repo.py
git commit -m "refactor(vm): update repo to use Project ORM model"
```

---

### Task 4: Fix any remaining imports/references to `Product`

**Files:**
- Modify: any file flagged by grep/pytest

**Step 1: Find remaining references**

Run: `rg -n "\\bProduct\\b" 09-tools/vm_webapp`  
Expected: no Python imports referencing `Product` remain (string literals may remain).

**Step 2: Minimal fixes**

- Replace remaining imports/usages with `Project`.
- Do not change API routes or JSON keys.

**Step 3: Run regression tests**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add 09-tools/vm_webapp
git commit -m "refactor(vm): remove remaining Product references"
```

