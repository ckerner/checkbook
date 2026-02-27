#!/usr/bin/env python3
import argparse
import curses
import json
import os
from decimal import Decimal
from datetime import date

TODAY = date.today().isoformat()


# =========================
# Ledger and helper
# =========================

class Ledger:
    def __init__(self, account):
        self.account = account
        self.transactions = [t for t in account.get("transactions", []) if not t.get("deleted")]
        self.initial_balance = Decimal(str(account.get("initial_balance", "0.00")))

    def running_balance(self):
        bal = self.initial_balance
        balances = []
        for t in self.transactions:
            bal += Decimal(str(t["amount"]))
            balances.append(bal)
        return balances

    def register_balance(self):
        return self.initial_balance + sum(Decimal(str(t["amount"])) for t in self.transactions)

    def reconcile(self, bank_balance):
        bank_balance = Decimal(str(bank_balance))
        uncleared_checks = sum(
            -Decimal(str(t["amount"])) for t in self.transactions
            if not t.get("cleared") and Decimal(str(t["amount"])) < 0
        )
        uncleared_deposits = sum(
            Decimal(str(t["amount"])) for t in self.transactions
            if not t.get("cleared") and Decimal(str(t["amount"])) > 0
        )
        ending_balance = bank_balance - uncleared_checks + uncleared_deposits
        difference = ending_balance - self.register_balance()
        return {
            "bank_balance": bank_balance,
            "uncleared_checks": uncleared_checks,
            "uncleared_deposits": uncleared_deposits,
            "ending_balance": ending_balance,
            "register_balance": self.register_balance(),
            "difference": difference
        }

    def add_transaction(self, t):
        self.account.setdefault("transactions", []).append(t)
        self.transactions.append(t)

    def delete_transaction(self, idx):
        t = self.transactions[idx]
        t["deleted"] = True
        self.transactions.pop(idx)


def compute_balances(account, bank_balance=None):
    ledger = Ledger(account)
    balances = {"register": ledger.register_balance()}
    if bank_balance is not None:
        balances.update(ledger.reconcile(bank_balance))
    balances["running"] = ledger.running_balance()
    return balances


# =========================
# Utilities
# =========================

def today_if_dot(s):
    return TODAY if s.strip() == "." else s.strip()


def load_account(path):
    with open(path) as f:
        acct = json.load(f)
    if "initial_balance" not in acct:
        acct["initial_balance"] = "0.00"
    if "transactions" not in acct:
        acct["transactions"] = []
    return acct


def save_account(path, acct):
    with open(path, "w") as f:
        json.dump(acct, f, indent=2)


def new_account(initial_balance):
    return {
        "initial_balance": str(Decimal(str(initial_balance))),
        "transactions": []
    }


# =========================
# CLI Reports
# =========================

def print_register(acct):
    ledger = Ledger(acct)
    running = ledger.running_balance()
    print(f"{'Date':10}  {'Description':30} {'Category':15} {'Debit':>10} {'Credit':>10} {'Balance':>12}")
    print("-" * 95)
    for t, bal in zip(ledger.transactions, running):
        amt = Decimal(str(t["amount"]))
        debit = f"{-amt:.2f}" if amt < 0 else ""
        credit = f"{amt:.2f}" if amt > 0 else ""
        cat = t.get("category") or "Uncategorized"
        mark = "✔" if t.get("cleared") else " "
        print(f"{mark} {t['date']} {t['description'][:30]:30} {cat[:15]:15} {debit:>10} {credit:>10} {bal:12.2f}")


def category_report(acct, start=None, end=None):
    totals = {}
    for t in Ledger(acct).transactions:
        if start and t["date"] < start:
            continue
        if end and t["date"] > end:
            continue
        cat = t.get("category") or "Uncategorized"
        totals.setdefault(cat, Decimal("0.00"))
        totals[cat] += Decimal(str(t["amount"]))
    for cat, amt in sorted(totals.items()):
        print(f"{cat:20} {amt:10.2f}")


def reconcile_report(acct, bank_balance):
    ledger = Ledger(acct)
    rec = ledger.reconcile(bank_balance)
    print("\nRECONCILIATION REPORT")
    print("=" * 52)
    print(f"Bank balance           : {rec['bank_balance']:12.2f}")
    print(f"Uncleared checks       : {rec['uncleared_checks']:12.2f}")
    print(f"Uncleared deposits     : {rec['uncleared_deposits']:12.2f}")
    print("-" * 52)
    print(f"Ending balance (bank)  : {rec['ending_balance']:12.2f}")
    print(f"Register balance       : {rec['register_balance']:12.2f}")
    print(f"Difference             : {rec['difference']:12.2f}")
    print("\nUNCLEARED TRANSACTIONS")
    print("-" * 52)
    for t in sorted([tx for tx in ledger.transactions if not tx.get("cleared")], key=lambda x: x["date"]):
        print(f"{t['date']} {t['description'][:30]:30} {Decimal(str(t['amount'])):10.2f}")


# =========================
# TUI
# =========================

def launch_tui(path, initial_bank=None):
    acct = load_account(path)
    ledger = Ledger(acct)
    bank_balance = Decimal(str(initial_bank)) if initial_bank is not None else None

    txns = ledger.transactions
    idx = 0
    scroll = 0
    last_search = None

    def draw(stdscr):
        nonlocal scroll
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Reconciliation panel
        if bank_balance is not None:
            rec = ledger.reconcile(bank_balance)
            lines = [
                f"Bank balance        : {rec['bank_balance']:10.2f}",
                f"Uncleared checks    : {rec['uncleared_checks']:10.2f}",
                f"Uncleared deposits  : {rec['uncleared_deposits']:10.2f}",
                f"Ending balance      : {rec['ending_balance']:10.2f}",
                f"Register balance    : {rec['register_balance']:10.2f}",
                f"Difference          : {rec['difference']:10.2f}",
            ]
        else:
            lines = ["Bank balance not entered (press b)"]

        for i, line in enumerate(lines):
            stdscr.addstr(i, 0, line)

        top = len(lines) + 1
        visible = h - top - 1

        running_balances = ledger.running_balance()
        if idx < scroll:
            scroll = idx
        if idx >= scroll + visible:
            scroll = idx - visible + 1

        for row, t in enumerate(txns[scroll:scroll + visible]):
            y = top + row
            attr = curses.A_REVERSE if scroll + row == idx else curses.A_NORMAL
            amt = Decimal(str(t["amount"]))
            debit = f"{-amt:.2f}" if amt < 0 else ""
            credit = f"{amt:.2f}" if amt > 0 else ""
            bal = running_balances[scroll + row]
            cat = t.get("category") or ""
            mark = "✔" if t.get("cleared") else " "
            stdscr.addstr(y, 0,
                          f"{mark} {t['date']} {t['description'][:20]:20} {cat[:10]:10} {debit:>8} {credit:>8} {bal:>10.2f}",
                          attr)

        # Right side help
        nav = ["Navigation", "↑/↓ move", "t top", "b bottom", "n/N uncleared", "F find", "f next", "q quit"]
        act = ["Actions", "space clear", "a add", "e edit", "d delete", "r bank bal"]

        col = w - 22
        for i, s in enumerate(nav):
            stdscr.addstr(i, col, s)
        for i, s in enumerate(act):
            stdscr.addstr(i + len(nav) + 1, col, s)

        stdscr.refresh()

    def prompt(stdscr, msg):
        curses.curs_set(1)  # turn cursor on
        curses.echo()
        stdscr.addstr(curses.LINES - 1, 0, msg)
        stdscr.clrtoeol()
        s = stdscr.getstr().decode()
        curses.noecho()
        curses.curs_set(0)  # turn cursor off again
        return s

    def add_transaction_tui(stdscr):
        date_in = prompt(stdscr, "Date (YYYY-MM-DD or . for today): ")
        date_val = today_if_dot(date_in)
        desc = prompt(stdscr, "Description: ")
        cat = prompt(stdscr, "Category (blank = uncategorized): ")
        amt = Decimal(prompt(stdscr, "Amount (negative = debit): "))
        cleared = prompt(stdscr, "Cleared? (y/N): ").lower().startswith("y")
        t = {"date": date_val, "description": desc, "category": cat or None, "amount": str(amt),
             "cleared": cleared, "deleted": False}
        ledger.add_transaction(t)

    def edit_transaction(stdscr, t):
        for field in ("date", "description", "category", "amount"):
            val = t.get(field, "")
            s = prompt(stdscr, f"{field} [{val}]: ").strip()
            if s:
                if field == "date":
                    t[field] = today_if_dot(s)
                elif field == "category":
                    t[field] = None if s == " " else s
                else:
                    t[field] = s

    def jump_next_uncleared():
        nonlocal idx
        for i in range(idx + 1, len(txns)):
            if not txns[i].get("cleared"):
                idx_set(i)
                return
        for i in range(0, idx + 1):
            if not txns[i].get("cleared"):
                idx_set(i)
                return

    def jump_prev_uncleared():
        nonlocal idx
        for i in range(idx - 1, -1, -1):
            if not txns[i].get("cleared"):
                idx_set(i)
                return
        for i in range(len(txns) - 1, idx - 1, -1):
            if not txns[i].get("cleared"):
                idx_set(i)
                return

    def idx_set(new_idx):
        nonlocal idx, scroll
        idx = new_idx
        scroll = idx

    def find_next(search):
        nonlocal idx
        start = idx + 1
        wrapped = False
        while True:
            if start >= len(txns):
                if wrapped:
                    break
                start = 0
                wrapped = True
            if search.lower() in json.dumps(txns[start]).lower():
                idx_set(start)
                break
            start += 1

    def curses_main(stdscr):
        nonlocal idx, bank_balance, last_search
        curses.curs_set(0)
        while True:
            draw(stdscr)
            ch = stdscr.getch()
            if ch == ord("q"):
                save_account(path, acct)
                break
            elif ( ch == curses.KEY_DOWN or ch == ord("j") ) and idx < len(txns) - 1:
                idx += 1
            elif ( ch == curses.KEY_UP or ch == ord("k") ) and idx > 0:
                idx -= 1
            elif ch == ord("t"):
                idx = 0
            elif ch == ord("b"):
                idx = len(txns) - 1
            elif ch == ord(" "):
                txns[idx]["cleared"] = not txns[idx].get("cleared")
            elif ch == ord("r"):
                # Enter bank balance for reconciliation, allow empty input to keep current
                s = prompt(stdscr, f"Bank balance [{bank_balance if bank_balance is not None else ''}]: ").strip()
                if s:
                    bank_balance = Decimal(s)
            elif ch == ord("e"):
                edit_transaction(stdscr, txns[idx])
            elif ch == ord("d"):
                ledger.delete_transaction(idx)
                idx = max(0, idx - 1)
            elif ch == ord("a"):
                add_transaction_tui(stdscr)
            elif ch == ord("n"):
                jump_next_uncleared()
            elif ch == ord("N"):
                jump_prev_uncleared()
            elif ch == ord("F"):
                last_search = prompt(stdscr, "Find: ")
                find_next(last_search)
            elif ch == ord("f") and last_search:
                find_next(last_search)

    curses.wrapper(curses_main)


# =========================
# CLI
# =========================

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    i = sub.add_parser("init")
    i.add_argument("file")
    i.add_argument("balance")

    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("date")
    a.add_argument("description")
    a.add_argument("amount")
    a.add_argument("-c", "--category")
    a.add_argument("--cleared", action="store_true")

    r = sub.add_parser("register")
    r.add_argument("file")

    c = sub.add_parser("categories")
    c.add_argument("file")
    c.add_argument("--start")
    c.add_argument("--end")

    t = sub.add_parser("tui")
    t.add_argument("file")
    t.add_argument("--bank-balance")

    rec = sub.add_parser("reconcile")
    rec.add_argument("file")
    rec.add_argument("--bank-balance", required=True)

    args = p.parse_args()

    if args.cmd == "init":
        save_account(args.file, new_account(args.balance))
    elif args.cmd == "add":
        acct = load_account(args.file)
        ledger = Ledger(acct)
        t = {"date": today_if_dot(args.date), "description": args.description, "category": args.category or None,
             "amount": args.amount, "cleared": args.cleared, "deleted": False}
        ledger.add_transaction(t)
        save_account(args.file, acct)
    elif args.cmd == "register":
        print_register(load_account(args.file))
    elif args.cmd == "categories":
        category_report(load_account(args.file), args.start, args.end)
    elif args.cmd == "tui":
        launch_tui(args.file, args.bank_balance)
    elif args.cmd == "reconcile":
        reconcile_report(load_account(args.file), args.bank_balance)


if __name__ == "__main__":
    main()
