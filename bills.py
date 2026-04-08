#!/usr/bin/env python3
import argparse
import curses
import json
import sys
from datetime import date, timedelta
from decimal import Decimal


# ============================================================
# ===================== DATA HANDLING =========================
# ============================================================

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
    if not path:
        return []
    try:
        with open(path) as f:
            acct = json.load(f)
        return [t for t in acct.get("transactions", []) if not t.get("deleted")]
    except Exception:
        return []


# ============================================================
# ===================== CORE LOGIC ============================
# ============================================================

def today():
    return date.today()


def due_date_for(bill, ref=None):
    ref = ref or today()

    if bill["frequency"] == "monthly":
        return date(ref.year, ref.month, bill["due_day"])
    elif bill["frequency"] == "yearly":
        return date(ref.year, bill["due_month"], bill["due_day"])
    else:
        raise ValueError("Invalid frequency")


def txn_matches_bill(txn, bill, due):
    if txn.get("category") != bill.get("category"):
        return False

    txn_date = date.fromisoformat(txn["date"])
    return abs((txn_date - due).days) <= 5


def find_payment(bill, txns):
    due = due_date_for(bill)

    for t in txns:
        if txn_matches_bill(t, bill, due):
            return t
    return None


def compute_status(bill, txns):
    now = today()
    due = due_date_for(bill)

    payment = find_payment(bill, txns)

    if payment:
        return "PAID", payment["date"]

    if now > due:
        return "OVERDUE", None

    if (due - now).days <= 5:
        return "DUE", None

    return "UPCOMING", None


# ============================================================
# ===================== CLI COMMANDS ==========================
# ============================================================

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
    data = load_bills(args.file)
    txns = load_transactions(args.account)

    print(f"{'Name':20} {'Amount':>10} {'Due':>10} {'Freq':>10} {'Status':>10} {'Last Paid':>12}")
    print("-" * 80)

    for b in data["bills"]:
        status, paid = compute_status(b, txns)
        due = due_date_for(b)

        print(
            f"{b['name'][:20]:20} "
            f"{Decimal(b['amount']):10.2f} "
            f"{due.isoformat():10} "
            f"{b['frequency']:10} "
            f"{status:10} "
            f"{(paid or ''):12}"
        )


def cmd_upcoming(args):
    data = load_bills(args.file)
    txns = load_transactions(args.account)

    now = today()
    horizon = now + timedelta(days=args.days)

    print(f"Upcoming bills in next {args.days} days\n")
    print(f"{'Name':20} {'Due':>10} {'Amount':>10} {'Status':>10}")
    print("-" * 60)

    for b in data["bills"]:
        due = due_date_for(b)

        if now <= due <= horizon:
            status, _ = compute_status(b, txns)
            print(
                f"{b['name'][:20]:20} "
                f"{due.isoformat():10} "
                f"{Decimal(b['amount']):10.2f} "
                f"{status:10}"
            )


def cmd_mark_paid(args):
    data = load_bills(args.file)

    for b in data["bills"]:
        if b["name"].lower() == args.name.lower():
            b["last_paid"] = args.date or today().isoformat()
            save_bills(args.file, data)
            print(f"Marked {b['name']} as paid on {b['last_paid']}")
            return

    print("Bill not found")


# ============================================================
# ===================== TUI ==================================
# ============================================================


def launch_tui(bills_path, acct_path=None):
    ROW_FMT = "{name:20} {due:10} {amount:>10} {freq:8} {status:10} {paid:12}"

    data = load_bills(bills_path)
    txns = load_transactions(acct_path)

    bills = data["bills"]
    idx = 0
    scroll = 0

    def refresh():
        nonlocal data, bills, txns
        data = load_bills(bills_path)
        bills = data["bills"]
        txns = load_transactions(acct_path)

    def prompt(stdscr, msg):
        curses.curs_set(1)
        curses.echo()

        stdscr.addstr(curses.LINES - 1, 0, msg)
        stdscr.clrtoeol()
        stdscr.move(curses.LINES - 1, len(msg))
        stdscr.refresh()

        try:
            s = stdscr.getstr().decode()
        except KeyboardInterrupt:
            raise  # 👈 let caller handle cancel
        finally:
            curses.noecho()
            curses.curs_set(0)

        return s

    def draw(stdscr):
        nonlocal scroll
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        stdscr.addstr(0, 0, f"BILLS - {bills_path}")

        header = ROW_FMT.format(
            name="Name",
            due="Due",
            amount="Amount",
            freq="Freq",
            status="Status",
            paid="Last Paid"
        )
        stdscr.addstr(2, 0, header)
        stdscr.addstr(3, 0, "-" * len(header))

        visible = h - 6

        if idx < scroll:
            scroll = idx
        if idx >= scroll + visible:
            scroll = idx - visible + 1

        for i, b in enumerate(bills[scroll:scroll + visible]):
            row = scroll + i
            y = 4 + i

            status, paid = compute_status(b, txns)
            due = due_date_for(b)

            attr = curses.A_REVERSE if row == idx else curses.A_NORMAL

            line = ROW_FMT.format(
                 name=b["name"][:20],
                 due=due.isoformat(),
                 amount=f"{Decimal(b['amount']):.2f}",
                 freq=b["frequency"][:8],
                 status=status,
                 paid=(paid or "")
            )

            stdscr.addstr(y, 0, line, attr)


        help_text = [
            "↑/↓ move",
            "a add",
            "e edit",
            "d delete",
            "r refresh",
            "q quit"
        ]

        col = w - 20
        for i, line in enumerate(help_text):
            stdscr.addstr(i, col, line)

        stdscr.refresh()

    def add_bill(stdscr):
        try:
            name = prompt(stdscr, "Name: ")
            amount = Decimal(prompt(stdscr, "Amount: "))
            freq = prompt(stdscr, "Frequency (monthly/yearly): ").strip()

            day = int(prompt(stdscr, "Due day: "))
            category = prompt(stdscr, "Category: ")

            bill = {
                "name": name,
                "amount": str(amount),
                "frequency": freq,
                "due_day": day,
                "category": category,
                "last_paid": None
            }

            if freq == "yearly":
                bill["due_month"] = int(prompt(stdscr, "Due month (1-12): "))

            data["bills"].append(bill)
            save_bills(bills_path, data)

        except KeyboardInterrupt:
            # 👈 cancel cleanly, do nothing
            return


    def edit_bill(stdscr, b):
        try:
            for field in ["name", "amount", "category"]:
                val = str(b.get(field, ""))
                s = prompt(stdscr, f"{field} [{val}]: ")
                if s:
                    b[field] = s

            save_bills(bills_path, data)

        except KeyboardInterrupt:
            return

    def delete_bill():
        bills.pop(idx)
        save_bills(bills_path, data)

    def curses_main(stdscr):
        nonlocal idx

        curses.curs_set(0)

        while True:
            draw(stdscr)
            ch = stdscr.getch()

            if ch == ord("q"):
                break
            elif ch in (curses.KEY_DOWN, ord("j")) and idx < len(bills) - 1:
                idx += 1
            elif ch in (curses.KEY_UP, ord("k")) and idx > 0:
                idx -= 1
            elif ch == ord("a"):
                add_bill(stdscr)
                refresh()
                idx = len(bills) - 1
            elif ch == ord("e") and bills:
                edit_bill(stdscr, bills[idx])
                refresh()
            elif ch == ord("d") and bills:
                delete_bill()
                refresh()
                idx = max(0, idx - 1)
            elif ch == ord("r"):
                refresh()

    curses.wrapper(curses_main)


# ============================================================
# ===================== MAIN =================================
# ============================================================

def main():
    p = argparse.ArgumentParser(description="Bill tracking utility")
    sub = p.add_subparsers(dest="cmd")

    # CLI
    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("name")
    a.add_argument("amount")
    a.add_argument("day", type=int)
    a.add_argument("-c", "--category", required=True)
    a.add_argument("-f", "--frequency", choices=["monthly", "yearly"], default="monthly")
    a.add_argument("--month", type=int)

    l = sub.add_parser("list")
    l.add_argument("file")
    l.add_argument("--account")

    u = sub.add_parser("upcoming")
    u.add_argument("file")
    u.add_argument("--account")
    u.add_argument("--days", type=int, default=7)

    m = sub.add_parser("mark-paid")
    m.add_argument("file")
    m.add_argument("name")
    m.add_argument("--date")

    # TUI
    t = sub.add_parser("tui")
    t.add_argument("file")
    t.add_argument("--account")

    args = p.parse_args()

    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "upcoming":
        cmd_upcoming(args)
    elif args.cmd == "mark-paid":
        cmd_mark_paid(args)
    elif args.cmd == "tui":
        launch_tui(args.file, args.account)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
