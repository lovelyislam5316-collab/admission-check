import os, json, time, re, requests
from bs4 import BeautifulSoup

# ===== শুধু এই অংশ বদলাবে =====
URLS = [
    "https://cadetcollegeadmission.army.mil.bd/",
]
SLOW_SECONDS = 8      # এর বেশি সময় লাগলে 🐢 মেসেজ
FAIL_LIMIT = 2        # পরপর এতবার সমস্যা হলে তবেই সমস্যার মেসেজ
KEYWORDS = ["সিট", "আসন", "ফাঁকা", "খালি", "vacant", "seat",
            "available", "waiting", "ভর্তি", "নোটিশ", "notice", "admission"]
# ================================

TOKEN = os.environ["BOT_TOKEN"]
CHAT = os.environ["CHAT_ID"]

def notify(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                     params={"chat_id": CHAT, "text": msg[:4000]}, timeout=20)
    except Exception as e:
        print("notify error", e)

def relevant_lines(html):
    text = BeautifulSoup(html, "html.parser").get_text("\n")
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    return [l for l in lines
            if l and any(k.lower() in l.lower() for k in KEYWORDS)]

def classify(code):
    if code == 200: return "ok"
    if code in (429, 503): return "busy"
    if code in (401, 403): return "blocked"
    if code >= 500: return "error"
    return "other"

LABEL = {
    "ok": "✅ সাইট ঠিক আছে",
    "busy": "🔥 ভিড়ে সার্ভার চাপে (429/503)",
    "blocked": "🚫 সাইট বট বা আইপি আটকাচ্ছে (403)",
    "error": "⚠️ সার্ভারে সমস্যা (5xx)",
    "other": "❓ অন্য ধরনের সাড়া",
    "timeout": "⏳ সাইট সাড়া দিচ্ছে না (টাইমআউট)",
    "down": "❌ সংযোগই হচ্ছে না",
}

try:
    state = json.load(open("state.json"))
except Exception:
    state = {}

for u in URLS:
    s = state.setdefault(u, {"status": "ok", "bad": 0, "slow": False, "lines": None})
    code = secs = html = None
    try:
        t = time.time()
        r = requests.get(u, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        secs = round(time.time() - t, 1)
        code = r.status_code
        kind = classify(code)
        html = r.text
    except requests.exceptions.Timeout:
        kind = "timeout"
    except Exception:
        kind = "down"

    print(u, kind, code, secs)

    # ১) সার্ভারের অবস্থা: পরপর FAIL_LIMIT বার সমস্যা হলে একবার জানাবে
    if kind != "ok":
        s["bad"] += 1
        if s["bad"] >= FAIL_LIMIT and s["status"] == "ok":
            msg = f"{LABEL[kind]}\n{u}"
            if code: msg += f"\nকোড: {code}"
            msg += "\n\nভিড়ে সাইট ধীর হওয়া অনেক সময় নতুন কিছু ঘটার ইঙ্গিত। নিজে একবার ঢুকে দেখো।"
            notify(msg)
            s["status"] = kind
        continue

    # সাইট ঠিক হয়ে গেলে একবার জানাবে
    if s["status"] != "ok":
        notify(f"✅ সাইট আবার সচল হয়েছে\n{u}\nনিজে একবার দেখে নাও।")
    s["status"] = "ok"
    s["bad"] = 0

    # ২) রেসপন্স টাইমের লিমিট
    if secs > SLOW_SECONDS and not s["slow"]:
        notify(f"🐢 সাইট হঠাৎ ধীর: {secs} সেকেন্ড (লিমিট {SLOW_SECONDS})\n{u}\nভিড় বাড়ছে হতে পারে।")
        s["slow"] = True
    elif secs <= SLOW_SECONDS:
        s["slow"] = False

    # ৩) সিট/নোটিশের লাইন বদল
    now = relevant_lines(html)
    old = s["lines"]
    if old is not None and now and old != now:
        added = [l for l in now if l not in old]
        removed = [l for l in old if l not in now]
        msg = f"🔔 পেজে বদল!\n{u}\n"
        if added:
            msg += "\nনতুন:\n" + "\n".join(added[:6])
        if removed:
            msg += "\n\nআগে ছিল:\n" + "\n".join(removed[:6])
        notify(msg)
    if now:
        s["lines"] = now

json.dump(state, open("state.json", "w"), ensure_ascii=False)
