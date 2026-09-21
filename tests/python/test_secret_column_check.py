# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Unit tests for scripts/secret_column_check.py, the scanner behind the
advisory secret-column-check.sh hook.

Run: npm run test:py (pytest, config in pytest.ini).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from secret_column_check import find, looks_secret, main  # noqa: E402


@pytest.mark.parametrize(
    ("path", "text", "expected"),
    [
        (
            "src/Entity/Company.php",
            "    #[ORM\\Column(length: 255, nullable: true)]\n    private ?string $smsApiToken = null;\n",
            [("smsApiToken", "Doctrine column")],
        ),
        (
            "src/Entity/Company.php",
            "    #[ORM\\Column(\n        type: Types::STRING,\n        length: 64,\n    )]\n    private ?string $webhookSecret = null;\n",
            [("webhookSecret", "Doctrine column")],
        ),
        (
            "migrations/Version20260921.php",
            '$this->addSql("ALTER TABLE company ADD api_key VARCHAR(64) DEFAULT NULL, ADD api_key_hash VARCHAR(64)");',
            [("api_key", "SQL column")],
        ),
        ("db/schema.sql", "CREATE TABLE s (\n  id INT,\n  client_secret TEXT NOT NULL\n);", [("client_secret", "SQL column")]),
        (
            "app/db/models.py",
            "    client_secret: Mapped[str] = mapped_column(String(255))\n",
            [("client_secret", "SQLAlchemy column")],
        ),
        ("app/models.py", "    smtp_password = models.CharField(max_length=255)\n", [("smtp_password", "Django field")]),
        ("prisma/schema.prisma", "model User {\n  id Int @id\n  apiKey String\n}\n", [("apiKey", "Prisma field")]),
        ("db/migrate/20260921_add.rb", "t.string :remember_token\n", [("remember_token", "Rails column")]),
        (
            "database/migrations/2026_09_21_add.php",
            "$table->string('webhook_secret')->nullable();",
            [("webhook_secret", "Laravel column")],
        ),
        (
            "src/user.entity.ts",
            "  @Column()\n  accessToken: string;\n",
            [("accessToken", "TypeORM column")],
        ),
        (
            "src/main/java/App/Account.java",
            "    @Column(name = \"api_key\")\n    private String apiKey;\n",
            [("apiKey", "JPA column")],
        ),
    ],
)
def test_finds_a_plaintext_secret_column(path: str, text: str, expected: list[tuple[str, str]]) -> None:
    assert find(path, text) == expected


@pytest.mark.parametrize(
    ("path", "text"),
    [
        # Protected by a marker on or above the declaration.
        ("src/Entity/Company.php", "    #[ORM\\Column(type: EncryptedTextType::NAME, nullable: true)]\n    private ?string $ksefAuthToken = null;\n"),
        ("src/Entity/User.php", "    #[ORM\\Column(length: 64, nullable: true)]\n    #[HashedToken(purpose: 'reset')]\n    private ?string $passwordResetToken = null;\n"),
        ("app/db/models.py", "    card_token: Mapped[str] = mapped_column(EncryptedText())\n"),
        ("src/user.entity.ts", "  @Column({ transformer: encrypted })\n  accessToken: string;\n"),
        ("src/main/java/App/Account.java", "    @Convert(converter = Encrypted.class)\n    @Column\n    private String apiKey;\n"),
        # Derived or descriptive names, and framework password hashes.
        ("app/models.py", "    token_hash = models.CharField(max_length=64)\n    password = models.CharField(max_length=128)\n"),
        ("app/models.py", "    reset_token_expires_at = models.CharField(max_length=30)\n"),
        ("migrations/Version1.php", '$this->addSql("ALTER TABLE s ADD min_password_length VARCHAR(4)");'),
        # An unmapped property is not a column, even right under a mapped one.
        (
            "src/Entity/RefreshToken.php",
            "    #[ORM\\Column(type: Types::STRING, length: 36, nullable: true)]\n    private ?string $sessionId = null;\n\n"
            "    /** The plaintext this object was issued with. */\n    private ?string $issuedToken = null;\n",
        ),
        # Files that are not schema, model or migration files.
        ("README.md", "api_key VARCHAR(64) token secret"),
        ("src/Service/Mailer.php", "    private ?string $smtpPassword = null;\n"),
    ],
)
def test_ignores_protected_derived_or_non_schema_declarations(path: str, text: str) -> None:
    assert find(path, text) == []


def test_a_marker_on_the_previous_property_does_not_protect_the_next_one() -> None:
    text = (
        "    #[ORM\\Column(type: EncryptedTextType::NAME)]\n    private ?string $clientSecret = null;\n\n"
        "    #[ORM\\Column(length: 255)]\n    private ?string $webhookSecret = null;\n"
    )
    assert find("src/Entity/Company.php", text) == [("webhookSecret", "Doctrine column")]


@pytest.mark.parametrize(
    ("name", "secret"),
    [
        ("api_key", True),
        ("apiKey", True),
        ("licenceKey", True),
        ("smtp_password", True),
        ("password", False),
        ("password_hash", False),
        ("tokenExpiresAt", False),
        ("created_at", False),
        ("display_name", False),
    ],
)
def test_looks_secret(name: str, secret: bool) -> None:
    assert looks_secret(name) is secret


def test_main_prints_tab_separated_findings_and_always_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("  apiKey String\n"))
    assert main(["secret_column_check.py", "schema.prisma"]) == 0
    assert capsys.readouterr().out == "apiKey\tPrisma field\n"

    assert main(["secret_column_check.py"]) == 0
    assert capsys.readouterr().out == ""
