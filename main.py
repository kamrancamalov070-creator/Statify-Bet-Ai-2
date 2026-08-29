import asyncio
import logging
import os
import sqlite3
import threading
import re
from datetime import datetime

from flask import Flask
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.markdown import hbold, hlink

from texts import TEXTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- ENV & ADMIN --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8105745014:AAHqgQunU4gK5fWwi4bFwE1GXuludZpFz3Y")
ADMIN_USERNAME = "kamrancmlv"  # İstifadəçi adı ( @ olmadan )

# İsterseniz şəkil URL-i əlavə edin (statistika görseli)
STATS_IMAGE_URL = os.getenv("STATS_IMAGE_URL", None)  # məs. "https://example.com/stats.png"

# -------------------- DATABASE --------------------
DB_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'tr')''')
    c.execute('''CREATE TABLE IF NOT EXISTS matches
                 (match_id TEXT PRIMARY KEY, date TEXT, league TEXT,
                  home TEXT, away TEXT, pred_tr TEXT, pred_en TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS support_tickets
                 (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, message TEXT, timestamp TEXT,
                  replied INTEGER DEFAULT 0)''')
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

def get_all_matches():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT match_id, date, league, home, away, pred_tr, pred_en FROM matches ORDER BY date")
    rows = c.fetchall()
    conn.close()
    matches = {}
    for row in rows:
        match_id, date, league, home, away, pred_tr, pred_en = row
        matches[match_id] = {
            "date": date,
            "league": league,
            "home": home,
            "away": away,
            "prediction": {"tr": pred_tr, "en": pred_en}
        }
    return matches

def get_match(match_id: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT date, league, home, away, pred_tr, pred_en FROM matches WHERE match_id = ?", (match_id,))
    row = c.fetchone()
    conn.close()
    if row:
        date, league, home, away, pred_tr, pred_en = row
        return {
            "date": date,
            "league": league,
            "home": home,
            "away": away,
            "prediction": {"tr": pred_tr, "en": pred_en}
        }
    return None

def add_match(match_id, date, league, home, away, pred_tr, pred_en):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO matches (match_id, date, league, home, away, pred_tr, pred_en) VALUES (?,?,?,?,?,?,?)",
              (match_id, date, league, home, away, pred_tr, pred_en))
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

# -------------------- HELPERS --------------------
def is_admin(user: types.User) -> bool:
    return user.username and user.username.lower() == ADMIN_USERNAME.lower()

def parse_match_date(date_str: str):
    """'28.08 21:45 (UTC+3)' → datetime object (cari il ilə)"""
    try:
        match = re.match(r'(\d{2})\.(\d{2}) (\d{2}):(\d{2})', date_str)
        if match:
            day, month, hour, minute = map(int, match.groups())
            now = datetime.now()
            year = now.year
            # Əgər ay yanvardırsa və indiki ay dekabrdırsa, il əvvəlki il ola bilər? Sadəlik üçün cari il.
            dt = datetime(year, month, day, hour, minute)
            return dt
    except:
        pass
    return None

def is_past_match(date_str: str) -> bool:
    dt = parse_match_date(date_str)
    if dt:
        return dt < datetime.now()
    return False  # parse olunmazsa keçmiş sayma

# -------------------- BOT & ROUTER --------------------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
router = Router()

# -------------------- KEYBOARDS --------------------
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

def tips_inline_kb(matches: dict):
    rows = []
    for match_id, m in matches.items():
        label = f"{m['date']} {m['home']} — {m['away']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"match_{match_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def match_detail_text(match_id: str, lang: str):
    m = get_match(match_id)
    if not m:
        return None
    return (
        f"⚽ *{m['home']} vs {m['away']}*\n"
        f"🏆 {m['league']}\n"
        f"🗓 {m['date']}\n\n"
        f"{m['prediction'][lang]}"
    )

# -------------------- LABELS FOR FILTERING --------------------
def _labels(key: str):
    return {TEXTS["tr"][key], TEXTS["en"][key]}

TIPS_LABELS = _labels("menu_tips")
HISTORY_LABELS = _labels("menu_history")
VIP_LABELS = _labels("menu_vip")
SUPPORT_LABELS = _labels("menu_support")
LANGUAGE_LABELS = _labels("menu_language")

# -------------------- HANDLERS --------------------
@router.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.first_name or "İstifadəçi"
    # Əgər STATS_IMAGE_URL varsa şəkil göndər, yoxsa sadəcə mətn
    if STATS_IMAGE_URL:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=STATS_IMAGE_URL,
            caption=TEXTS["tr"]["choose_language_prompt"].format(name=name),
            reply_markup=language_inline_kb()
        )
    else:
        await message.answer(
            TEXTS["tr"]["choose_language_prompt"].format(name=name),
            reply_markup=language_inline_kb()
        )

@router.callback_query(F.data.startswith("lang_"))
async def process_language(callback: CallbackQuery):
    lang = callback.data.split("_", 1)[1]
    if lang not in TEXTS:
        lang = "tr"
    set_user_lang(callback.from_user.id, lang)
    t = TEXTS[lang]
    # Orijinal mesajı redaktə etmirik, sadəcə altına menyu göndəririk
    await callback.message.answer(t["menu_prompt"], reply_markup=main_menu_kb(lang))
    await callback.answer()

@router.message(F.text.in_(TIPS_LABELS))
async def show_tips(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    matches = get_all_matches()
    if not matches:
        await message.answer(t["no_matches"])
        return
    await message.answer(t["tips_title"], reply_markup=tips_inline_kb(matches))

@router.callback_query(F.data.startswith("match_"))
async def show_match(callback: CallbackQuery):
    match_id = callback.data.split("_", 1)[1]
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    text = match_detail_text(match_id, lang)
    if text is None:
        await callback.answer(t["match_not_found"], show_alert=True)
        return
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t["back"], callback_data="back_to_tips")]]
    )
    await callback.message.edit_text(text, reply_markup=back_kb)
    await callback.answer()

@router.callback_query(F.data == "back_to_tips")
async def back_to_tips(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    matches = get_all_matches()
    if not matches:
        await callback.message.edit_text(t["no_matches"])
        await callback.answer()
        return
    await callback.message.edit_text(t["tips_title"], reply_markup=tips_inline_kb(matches))
    await callback.answer()

@router.message(F.text.in_(HISTORY_LABELS))
async def show_history(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    all_matches = get_all_matches()
    past_matches = {mid: m for mid, m in all_matches.items() if is_past_match(m["date"])}
    if not past_matches:
        await message.answer(t["no_history"])
        return
    lines = []
    for mid, m in past_matches.items():
        lines.append(f"• {m['date']} – {m['league']}: {m['home']} vs {m['away']}")
    await message.answer(t["history_text"].format(matches="\n".join(lines)))

@router.message(F.text.in_(VIP_LABELS))
async def show_vip(message: Message):
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["vip_coming_soon"])

# -------------------- SUPPORT --------------------
support_mode = {}  # {user_id: True/False}

@router.message(F.text.in_(SUPPORT_LABELS))
async def support_start(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    support_mode[message.from_user.id] = True
    await message.answer(t["support_prompt"])

@router.message(F.text & ~F.text.in_(TIPS_LABELS | HISTORY_LABELS | VIP_LABELS | SUPPORT_LABELS | LANGUAGE_LABELS) & ~F.text.startswith("/"))
async def handle_support_message(message: Message):
    user_id = message.from_user.id
    if is_admin(message.from_user):
        # Adminin yazdığı mesajları rəhbər tutmuruq (cavab üçün ayrıca mexanizm)
        return
    if support_mode.get(user_id, False):
        # Destek mesajı
        ticket_id = add_support_ticket(user_id, message.text)
        # Adminə xəbər ver
        await bot.send_message(
            chat_id=message.chat.id,  # Admin ilə eyni chatda deyil, amma adminə birbaşa göndərək
            text=TEXTS["tr"]["admin_notify"].format(
                user=f"{message.from_user.full_name} (@{message.from_user.username})",
                msg=message.text
            )
        )
        # İstifadəçiyə təşəkkür
        lang = get_user_lang(user_id)
        await message.answer(TEXTS[lang]["support_thanks"])
        support_mode[user_id] = False
    else:
        # Normal mesaj, heç nə etmə
        pass

# -------------------- ADMIN COMMANDS --------------------
@router.message(Command("addmatch"))
async def add_match_command(message: Message):
    if not is_admin(message.from_user):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(TEXTS["tr"]["add_match_usage"])
        return
    parts = [p.strip() for p in args[1].split('|')]
    if len(parts) != 6:
        await message.answer("Lütfen 6 bölümü '|' ile ayırın.\n" + TEXTS["tr"]["add_match_usage"])
        return
    date, league, home, away, pred_tr, pred_en = parts
    import time
    match_id = str(int(time.time() * 1000))
    add_match(match_id, date, league, home, away, pred_tr, pred_en)
    await message.answer(TEXTS["tr"]["match_added"].format(match_id=match_id))

@router.message(Command("deletematch"))
async def delete_match_command(message: Message):
    if not is_admin(message.from_user):
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
        return
    matches = get_all_matches()
    if not matches:
        await message.answer(TEXTS["tr"]["no_matches_list"])
        return
    lines = [f"• {mid}: {m['date']} {m['home']} - {m['away']}" for mid, m in matches.items()]
    await message.answer(TEXTS["tr"]["match_list"].format(list="\n".join(lines)))

@router.message(Command("reply"))
async def reply_to_ticket(message: Message):
    if not is_admin(message.from_user):
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Kullanım: /reply <ticket_id> <cevap>")
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

# -------------------- FLASK KEEP-ALIVE --------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Statify Bet AI is running!"

def run_flask():
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# -------------------- MAIN --------------------
async def main():
    dp.include_router(router)
    logger.info("Starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
