import asyncio
import logging
import os
import sqlite3
import threading
from datetime import datetime

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
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from texts import TEXTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8105745014:AAHqgQunU4gK5fWwi4bFwE1GXuludZpFz3Y")
ADMIN_USERNAME = "kamrancmlv"
ADMIN_ID = 1337915501
STATS_IMAGE_URL = os.getenv("STATS_IMAGE_URL", None)

DB_NAME = "bot_data.db"

# ---------- DATABASE ----------
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

def tips_inline_kb(matches: dict, show_delete=False):
    rows = []
    for match_id, m in matches.items():
        label = f"{m['date']} {m['home']} — {m['away']}"
        buttons = [InlineKeyboardButton(text=label, callback_data=f"match_{match_id}")]
        if show_delete:
            buttons.append(InlineKeyboardButton(text="🗑 Sil", callback_data=f"delete_{match_id}"))
        rows.append(buttons)
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

def category_kb(lang: str):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["category_normal"]), KeyboardButton(text=t["category_vip"])]
        ],
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
    await message.answer(t["tips_title"], reply_markup=tips_inline_kb(matches))

@router.message(F.text.in_(VIP_LABELS))
async def show_vip(message: Message):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    vip_text = (
        "⭐ *VIP Üzvlük*\n\n"
        "VIP üzvlər üçün xüsusi tahminlər və analizlər!\n"
        "VIP olmaq üçün kanalımıza qoşulun: @statifybetvip\n"
        "Ödənişli üzvlük üçün adminə yazın: @kamrancmlv"
    )
    await message.answer(vip_text, parse_mode="MARKDOWN")

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
    matches = get_matches_by_category('normal')
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
    if not all_matches:
        await message.answer(t["no_history"])
        return
    lines = [f"• {m['date']} – {m['league']}: {m['home']} vs {m['away']}" for mid, m in all_matches.items()]
    await message.answer(t["history_text"].format(matches="\n".join(lines)))

# ---------- SUPPORT ----------
support_mode = {}

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

# ---------- ADMIN COMMANDS ----------
@router.message(Command("addmatch"))
async def add_match_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user):
        await message.answer(TEXTS["tr"]["admin_denied"])
        return
    await state.set_state(AddMatchStates.waiting_match_info)
    await message.answer(TEXTS["tr"]["add_match_info"])

@router.message(AddMatchStates.waiting_match_info)
async def add_match_info(message: Message, state: FSMContext):
    await state.update_data(match_info=message.text)
    await state.set_state(AddMatchStates.waiting_prediction_stats)
    await message.answer(TEXTS["tr"]["add_match_prediction_stats"])

@router.message(AddMatchStates.waiting_prediction_stats)
async def add_prediction_stats(message: Message, state: FSMContext):
    await state.update_data(prediction_stats=message.text)
    lang = get_user_lang(message.from_user.id)
    await state.set_state(AddMatchStates.waiting_category)
    await message.answer(
        TEXTS[lang]["add_match_category"],
        reply_markup=category_kb(lang)
    )

@router.message(AddMatchStates.waiting_category, F.text.in_(CAT_NORMAL_LABELS | CAT_VIP_LABELS))
async def add_match_category(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    category = 'vip' if message.text in CAT_VIP_LABELS else 'normal'
    data = await state.get_data()
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
    await message.answer(t["match_added"].format(match_id=match_id), reply_markup=ReplyKeyboardRemove())
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
        await message.answer(TEXTS["tr"]["no_matches_list"])
        return
    rows = []
    for mid, m in matches.items():
        label = f"{m['date']} {m['home']} - {m['away']} [{ 'VIP' if m['category']=='vip' else 'Normal' }]"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"list_match_{mid}")])
        rows.append([InlineKeyboardButton(text="🗑 Sil", callback_data=f"delete_{mid}")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer("📋 *Mevcut maçlar (silme için butona tıkla):*", reply_markup=kb, parse_mode="MARKDOWN")

@router.callback_query(F.data.startswith("delete_"))
async def delete_match_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Bu komutu sadece admin kullanabilir!", show_alert=True)
        return
    match_id = callback.data.split("_", 1)[1]
    delete_match(match_id)
    await callback.answer("✅ Maç silindi!", show_alert=True)
    matches = get_all_matches()
    if not matches:
        await callback.message.edit_text("📋 Hiç maç kalmadı.")
        return
    rows = []
    for mid, m in matches.items():
        label = f"{m['date']} {m['home']} - {m['away']} [{ 'VIP' if m['category']=='vip' else 'Normal' }]"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"list_match_{mid}")])
        rows.append([InlineKeyboardButton(text="🗑 Sil", callback_data=f"delete_{mid}")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text("📋 *Mevcut maçlar (silme için butona tıkla):*", reply_markup=kb, parse_mode="MARKDOWN")

@router.callback_query(F.data.startswith("list_match_"))
async def list_match_detail(callback: CallbackQuery):
    match_id = callback.data.split("_", 2)[2]
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    text = match_detail_text(match_id, lang)
    if text is None:
        await callback.answer(t["match_not_found"], show_alert=True)
        return
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Listeye Dön", callback_data="back_to_list")]]
    )
    await callback.message.edit_text(text, reply_markup=back_kb)
    await callback.answer()

@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    matches = get_all_matches()
    if not matches:
        await callback.message.edit_text("📋 Hiç maç kalmadı.")
        await callback.answer()
        return
    rows = []
    for mid, m in matches.items():
        label = f"{m['date']} {m['home']} - {m['away']} [{ 'VIP' if m['category']=='vip' else 'Normal' }]"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"list_match_{mid}")])
        rows.append([InlineKeyboardButton(text="🗑 Sil", callback_data=f"delete_{mid}")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text("📋 *Mevcut maçlar (silme için butona tıkla):*", reply_markup=kb, parse_mode="MARKDOWN")
    await callback.answer()

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
