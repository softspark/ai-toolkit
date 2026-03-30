#!/usr/bin/env python3
"""benchmarks/run.py — structured benchmark runner for ai-toolkit.

Usage:
    ./benchmarks/run.py          Show available benchmarks
    ./benchmarks/run.py B1       Scaffold B1 benchmark environment
    ./benchmarks/run.py all      Scaffold all 5 benchmarks
    ./benchmarks/run.py --report Print last results
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLKIT_DIR = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = TOOLKIT_DIR / "benchmarks"
RESULTS_FILE = BENCHMARKS_DIR / "results.json"

USAGE_TEXT = """\
ai-toolkit Benchmark Runner

Usage:
  ./benchmarks/run.py              Show available benchmarks
  ./benchmarks/run.py B1           Scaffold B1 (debug) benchmark environment
  ./benchmarks/run.py all          Scaffold all 5 benchmarks
  ./benchmarks/run.py --report     Print results from last run

Benchmarks:
  B1  Debug multi-file bug (FastAPI JWT authentication)
  B2  Code review (SQL injection, error handling, N+1)
  B3  Refactor to clean code (god function -> SRP)
  B4  Generate tests (payment processing module)
  B5  Generate documentation (Flask microservice)

Methodology:
  Each benchmark run measures:
    - time_to_first_output (seconds)
    - tool_calls (count)
    - completion_rate (0.0-1.0)
    - corrections_needed (count)

  Run each benchmark WITH and WITHOUT the toolkit, compare.
  See benchmarks/README.md for full methodology.
"""

# ---------------------------------------------------------------------------
# Benchmark scaffolding files
# ---------------------------------------------------------------------------

B1_AUTH = '''\
from fastapi import FastAPI, Header, HTTPException
import jwt

app = FastAPI()
SECRET = "mysecret"

@app.get("/protected")
def protected(authorization: str = Header(None)):
    # BUG: token validation fails silently — no exception raised on invalid token
    try:
        payload = jwt.decode(authorization, SECRET, algorithms=["HS256"])
    except:
        pass  # silent failure — any token passes
    return {"user": payload.get("sub", "unknown")}
'''

B2_USERS = '''\
import sqlite3

def get_user(db_path, username):
    # BUG 1: SQL injection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchone()

def get_user_posts(db_path, user_ids):
    # BUG 2: N+1 query
    conn = sqlite3.connect(db_path)
    posts = []
    for uid in user_ids:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE user_id = ?", (uid,))
        posts.extend(cursor.fetchall())
    return posts

def delete_user(db_path, user_id):
    # BUG 3: No error handling — conn.close() never called on exception
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
'''

B3_ORDER = '''\
import sqlite3
import smtplib
import logging
from datetime import datetime

# God function — 4 responsibilities in one: validate, calculate, persist, notify
def process_order(db_path, customer_id, items, discount_code, email):
    # 1. Validate
    if not items:
        raise ValueError("No items")
    if not customer_id:
        raise ValueError("No customer")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    customer = cursor.fetchone()
    if not customer:
        raise ValueError("Customer not found")

    # 2. Calculate total
    total = 0
    for item in items:
        cursor.execute("SELECT price FROM products WHERE id = ?", (item["product_id"],))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Product {item[\\'product_id\\']} not found")
        total += row[0] * item["quantity"]
    if discount_code == "SAVE10":
        total *= 0.9
    elif discount_code == "SAVE20":
        total *= 0.8
    tax = total * 0.23
    total_with_tax = total + tax

    # 3. Persist
    cursor.execute(
        "INSERT INTO orders (customer_id, total, tax, created_at) VALUES (?, ?, ?, ?)",
        (customer_id, total_with_tax, tax, datetime.now().isoformat())
    )
    order_id = cursor.lastrowid
    for item in items:
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
            (order_id, item["product_id"], item["quantity"])
        )
    conn.commit()
    conn.close()

    # 4. Notify
    try:
        server = smtplib.SMTP("smtp.example.com", 587)
        server.starttls()
        server.login("noreply@example.com", "password123")
        server.sendmail(
            "noreply@example.com", email,
            f"Subject: Order #{order_id} confirmed\\n\\nTotal: {total_with_tax:.2f}"
        )
        server.quit()
    except Exception as e:
        logging.error(f"Email failed: {e}")

    return order_id
'''

B4_PAYMENTS = '''\
import uuid
from dataclasses import dataclass
from typing import Optional

@dataclass
class Payment:
    id: str
    amount: float
    currency: str
    status: str  # pending | completed | failed | refunded

class PaymentProcessor:
    def __init__(self, gateway_client):
        self.gateway = gateway_client

    def charge(self, amount: float, currency: str, card_token: str) -> Payment:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if currency not in ("USD", "EUR", "GBP"):
            raise ValueError(f"Unsupported currency: {currency}")
        result = self.gateway.charge(card_token, amount, currency)
        return Payment(id=result["id"], amount=amount, currency=currency, status="completed")

    def refund(self, payment: Payment, amount: Optional[float] = None) -> Payment:
        if payment.status != "completed":
            raise ValueError("Can only refund completed payments")
        refund_amount = amount or payment.amount
        if refund_amount > payment.amount:
            raise ValueError("Refund exceeds original amount")
        self.gateway.refund(payment.id, refund_amount)
        return Payment(id=payment.id, amount=refund_amount, currency=payment.currency, status="refunded")

    def get_status(self, payment_id: str) -> str:
        result = self.gateway.get_payment(payment_id)
        return result.get("status", "unknown")

    def batch_charge(self, charges: list) -> list:
        results = []
        for charge in charges:
            try:
                p = self.charge(charge["amount"], charge["currency"], charge["card_token"])
                results.append({"success": True, "payment": p})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        return results

    def calculate_fee(self, amount: float, currency: str) -> float:
        base_fee = 0.029 * amount + 0.30
        if currency != "USD":
            base_fee *= 1.015  # FX surcharge
        return round(base_fee, 2)
'''

B5_APP = '''\
from flask import Flask, request, jsonify
from models import db, Task
from auth import require_api_key

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"
db.init_app(app)

@app.route("/tasks", methods=["GET"])
@require_api_key
def list_tasks():
    tasks = Task.query.all()
    return jsonify([t.to_dict() for t in tasks])

@app.route("/tasks", methods=["POST"])
@require_api_key
def create_task():
    data = request.get_json()
    task = Task(title=data["title"], done=False)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201

@app.route("/tasks/<int:task_id>", methods=["PATCH"])
@require_api_key
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    if "done" in data:
        task.done = data["done"]
    if "title" in data:
        task.title = data["title"]
    db.session.commit()
    return jsonify(task.to_dict())

@app.route("/tasks/<int:task_id>", methods=["DELETE"])
@require_api_key
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return "", 204
'''

B5_MODELS = '''\
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Task:
    id: int
    title: str
    done: bool

    def to_dict(self):
        return {"id": self.id, "title": self.title, "done": self.done}
'''

B5_AUTH = '''\
import os
from functools import wraps
from flask import request, jsonify

API_KEY = os.environ.get("API_KEY", "dev-key")

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
'''


def scaffold(name: str, directory: str, files: dict[str, str], task_desc: str) -> None:
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        (d / filename).write_text(content, encoding="utf-8")
    print(f"{name} scaffolded at: {directory}")
    print(f"Task: {task_desc}")


def scaffold_b1(d: str = "/tmp/benchmark-b1") -> None:
    scaffold("B1", d, {"auth.py": B1_AUTH},
             "Find why any JWT token (including invalid ones) is accepted.")

def scaffold_b2(d: str = "/tmp/benchmark-b2") -> None:
    scaffold("B2", d, {"users.py": B2_USERS},
             "Find 3 issues: SQL injection, N+1 query, missing error handling.")

def scaffold_b3(d: str = "/tmp/benchmark-b3") -> None:
    scaffold("B3", d, {"order_processor.py": B3_ORDER},
             "Refactor process_order() — split into 4 single-responsibility functions.")

def scaffold_b4(d: str = "/tmp/benchmark-b4") -> None:
    scaffold("B4", d, {"payments.py": B4_PAYMENTS},
             "Generate unit tests for all 5 PaymentProcessor methods with edge cases.")

def scaffold_b5(d: str = "/tmp/benchmark-b5") -> None:
    scaffold("B5", d, {"app.py": B5_APP, "models.py": B5_MODELS, "auth.py": B5_AUTH},
             "Generate README, API docs, and docstrings for this Flask task API.")


SCAFFOLDERS = {"B1": scaffold_b1, "B2": scaffold_b2, "B3": scaffold_b3, "B4": scaffold_b4, "B5": scaffold_b5}


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    target = sys.argv[2] if len(sys.argv) > 2 else ""

    if arg == "--report":
        if RESULTS_FILE.is_file():
            print(RESULTS_FILE.read_text())
        else:
            print("No results yet. Run benchmarks first.")
            print(f"Results will be saved to: {RESULTS_FILE}")
    elif arg == "all":
        for name, fn in SCAFFOLDERS.items():
            fn(f"/tmp/benchmark-{name.lower()}")
    elif arg in SCAFFOLDERS:
        d = target or f"/tmp/benchmark-{arg.lower()}"
        SCAFFOLDERS[arg](d)
    elif arg:
        print(f"Unknown: {arg}")
        print(USAGE_TEXT)
        sys.exit(1)
    else:
        print(USAGE_TEXT)


if __name__ == "__main__":
    main()
