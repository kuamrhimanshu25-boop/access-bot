import json
import sqlite3
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
import random
import string
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta

# ============ CONFIG ============
BOT_TOKEN = "8516599812:AAEJdWUMcZWeXSCSsHYM7FCOG0YEbNvQmRM"
CHANNEL_ID = -1004463557586
OWNER_ID = 7578158962
ADMIN_IDS = [7578158962]

CHANNEL_LINK = "https://t.me/JoinThePiratesCloud"
CHANNEL_NAME = "THE PIRATE'S CLOUD"
GROUP_LINK = "https://t.me/JoinPiratesCloudChat"
OWNER_USERNAME = "@TheInvisibleGhost"

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_PATH = "database.db"
POLL_INTERVAL = 60
INVITE_EXPIRE_SECONDS = 900  # 15 minutes


# ============ FAKE WEB SERVER ============
def run_fake_server():
    port = int(os.environ.get("PORT", 8080))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is running")
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
        def log_message(self, format, *args):
            pass
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[*] Fake web server started on port {port}")
    server.serve_forever()


# ============ PROMO TEXT ============
PROMO_FULL = (
    "\n\n╔══════════════════════╗\n"
    "   🏴‍☠️  *THE PIRATE'S CLOUD*  🏴‍☠️\n"
    "╚══════════════════════╝\n\n"
    "Shiver Me Timbers ⚓\n\n"
    "🔥🔥 *JOIN FOR DAILY PREMIUM DROPS* 🔥🔥\n\n"
    "🎮 XBOX ACCOUNTS\n"
    "📺 STREAMING ACCOUNTS\n"
    "📧 GOOD QUALITY HOTMAILS\n"
    "💥 METHODS\n"
    "⚡ AND MANY MORE PREMIUM DROPS ⚡\n\n"
    "👑 *Owner:* " + OWNER_USERNAME + "\n"
    "💬 *Group Chat:* @JoinPiratesCloudChat\n\n"
    "🔗 *Join Now:* " + CHANNEL_LINK + "\n\n"
    "⚠️ _Content shared is for educational purposes only._"
)

PROMO_SHORT = (
    "\n\n────────────────────\n"
    "🏴‍☠️ *THE PIRATE'S CLOUD* 🏴‍☠️\n"
    "🔥 Premium Drops Daily\n"
    f"🔗 {CHANNEL_LINK}\n"
    "────────────────────"
)


# ============ HTTP HELPERS ============
def api_call(method, params=None, timeout=30):
    url = f"{API}/{method}"
    data = None
    headers = {}
    if params:
        data = json.dumps(params).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "description": str(e)}
    except Exception as e:
        return {"ok": False, "description": str(e)}


def send_message(chat_id, text, parse_mode="Markdown", keyboard=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if keyboard:
        params["reply_markup"] = json.dumps(keyboard)
    return api_call("sendMessage", params)


def edit_message(chat_id, message_id, text, parse_mode="Markdown", keyboard=None):
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if keyboard:
        params["reply_markup"] = json.dumps(keyboard)
    return api_call("editMessageText", params)


def answer_callback(callback_id, text=None, show_alert=False):
    params = {"callback_query_id": callback_id}
    if text:
        params["text"] = text
        params["show_alert"] = show_alert
    return api_call("answerCallbackQuery", params)


def ban_chat_member(user_id):
    return api_call("banChatMember", {"chat_id": CHANNEL_ID, "user_id": user_id})


def unban_chat_member(user_id):
    return api_call("unbanChatMember", {
        "chat_id": CHANNEL_ID, "user_id": user_id, "only_if_banned": True,
    })


def get_chat_member(user_id):
    return api_call("getChatMember", {"chat_id": CHANNEL_ID, "user_id": user_id})


def create_invite_link(name="Access", member_limit=1):
    expire_ts = int(time.time()) + INVITE_EXPIRE_SECONDS
    return api_call("createChatInviteLink", {
        "chat_id": CHANNEL_ID,
        "name": name[:32],
        "member_limit": member_limit,
        "expire_date": expire_ts,
    })


def revoke_invite_link(invite_link):
    return api_call("revokeChatInviteLink", {
        "chat_id": CHANNEL_ID,
        "invite_link": invite_link,
    })


def get_updates(offset=None, timeout=25):
    params = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
    if offset:
        params["offset"] = offset
    return api_call("getUpdates", params, timeout=timeout + 10)


# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS access (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            display_name TEXT,
            expires_at TEXT NOT NULL,
            added_by INTEGER,
            added_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT,
            duration TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            added_by INTEGER,
            added_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key_code TEXT PRIMARY KEY,
            duration TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            price_usd REAL DEFAULT 0,
            created_by INTEGER,
            created_at TEXT NOT NULL,
            redeemed_by INTEGER,
            redeemed_at TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            username TEXT,
            display_name TEXT,
            key_code TEXT,
            duration TEXT,
            price_usd REAL,
            issued_by INTEGER,
            issued_at TEXT,
            expires_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def db_execute(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()


def db_fetchone(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    row = c.fetchone()
    conn.close()
    return row


def db_fetchall(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


# --- Access ---
def add_access(user_id, username, display_name, expires_at, added_by):
    db_execute("""
        INSERT INTO access (user_id, username, display_name, expires_at, added_by, added_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            expires_at = excluded.expires_at,
            username = excluded.username,
            display_name = excluded.display_name
    """, (user_id, username, display_name, expires_at.isoformat(), added_by, datetime.now().isoformat()))


def get_access(user_id):
    row = db_fetchone(
        "SELECT user_id, username, display_name, expires_at FROM access WHERE user_id = ?",
        (user_id,)
    )
    if row:
        return {
            "user_id": row[0], "username": row[1],
            "display_name": row[2] or row[1] or str(row[0]),
            "expires_at": datetime.fromisoformat(row[3]),
        }
    return None


def remove_access(user_id):
    db_execute("DELETE FROM access WHERE user_id = ?", (user_id,))


def get_all_expired():
    return db_fetchall(
        "SELECT user_id, username, display_name, expires_at FROM access WHERE expires_at <= ?",
        (datetime.now().isoformat(),)
    )


def get_all_active():
    return db_fetchall(
        "SELECT user_id, username, display_name, expires_at FROM access "
        "WHERE expires_at > ? ORDER BY expires_at",
        (datetime.now().isoformat(),)
    )


def log_history(user_id, username, action, duration):
    db_execute(
        "INSERT INTO history (user_id, username, action, duration, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, action, duration, datetime.now().isoformat())
    )


# --- Admins ---
def add_admin_db(user_id, username, added_by):
    db_execute("""
        INSERT OR REPLACE INTO admins (user_id, username, added_by, added_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, added_by, datetime.now().isoformat()))


def remove_admin_db(user_id):
    db_execute("DELETE FROM admins WHERE user_id = ?", (user_id,))


def get_all_admins_db():
    return db_fetchall("SELECT user_id, username FROM admins ORDER BY added_at")


# --- Keys ---
def generate_key_code():
    chars = string.ascii_uppercase + string.digits
    part = lambda: "".join(random.choices(chars, k=4))
    return f"PIRATE-{part()}-{part()}-{part()}"


def create_key(duration_text, duration_seconds, created_by, price_usd=0.0):
    key = generate_key_code()
    while db_fetchone("SELECT 1 FROM keys WHERE key_code = ?", (key,)):
        key = generate_key_code()
    db_execute("""
        INSERT INTO keys (key_code, duration, duration_seconds, price_usd, created_by, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, 'active')
    """, (key, duration_text, duration_seconds, price_usd, created_by, datetime.now().isoformat()))
    return key


def get_key(key_code):
    row = db_fetchone(
        "SELECT key_code, duration, duration_seconds, price_usd, created_by, created_at, "
        "redeemed_by, redeemed_at, status FROM keys WHERE key_code = ?",
        (key_code.upper(),)
    )
    if row:
        return {
            "key_code": row[0], "duration": row[1], "duration_seconds": row[2],
            "price_usd": row[3] or 0.0, "created_by": row[4], "created_at": row[5],
            "redeemed_by": row[6], "redeemed_at": row[7], "status": row[8],
        }
    return None


def redeem_key(key_code, user_id):
    db_execute("""
        UPDATE keys SET redeemed_by = ?, redeemed_at = ?, status = 'redeemed'
        WHERE key_code = ?
    """, (user_id, datetime.now().isoformat(), key_code.upper()))


def get_all_keys(status=None):
    if status:
        return db_fetchall(
            "SELECT key_code, duration, duration_seconds, price_usd, created_at, redeemed_by, status "
            "FROM keys WHERE status = ? ORDER BY created_at DESC",
            (status,)
        )
    return db_fetchall(
        "SELECT key_code, duration, duration_seconds, price_usd, created_at, redeemed_by, status "
        "FROM keys ORDER BY created_at DESC"
    )


# --- Receipts ---
def generate_receipt_no():
    now = datetime.now()
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TPC-{now.strftime('%Y%m%d')}-{rand}"


def create_receipt(user_id, username, display_name, key_code, duration, price_usd, issued_by, expires_at):
    receipt_no = generate_receipt_no()
    while db_fetchone("SELECT 1 FROM receipts WHERE receipt_no = ?", (receipt_no,)):
        receipt_no = generate_receipt_no()
    db_execute("""
        INSERT INTO receipts (receipt_no, user_id, username, display_name, key_code, duration, price_usd, issued_by, issued_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (receipt_no, user_id, username, display_name, key_code, duration, price_usd,
          issued_by, datetime.now().isoformat(), expires_at.isoformat()))
    return receipt_no


def get_receipt(receipt_no):
    row = db_fetchone(
        "SELECT receipt_no, user_id, username, display_name, key_code, duration, price_usd, "
        "issued_by, issued_at, expires_at FROM receipts WHERE receipt_no = ?",
        (receipt_no,)
    )
    if row:
        return {
            "receipt_no": row[0], "user_id": row[1], "username": row[2],
            "display_name": row[3], "key_code": row[4], "duration": row[5],
            "price_usd": row[6], "issued_by": row[7],
            "issued_at": datetime.fromisoformat(row[8]),
            "expires_at": datetime.fromisoformat(row[9]),
        }
    return None


# ============ HELPERS ============
def is_owner(user_id):
    return user_id == OWNER_ID


def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    if user_id in ADMIN_IDS:
        return True
    return db_fetchone("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) is not None


def parse_duration(text):
    text = text.lower().replace(" ", "")
    total = timedelta()
    num = ""
    for ch in text:
        if ch.isdigit():
            num += ch
        elif ch in ("d", "h", "m"):
            if not num:
                return None
            n = int(num)
            if ch == "d":
                total += timedelta(days=n)
            elif ch == "h":
                total += timedelta(hours=n)
            elif ch == "m":
                total += timedelta(minutes=n)
            num = ""
        else:
            return None
    if num:
        return None
    return total if total.total_seconds() > 0 else None


def format_duration(td):
    total_sec = int(td.total_seconds())
    days = total_sec // 86400
    hours = (total_sec % 86400) // 3600
    mins = (total_sec % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    return " ".join(parts) or "0m"


def user_mention(user_id, name):
    safe = str(name).replace("*", "").replace("_", "").replace("[", "").replace("]", "").replace("`", "")
    return f"[{safe}](tg://user?id={user_id})"


def kick_user(user_id):
    r = ban_chat_member(user_id)
    return r.get("ok", False)


def get_user_identity(user_id):
    info = get_chat_member(user_id)
    if info.get("ok"):
        u = info["result"]["user"]
        username = u.get("username") or ""
        display = u.get("first_name", "")
        if u.get("last_name"):
            display = f"{display} {u['last_name']}".strip()
        return username or str(user_id), display or str(user_id)
    return str(user_id), str(user_id)


def build_receipt_text(receipt_no, display_name, username, user_id, key_code,
                       duration, price_usd, expires_at, invite_link=None):
    """Build a professional billing receipt."""
    issued = datetime.now()
    price_str = f"${price_usd:.2f}" if price_usd and price_usd > 0 else "FREE / GIFT"
    total_str = f"${price_usd:.2f}" if price_usd and price_usd > 0 else "$0.00"

    link_section = ""
    if invite_link:
        link_section = (
            "\n┌──────────────────────────────┐\n"
            "│  🔗  *YOUR PRIVATE INVITE LINK*  │\n"
            "└──────────────────────────────┘\n\n"
            f"{invite_link}\n\n"
            "⚠️ *Important Notes:*\n"
            "• This link works for *ONE person* only\n"
            "• Expires in *15 minutes*\n"
            "• Join now before it expires!\n"
        )

    receipt = (
        "╔══════════════════════════════╗\n"
        "║   🧾  *OFFICIAL RECEIPT*  🧾   ║\n"
        "║      THE PIRATE'S CLOUD       ║\n"
        "╚══════════════════════════════╝\n\n"
        f"📄 *Receipt No:* `{receipt_no}`\n"
        f"📅 *Date:* `{issued.strftime('%d %b %Y, %I:%M %p')}`\n"
        f"🏴‍☠️ *Issued By:* {OWNER_USERNAME}\n\n"
        "┌──────────────────────────────┐\n"
        "│      👤  *BILLED TO*           │\n"
        "└──────────────────────────────┘\n"
        f"👤 *Name:* {display_name}\n"
        f"🔗 *Username:* @{username}\n"
        f"🆔 *User ID:* `{user_id}`\n\n"
        "┌──────────────────────────────┐\n"
        "│      🛒  *ORDER DETAILS*       │\n"
        "└──────────────────────────────┘\n"
        f"🎁 *Product:* Premium Channel Access\n"
        f"🏴‍☠️ *Channel:* {CHANNEL_NAME}\n"
        f"🔑 *Access Key:* `{key_code}`\n"
        f"⏱️ *Duration:* {duration}\n"
        f"💰 *Unit Price:* {price_str}\n"
        f"🔢 *Quantity:* 1\n\n"
        "──────────────────────────────\n"
        f"💵 *SUBTOTAL:* {price_str}\n"
        f"🎟️ *Discount:* $0.00\n"
        f"🧾 *TAX:* $0.00\n"
        "──────────────────────────────\n"
        f"✅ *TOTAL PAID:* {total_str}\n"
        "──────────────────────────────\n\n"
        "┌──────────────────────────────┐\n"
        "│      ⏳  *VALIDITY*            │\n"
        "└──────────────────────────────┘\n"
        f"📆 *Activated:* `{issued.strftime('%d %b %Y, %I:%M %p')}`\n"
        f"⌛ *Expires On:* `{expires_at.strftime('%d %b %Y, %I:%M %p')}`\n"
        f"⏱️ *Total Duration:* {duration}\n"
        + link_section +
        "\n╔══════════════════════════════╗\n"
        "║   ✅  *PAYMENT CONFIRMED*  ✅  ║\n"
        "╚══════════════════════════════╝\n\n"
        "🙏 *Thank you for your purchase!*\n"
        "We hope you enjoy your premium access.\n\n"
        "📌 *Note:* Please keep this receipt safe.\n"
        "It serves as proof of your purchase.\n"
        "──────────────────────────────\n"
        f"💬 *Support:* {OWNER_USERNAME}\n"
        f"📢 *Channel:* {CHANNEL_LINK}\n"
        f"👥 *Group:* {GROUP_LINK}\n"
        "──────────────────────────────\n\n"
        "_This is a system-generated receipt._\n"
        "_No signature required._ 🏴‍☠️"
    )
    return receipt


# ============ KEYBOARDS ============
def main_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🎟️ Generate Key", "callback_data": "menu_genkey"},
                {"text": "📋 Key List", "callback_data": "menu_keylist"},
            ],
            [
                {"text": "➕ Grant Access", "callback_data": "menu_add"},
                {"text": "📊 Active Members", "callback_data": "menu_list"},
            ],
            [
                {"text": "📢 Broadcast", "callback_data": "menu_broadcast"},
                {"text": "👑 Admins", "callback_data": "menu_admins"},
            ],
            [
                {"text": "🧾 Receipts", "callback_data": "menu_receipts"},
                {"text": "🔍 Find Receipt", "callback_data": "menu_find_receipt"},
            ],
            [
                {"text": "🏴‍☠️ Join Channel", "url": CHANNEL_LINK},
                {"text": "💬 Group Chat", "url": GROUP_LINK},
            ],
            [{"text": "❓ Help", "callback_data": "menu_help"}],
        ]
    }


def user_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🎟️ Redeem Key", "callback_data": "user_redeem"}],
            [{"text": "🔄 My Status", "callback_data": "user_status"}],
            [{"text": "🧾 My Receipts", "callback_data": "user_receipts"}],
            [
                {"text": "🏴‍☠️ Join Channel", "url": CHANNEL_LINK},
                {"text": "💬 Group Chat", "url": GROUP_LINK},
            ],
        ]
    }


user_states = {}


# ============ SCREENS ============
def show_main_menu(chat_id, user_id, message_id=None):
    text = (
        "🏴‍☠️ *Welcome aboard, Captain!* ⚓\n\n"
        f"I am your *Access Bot* for *{CHANNEL_NAME}*.\n"
        "Manage members with elegance and power. 🎯\n\n"
        "────────────────────\n"
        "📋 *Admin Menu:*\n"
        "────────────────────"
        + PROMO_SHORT
    )
    kb = main_menu_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, keyboard=kb)
    else:
        send_message(chat_id, text, keyboard=kb)


def show_user_menu(chat_id, user_id, message_id=None):
    text = (
        "🏴‍☠️ *Welcome to THE PIRATE'S CLOUD!* ⚓\n\n"
        "Redeem your access key to join our premium channel. 🎟️\n\n"
        "────────────────────\n"
        "🎟️ *How it works:*\n"
        "1️⃣ Click *Redeem Key* below\n"
        "2️⃣ Send your access key\n"
        "3️⃣ Get your receipt + private channel link instantly!\n"
        "────────────────────"
        + PROMO_FULL
    )
    kb = user_menu_keyboard()
    if message_id:
        edit_message(chat_id, message_id, text, keyboard=kb)
    else:
        send_message(chat_id, text, keyboard=kb)


def show_help(chat_id, user_id, message_id=None):
    text = (
        "❓ *Help & Commands Guide*\n\n"
        "────────────────────\n"
        "🎟️ `/genkey <duration> <price>` — Generate key with price\n"
        "📋 `/keys` — View all keys\n"
        "➕ `/add` — Grant access manually\n"
        "➖ `/remove <id>` — Revoke access\n"
        "📊 `/list` — Active members\n"
        "🔍 `/check <id>` — Check member\n"
        "📢 `/broadcast` — Broadcast\n"
        "👑 `/admins` — Manage admins\n"
        "🧾 `/receipt <receipt_no>` — Find a receipt\n"
        "🎟️ `/redeem <key>` — Redeem key\n"
        "────────────────────\n\n"
        "⏱️ *Duration:* `2d 5h`, `3h`, `1d 12h`\n"
        "💰 *Price:* `4.99`, `10`, `0` (for free)"
        + PROMO_SHORT
    )
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "menu_main"}]]}
    if message_id:
        edit_message(chat_id, message_id, text, keyboard=kb)
    else:
        send_message(chat_id, text, keyboard=kb)


def show_admins_menu(chat_id, user_id, message_id=None):
    if not is_owner(user_id):
        send_message(chat_id, "🚫 *Access Denied*\n\nOnly Owner can manage admins.")
        return
    text = (
        "👑 *Admin Management*\n\n"
        "➕ Add Admin\n➖ Remove Admin\n📋 List Admins\n\n"
        f"👤 Owner: {OWNER_USERNAME}"
        + PROMO_SHORT
    )
    kb = {
        "inline_keyboard": [
            [
                {"text": "➕ Add Admin", "callback_data": "admin_add"},
                {"text": "➖ Remove Admin", "callback_data": "admin_remove"},
            ],
            [{"text": "📋 List Admins", "callback_data": "admin_list"}],
            [{"text": "🔙 Back", "callback_data": "menu_main"}],
        ]
    }
    if message_id:
        edit_message(chat_id, message_id, text, keyboard=kb)
    else:
        send_message(chat_id, text, keyboard=kb)


# ============ USER COMMANDS ============
def cmd_start(chat_id, user_id):
    if is_admin(user_id):
        show_main_menu(chat_id, user_id)
    else:
        show_user_menu(chat_id, user_id)


def user_redeem_start(chat_id, user_id):
    user_states[user_id] = {"step": "waiting_key"}
    send_message(chat_id,
        "🎟️ *Redeem Your Key*\n\n"
        "Send your access key.\nFormat: `PIRATE-XXXX-XXXX-XXXX`\n\n"
        "🚫 /cancel"
    )


def user_redeem_key(chat_id, user_id, text):
    user_states.pop(user_id, None)
    key_code = text.strip().upper()

    key = get_key(key_code)
    if not key:
        send_message(chat_id, "❌ *Invalid Key*\n\nThis key does not exist." + PROMO_SHORT)
        return
    if key["status"] == "redeemed":
        send_message(chat_id, "❌ *Key Already Used*\n\nEach key works once." + PROMO_SHORT)
        return

    existing = get_access(user_id)
    if existing:
        remaining = existing["expires_at"] - datetime.now()
        if remaining.total_seconds() > 0:
            send_message(chat_id,
                f"ℹ️ *You Already Have Access*\n\n"
                f"⏳ Remaining: {format_duration(remaining)}\n"
                f"📅 Expires: `{existing['expires_at'].strftime('%d %b %Y, %I:%M %p')}`\n\n"
                f"Your key was *not* used. Save it for later!"
                + PROMO_SHORT
            )
            return

    username, display = get_user_identity(user_id)
    if username == str(user_id):
        r = api_call("getChat", {"chat_id": user_id})
        if r.get("ok"):
            u = r["result"]
            username = u.get("username") or str(user_id)
            display = u.get("first_name", "")
            if u.get("last_name"):
                display = f"{display} {u['last_name']}".strip()

    unban_chat_member(user_id)
    time.sleep(0.5)

    link_resp = create_invite_link(name=f"Access - {display}")
    if not link_resp.get("ok"):
        err = link_resp.get("description", "Unknown error")
        send_message(chat_id,
            f"❌ *Failed to Create Invite Link*\n\n"
            f"Error: `{err}`\n\n"
            f"Please contact admin. Bot needs *Invite Users* permission."
        )
        return

    invite_link = link_resp["result"]["invite_link"]

    duration_seconds = key["duration_seconds"]
    expires_at = datetime.now() + timedelta(seconds=duration_seconds)
    price_usd = key.get("price_usd", 0.0)

    add_access(user_id, username, display, expires_at, key["created_by"])
    redeem_key(key_code, user_id)
    log_history(user_id, username, "REDEEM", key["duration"])

    # Create receipt
    receipt_no = create_receipt(
        user_id, username, display, key_code, key["duration"],
        price_usd, key["created_by"], expires_at
    )

    # Send congratulations
    send_message(chat_id,
        f"🎉 *Congratulations, {display}!* 🎊\n\n"
        f"Your access key has been redeemed! 🏴‍☠️\n\n"
        f"────────────────────\n"
        f"🎟️ *Key:* `{key_code}`\n"
        f"⏱️ *Duration:* {key['duration']}\n"
        f"💰 *Amount Paid:* {'$' + format(price_usd, '.2f') if price_usd > 0 else 'FREE / GIFT'}\n"
        f"📅 *Valid Until:* `{expires_at.strftime('%d %b %Y, %I:%M %p')}`\n"
        f"────────────────────\n\n"
        f"🧾 *Your billing receipt is below* 👇"
    )

    # Send the professional receipt
    receipt_text = build_receipt_text(
        receipt_no, display, username, user_id, key_code,
        key["duration"], price_usd, expires_at, invite_link
    )
    send_message(chat_id, receipt_text)

    # Notify admins
    for admin_id in ADMIN_IDS:
        send_message(admin_id,
            f"🎟️ *Key Redeemed*\n\n"
            f"👤 {user_mention(user_id, display)}\n"
            f"🔗 @{username}\n"
            f"🆔 `{user_id}`\n"
            f"🎟️ `{key_code}`\n"
            f"⏱️ {key['duration']}\n"
            f"💰 {'$' + format(price_usd, '.2f') if price_usd > 0 else 'FREE'}\n"
            f"🧾 `{receipt_no}`\n"
            f"📅 `{expires_at.strftime('%d %b %Y, %I:%M %p')}`"
            + PROMO_SHORT
        )


def user_status(chat_id, user_id):
    info = get_access(user_id)
    if not info:
        send_message(chat_id, "ℹ️ *No Active Access*\n\nRedeem a key to get access." + PROMO_SHORT)
        return
    remaining = info["expires_at"] - datetime.now()
    if remaining.total_seconds() <= 0:
        send_message(chat_id, "⌛ *Access Expired*" + PROMO_SHORT)
        return
    send_message(chat_id,
        f"✅ *Your Access Status*\n\n"
        f"👤 {user_mention(user_id, info['display_name'])}\n"
        f"⏳ *Remaining:* {format_duration(remaining)}\n"
        f"📅 *Expires:* `{info['expires_at'].strftime('%d %b %Y, %I:%M %p')}`"
        + PROMO_SHORT
    )


def user_receipts(chat_id, user_id):
    rows = db_fetchall(
        "SELECT receipt_no, key_code, duration, price_usd, issued_at, expires_at "
        "FROM receipts WHERE user_id = ? ORDER BY issued_at DESC LIMIT 10",
        (user_id,)
    )
    if not rows:
        send_message(chat_id, "🧾 *No Receipts Found*\n\nYou have no purchase history yet." + PROMO_SHORT)
        return

    lines = ["🧾 *Your Receipt History*\n────────────────────"]
    for r in rows:
        receipt_no, key_code, duration, price_usd, issued_at, expires_at = r
        issued = datetime.fromisoformat(issued_at)
        price_str = f"${price_usd:.2f}" if price_usd and price_usd > 0 else "FREE"
        lines.append(
            f"📄 `{receipt_no}`\n"
            f"   🎟️ `{key_code}`\n"
            f"   ⏱️ {duration} • 💰 {price_str}\n"
            f"   📅 {issued.strftime('%d %b %Y')}\n"
        )
    lines.append("────────────────────")
    lines.append("💡 Use `/receipt <receipt_no>` to view full receipt.")
    send_message(chat_id, "\n".join(lines) + PROMO_SHORT)


# ============ ADMIN — KEY GENERATION ============
def cmd_genkey_start(chat_id, user_id):
    if not is_admin(user_id):
        return
    user_states[user_id] = {"step": "waiting_key_duration"}
    send_message(chat_id,
        "🎟️ *Generate Access Key*\n\n"
        "Send duration and price separated by space:\n\n"
        "📌 *Format:* `<duration> <price>`\n"
        "📌 *Examples:*\n"
        "• `7d 4.99` → 7 days for $4.99\n"
        "• `30d 15` → 30 days for $15.00\n"
        "• `1d 0` → 1 day for FREE\n"
        "• `12h 2.50` → 12 hours for $2.50\n\n"
        "🚫 /cancel"
    )


def cmd_genkey_duration(chat_id, user_id, text):
    user_states.pop(user_id, None)
    parts = text.strip().split()
    if len(parts) < 1:
        send_message(chat_id, "❌ Invalid format. Use: `7d 4.99`")
        return

    td = parse_duration(parts[0])
    if not td:
        send_message(chat_id, "❌ Invalid duration. Use: `7d`, `12h` etc.")
        return

    price_usd = 0.0
    if len(parts) >= 2:
        try:
            price_usd = float(parts[1].replace("$", ""))
            if price_usd < 0:
                price_usd = 0.0
        except ValueError:
            send_message(chat_id, "❌ Invalid price. Use numbers like: `4.99` or `0`")
            return

    duration_text = format_duration(td)
    duration_seconds = int(td.total_seconds())
    key_code = create_key(duration_text, duration_seconds, user_id, price_usd)

    price_str = f"${price_usd:.2f}" if price_usd > 0 else "FREE / GIFT"

    send_message(chat_id,
        f"🎟️ *Access Key Generated!*\n\n"
        f"────────────────────\n"
        f"`{key_code}`\n"
        f"────────────────────\n\n"
        f"⏱️ Duration: {duration_text}\n"
        f"💰 Price: {price_str}\n\n"
        f"💡 Share with buyer. They redeem via:\n"
        f"`/redeem {key_code}`\n\n"
        f"🧾 Receipt will be auto-generated on redeem."
        + PROMO_SHORT
    )


def cmd_keys_list(chat_id, user_id, args=None):
    if not is_admin(user_id):
        return
    status_filter = args[0].lower() if args else None

    if status_filter == "active":
        rows = get_all_keys("active")
        title = "🎟️ *Active Keys*"
    elif status_filter == "redeemed":
        rows = get_all_keys("redeemed")
        title = "✅ *Redeemed Keys*"
    else:
        rows = get_all_keys()
        title = "🎟️ *All Keys*"

    if not rows:
        send_message(chat_id, f"{title}\n\n_No keys found._" + PROMO_SHORT)
        return

    lines = [f"{title} — {len(rows)}\n────────────────────"]
    for r in rows[:30]:
        key_code, duration, dur_sec, price_usd, created_at, redeemed_by, status = r
        icon = "🟢" if status == "active" else "🔴"
        price_str = f"${price_usd:.2f}" if price_usd and price_usd > 0 else "FREE"
        lines.append(
            f"{icon} `{key_code}`\n"
            f"   ⏱️ {duration} • 💰 {price_str} • {'Used' if status == 'redeemed' else 'Available'}"
        )
    if len(rows) > 30:
        lines.append(f"\n_...and {len(rows) - 30} more._")
    lines.append("\n💡 Filter: `/keys active` or `/keys redeemed`")
    send_message(chat_id, "\n".join(lines) + PROMO_SHORT)


# ============ ADMIN — MANUAL ADD / REMOVE ============
def cmd_add_start(chat_id, user_id):
    if not is_admin(user_id):
        return
    user_states[user_id] = {"step": "waiting_user_id"}
    send_message(chat_id, "➕ *Step 1/3:* Send member's User ID.\n\n🚫 /cancel")


def cmd_add_user_id(chat_id, user_id, text):
    text = text.strip()
    if not text.lstrip("-").isdigit():
        send_message(chat_id, "❌ Valid numeric User ID required.")
        return
    user_states[user_id] = {"step": "waiting_duration", "target": int(text)}
    send_message(chat_id,
        "⏱️ *Step 2/3:* Duration? `2d 5h`, `3h`\n\n"
        "🚫 /cancel"
    )


def cmd_add_duration(chat_id, user_id, text):
    td = parse_duration(text.strip())
    if not td:
        send_message(chat_id, "❌ Invalid format.")
        return
    user_states[user_id]["duration"] = format_duration(td)
    user_states[user_id]["duration_seconds"] = int(td.total_seconds())
    user_states[user_id]["step"] = "waiting_add_price"
    send_message(chat_id,
        "💰 *Step 3/3:* Price in USD?\n\n"
        "Examples: `4.99`, `15`, `0` (for free/gift)\n\n"
        "🚫 /cancel"
    )


def cmd_add_price(chat_id, user_id, text):
    text = text.strip().replace("$", "")
    try:
        price_usd = float(text)
        if price_usd < 0:
            price_usd = 0.0
    except ValueError:
        send_message(chat_id, "❌ Invalid price. Use numbers like: `4.99` or `0`")
        return

    state = user_states[user_id]
    target = state["target"]
    duration_text = state["duration"]
    duration_seconds = state["duration_seconds"]

    td = timedelta(seconds=duration_seconds)
    expires_at = datetime.now() + td

    unban_chat_member(target)
    time.sleep(0.5)

    username, display = get_user_identity(target)
    add_access(target, username, display, expires_at, user_id)
    log_history(target, username, "ADD", duration_text)

    # Create receipt for manual add too
    receipt_no = create_receipt(
        target, username, display, "MANUAL-ADD", duration_text,
        price_usd, user_id, expires_at
    )

    link_resp = create_invite_link(name=f"Access - {display}")
    invite_link = link_resp.get("result", {}).get("invite_link") if link_resp.get("ok") else None

    price_str = f"${price_usd:.2f}" if price_usd > 0 else "FREE / GIFT"

    send_message(chat_id,
        f"✅ *Access Granted!*\n\n"
        f"👤 {user_mention(target, display)}\n"
        f"🆔 `{target}`\n"
        f"⏱️ {duration_text}\n"
        f"💰 {price_str}\n"
        f"📅 `{expires_at.strftime('%d %b %Y, %I:%M %p')}`\n"
        f"🧾 `{receipt_no}`"
        + PROMO_SHORT
    )

    if invite_link:
        # Send receipt to user
        receipt_text = build_receipt_text(
            receipt_no, display, username, target, "MANUAL-ADD",
            duration_text, price_usd, expires_at, invite_link
        )
        send_message(target, receipt_text)

    user_states.pop(user_id, None)


def cmd_remove(chat_id, user_id, args):
    if not is_admin(user_id):
        return
    if not args:
        send_message(chat_id, "ℹ️ *Usage:* `/remove <user_id>`")
        return
    try:
        target = int(args[0])
    except ValueError:
        send_message(chat_id, "❌ Provide a valid numeric User ID.")
        return

    info = get_access(target)
    if not info:
        send_message(chat_id, f"ℹ️ No active access for `{target}`.")
        return

    kicked = kick_user(target)
    remove_access(target)
    log_history(target, info["username"], "REMOVE", "manual")

    if kicked:
        send_message(chat_id,
            f"✅ *Access Revoked*\n\n"
            f"👤 {user_mention(target, info['display_name'])}\n"
            f"🆔 `{target}`\n"
            f"🚫 Member removed from channel."
            + PROMO_SHORT
        )
        send_message(target,
            f"👋 *Dear {info['display_name']},*\n\n"
            f"Your access to *{CHANNEL_NAME}* has ended. ⌛\n\n"
            f"We hope you enjoyed your time with us! 🏴‍☠️\n\n"
            f"────────────────────\n"
            f"🌟 *Want to continue?*\n\n"
            f"Contact our admin for a new access key.\n"
            f"Once you have it, simply send:\n"
            f"`/redeem YOUR-KEY`\n\n"
            f"You'll get a fresh receipt + invite link instantly! 🎟️\n"
            f"────────────────────\n\n"
            f"🔗 {CHANNEL_LINK}\n"
            f"💬 {GROUP_LINK}\n\n"
            f"We'd love to welcome you back! 💞"
            + PROMO_FULL
        )
    else:
        send_message(chat_id, "⚠️ Removed from DB, but action failed. Check *Ban Users* permission.")


def cmd_list(chat_id, user_id):
    if not is_admin(user_id):
        return
    rows = get_all_active()
    if not rows:
        send_message(chat_id, "📭 *No Active Members*" + PROMO_SHORT)
        return
    now = datetime.now()
    lines = [f"📊 *Active Members* — {len(rows)}\n────────────────────"]
    for uid, uname, display, exp_str in rows:
        exp = datetime.fromisoformat(exp_str)
        remaining = exp - now
        lines.append(f"👤 {user_mention(uid, display or uname or str(uid))}\n   🆔 `{uid}` • ⏳ {format_duration(remaining)}")
    send_message(chat_id, "\n\n".join(lines) + PROMO_SHORT)


def cmd_check(chat_id, user_id, args):
    if not is_admin(user_id):
        return
    if not args:
        send_message(chat_id, "ℹ️ `/check <user_id>`")
        return
    try:
        target = int(args[0])
    except ValueError:
        send_message(chat_id, "❌ Valid User ID required.")
        return
    info = get_access(target)
    if not info:
        send_message(chat_id, f"ℹ️ No access for `{target}`.")
        return
    remaining = info["expires_at"] - datetime.now()
    if remaining.total_seconds() <= 0:
        send_message(chat_id, "⌛ *Expired*")
        return
    send_message(chat_id,
        f"🔍 *Member Details*\n\n"
        f"👤 {user_mention(target, info['display_name'])}\n"
        f"🆔 `{target}`\n⏳ {format_duration(remaining)}\n"
        f"📅 `{info['expires_at'].strftime('%d %b %Y, %I:%M %p')}`"
        + PROMO_SHORT
    )


def cmd_cancel(chat_id, user_id):
    user_states.pop(user_id, None)
    send_message(chat_id, "✅ *Cancelled*")


# ============ RECEIPT COMMANDS ============
def cmd_find_receipt_start(chat_id, user_id):
    if not is_admin(user_id):
        return
    user_states[user_id] = {"step": "waiting_receipt_no"}
    send_message(chat_id, "🔍 *Find Receipt*\n\nSend the receipt number.\nFormat: `TPC-YYYYMMDD-XXXXXX`\n\n🚫 /cancel")


def cmd_find_receipt(chat_id, user_id, text):
    user_states.pop(user_id, None)
    receipt_no = text.strip().upper()
    receipt = get_receipt(receipt_no)
    if not receipt:
        send_message(chat_id, f"❌ *Receipt Not Found*\n\nNo receipt with number `{receipt_no}`." + PROMO_SHORT)
        return

    price_str = f"${receipt['price_usd']:.2f}" if receipt['price_usd'] and receipt['price_usd'] > 0 else "FREE / GIFT"
    send_message(chat_id,
        f"🧾 *Receipt Details*\n\n"
        f"📄 *Receipt No:* `{receipt['receipt_no']}`\n"
        f"👤 *User:* {user_mention(receipt['user_id'], receipt['display_name'])}\n"
        f"🆔 `{receipt['user_id']}`\n"
        f"🔗 @{receipt['username']}\n"
        f"🎟️ *Key:* `{receipt['key_code']}`\n"
        f"⏱️ *Duration:* {receipt['duration']}\n"
        f"💰 *Amount:* {price_str}\n"
        f"📅 *Issued:* `{receipt['issued_at'].strftime('%d %b %Y, %I:%M %p')}`\n"
        f"⌛ *Expires:* `{receipt['expires_at'].strftime('%d %b %Y, %I:%M %p')}`"
        + PROMO_SHORT
    )


def cmd_receipts_list(chat_id, user_id):
    if not is_admin(user_id):
        return
    rows = db_fetchall(
        "SELECT receipt_no, user_id, display_name, key_code, duration, price_usd, issued_at "
        "FROM receipts ORDER BY issued_at DESC LIMIT 20"
    )
    if not rows:
        send_message(chat_id, "🧾 *No Receipts Yet*" + PROMO_SHORT)
        return

    lines = ["🧾 *Recent Receipts*\n────────────────────"]
    for r in rows:
        receipt_no, uid, display, key_code, duration, price_usd, issued_at = r
        issued = datetime.fromisoformat(issued_at)
        price_str = f"${price_usd:.2f}" if price_usd and price_usd > 0 else "FREE"
        lines.append(
            f"📄 `{receipt_no}`\n"
            f"   👤 {display or uid}\n"
            f"   🎟️ `{key_code}` • ⏱️ {duration}\n"
            f"   💰 {price_str} • 📅 {issued.strftime('%d %b %Y')}"
        )
    lines.append("\n💡 Use `/receipt <no>` for full details.")
    send_message(chat_id, "\n".join(lines) + PROMO_SHORT)


# ============ BROADCAST ============
def cmd_broadcast_start(chat_id, user_id):
    if not is_admin(user_id):
        return
    user_states[user_id] = {"step": "waiting_broadcast"}
    send_message(chat_id, "📢 *Broadcast Mode*\n\nSend your message.\n\n🚫 /cancel")


def cmd_broadcast_send(chat_id, user_id, text):
    user_states.pop(user_id, None)
    rows = get_all_active()
    if not rows:
        send_message(chat_id, "📭 No recipients.")
        return
    send_message(chat_id, f"📢 Broadcasting to {len(rows)} members...")
    final_text = text + PROMO_SHORT
    success = failed = 0
    for uid, uname, display, exp_str in rows:
        r = send_message(uid, final_text)
        if r.get("ok"):
            success += 1
        else:
            failed += 1
        time.sleep(0.05)
    send_message(chat_id, f"✅ *Done!*\n📨 {success} sent, ❌ {failed} failed" + PROMO_SHORT)


# ============ ADMIN MANAGEMENT ============
def cmd_admins(chat_id, user_id):
    if is_admin(user_id):
        show_admins_menu(chat_id, user_id)


def cmd_admin_add_start(chat_id, user_id):
    if not is_owner(user_id):
        return
    user_states[user_id] = {"step": "waiting_admin_id"}
    send_message(chat_id, "👑 Send new admin's User ID.\n\n🚫 /cancel")


def cmd_admin_add_id(chat_id, user_id, text):
    text = text.strip()
    if not text.lstrip("-").isdigit():
        send_message(chat_id, "❌ Invalid.")
        return
    target = int(text)
    if target == OWNER_ID:
        send_message(chat_id, "ℹ️ Already Owner.")
        user_states.pop(user_id, None)
        return
    username, display = get_user_identity(target)
    add_admin_db(target, username, user_id)
    send_message(chat_id, f"✅ Admin added: {user_mention(target, display)}" + PROMO_SHORT)
    send_message(target, f"👑 *You are now Admin!*\n\nSend /start" + PROMO_SHORT)
    user_states.pop(user_id, None)


def cmd_admin_remove_start(chat_id, user_id):
    if not is_owner(user_id):
        return
    user_states[user_id] = {"step": "waiting_admin_remove_id"}
    send_message(chat_id, "👑 Send admin User ID to remove.\n\n🚫 /cancel")


def cmd_admin_remove_id(chat_id, user_id, text):
    text = text.strip()
    if not text.lstrip("-").isdigit():
        send_message(chat_id, "❌ Invalid.")
        return
    target = int(text)
    if target == OWNER_ID:
        send_message(chat_id, "⚠️ Cannot remove Owner.")
        user_states.pop(user_id, None)
        return
    if not db_fetchone("SELECT 1 FROM admins WHERE user_id = ?", (target,)):
        send_message(chat_id, "ℹ️ Not an admin.")
        user_states.pop(user_id, None)
        return
    remove_admin_db(target)
    send_message(chat_id, f"✅ Admin `{target}` removed." + PROMO_SHORT)
    user_states.pop(user_id, None)


def cmd_admin_list(chat_id, user_id):
    if not is_admin(user_id):
        return
    rows = get_all_admins_db()
    lines = [f"👑 *Admins*\n\n👤 {user_mention(OWNER_ID, 'Owner')} — `{OWNER_ID}`"]
    for i, (uid, uname) in enumerate(rows, 1):
        lines.append(f"{i}. {user_mention(uid, uname or str(uid))} — `{uid}`")
    send_message(chat_id, "\n".join(lines) + PROMO_SHORT)


# ============ CALLBACK HANDLER ============
def handle_callback(cb):
    cb_id = cb.get("id")
    user_id = cb.get("from", {}).get("id")
    chat_id = cb.get("message", {}).get("chat", {}).get("id")
    message_id = cb.get("message", {}).get("message_id")
    data = cb.get("data", "")

    # User callbacks
    if data == "user_redeem":
        answer_callback(cb_id)
        user_redeem_start(chat_id, user_id)
        return
    if data == "user_status":
        answer_callback(cb_id)
        user_status(chat_id, user_id)
        return
    if data == "user_receipts":
        answer_callback(cb_id)
        user_receipts(chat_id, user_id)
        return

    # Admin-only callbacks
    if not is_admin(user_id):
        answer_callback(cb_id, "Denied.", show_alert=True)
        return
    answer_callback(cb_id)

    if data == "menu_main":
        show_main_menu(chat_id, user_id, message_id)
    elif data == "menu_help":
        show_help(chat_id, user_id, message_id)
    elif data == "menu_genkey":
        cmd_genkey_start(chat_id, user_id)
    elif data == "menu_keylist":
        cmd_keys_list(chat_id, user_id)
    elif data == "menu_add":
        cmd_add_start(chat_id, user_id)
    elif data == "menu_list":
        cmd_list(chat_id, user_id)
    elif data == "menu_broadcast":
        cmd_broadcast_start(chat_id, user_id)
    elif data == "menu_admins":
        show_admins_menu(chat_id, user_id, message_id)
    elif data == "menu_receipts":
        cmd_receipts_list(chat_id, user_id)
    elif data == "menu_find_receipt":
        cmd_find_receipt_start(chat_id, user_id)
    elif data == "admin_add":
        cmd_admin_add_start(chat_id, user_id)
    elif data == "admin_remove":
        cmd_admin_remove_start(chat_id, user_id)
    elif data == "admin_list":
        cmd_admin_list(chat_id, user_id)


# ============ MESSAGE ROUTER ============
def handle_message(msg):
    chat = msg.get("chat", {})
    from_user = msg.get("from", {})
    chat_id = chat.get("id")
    user_id = from_user.get("id")
    text = msg.get("text", "")

    if not text or not user_id:
        return

    state = user_states.get(user_id)
    if state:
        if text.startswith("/cancel"):
            cmd_cancel(chat_id, user_id)
            return
        step = state["step"]
        if step == "waiting_user_id":
            cmd_add_user_id(chat_id, user_id, text); return
        if step == "waiting_duration":
            cmd_add_duration(chat_id, user_id, text); return
        if step == "waiting_add_price":
            cmd_add_price(chat_id, user_id, text); return
        if step == "waiting_broadcast":
            cmd_broadcast_send(chat_id, user_id, text); return
        if step == "waiting_admin_id":
            cmd_admin_add_id(chat_id, user_id, text); return
        if step == "waiting_admin_remove_id":
            cmd_admin_remove_id(chat_id, user_id, text); return
        if step == "waiting_key":
            user_redeem_key(chat_id, user_id, text); return
        if step == "waiting_key_duration":
            cmd_genkey_duration(chat_id, user_id, text); return
        if step == "waiting_receipt_no":
            cmd_find_receipt(chat_id, user_id, text); return

    if text.startswith("/start") or text.startswith("/help"):
        cmd_start(chat_id, user_id)
    elif text.startswith("/redeem"):
        args = text.split(maxsplit=1)
        if len(args) > 1:
            user_redeem_key(chat_id, user_id, args[1])
        else:
            user_redeem_start(chat_id, user_id)
    elif text.startswith("/genkey"):
        cmd_genkey_start(chat_id, user_id)
    elif text.startswith("/keys"):
        cmd_keys_list(chat_id, user_id, text.split()[1:])
    elif text.startswith("/add"):
        cmd_add_start(chat_id, user_id)
    elif text.startswith("/remove"):
        cmd_remove(chat_id, user_id, text.split()[1:])
    elif text.startswith("/list"):
        cmd_list(chat_id, user_id)
    elif text.startswith("/check"):
        cmd_check(chat_id, user_id, text.split()[1:])
    elif text.startswith("/broadcast"):
        cmd_broadcast_start(chat_id, user_id)
    elif text.startswith("/admins"):
        cmd_admins(chat_id, user_id)
    elif text.startswith("/receipt"):
        args = text.split(maxsplit=1)
        if len(args) > 1 and is_admin(user_id):
            cmd_find_receipt(chat_id, user_id, args[1])
        else:
            cmd_find_receipt_start(chat_id, user_id)
    elif text.startswith("/cancel"):
        cmd_cancel(chat_id, user_id)


# ============ POLLING ============
def polling_loop():
    print("[*] Bot polling started...")
    offset = None
    while True:
        try:
            resp = get_updates(offset=offset, timeout=25)
            if not resp.get("ok"):
                print(f"[!] getUpdates error: {resp.get('description')}")
                time.sleep(5)
                continue
            for upd in resp.get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    try:
                        handle_message(upd["message"])
                    except Exception as e:
                        print(f"[!] Handler error: {e}")
                elif "callback_query" in upd:
                    try:
                        handle_callback(upd["callback_query"])
                    except Exception as e:
                        print(f"[!] Callback error: {e}")
        except Exception as e:
            print(f"[!] Polling error: {e}")
            time.sleep(5)


# ============ AUTO KICK ============
def auto_kick_loop():
    print("[*] Auto-kick worker started (every 60s).")
    while True:
        try:
            expired = get_all_expired()
            for user_id, username, display, exp_str in expired:
                kicked = kick_user(user_id)
                remove_access(user_id)
                log_history(user_id, username, "AUTO_KICK", "expired")
                status = "✅ Kicked" if kicked else "⚠️ Failed"
                print(f"[+] Auto-kick {user_id} ({display}): {status}")

                for admin_id in ADMIN_IDS:
                    send_message(admin_id,
                        f"⌛ *Access Expired*\n\n"
                        f"👤 {user_mention(user_id, display or username or str(user_id))}\n"
                        f"🆔 `{user_id}`\n{status}"
                        + PROMO_SHORT
                    )

                send_message(user_id,
                    f"👋 *Dear {display or 'Valued Member'},*\n\n"
                    f"Your access to *{CHANNEL_NAME}* has *expired*. ⌛\n\n"
                    f"We truly hope you enjoyed your time with us! 🏴‍☠️\n\n"
                    f"────────────────────\n"
                    f"🌟 *Want to continue?*\n\n"
                    f"Getting back in is easy:\n"
                    f"1️⃣ Contact our admin for a new access key\n"
                    f"2️⃣ Redeem it here with `/redeem`\n"
                    f"3️⃣ You'll receive a fresh receipt + invite link instantly\n"
                    f"────────────────────\n\n"
                    f"🔗 *Channel:* {CHANNEL_LINK}\n"
                    f"💬 *Group Chat:* {GROUP_LINK}\n\n"
                    f"We'd love to welcome you back! 💞"
                    + PROMO_FULL
                )
        except Exception as e:
            print(f"[!] Auto-kick error: {e}")
        time.sleep(POLL_INTERVAL)


# ============ MAIN ============
def main():
    threading.Thread(target=run_fake_server, daemon=True).start()

    init_db()

    me = api_call("getMe")
    if not me.get("ok"):
        print(f"[!] Invalid token: {me.get('description')}")
        return
    print(f"[+] Bot connected: @{me['result'].get('username')}")
    print(f"[+] Channel: {CHANNEL_NAME}")
    print(f"[+] Owner ID: {OWNER_ID}")
    print(f"[+] Receipt system: ACTIVE")

    threading.Thread(target=auto_kick_loop, daemon=True).start()

    polling_loop()


if __name__ == "__main__":
    main()