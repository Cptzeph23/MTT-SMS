# Phase 0 - Existing Project Assessment and Scaffolding

## 1. Current state (as inspected)

- Repository root: `MTT-SMS/` containing `.venv/`, `SMS/`, `project_structure.txt`.
- Django project package: `SMS/SMS/` (`settings.py`, `urls.py`, `asgi.py`, `wsgi.py`). `manage.py` sits in `SMS/`.
- One app: `SMS/smsApp/` with default files (`models.py`, `views.py`, `admin.py`, `apps.py`, `tests.py`, `migrations/__init__.py`).
- No `db.sqlite3` is present, so `migrate` has never been run. No migrations exist.
- Assumption (per instruction): all files contain only Django-generated defaults.
- Virtual environment: Python 3.12, Django and its direct dependencies only.

## 2. Reuse and duplication check

| Area | Existing | Decision |
|---|---|---|
| Apps | `smsApp` (empty) | Keep as the shared core app |
| Models, views, forms, serializers | None | Nothing to reuse or conflict with |
| Templates, static, JS, CSS | None | Create project-level `templates/` and `static/` |
| Authentication, dashboards | None | Built in Phase 1 (single implementation) |
| APIs | None | Built per phase under `/api/v1/` |
| Migrations | None | Custom User model can be introduced safely in Phase 1 |

Conclusion: greenfield. There is nothing to migrate and no risk of duplication.

## 3. Target architecture

```
MTT-SMS/
  .gitignore
  README.md                      (delivered in Phase 13)
  project_structure.txt
  requirements/  base.txt  dev.txt  prod.txt
  docs/          PHASE0_ASSESSMENT.md
  .venv/
  SMS/
    manage.py
    .env.example                 (copy to .env, git-ignored)
    SMS/                         project package
      settings/  base.py dev.py prod.py test.py     (Phase 1a, replaces settings.py)
      urls.py  asgi.py  wsgi.py  celery.py          (celery.py in Phase 1a)
    smsApp/                      shared core: abstract models, mixins, dashboard router, error views
    apps/
      accounts/       users, roles, first-login, password reset, auth backend
      schools/        school, branding, academic years, terms, education system, grading
      people/         classes, streams, students, parents, families, enrollment, teachers, salary
      academics/      subjects, curriculum, teaching assignments, term rollover
      assessments/    assessment structure, marks, result engine, approval, publication
      attendance/     attendance records
      finance/        fee structures, family accounts, invoices, payments, receipts
      reports/        report books, transcripts, PDF generation
      imports/        Excel/CSV/PDF import pipeline
      notifications/  SMS abstraction, announcements, notification log
      audit/          audit log
      api/            DRF routing, JWT, shared API permissions
    templates/
    static/
```

Each domain app follows the same internal layout as it grows: `models.py`, `services.py` (business rules, shared by web and API), `views.py`, `urls.py`, `forms.py`, `serializers.py`, `api_views.py`, `admin.py`, `tests/`.

Rules:
- Views and API views call `services.py`. They never duplicate business logic.
- Every school-owned model carries a `school` foreign key and uses the scoped manager from `smsApp`.
- Money uses `Decimal`. Balances are derived from ledger rows, never stored as editable values.

## 4. Technology stack

| Concern | Choice |
|---|---|
| Language / framework | Python 3.12, Django, Django REST Framework |
| Database | Supabase PostgreSQL via `psycopg` 3 and `DATABASE_URL` |
| Object storage | Supabase Storage through `django-storages` (S3-compatible) |
| Auth | Django sessions (web), JWT via `djangorestframework-simplejwt` (API) |
| Config / secrets | `django-environ`, `SMS/.env` |
| Static files | WhiteNoise |
| Background jobs | Celery + Redis (eager mode when Redis is unavailable) |
| PDFs | ReportLab |
| Spreadsheet import | openpyxl, csv; PDF text via pdfplumber |
| Frontend | Django templates, Bootstrap 5, vanilla JS, Chart.js |
| Testing | Django test runner, coverage |

## 5. Decisions carried forward

1. `smsApp` is retained as the core app; domain apps live under `SMS/apps/`.
2. Custom User model in Phase 1b, before any migration is run.
3. School-branded login at `/login/<school-code>/`; username unique per school; Super Admin uses `/login/`.
4. Classes and streams are built in Phase 3 (needed for enrollment). Subjects and teaching assignments are built in Phase 5.
5. Education-system and grading configuration are built in Phase 2.
6. SMS provider starts as a console/log provider; a real provider is plugged in at Phase 7.
7. `settings.py` becomes a `settings/` package in Phase 1a.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Cross-school data leakage | Scoped manager, view/API mixins, per-phase isolation tests |
| Financial inconsistency | Ledger design, computed balances, reversal-only corrections |
| Slow list pages at scale | Indexes from day one, `select_related`/`prefetch_related`, pagination, query-count tests |
| Supabase pooler quirks | Use the pooler connection string; keep connection age modest; tests run on SQLite |
| Secret exposure | `.env` git-ignored, service-role key server-side only |
| PDF/import blocking requests | Celery tasks for bulk and large operations |

## 7. Phase 0 deliverables

- `.gitignore`
- `requirements/base.txt`, `dev.txt`, `prod.txt`
- `SMS/.env.example`
- `SMS/apps/` package with 12 domain app skeletons (not yet registered in settings)
- `SMS/templates/`, `SMS/static/`
- `SMS/smsApp/tests.py` (scaffold verification tests)
- This document

`SMS/SMS/settings.py`, `urls.py`, `manage.py` and all models are intentionally untouched.

## 8. Open items (needed by the phase shown)

| Item | Needed by |
|---|---|
| Supabase project: DB pooler URL, storage bucket names, S3 access keys (in `.env`, never shared in chat) | Phase 1a |
| Redis availability locally | Phase 7 (optional before) |
| SMS provider choice and sender ID | Phase 7b |
| School logo/badge, motto, colors for first school | Phase 2 |
| Education system and grading scheme of the first school | Phase 2c |
