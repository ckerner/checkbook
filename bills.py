#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal


# =========================
# Data Handling
# =========================

def load_bills(path):
    try:
        with open(path) as f:
            data = json.load(f)
        data.setdefault("bills", [])
        return data
    except FileNotFoundError:
        return {"bills": []}


def save_bills(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_transactions(path):
    try:
        with open(path) as f:
            acct = json.load(f)
        return [t for t in acct.get("transactions", []) if not t.get("deleted")]
    except Exception:
        return []


# =========================
# Date Helpers
# =========================

def today():
    return date.today()


def parse_date(s):
    return date.fromisoformat(s)


def due_date_for(bill, ref_date=None):
    ref_date = ref_date or today()

    if bill["frequency"] == "monthly":
        return date(ref_date.year, ref_date.month, bill["due_day"])

    elif bill["frequency"] == "yearly":
        return date(ref_date.year, bill["due_month"], bill["due_day"])

    else:
        raise ValueError("Unknown frequency")


# =========================
# Matching Logic
# =========================

def txn_matches_bill(txn, bill, due_date):
    if txn.get("category") != bill.get("category"):
        return False

    txn_date = parse_date(txn["date"])

    # Allow ±5 day window
    if abs((txn_date - due_date).days) > 5:
        return False

    return True


def find_payment(bill, txns, ref_date=None):
    ref_date = ref_date or today()
    due = due_date_for(bill, ref_date)

    for t in txns:
        if txn_matches_bill(t, bill, due):
            return t

    return None


# =========================
# Status Logic
# =========================

def compute_status(bill, txns):
    now = today()
    due = due_date_for(bill, now)

    payment = find_payment(bill, txns, now)

    if payment:
        return "PAID", payment["date"]

    if now > due:
        return "OVERDUE", None

    if (due - now).days <= 5:
        return "DUE", None

    return "UPCOMING", None


# =========================
# CLI Actions
# =========================

def cmd_add(args):
    data = load_bills(args.file)

    bill = {
        "name": args.name,
        "amount": str(Decimal(args.amount)),
        "category": args.category,
        "frequency": args.frequency,
        "due_day": args.day,
        "last_paid": None
    }

    if args.frequency == "yearly":
        if not args.month:
            print("Yearly bills require --month")
            sys.exit(1)
        bill["due_month"] = args.month

    data["bills"].append(bill)
    save_bills(args.file, data)

    print(f"Added bill: {args.name}")


def cmd_list(args):
    bills = load_bills(args.file)["bills"]
    txns = load_transactions(args.account) if args.account else []

    print(f"{'Name':20} {'Amount':>10} {'Due':>10} {'Freq':>10} {'Status':>10} {'Last Paid':>12}")
    print("-" * 80)

    for b in bills:
        status, paid_date = compute_status(b, txns)

        due = due_date_for(b)
        amt = Decimal(b["amount"])

        print(f"{b['name'][:20]:20} {amt:10.2f} {due.isoformat():10} {b['frequency']:10} {status:10} {(paid_date or ''):12}")


def cmd_upcoming(args):
    bills = load_bills(args.file)["bills"]
    txns = load_transactions(args.account) if args.account else []

    now = today()
    horizon = now + timedelta(days=args.days)

    print(f"Upcoming bills in next {args.days} days\n")
    print(f"{'Name':20} {'Due':>10} {'Amount':>10} {'Status':>10}")
    print("-" * 60)

    for b in bills:
        due = due_date_for(b)

        if now <= due <= horizon:
            status, _ = compute_status(b, txns)
            print(f"{b['name'][:20]:20} {due.isoformat():10} {Decimal(b['amount']):10.2f} {status:10}")


def cmd_mark_paid(args):
    data = load_bills(args.file)

    for b in data["bills"]:
        if b["name"].lower() == args.name.lower():
            b["last_paid"] = args.date or today().isoformat()
            save_bills(args.file, data)
            print(f"Marked {b['name']} as paid on {b['last_paid']}")
            return

    print("Bill not found")


# =========================
# CLI Setup
# =========================

def main():
    p = argparse.ArgumentParser(description="Bill tracking utility")
    sub = p.add_subparsers(dest="cmd")

    # add
    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("name")
    a.add_argument("amount")
    a.add_argument("day", type=int)
    a.add_argument("-c", "--category", required=True)
    a.add_argument("-f", "--frequency", choices=["monthly", "yearly"], default="monthly")
    a.add_argument("--month", type=int)

    # list
    l = sub.add_parser("list")
    l.add_argument("file")
    l.add_argument("--account", help="checkbook json file")

    # upcoming
    u = sub.add_parser("upcoming")
    u.add_argument("file")
    u.add_argument("--account")
    u.add_argument("--days", type=int, default=7)

    # mark paid
    m = sub.add_parser("mark-paid")
    m.add_argument("file")
    m.add_argument("name")
    m.add_argument("--date")

    args = p.parse_args()

    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "upcoming":
        cmd_upcoming(args)
    elif args.cmd == "mark-paid":
        cmd_mark_paid(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
