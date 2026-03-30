#!/usr/bin/env python3
"""Detect migration tool and report status with commands reference.

Scans a project directory for well-known migration configuration files
(Alembic, Prisma, Laravel, Django, Drizzle) and returns a JSON object
describing the detected tool, config file location, migrations
directory, migration count, latest migration file, and command
references for common operations.

Usage::

    python3 migration-status.py [directory]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TOOLS = {
    "alembic": {
        "config": "alembic.ini",
        "migrations_dir": "alembic/versions",
        "pattern": ".py",
        "commands": {
            "status": "alembic current",
            "create": "alembic revision --autogenerate -m '<message>'",
            "upgrade": "alembic upgrade head",
            "downgrade": "alembic downgrade -1",
        },
    },
    "prisma": {
        "config": "prisma/schema.prisma",
        "migrations_dir": "prisma/migrations",
        "pattern": ".sql",
        "commands": {
            "status": "npx prisma migrate status",
            "create": "npx prisma migrate dev --name <name>",
            "upgrade": "npx prisma migrate deploy",
            "downgrade": "npx prisma migrate resolve --rolled-back <name>",
        },
    },
    "laravel": {
        "config": "database/migrations",
        "migrations_dir": "database/migrations",
        "pattern": ".php",
        "commands": {
            "status": "php artisan migrate:status",
            "create": "php artisan make:migration <name>",
            "upgrade": "php artisan migrate",
            "downgrade": "php artisan migrate:rollback --step=1",
        },
    },
    "django": {
        "config": "manage.py",
        "migrations_dir": None,  # detected dynamically
        "pattern": ".py",
        "commands": {
            "status": "python manage.py showmigrations",
            "create": "python manage.py makemigrations",
            "upgrade": "python manage.py migrate",
            "downgrade": "python manage.py migrate <app> <previous>",
        },
    },
    "drizzle": {
        "config": "drizzle.config.ts",
        "migrations_dir": "drizzle",
        "pattern": ".sql",
        "commands": {
            "status": "npx drizzle-kit check",
            "create": "npx drizzle-kit generate",
            "upgrade": "npx drizzle-kit push",
            "downgrade": "npx drizzle-kit drop",
        },
    },
}


def find_django_migrations(project_dir: Path) -> str | None:
    """Find Django migration directories by looking for apps with migrations/.

    Args:
        project_dir: Root directory of the Django project.

    Returns:
        Relative path to the first discovered migrations directory, or
        ``None`` if no Django app with migrations is found.
    """
    for item in project_dir.iterdir():
        if item.is_dir() and (item / "migrations").is_dir():
            mig_init = item / "migrations" / "__init__.py"
            if mig_init.exists():
                return str(item / "migrations")
    return None


def count_migrations(mig_dir: Path, pattern: str) -> tuple[int, str | None]:
    """Count migration files and find the latest one.

    Args:
        mig_dir: Directory containing migration files.
        pattern: File extension to match (e.g. ``".py"``, ``".sql"``).

    Returns:
        A tuple of ``(count, latest_filename)`` where *latest_filename*
        is the name of the most recently modified migration, or ``None``
        if no migrations exist.
    """
    if not mig_dir.is_dir():
        return 0, None
    files = sorted(
        [f for f in mig_dir.iterdir() if f.suffix == pattern and f.name != "__init__.py"],
        key=lambda p: p.stat().st_mtime,
    )
    return len(files), files[-1].name if files else None


def detect(project_dir: Path) -> dict[str, object]:
    """Detect migration tool and gather status.

    Iterates through known migration tools and checks for their
    configuration files. Returns the first match with tool name,
    config location, migrations directory, file counts, and
    command references.

    Args:
        project_dir: Root directory of the project to analyse.

    Returns:
        Dictionary with keys ``tool``, ``config_file``,
        ``migrations_dir``, ``total_migrations``, ``latest``,
        and ``commands``.
    """
    for tool_name, info in TOOLS.items():
        config_path = project_dir / info["config"]
        if tool_name == "laravel":
            if not config_path.is_dir():
                continue
        elif tool_name == "drizzle":
            # Also check .js variant
            if not config_path.exists() and not (project_dir / "drizzle.config.js").exists():
                continue
        else:
            if not config_path.exists():
                continue

        # Determine migrations directory
        mig_dir_rel = info["migrations_dir"]
        if tool_name == "django":
            mig_dir_rel = find_django_migrations(project_dir)
            if not mig_dir_rel:
                mig_dir_rel = "<app>/migrations"

        mig_dir = project_dir / mig_dir_rel if mig_dir_rel else None
        total, latest = (0, None)
        if mig_dir and mig_dir.is_dir():
            total, latest = count_migrations(mig_dir, info["pattern"])

        return {
            "tool": tool_name,
            "config_file": str(config_path.relative_to(project_dir)),
            "migrations_dir": mig_dir_rel,
            "total_migrations": total,
            "latest": latest,
            "commands": info["commands"],
        }

    return {
        "tool": None,
        "config_file": None,
        "migrations_dir": None,
        "total_migrations": 0,
        "latest": None,
        "commands": {},
    }


def main() -> None:
    """Entry point: detect migration tool and print JSON result to stdout."""
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not project_dir.is_dir():
        print(json.dumps({"error": f"Not a directory: {project_dir}"}))
        sys.exit(1)
    try:
        result = detect(project_dir)
        result["project_dir"] = str(project_dir)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
