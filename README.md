# Checkbook Ledger

A terminal-based personal checkbook register and reconciliation tool
written in Python.

Features:

-   Transaction register with running balance
-   Category summary and detailed category reports
-   Reconciliation against bank balance
-   Interactive curses TUI
-   Daily operational summary
-   Simple JSON file storage
-   No external services required

------------------------------------------------------------------------

# Account File Structure

Example:

{ "initial_balance": "1000.00", "bank_balance": "1050.00",
"transactions": \[ { "date": "2026-03-01", "description": "Deposit",
"category": "Income", "amount": "500.00", "cleared": true, "deleted":
false } \] }

Fields:

  Field             Meaning
  ----------------- ------------------------------
  initial_balance   Opening account balance
  bank_balance      Last reconciled bank balance
  transactions      Transaction list

Transaction fields:

  Field         Meaning
  ------------- ----------------------------------
  date          ISO date YYYY-MM-DD
  description   Description text
  category      Category name
  amount        Positive=deposit, Negative=debit
  cleared       Reconciled flag
  deleted       Soft delete flag

------------------------------------------------------------------------

# Commands

## Initialize Account

checkbook.py init account.json 1000

Creates a new account with the starting balance.

------------------------------------------------------------------------

## Add Transaction

checkbook.py add account.json 2026-03-05 "Groceries" -45.22 -c Food

Options:

-c CATEGORY\
--cleared

Example:

checkbook.py add acct.json . "Paycheck" 2200 -c Income --cleared

Date shortcuts:

  Input   Meaning
  ------- --------------
  .       today
  -1      yesterday
  -2      two days ago

------------------------------------------------------------------------

## Register Report

checkbook.py register account.json

Prints the full check register with running balance.

------------------------------------------------------------------------

## Category Summary

checkbook.py categories account.json

With date range:

checkbook.py categories account.json --start 2026-01-01 --end 2026-03-01

Example output:

Food -325.20 Utilities -180.00 Income 2400.00

------------------------------------------------------------------------

## Category Detail Report

checkbook.py category-report account.json

Shows totals and transactions for each category.

Example:

## Food -325.20

2026-03-01 Grocery Store 85.20 2026-03-03 Restaurant 45.00

Supports:

--start\
--end

------------------------------------------------------------------------

## Reconciliation Report

checkbook.py reconcile account.json --bank-balance 1243.55

Displays:

-   Bank balance
-   Uncleared checks
-   Uncleared deposits
-   Ending bank balance
-   Register balance
-   Difference

The provided bank balance is saved to the account file.

------------------------------------------------------------------------

## Daily Report

checkbook.py daily-report account.json

Includes:

-   Reconciliation summary
-   Uncleared transactions
-   Last 2 days of register activity

Example:

# DAILY ACCOUNT REPORT

RECONCILIATION Bank balance : 1543.55 Uncleared checks : 45.00 Uncleared
deposits : 200.00 Ending balance : 1698.55 Register balance : 1698.55
Difference : 0.00

UNCLEARED TRANSACTIONS 2026-03-02 Grocery Store -45.00

LAST TWO DAYS ACTIVITY 2026-03-03 Paycheck 2000.00 2026-03-02 Grocery
Store -45.00

------------------------------------------------------------------------

# TUI Interface

Launch:

checkbook.py tui account.json

Navigation:

↑/↓ move\
t top\
b bottom\
n next uncleared\
N previous uncleared\
F search\
f next match

Actions:

space toggle cleared\
a add transaction\
e edit transaction\
d delete\
r enter bank balance\
q quit

------------------------------------------------------------------------

# Design Goals

-   Human‑readable storage
-   Fast CLI workflows
-   Keyboard-driven interface
-   No external dependencies
