# Checkbook Ledger

A terminal-based **personal checkbook register and reconciliation tool**
written in Python.

This tool provides a fast keyboard‑driven interface for managing a
checking account, tracking categories, and reconciling against your bank
balance.

It combines:

-   CLI reports
-   A full screen curses TUI
-   Simple JSON storage
-   Zero external dependencies

------------------------------------------------------------------------

# Features

-   Running register balance
-   Transaction categories
-   Category summaries and drill‑down reports
-   Bank reconciliation
-   Daily operational report
-   Interactive TUI with keyboard navigation
-   Human‑readable JSON storage

------------------------------------------------------------------------

# Quick Start

Initialize an account:

    checkbook.py init checking.json 1000

Add a transaction:

    checkbook.py add checking.json . "Groceries" -45.23 -c Food

Open the interactive interface:

    checkbook.py tui checking.json

------------------------------------------------------------------------

# Account File Format

Accounts are stored as JSON.

Example:

``` json
{
  "initial_balance": "1000.00",
  "bank_balance": "1500.00",
  "transactions": [
    {
      "date": "2026-03-01",
      "description": "Paycheck",
      "category": "Income",
      "amount": "2000.00",
      "cleared": true,
      "deleted": false
    }
  ]
}
```

------------------------------------------------------------------------

# CLI Commands

## Initialize Account

    checkbook.py init FILE BALANCE

Example:

    checkbook.py init acct.json 500

------------------------------------------------------------------------

## Add Transaction

    checkbook.py add FILE DATE DESCRIPTION AMOUNT

Example:

    checkbook.py add acct.json . "Coffee" -4.50 -c Food

```
Options:

    -c CATEGORY
    --cleared

Date shortcuts:

  Input   Meaning
  ------- --------------
  .       today
  -1      yesterday
  -2      two days ago

```
------------------------------------------------------------------------

## Print Register

    checkbook.py register acct.json

Example output:

    Date        Description                     Category        Debit     Credit     Balance
    -----------------------------------------------------------------------------------------
    ✔ 2026-03-01 Paycheck                       Income                     2000.00     3000.00
      2026-03-02 Grocery Store                  Food            85.20                 2914.80

------------------------------------------------------------------------

## Category Summary

    checkbook.py categories acct.json

With date filtering:

    checkbook.py categories acct.json --start 2026-01-01 --end 2026-03-01

Example:

    Food               -325.20
    Utilities          -180.00
    Income             2400.00

------------------------------------------------------------------------

## Category Detail Report

    checkbook.py category-report acct.json

Example:

    Food                           -325.20
    ----------------------------------------------------
    2026-03-01 Grocery Store        85.20
    2026-03-03 Restaurant           45.00

------------------------------------------------------------------------

## Reconciliation

    checkbook.py reconcile acct.json --bank-balance 1450.32

Displays:

-   Bank balance
-   Uncleared checks
-   Uncleared deposits
-   Ending bank balance
-   Register balance
-   Difference

If `--bank-balance` is provided, it is automatically saved into the
account file.

------------------------------------------------------------------------

# Daily Report

    checkbook.py daily-report acct.json

This report includes:

1.  Reconciliation summary
2.  Uncleared transactions
3.  Last 2 days of register activity

Example:

    DAILY ACCOUNT REPORT
    ======================================================

    RECONCILIATION
    Bank balance       :     1543.55
    Uncleared checks   :       45.00
    Uncleared deposits :      200.00
    Ending balance     :     1698.55
    Register balance   :     1698.55
    Difference         :        0.00


    UNCLEARED TRANSACTIONS
    ------------------------------------------------------
    2026-03-02 Grocery Store        -45.00


    LAST TWO DAYS ACTIVITY
    ------------------------------------------------------
    Date        Description               Amount     Balance
    2026-03-03  Paycheck                 2000.00     3698.55
    2026-03-02  Grocery Store             -45.00     1698.55

Each register entry includes the **running register balance**.

------------------------------------------------------------------------

# TUI Interface

Launch the interactive interface:

    checkbook.py tui acct.json

------------------------------------------------------------------------

## Navigation

  Key     Action
  ------- --------------------
  ↑ / ↓   move
  t       jump to top
  b       jump to bottom
  n       next uncleared
  N       previous uncleared
  F       search
  f       next match

------------------------------------------------------------------------

## Actions

  Key     Action
  ------- --------------------
  space   toggle cleared
  a       add transaction
  e       edit transaction
  d       delete
  r       enter bank balance
  q       quit

------------------------------------------------------------------------

# Screenshots

## TUI Interface

Example layout:

    Account: checking.json

    Bank balance        :   1543.22
    Uncleared checks    :     45.00
    Uncleared deposits  :    200.00
    Ending balance      :   1698.22
    Register balance    :   1698.22
    Difference          :      0.00

    ✔ 2026-03-02 Grocery Store   Food        45.00      0      1698.22
      2026-03-03 Paycheck        Income                 2000   3698.22

(Replace this section with real screenshots if publishing the project.)

------------------------------------------------------------------------

# Example Workflow

    # create account
    checkbook.py init checking.json 1000

    # add income
    checkbook.py add checking.json . "Paycheck" 2200 -c Income --cleared

    # add expense
    checkbook.py add checking.json . "Groceries" -85 -c Food

    # review daily status
    checkbook.py daily-report checking.json

    # reconcile against bank
    checkbook.py reconcile checking.json --bank-balance 3100

------------------------------------------------------------------------

# Design Goals

-   Human readable financial data
-   Fast CLI workflow
-   Keyboard driven interface
-   No database required
-   Works well over SSH

------------------------------------------------------------------------

# License

MIT
