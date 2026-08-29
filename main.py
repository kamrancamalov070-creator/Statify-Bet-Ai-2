# main.py
import asyncio
import logging
import os
import sqlite3
import threading
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

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "8105745014:AAHqgQunU4gK5fWwi4bFwE1GXuludZpFz3Y")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # Değiştirin!

# SQLite database
DB_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Users table for language preference
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'tr')''')
    # Matches table
    c.execute('''CREATE TABLE IF NOT EXISTS matches
                 (match_id TEXT PRIMARY KEY, date TEXT, league TEXT,
                  home TEXT, away TEXT, pred_tr TEXT, pred_en TEXT)''')
    # Support tickets
    c.execute('''CREATE TABLE IF NOT EXISTS support_tickets
                 (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, message TEXT, timestamp TEXT,
                  replied INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# Database helper functions
def get_user_lang(user_id: int) -> str:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return "tr"  # default Turkish

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

# Bot & router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
router = Router()

# Helper functions for keyboards
def language_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang_tr"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            ]
        ]
    )

def main_menu_kb(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["menu_tips"])],
            [KeyboardButton(text=t["menu_history"])],
            [KeyboardButton(text=t["menu_vip"])],
            [KeyboardButton(text=t["menu_support"])],
            [KeyboardButton(text=t["menu_language"])],
        ],
        resize_keyboard=True,
    )

def tips_inline_kb(matches):
    rows = []
    for match_id, m in matches.items():
        label = f"{m['date']} {m['home']} — {m['away']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"match_{match_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def match_detail_text(match_id, lang):
    m = get_match(match_id)
    if not m:
        return None
    return (
        f"⚽ *{m['home']} vs {m['away']}*\n"
        f"🏆 {m['league']}\n"
        f"🗓 {m['date']}\n\n"
        f"{m['prediction'][lang]}"
    )

# Precompute labels for reply keyboard
def _labels(key):
    return {TEXTS["tr"][key], TEXTS["en"][key]}

TIPS_LABELS = _labels("menu_tips")
HISTORY_LABELS = _labels("menu_history")
VIP_LABELS = _labels("menu_vip")
SUPPORT_LABELS = _labels("menu_support")
LANGUAGE_LABELS = _labels("menu_language")

# ---------- Handlers ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.first_name or "İstifadəçi"
    # Show language selection with prompt
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
    name = callback.from_user.first_name or ""
    await callback.message.edit_text(t["welcome"].format(name=name))
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
    await message.answer(TEXTS[lang]["history_text"])

@router.message(F.text.in_(VIP_LABELS))
async def show_vip(message: Message):
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["vip_coming_soon"])

# Support - when user clicks Support button, prompt them to send a message
@router.message(F.text.in_(SUPPORT_LABELS))
async def support_start(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    await message.answer(t["support_prompt"])
    # Next message from this user will be treated as support message
    # We'll handle it with a generic text handler below.

@router.message(F.text & ~F.text.in_(TIPS_LABELS | HISTORY_LABELS | VIP_LABELS | SUPPORT_LABELS | LANGUAGE_LABELS) & ~F.text.startswith("/"))
async def handle_support_message(message: Message):
    # This catches any text not matching menu buttons and not command.
    # We'll treat it as support message if the user is not admin (or we can check if they are in support mode)
    # To avoid confusion, we'll check if the user recently clicked Support (we can set a flag in DB or in memory)
    # For simplicity, we assume any non-command text after support prompt is support.
    # But we need to differentiate between normal chat and support.
    # We'll use a simple in-memory dict to track users in support mode.
    # However, since we have DB, we can store a support_mode flag.
    # For this example, we'll use a global dict (it will reset on restart, but acceptable for demo)
    if not hasattr(handle_support_message, "support_mode"):
        handle_support_message.support_mode = {}
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        # Admin messages might be replies; we handle replies separately.
        return
    if handle_support_message.support_mode.get(user_id, False):
        # User is in support mode, send message to DB and admin
        ticket_id = add_support_ticket(user_id, message.text)
        # Notify admin
        await bot.send_message(
            ADMIN_ID,
            TEXTS["tr"]["admin_notify"].format(
                user=f"{message.from_user.full_name} (@{message.from_user.username})",
                msg=message.text
            )
        )
        # Acknowledge user
        lang = get_user_lang(user_id)
        await message.answer(TEXTS[lang]["support_thanks"])
        # Clear support mode
        handle_support_message.support_mode[user_id] = False
    else:
        # Not in support mode, ignore or treat as unknown
        pass

# We need to set support_mode when user clicks Support button
# We'll modify support_start to set the flag
@router.message(F.text.in_(SUPPORT_LABELS))
async def support_start(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    await message.answer(t["support_prompt"])
    # Set support mode for this user
    if not hasattr(handle_support_message, "support_mode"):
        handle_support_message.support_mode = {}
    handle_support_message.support_mode[message.from_user.id] = True

# Language change
@router.message(F.text.in_(LANGUAGE_LABELS))
async def change_language(message: Message):
    await message.answer(
        TEXTS["tr"]["choose_language_prompt"].format(name=""),
        reply_markup=language_inline_kb()
    )

# ---------- Admin commands ----------
@router.message(Command("addmatch"))
async def add_match_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(TEXTS["tr"]["add_match_usage"])
        return
    # Format: /addmatch date | league | home | away | tr_pred | en_pred
    # We'll split by '|' but allow spaces around
    parts = [p.strip() for p in args[1].split('|')]
    if len(parts) != 6:
        await message.answer("Lütfen 6 bölümü de '|' ile ayırarak girin.\n" + TEXTS["tr"]["add_match_usage"])
        return
    date, league, home, away, pred_tr, pred_en = parts
    # Generate a unique ID: we can use timestamp or increment
    import time
    match_id = str(int(time.time() * 1000))
    add_match(match_id, date, league, home, away, pred_tr, pred_en)
    await message.answer(TEXTS["tr"]["match_added"].format(match_id=match_id))

@router.message(Command("deletematch"))
async def delete_match_command(message: Message):
    if message.from_user.id != ADMIN_ID:
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
    if message.from_user.id != ADMIN_ID:
        return
    matches = get_all_matches()
    if not matches:
        await message.answer(TEXTS["tr"]["no_matches_list"])
        return
    lines = []
    for mid, m in matches.items():
        lines.append(f"• {mid}: {m['date']} {m['home']} - {m['away']}")
    await message.answer(TEXTS["tr"]["match_list"].format(list="\n".join(lines)))

# Admin reply to support tickets: when admin replies to a forwarded message, we need to catch that.
# We'll implement a message handler that checks if the message is from admin and is a reply to a message that was sent by bot.
# But we don't have a way to link reply to ticket easily. Instead, we can use a command: /reply <ticket_id> <text>
# For simplicity, we'll use a command /reply
@router.message(Command("reply"))
async def reply_to_ticket(message: Message):
    if message.from_user.id != ADMIN_ID:
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
    # Send reply to user
    lang = get_user_lang(user_id)
    await bot.send_message(user_id, TEXTS[lang]["support_reply"].format(reply_text=reply_text))
    # Mark ticket as replied
    mark_ticket_replied(ticket_id)
    await message.answer("✅ Yanıt gönderildi.")

# Also we can handle admin replying to the notification message by forwarding? But we'll keep it simple.

# ---------- Flask keep-alive ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Statify Bet AI is running!"

def run_flask():
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# ---------- Main ----------
async def main():
    dp.include_router(router)
    logger.info("Starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
