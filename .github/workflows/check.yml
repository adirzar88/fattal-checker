name: U Splash Availability Check

on:
  schedule:
    - cron: '*/5 * * * *'   # כל 5 דקות
  workflow_dispatch:          # אפשרות להפעיל ידנית

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Run availability check
        run: python check.py
