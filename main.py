import asyncio
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta

from flask import Flask
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    FSInputFile,
)

from texts import TEXTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8105745014:AAHqgQunU4gK5fWwi4bFwE1GXuludZpFz3Y")
ADMIN_USERNAME = "kamrancmlv"
ADMIN_ID = 1337915501
STATS_IMAGE_URL = os.getenv("STATS_IMAGE_URL", None)

DB_NAME = "bot_data.db"

# ---------- VIP PLANS (Telegram Stars) ----------
VIP_PLANS = {
    "vip_3d": {"days": 3, "stars": 150, "label": {"tr": "3 Günlük VIP", "en": "3-Day VIP"}},
    "vip_7d": {"days": 7, "stars": 250, "label": {"tr": "1 Haftalık VIP", "en": "1-Week VIP"}},
    "vip_30d": {"days": 30, "stars": 500, "label": {"tr": "1 Aylık VIP", "en": "1-Month VIP"}},
}

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'tr')''')
    c.execute('''CREATE TABLE IF NOT EXISTS matches
                 (match_id TEXT PRIMARY KEY, date TEXT, league TEXT,
                  home TEXT, away TEXT, pred_tr TEXT, pred_en TEXT,
                  category TEXT DEFAULT 'normal',
                  status TEXT DEFAULT 'active',
                  result TEXT DEFAULT 'pending')''')  # pending, win, lose, draw
    c.execute('''CREATE TABLE IF NOT EXISTS support_tickets
                 (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, message TEXT, timestamp TEXT,
                  replied INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vip_users
                 (user_id INTEGER PRIMARY KEY, expires_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, plan TEXT, stars INTEGER,
                  charge_id TEXT, timestamp TEXT)''')
    # Migrate old tables if needed
    try:
        c.execute("ALTER TABLE matches ADD COLUMN category TEXT DEFAULT 'normal'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE matches ADD COLUMN status TEXT DEFAULT 'active'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE matches ADD COLUMN result TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def get_user_lang(user_id: int) -> str:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "tr"

def set_user_lang(user_id: int, lang: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    conn.close()

def get_matches_by_category(category: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """SELECT match_id, date, league, home, away, pred_tr, pred_en, result
           FROM matches
           WHERE category = ? AND status = 'active'
           ORDER BY date""",
        (category,)
    )
    rows = c.fetchall()
    conn.close()

    matches = {}
    for row in rows:
        match_id, date, league, home, away, pred_tr, pred_en, result = row
        matches[match_id] = {
            "date": date,
            "league": league,
            "home": home,
            "away": away,
            "prediction": {"tr": pred_tr, "en": pred_en},
            "result": result,
        }
    return matches

def get_all_matches(include_history=True):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if include_history:
        c.execute(
            """SELECT match_id, date, league, home, away, pred_tr, pred_en,
                      category, status, result
               FROM matches ORDER BY date"""
        )
    else:
        c.execute(
            """SELECT match_id, date, league, home, away, pred_tr, pred_en,
                      category, status, result
               FROM matches
               WHERE status = 'active'
               ORDER BY date"""
        )

    rows = c.fetchall()
    conn.close()

    matches = {}
    for row in rows:
        match_id, date, league, home, away, pred_tr, pred_en, category, status, result = row
        matches[match_id] = {
            "date": date,
            "league": league,
            "home": home,
            "away": away,
            "prediction": {"tr": pred_tr, "en": pred_en},
            "category": category,
            "status": status,
            "result": result,
        }
    return matches

def get_match(match_id: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """SELECT date, league, home, away, pred_tr, pred_en, category, status, result
           FROM matches WHERE match_id = ?""",
        (match_id,)
    )
    row = c.fetchone()
    conn.close()

    if row:
        date, league, home, away, pred_tr, pred_en, category, status, result = row
        return {
            "date": date,
            "league": league,
            "home": home,
            "away": away,
            "prediction": {"tr": pred_tr, "en": pred_en},
            "category": category,
            "status": status,
            "result": result,
        }
    return None

def add_match(match_id, date, league, home, away, pred_tr, pred_en, category='normal', status='active', result='pending'):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO matches
           (match_id, date, league, home, away, pred_tr, pred_en, category, status, result)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (match_id, date, league, home, away, pred_tr, pred_en, category, status, result)
    )
    conn.commit()
    conn.close()

def set_match_status(match_id, status):
    if status not in ("active", "history"):
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE matches SET status = ? WHERE match_id = ?", (status, match_id))
    conn.commit()
    conn.close()

def set_match_result(match_id, result):
    if result not in ("pending", "win", "lose", "draw"):
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE matches SET result = ? WHERE match_id = ?", (result, match_id))
    conn.commit()
    conn.close()

def delete_match(match_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM matches WHERE match_id = ?", (match_id,))
    conn.commit()
    conn.close()

def add_support_ticket(user_id, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO support_tickets (user_id, message, timestamp) VALUES (?,?,?)",
              (user_id, message, timestamp))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

def get_ticket(ticket_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, message FROM support_tickets WHERE ticket_id = ?", (ticket_id,))
    row = c.fetchone()
    conn.close()
    return row

def mark_ticket_replied(ticket_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE support_tickets SET replied = 1 WHERE ticket_id = ?", (ticket_id,))
    conn.commit()
    conn.close()

def get_all_tickets(unreplied_only=False):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if unreplied_only:
        c.execute("SELECT ticket_id, user_id, message, timestamp FROM support_tickets WHERE replied = 0 ORDER BY timestamp")
    else:
        c.execute("SELECT ticket_id, user_id, message, timestamp FROM support_tickets ORDER BY timestamp")
    rows = c.fetchall()
    conn.close()
    return rows

def is_admin(user) -> bool:
    if user.username and user.username.lower() == ADMIN_USERNAME.lower():
        return True
    if user.id == ADMIN_ID:
        return True
    return False

# ---------- VIP MEMBERSHIP ----------
def get_vip_expiry(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT expires_at FROM vip_users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def is_vip(user_id: int) -> bool:
    expires_at = get_vip_expiry(user_id)
    if not expires_at:
        return False
    return datetime.fromisoformat(expires_at) > datetime.now()

def extend_vip(user_id: int, days: int) -> datetime:
    current = get_vip_expiry(user_id)
    now = datetime.now()
    if current:
        current_dt = datetime.fromisoformat(current)
        base = current_dt if current_dt > now else now
    else:
        base = now
    new_expiry = base + timedelta(days=days)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO vip_users (user_id, expires_at) VALUES (?, ?)",
              (user_id, new_expiry.isoformat()))
    conn.commit()
    conn.close()
    return new_expiry

def log_payment(user_id: int, plan: str, stars: int, charge_id: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO payments (user_id, plan, stars, charge_id, timestamp) VALUES (?,?,?,?,?)",
              (user_id, plan, stars, charge_id, timestamp))
    conn.commit()
    conn.close()

# ---------- MATCH INPUT PARSER ----------
def parse_match_info(text: str):
    raw = (text or "").strip()
    raw = raw.lstrip("/").strip()

    date_match = re.search(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{4})\b", raw)
    if not date_match:
        return None

    date = date_match.group(1).replace("/", ".").replace("-", ".")
    rest = (raw[:date_match.start()] + " " + raw[date_match.end():]).strip()
    rest = re.sub(r"^[-–—:|]+\s*", "", rest)

    parts = re.split(r"\s+(?:vs\.?|v\.?|x)\s+|\s*[-–—]\s*", rest, maxsplit=1, flags=re.IGNORECASE)

    if len(parts) != 2:
        return None

    home = parts[0].strip(" -–—|:")
    away = parts[1].strip(" -–—|:")

    if not home or not away:
        return None

    return date, home, away

# ---------- ADMIN KEYBOARDS ----------
def admin_match_list_kb(matches: dict):
    rows = []
    for match_id, m in matches.items():
        status = m.get("status", "active")
        status_icon = "📜" if status == "history" else "🟢"
        result = m.get("result", "pending")
        result_icon = {
            "pending": "⏳",
            "win": "✅",
            "lose": "❌",
            "draw": "➖"
        }.get(result, "⏳")
        category = "VIP" if m.get("category") == "vip" else "Normal"
        label = f"{status_icon} {m['date']} {m['home']} - {m['away']} [{category}] {result_icon}"
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"list_match_{match_id}")
        ])

        if status == "active":
            rows.append([
                InlineKeyboardButton(text="🗑 Sil", callback_data=f"delete_{match_id}"),
                InlineKeyboardButton(text="📜 Keçmişə at", callback_data=f"history_{match_id}")
            ])
        else:
            rows.append([
                InlineKeyboardButton(text="↩️ Aktiv et", callback_data=f"active_{match_id}"),
                InlineKeyboardButton(text="🗑 Sil", callback_data=f"delete_{match_id}")
            ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_list_text():
    return (
        "📋 *Maç idarəsi*\n\n"
        "🟢 Aktiv — istifadəçilərin \"Təxminlər\" bölməsində görünür.\n"
        "📜 Keçmiş — \"Keçmiş\" bölməsində görünür.\n"
        "⏳ Gözləmədə | ✅ Qalib | ❌ Uduzdu | ➖ Heç-heçə\n\n"
        "Maçın üzərinə basaraq detallara baxa bilərsən."
    )

# ---------- FSM STATES ----------
class AddMatchStates(StatesGroup):
    waiting_match_info = State()
    waiting_prediction_stats = State()
    waiting_category = State()

# ---------- BOT & ROUTER ----------
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=storage)
router = Router()

# ---------- KEYBOARDS ----------
def language_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang_tr"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            ]
        ]
    )

def main_menu_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["menu_tips"]), KeyboardButton(text=t["menu_history"])],
            [KeyboardButton(text=t["menu_vip"]), KeyboardButton(text=t["menu_support"]), KeyboardButton(text=t["menu_language"])],
        ],
        resize_keyboard=True,
    )

def tips_inline_kb(matches: dict, category: str, show_delete=False):
    rows = []
    for match_id, m in matches.items():
        label = f"{m['date']} {m['home']} — {m['away']}"
        buttons = [InlineKeyboardButton(text=label, callback_data=f"match_{category}_{match_id}")]
        if show_delete:
            buttons.append(InlineKeyboardButton(text="🗑 Sil", callback_data=f"delete_{match_id}"))
        rows.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def vip_plans_kb(lang: str, show_tips_button=False):
    t = TEXTS[lang]
    rows = []
    if show_tips_button:
        rows.append([InlineKeyboardButton(text=t["vip_tips_button"], callback_data="viptips")])
    for key, plan in VIP_PLANS.items():
        rows.append([InlineKeyboardButton(
            text=f"{plan['label'][lang]} — {plan['stars']} ⭐",
            callback_data=f"buyvip_{key}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def match_detail_text(match_id: str, lang: str, for_admin=False):
    m = get_match(match_id)
    if not m:
        return None

    league_line = f"🏆 {m['league']}\n" if m.get("league") else ""
    status_line = "📜 Keçmiş" if m.get("status") == "history" else "🟢 Aktiv"
    result = m.get("result", "pending")
    result_map = {
        "pending": "⏳ Gözləmədə",
        "win": "✅ Qalib",
        "lose": "❌ Uduzdu",
        "draw": "➖ Heç-heçə"
    }
    result_line = f"📊 Nəticə: {result_map.get(result, '⏳ Gözləmədə')}\n"

    text = (
        f"⚽ *{m['home']} vs {m['away']}*\n"
        f"🗓 {m['date']}\n"
        f"{league_line}"
        f"{status_line}\n"
        f"{result_line}\n"
        f"{m['prediction'][lang]}"
    )
    return text

def category_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["category_normal"]), KeyboardButton(text=t["category_vip"])]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def result_kb(match_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qalib", callback_data=f"setresult_{match_id}_win"),
                InlineKeyboardButton(text="❌ Uduzdu", callback_data=f"setresult_{match_id}_lose"),
            ],
            [
                InlineKeyboardButton(text="➖ Heç-heçə", callback_data=f"setresult_{match_id}_draw"),
                InlineKeyboardButton(text="⏳ Gözləmədə", callback_data=f"setresult_{match_id}_pending"),
            ],
        ]
    )

def _labels(key: str):
    return {TEXTS["tr"][key], TEXTS["en"][key]}

TIPS_LABELS = _labels("menu_tips")
HISTORY_LABELS = _labels("menu_history")
VIP_LABELS = _labels("menu_vip")
SUPPORT_LABELS = _labels("menu_support")
LANGUAGE_LABELS = _labels("menu_language")
CAT_NORMAL_LABELS = _labels("category_normal")
CAT_VIP_LABELS = _labels("category_vip")

# ---------- HANDLERS ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        TEXTS["tr"]["choose_language"],
        reply_markup=language_inline_kb()
    )

@router.callback_query(F.data.startswith("lang_"))
async def process_language(callback: CallbackQuery):
    lang = callback.data.split("_", 1)[1]
    if lang not in TEXTS:
        lang = "tr"
    set_user_lang(callback.from_user.id, lang)
    t = TEXTS[lang]
    name = callback.from_user.first_name or "İstifadəçi"
    await callback.message.edit_text(t["welcome"].format(name=name))
    await callback.message.answer(t["menu_prompt"], reply_markup=main_menu_kb(lang))
    await callback.answer()

@router.message(F.text.in_(LANGUAGE_LABELS))
async def change_language(message: Message):
    await message.answer(
        TEXTS["tr"]["choose_language"],
        reply_markup=language_inline_kb()
    )

@router.message(F.text.in_(TIPS_LABELS))
async def show_tips(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    matches = get_matches_by_category('normal')
    if not matches:
        await message.answer(t["no_matches"])
        return
    await message.answer(t["tips_title"], reply_markup=tips_inline_kb(matches, 'normal'))

@router.message(F.text.in_(VIP_LABELS))
async def show_vip(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]

    if is_vip(user_id):
        expiry = get_vip_expiry(user_id)
        expiry_str = datetime.fromisoformat(expiry).strftime("%d.%m.%Y")
        text = t["vip_active_status"].format(expiry=expiry_str)
    else:
        text = t["vip_intro"]

    await message.answer(
        text,
        parse_mode="MARKDOWN",
        reply_markup=vip_plans_kb(lang, show_tips_button=is_vip(user_id))
    )

@router.callback_query(F.data.startswith("buyvip_"))
async def buy_vip(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    key = callback.data.split("_", 1)[1]
    plan = VIP_PLANS.get(key)
    if not plan:
        await callback.answer(t["plan_not_found"], show_alert=True)
        return

    await callback.answer()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=plan["label"][lang],
        description=t["invoice_description"].format(days=plan["days"]),
        payload=f"vip_{key}_{callback.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["label"][lang], amount=plan["stars"])],
    )

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]

    payment = message.successful_payment
    payload_parts = payment.invoice_payload.split("_")
    key = payload_parts[1] if len(payload_parts) > 1 else None
    plan = VIP_PLANS.get(key)

    if not plan:
        await message.answer(t["payment_error"])
        return

    new_expiry = extend_vip(user_id, plan["days"])
    log_payment(user_id, key, payment.total_amount, payment.telegram_payment_charge_id)

    expiry_str = new_expiry.strftime("%d.%m.%Y")
    await message.answer(
        t["payment_success"].format(plan=plan["label"][lang], expiry=expiry_str)
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            "💰 *Yeni VIP ödənişi!*\n"
            f"İstifadəçi: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"Plan: {plan['label']['tr']}\n"
            f"Stars: {payment.total_amount} ⭐"
        )
    except Exception:
        logger.warning("Admin bildirişi göndərilə bilmədi.")

@router.callback_query(F.data == "viptips")
async def show_vip_tips(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]

    if not is_vip(user_id):
        # Admin may see VIP tips regardless
        if not is_admin(callback.from_user):
            await callback.answer(t["vip_denied"], show_alert=True)
            return

    matches = get_matches_by_category('vip')
    if not matches:
        await callback.message.edit_text(t["no_vip_matches"])
        await callback.answer()
        return

    await callback.message.edit_text(t["vip_tips_title"], reply_markup=tips_inline_kb(matches, 'vip'))
    await callback.answer()

@router.callback_query(F.data.startswith("match_"))
async def show_match(callback: CallbackQuery):
    _, category, match_id = callback.data.split("_", 2)
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]

    if category == "vip" and not is_vip(callback.from_user.id):
        if not is_admin(callback.from_user):
            await callback.answer(t["vip_denied"], show_alert=True)
            return

    text = match_detail_text(match_id, lang)
    if text is None:
        await callback.answer(t["match_not_found"], show_alert=True)
        return
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t["back"], callback_data=f"back_{category}")]]
    )
    await callback.message.edit_text(text, reply_markup=back_kb)
    await callback.answer()

@router.callback_query(F.data == "back_normal")
async def back_to_normal_tips(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    matches = get_matches_by_category('normal')
    if not matches:
        await callback.message.edit_text(t["no_matches"])
        await callback.answer()
        return
    await callback.message.edit_text(t["tips_title"], reply_markup=tips_inline_kb(matches, 'normal'))
    await callback.answer()

@router.callback_query(F.data == "back_vip")
async def back_to_vip_tips(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    if not is_vip(callback.from_user.id) and not is_admin(callback.from_user):
        await callback.answer(t["vip_denied"], show_alert=True)
        return
    matches = get_matches_by_category('vip')
    if not matches:
        await callback.message.edit_text(t["no_vip_matches"])
        await callback.answer()
        return
    await callback.message.edit_text(t["vip_tips_title"], reply_markup=tips_inline_kb(matches, 'vip'))
    await callback.answer()

@router.message(F.text.in_(HISTORY_LABELS))
async def show_history(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]

    all_matches = get_all_matches()
    history_matches = {
        mid: m for mid, m in all_matches.items()
        if m.get("status") == "history"
    }

    if not history_matches:
        await message.answer(t["no_history"])
        return

    lines = []
    for mid, m in history_matches.items():
        result = m.get("result", "pending")
        result_icon = {
            "pending": "⏳",
            "win": "✅",
            "lose": "❌",
            "draw": "➖"
        }.get(result, "⏳")
        lines.append(f"• {m['date']} – {m['home']} vs {m['away']} {result_icon}")

    await message.answer(
        t["history_text"].format(matches="\n".join(lines))
    )

# ---------- SUPPORT ----------
support_mode = {}
# Store forwarded messages to map back to user
forwarded_map = {}  # {forwarded_message_id: user_id}

@router.message(F.text.in_(SUPPORT_LABELS))
async def support_start(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    support_mode[message.from_user.id] = True
    await message.answer(t["support_prompt"])

@router.message(F.text & ~F.text.in_(TIPS_LABELS | HISTORY_LABELS | VIP_LABELS | SUPPORT_LABELS | LANGUAGE_LABELS | CAT_NORMAL_LABELS | CAT_VIP_LABELS) & ~F.text.startswith("/"))
async def handle_support_message(message: Message):
    user_id = message.from_user.id
    if is_admin(message.from_user):
        return
    if support_mode.get(user_id, False):
        # Forward the user's message to admin
        try:
            forwarded = await bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=user_id,
                message_id=message.message_id
            )
            # Store mapping
            forwarded_map[forwarded.message_id] = user_id
            # Also store ticket in DB
            ticket_id = add_support_ticket(user_id, message.text)
            # Notify admin with inline button to see tickets
            await bot.send_message(
                ADMIN_ID,
                f"📩 *Yeni dəstək mesajı!*\n"
                f"İstifadəçi: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"Ticket ID: #{ticket_id}\n"
                f"Mesajı görmək üçün yuxarıdakı yönləndirilmiş mesaja cavab verin.",
                parse_mode="MARKDOWN"
            )
        except Exception as e:
            logger.error(f"Support forward error: {e}")

        lang = get_user_lang(user_id)
        await message.answer(TEXTS[lang]["support_thanks"])
        support_mode[user_id] = False
    else:
        pass

@router.message(F.reply_to_message & F.from_user.id == ADMIN_ID)
async def admin_reply_to_forwarded(message: Message):
    # If admin replies to a forwarded message, send reply to original user
    if not is_admin(message.from_user):
        return

    reply_to = message.reply_to_message
    if not reply_to or reply_to.message_id not in forwarded_map:
        # Maybe it's a reply to the notification, not forwarded msg
        return

    user_id = forwarded_map.get(reply_to.message_id)
    if not user_id:
        return

    # Send reply to user
    try:
        await bot.send_message(
            user_id,
            f"📩 *Dəstək cavabı:*\n\n{message.text}",
            parse_mode="MARKDOWN"
        )
        await message.answer("✅ Cavab istifadəçiyə göndərildi.")
        # Mark ticket as replied
        # Find ticket for this user (latest unreplied)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT ticket_id FROM support_tickets WHERE user_id = ? AND replied = 0 ORDER BY timestamp DESC LIMIT 1", (user_id,))
        row = c.fetchone()
        if row:
            mark_ticket_replied(row[0])
        conn.close()
    except Exception as e:
        await message.answer(f"❌ Göndərmə xətası: {e}")

@router.message(Command("tickets"))
async def list_tickets(message: Message):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return

    tickets = get_all_tickets(unreplied_only=True)
    if not tickets:
        await message.answer("📭 Gözləyən bilet yoxdur.")
        return

    lines = []
    for ticket_id, user_id, msg, ts in tickets:
        lines.append(f"#{ticket_id} | istifadəçi {user_id} | {ts[:16]}\n{msg[:50]}...")
    await message.answer("📋 *Gözləyən biletlər:*\n\n" + "\n\n".join(lines))

# ---------- ADMIN COMMANDS ----------
@router.message(Command("addmatch"))
async def add_match_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return

    await state.set_state(AddMatchStates.waiting_match_info)
    await message.answer(
        "⚽ *Maç məlumatını bu formatda yaz:*\n\n"
        "`04.09.2026 Barcelona - Real Madrid`\n\n"
        "və ya\n"
        "`04.09.2026 Barcelona vs Real Madrid`"
    )

@router.message(AddMatchStates.waiting_match_info, F.text)
async def add_match_info(message: Message, state: FSMContext):
    parsed = parse_match_info(message.text)

    if not parsed:
        await message.answer(
            "❌ Format düzgün deyil. Belə yaz:\n"
            "`04.09.2026 Barcelona - Real Madrid`\n\n"
            "Tarix + ev sahibi + `-` + səfər komandası."
        )
        return

    date, home, away = parsed

    await state.update_data(
        date=date,
        home=home,
        away=away
    )
    await state.set_state(AddMatchStates.waiting_prediction_stats)

    await message.answer(
        f"✅ *{home} - {away}*\n"
        f"🗓 {date}\n\n"
        "İndi bu maçın təxminini/analizini göndər.\n"
        "Məsələn: `Barcelona qələbə + 2.5 ÜST`"
    )

@router.message(AddMatchStates.waiting_prediction_stats, F.text)
async def add_prediction_stats(message: Message, state: FSMContext):
    prediction = message.text.strip().lstrip("/").strip()

    if not prediction:
        await message.answer("❌ Təxmin boş ola bilməz. Təxmini yenidən göndər.")
        return

    await state.update_data(prediction_stats=prediction)

    lang = get_user_lang(message.from_user.id)
    await state.set_state(AddMatchStates.waiting_category)

    await message.answer(
        "Maç hazırdır. İndi kateqoriyanı seç:",
        reply_markup=category_kb(lang)
    )

@router.message(AddMatchStates.waiting_category, F.text.in_(CAT_NORMAL_LABELS | CAT_VIP_LABELS))
async def add_match_category(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    category = "vip" if message.text in CAT_VIP_LABELS else "normal"

    data = await state.get_data()
    date = data.get("date", "")
    home = data.get("home", "")
    away = data.get("away", "")
    prediction_stats = data.get("prediction_stats", "")

    import time
    match_id = str(int(time.time() * 1000))

    add_match(
        match_id=match_id,
        date=date,
        league="",
        home=home,
        away=away,
        pred_tr=prediction_stats,
        pred_en=prediction_stats,
        category=category,
        status="active",
        result="pending"
    )

    await message.answer(
        "✅ *Maç uğurla əlavə edildi!*\n\n"
        f"⚽ {home} - {away}\n"
        f"🗓 {date}\n"
        f"📊 {'VIP' if category == 'vip' else 'Normal'}\n\n"
        "🟢 Aktiv olaraq \"Təxminlər\" bölməsində görünür.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

@router.message(AddMatchStates.waiting_category)
async def add_match_category_invalid(message: Message):
    lang = get_user_lang(message.from_user.id)
    await message.answer(
        TEXTS[lang]["add_match_category"],
        reply_markup=category_kb(lang)
    )

@router.message(Command("deletematch"))
async def delete_match_command(message: Message):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer(TEXTS["tr"]["delete_match_usage"])
        return
    match_id = args[1]
    delete_match(match_id)
    await message.answer(TEXTS["tr"]["match_deleted"])

@router.message(Command("listmatches"))
async def list_matches_command(message: Message):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return

    matches = get_all_matches()
    if not matches:
        await message.answer("📋 Heç bir maç yoxdur.")
        return

    await message.answer(
        admin_list_text(),
        reply_markup=admin_match_list_kb(matches)
    )

@router.message(Command("vipmatches"))
async def list_vip_matches_command(message: Message):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return

    all_matches = get_all_matches()
    vip_matches = {mid: m for mid, m in all_matches.items() if m.get("category") == "vip"}

    if not vip_matches:
        await message.answer("⭐ Hələ VIP maç əlavə edilməyib.")
        return

    await message.answer(
        "⭐ *VIP maçlar*\n\nHər hansı bir maçın üzərinə basaraq təxmini görə bilərsən.",
        reply_markup=admin_match_list_kb(vip_matches)
    )

async def refresh_admin_match_list(callback: CallbackQuery):
    matches = get_all_matches()

    if not matches:
        await callback.message.edit_text("📋 Heç bir maç yoxdur.")
        return

    await callback.message.edit_text(
        admin_list_text(),
        reply_markup=admin_match_list_kb(matches)
    )

@router.callback_query(F.data.startswith("delete_"))
async def delete_match_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Bu komutu sadece admin kullanabilir!", show_alert=True)
        return

    match_id = callback.data.split("_", 1)[1]
    delete_match(match_id)

    await callback.answer("✅ Maç silindi!", show_alert=True)
    await refresh_admin_match_list(callback)

@router.callback_query(F.data.startswith("history_"))
async def move_match_to_history(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Bu əməliyyat yalnız admin üçündür.", show_alert=True)
        return

    match_id = callback.data.split("_", 1)[1]
    if not get_match(match_id):
        await callback.answer("❌ Maç tapılmadı.", show_alert=True)
        return

    set_match_status(match_id, "history")
    await callback.answer("📜 Maç keçmişə köçürüldü.", show_alert=True)
    await refresh_admin_match_list(callback)

@router.callback_query(F.data.startswith("active_"))
async def move_match_to_active(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Bu əməliyyat yalnız admin üçündür.", show_alert=True)
        return

    match_id = callback.data.split("_", 1)[1]
    if not get_match(match_id):
        await callback.answer("❌ Maç tapılmadı.", show_alert=True)
        return

    set_match_status(match_id, "active")
    await callback.answer("🟢 Maç yenidən aktiv edildi.", show_alert=True)
    await refresh_admin_match_list(callback)

@router.callback_query(F.data.startswith("list_match_"))
async def list_match_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Bu əməliyyat yalnız admin üçündür.", show_alert=True)
        return

    match_id = callback.data.split("_", 2)[2]
    lang = get_user_lang(callback.from_user.id)
    text = match_detail_text(match_id, lang, for_admin=True)

    if text is None:
        await callback.answer("❌ Maç tapılmadı.", show_alert=True)
        return

    # Add result setting buttons
    result_kb = result_kb(match_id)
    back_btn = InlineKeyboardButton(text="◀️ Siyahıya qayıt", callback_data="back_to_list")
    result_kb.inline_keyboard.append([back_btn])

    await callback.message.edit_text(text, reply_markup=result_kb)
    await callback.answer()

@router.callback_query(F.data.startswith("setresult_"))
async def set_match_result_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Bu əməliyyat yalnız admin üçündür.", show_alert=True)
        return

    parts = callback.data.split("_")
    match_id = parts[1]
    result = parts[2]  # win, lose, draw, pending

    if not get_match(match_id):
        await callback.answer("❌ Maç tapılmadı.", show_alert=True)
        return

    set_match_result(match_id, result)
    await callback.answer("✅ Nəticə yeniləndi.", show_alert=True)

    # Refresh the detail view
    lang = get_user_lang(callback.from_user.id)
    text = match_detail_text(match_id, lang, for_admin=True)
    if text:
        result_kb = result_kb(match_id)
        back_btn = InlineKeyboardButton(text="◀️ Siyahıya qayıt", callback_data="back_to_list")
        result_kb.inline_keyboard.append([back_btn])
        await callback.message.edit_text(text, reply_markup=result_kb)

@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Bu əməliyyat yalnız admin üçündür.", show_alert=True)
        return

    await refresh_admin_match_list(callback)

@router.message(Command("reply"))
async def reply_to_ticket(message: Message):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(TEXTS["tr"]["reply_usage"])
        return
    ticket_id = int(args[1])
    reply_text = args[2]
    ticket = get_ticket(ticket_id)
    if not ticket:
        await message.answer("Bilet bulunamadı.")
        return
    user_id, original_msg = ticket
    lang = get_user_lang(user_id)
    await bot.send_message(user_id, TEXTS[lang]["support_reply"].format(reply_text=reply_text))
    mark_ticket_replied(ticket_id)
    await message.answer("✅ Yanıt gönderildi.")

# ---------- FLASK KEEP-ALIVE ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Statify Bet AI is running!"

def run_flask():
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# ---------- MAIN ----------
async def main():
    dp.include_router(router)
    logger.info("Starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
