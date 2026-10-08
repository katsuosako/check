name: X Person Monitor (Sato)

on:
  schedule:
    - cron: '*/5 * * * *'  # 5分おきに実行
  workflow_dispatch:

jobs:
  check-x-person:
    runs-on: ubuntu-latest

    permissions:
      contents: write  # 履歴ファイルをリポジトリへ自動コミットするために必須

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests resend

      - name: Run Person Monitor
        env:
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          NOTIFICATION_EMAIL: ${{ secrets.NOTIFICATION_EMAIL }}
        run: python check_x_person.py

      - name: Commit and push notification history
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add notified_person_ids.txt || true
          git diff --staged --quiet || (git commit -m "Chore: Update notification history [skip ci]" && git push)
