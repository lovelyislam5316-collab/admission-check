import os, json, hashlib, requests

URLS = [
    "https://cadetcollegeadmission.army.mil.bd/profile",
]
TOKEN = os.environ["BOT_TOKEN"]
CHAT = os.environ["CHAT_ID"]

def notify(msg):
    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                 params={"chat_id": CHAT, "text": msg})

try:
    state = json.load(open("state.json"))
except Exception:
    state = {}

for u in URLS:
    try:
        text = requests.get(u, timeout=600).text
        h = hashlib.md5(text.encode()).hexdigest()
        if u in state and state[u] != h:
            notify(f"পেজ বদলেছে, চেক করো:\n{u}")
        state[u] = h
    except Exception as e:
        print(u, e)

json.dump(state, open("state.json", "w"))
