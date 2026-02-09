import requests
from bs4 import BeautifulSoup
import os
import json
import smtplib
from email.mime.text import MIMEText
import subprocess

# 監視対象URL
URLS = [
    "https://store.m-piu.com/c-item-detail?ic=13816147",
    "https://store.m-piu.com/c-item-detail?ic=13816146",
]

STATE_FILE = "state.json"

MAIL_USER = os.environ["EMAIL_ADDRESS"]
MAIL_PASS = os.environ["EMAIL_PASSWORD"]


def is_in_stock(url):
    r = requests.get(url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    buttons = soup.find_all(["button", "input"])

    for b in buttons:
        if b.name == "button":
            text = b.get_text(strip=True)
        else:
            text = b.get("value", "")

        if "在庫分完売" in text:
            return False
        if "カートに入れる" in text:
            return True

    # 判定不能時は安全側
    return False


def notify(urls):
    body = "m-piu 商品の在庫が復活しました\n\n"
    body += "\n".join(urls)

    msg = MIMEText(body)
    msg["Subject"] = "【在庫復活】m-piu"
    msg["From"] = MAIL_USER
    msg["To"] = MAIL_USER

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(MAIL_USER, MAIL_PASS)
        s.send_message(msg)


# 前回状態読み込み
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        prev_states = json.load(f)
else:
    prev_states = {}

current_states = {}
recovered_urls = []

for url in URLS:
    current = "in" if is_in_stock(url) else "out"
    current_states[url] = current

    if prev_states.get(url) == "out" and current == "in":
        recovered_urls.append(url)

if recovered_urls:
    notify(recovered_urls)



# 状態保存
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(current_states, f, ensure_ascii=False, indent=2)

# state.json をGitHubに反映
subprocess.run(["git", "config", "--global", "user.name", "github-actions"])
subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"])
subprocess.run(["git", "add", STATE_FILE])
subprocess.run(["git", "commit", "-m", "update stock state"], check=False)
subprocess.run(["git", "push"])
