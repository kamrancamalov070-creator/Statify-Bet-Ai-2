# main.py (aiogram 2) - düzəlişlər: menyu itməsi aradan qaldırıldı, match başlığı düzəldi
import asyncio
import logging
import os
import sqlite3
import threading
from datetime import datetime

from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.utils.markdown import hbold

from texts import TEXTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8105745014:AAHqgQunU4gK5fWwi4bFwE1GXuludZpFz3Y")
ADMIN_USERNAME = "kamrancmlv"
ADMIN_ID = 1337915501
STATS_IMAGE_URL = os.getenv("STATS_IMAGE_URL", None)

DB_NAME = "bot_data.db"

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'tr')''')
    c.execute('''CREATE TABLE IF NOT EXISTS matches
                 (match_id TEXT PRIMARY KEY, date TEXT, league TEXT,
                  home TEXT, away TEXT, pred_tr TEXT, pred_en TEXT,
                  category TEXT DEFAULT 'normal')''')
    c.execute('''CREATE TABLE IF NOT EXISTS support_tickets
                 (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, message TEXT, timestamp TEXT,
                  replied INTEGER DEFAULT 0)''')
    try:
        c.execute("ALTER TABLE matches ADD COLUMN category TEXT DEFAULT 'normal'")
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
    c.execute("SELECT match_id, date, league, home, away, pred_tr, pred_en FROM matches WHERE category = ? ORDER BY date", (category,))
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

def get_all_matches():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT match_id, date, league, home, away, pred_tr, pred_en, category FROM matches ORDER BY date")
    rows = c.fetchall()
    conn.close()
    matches = {}
    for row in rows:
        match_id, date, league, home, away, pred_tr, pred_en, category = row
        matches[match_id] = {
            "date": date,
            "league": league,
            "home": home,
            "away": away,
            "prediction": {"tr": pred_tr, "en": pred_en},
            "category": category
        }
    return matches

def get_match(match_id: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT date, league, home, away, pred_tr, pred_en, category FROM matches WHERE match_id = ?", (match_id,))
    row = c.fetchone()
    conn.close()
    if row:
        date, league, home, away, pred_tr, pred_en, category = row
        return {
            "date": date,
            "league": league,
            "home": home,
            "away": away,
            "prediction": {"tr": pred_tr, "en": pred_en},
            "category": category
        }
    return None

def add_match(match_id, date, league, home, away, pred_tr, pred_en, category='normal'):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO matches (match_id, date, league, home, away, pred_tr, pred_en, category) VALUES (?,?,?,?,?,?,?,?)",
              (match_id, date, league, home, away, pred_tr, pred_en, category))
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

def is_admin(user) -> bool:
    if user.username and user.username.lower() == ADMIN_USERNAME.lower():
        return True
    if user.id == ADMIN_ID:
        return True
    return False

# --- FSM STATES ---
class AddMatchStates(StatesGroup):
    waiting_match_info = State()
    waiting_prediction_stats = State()
    waiting_category = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# --- KEYBOARDS ---
def language_inline_kb():
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang_tr"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
    )

def main_menu_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(t["menu_tips"]), KeyboardButton(t["menu_history"])],
            [KeyboardButton(t["menu_vip"]), KeyboardButton(t["menu_support"]), KeyboardButton(t["menu_language"])],
        ],
        resize_keyboard=True
    )

def tips_inline_kb(matches: dict):
    kb = InlineKeyboardMarkup(row_width=1)
    for match_id, m in matches.items():
        # başlıq üçün date istifadə et (çünki home/away boş ola bilər)
        label = m['date']
        kb.add(InlineKeyboardButton(label, callback_data=f"match_{match_id}"))
    return kb

def match_detail_text(match_id: str, lang: str):
    m = get_match(match_id)
    if not m:
        return None
    # Əgər home və away boşdursa, başlıq kimi date istifadə et
    if m['home'] and m['away']:
        title = f"⚽ *{m['home']} vs {m['away']}*"
    else:
        title = f"📌 *{m['date']}*"
    return (
        f"{title}\n"
        f"🏆 {m['league'] if m['league'] else '—'}\n"
        f"🗓 {m['date']}\n\n"
        f"{m['prediction'][lang]}"
    )

def category_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(t["category_normal"]), KeyboardButton(t["category_vip"])]],
        resize_keyboard=True,
        one_time_keyboard=True
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

# --- HANDLERS ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        TEXTS["tr"]["choose_language"],
        reply_markup=language_inline_kb()
    )

@dp.callback_query_handler(lambda c: c.data.startswith('lang_'))
async def process_language(callback_query: types.CallbackQuery):
    lang = callback_query.data.split("_", 1)[1]
    if lang not in TEXTS:
        lang = "tr"
    set_user_lang(callback_query.from_user.id, lang)
    t = TEXTS[lang]
    name = callback_query.from_user.first_name or "İstifadəçi"
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=t["welcome"].format(name=name)
    )
    await bot.send_message(
        chat_id=callback_query.message.chat.id,
        text=t["menu_prompt"],
        reply_markup=main_menu_kb(lang)
    )
    await callback_query.answer()

@dp.message_handler(lambda m: m.text in LANGUAGE_LABELS)
async def change_language(message: types.Message):
    await message.answer(
        TEXTS["tr"]["choose_language"],
        reply_markup=language_inline_kb()
    )

@dp.message_handler(lambda m: m.text in TIPS_LABELS)
async def show_tips(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    matches = get_matches_by_category('normal')
    if not matches:
        await message.answer(t["no_matches"])
        return
    await message.answer(t["tips_title"], reply_markup=tips_inline_kb(matches))

@dp.message_handler(lambda m: m.text in VIP_LABELS)
async def show_vip(message: types.Message):
    vip_text = (
        "⭐ *VIP Üzvlük*\n\n"
        "VIP üzvlər üçün xüsusi tahminlər və analizlər!\n"
        "VIP olmaq üçün kanalımıza qoşulun: @statifybetvip\n"
        "Ödənişli üzvlük üçün adminə yazın: @kamrancmlv"
    )
    await message.answer(vip_text, parse_mode="MARKDOWN")

@dp.callback_query_handler(lambda c: c.data.startswith('match_'))
async def show_match(callback_query: types.CallbackQuery):
    match_id = callback_query.data.split("_", 1)[1]
    lang = get_user_lang(callback_query.from_user.id)
    t = TEXTS[lang]
    text = match_detail_text(match_id, lang)
    if text is None:
        await callback_query.answer(t["match_not_found"], show_alert=True)
        return
    back_kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(text=t["back"], callback_data="back_to_tips")
    )
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=text,
        reply_markup=back_kb
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_tips')
async def back_to_tips(callback_query: types.CallbackQuery):
    lang = get_user_lang(callback_query.from_user.id)
    t = TEXTS[lang]
    matches = get_matches_by_category('normal')
    if not matches:
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=t["no_matches"]
        )
        await callback_query.answer()
        return
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=t["tips_title"],
        reply_markup=tips_inline_kb(matches)
    )
    await callback_query.answer()

@dp.message_handler(lambda m: m.text in HISTORY_LABELS)
async def show_history(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    all_matches = get_all_matches()
    if not all_matches:
        await message.answer(t["no_history"])
        return
    lines = [f"• {m['date']} – {m['league']}: {m['home']} vs {m['away']}" for mid, m in all_matches.items()]
    await message.answer(t["history_text"].format(matches="\n".join(lines)))

# --- SUPPORT ---
support_mode = {}

@dp.message_handler(lambda m: m.text in SUPPORT_LABELS)
async def support_start(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    support_mode[message.from_user.id] = True
    await message.answer(t["support_prompt"])

@dp.message_handler(lambda m: m.text and not m.text.startswith('/') and m.text not in (TIPS_LABELS | HISTORY_LABELS | VIP_LABELS | SUPPORT_LABELS | LANGUAGE_LABELS | CAT_NORMAL_LABELS | CAT_VIP_LABELS))
async def handle_support_message(message: types.Message):
    user_id = message.from_user.id
    if is_admin(message.from_user):
        return
    if support_mode.get(user_id, False):
        ticket_id = add_support_ticket(user_id, message.text)
        await bot.send_message(
            chat_id=message.chat.id,
            text=TEXTS["tr"]["admin_notify"].format(
                user=f"{message.from_user.full_name} (@{message.from_user.username})",
                msg=message.text
            )
        )
        lang = get_user_lang(user_id)
        await message.answer(TEXTS[lang]["support_thanks"])
        support_mode[user_id] = False
    else:
        pass

# --- ADMIN COMMANDS ---
@dp.message_handler(commands=['addmatch'])
async def add_match_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return
    await state.set_state(AddMatchStates.waiting_match_info)
    await message.answer(TEXTS["tr"]["add_match_info"])

@dp.message_handler(state=AddMatchStates.waiting_match_info)
async def add_match_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['match_info'] = message.text
    await state.set_state(AddMatchStates.waiting_prediction_stats)
    await message.answer(TEXTS["tr"]["add_match_prediction_stats"])

@dp.message_handler(state=AddMatchStates.waiting_prediction_stats)
async def add_prediction_stats(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['prediction_stats'] = message.text
    lang = get_user_lang(message.from_user.id)
    await state.set_state(AddMatchStates.waiting_category)
    await message.answer(
        TEXTS[lang]["add_match_category"],
        reply_markup=category_kb(lang)
    )

@dp.message_handler(state=AddMatchStates.waiting_category, text=CAT_NORMAL_LABELS | CAT_VIP_LABELS)
async def add_match_category(message: types.Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    category = 'vip' if message.text in CAT_VIP_LABELS else 'normal'
    async with state.proxy() as data:
        match_info = data.get('match_info', '')
        prediction_stats = data.get('prediction_stats', '')
    import time
    match_id = str(int(time.time() * 1000))
    add_match(
        match_id=match_id,
        date=match_info,
        league="",
        home="",
        away="",
        pred_tr=prediction_stats,
        pred_en=prediction_stats,
        category=category
    )
    # Menyunu geri qaytar
    await message.answer(t["match_added"].format(match_id=match_id), reply_markup=main_menu_kb(lang))
    await state.finish()

@dp.message_handler(state=AddMatchStates.waiting_category)
async def add_match_category_invalid(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    await message.answer(
        TEXTS[lang]["add_match_category"],
        reply_markup=category_kb(lang)
    )

@dp.message_handler(commands=['deletematch'])
async def delete_match_command(message: types.Message):
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

@dp.message_handler(commands=['listmatches'])
async def list_matches_command(message: types.Message):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return
    matches = get_all_matches()
    if not matches:
        await message.answer(TEXTS["tr"]["no_matches_list"])
        return
    kb = InlineKeyboardMarkup(row_width=2)
    for mid, m in matches.items():
        label = f"{m['date']} {m['home']} - {m['away']} [{ 'VIP' if m['category']=='vip' else 'Normal' }]"
        kb.add(
            InlineKeyboardButton(label, callback_data=f"list_match_{mid}"),
            InlineKeyboardButton("🗑 Sil", callback_data=f"delete_{mid}")
        )
    await message.answer("📋 *Mevcut maçlar (silme için butona tıkla):*", reply_markup=kb, parse_mode="MARKDOWN")

@dp.callback_query_handler(lambda c: c.data.startswith('delete_'))
async def delete_match_callback(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user):
        await callback_query.answer("Bu komutu sadece admin kullanabilir!", show_alert=True)
        return
    match_id = callback_query.data.split("_", 1)[1]
    delete_match(match_id)
    await callback_query.answer("✅ Maç silindi!", show_alert=True)
    matches = get_all_matches()
    if not matches:
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="📋 Hiç maç kalmadı."
        )
        return
    kb = InlineKeyboardMarkup(row_width=2)
    for mid, m in matches.items():
        label = f"{m['date']} {m['home']} - {m['away']} [{ 'VIP' if m['category']=='vip' else 'Normal' }]"
        kb.add(
            InlineKeyboardButton(label, callback_data=f"list_match_{mid}"),
            InlineKeyboardButton("🗑 Sil", callback_data=f"delete_{mid}")
        )
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="📋 *Mevcut maçlar (silme için butona tıkla):*",
        reply_markup=kb,
        parse_mode="MARKDOWN"
    )

@dp.callback_query_handler(lambda c: c.data.startswith('list_match_'))
async def list_match_detail(callback_query: types.CallbackQuery):
    match_id = callback_query.data.split("_", 2)[2]
    lang = get_user_lang(callback_query.from_user.id)
    t = TEXTS[lang]
    text = match_detail_text(match_id, lang)
    if text is None:
        await callback_query.answer(t["match_not_found"], show_alert=True)
        return
    back_kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(text="◀️ Listeye Dön", callback_data="back_to_list")
    )
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=text,
        reply_markup=back_kb
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_list')
async def back_to_list(callback_query: types.CallbackQuery):
    matches = get_all_matches()
    if not matches:
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="📋 Hiç maç kalmadı."
        )
        await callback_query.answer()
        return
    kb = InlineKeyboardMarkup(row_width=2)
    for mid, m in matches.items():
        label = f"{m['date']} {m['home']} - {m['away']} [{ 'VIP' if m['category']=='vip' else 'Normal' }]"
        kb.add(
            InlineKeyboardButton(label, callback_data=f"list_match_{mid}"),
            InlineKeyboardButton("🗑 Sil", callback_data=f"delete_{mid}")
        )
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="📋 *Mevcut maçlar (silme için butona tıkla):*",
        reply_markup=kb,
        parse_mode="MARKDOWN"
    )
    await callback_query.answer()

@dp.message_handler(commands=['reply'])
async def reply_to_ticket(message: types.Message):
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

# --- FLASK KEEP-ALIVE ---
flask_app = Flask(__name__)
@flask_app.route("/")
def health():
    return "Statify Bet AI is running!"

def run_flask():
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# --- MAIN ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    executor.start_polling(dp, skip_updates=True)
