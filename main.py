"""
main.py — Statify Bet AI Telegram bot (aiogram v3) + Flask keep-alive server for Render.

Run:
    export BOT_TOKEN="8105745014:AAHqgQunU4gK5fWwi4bFwE1GXuludZpFz3Y"
    python main.py

On Render:
    - Deploy as a Web Service (Flask binds $PORT so Render's health check passes).
    - Set BOT_TOKEN as an environment variable in the Render dashboard.
    - Start command: python main.py
"""

import asyncio
import logging
import os
import threading

from flask import Flask

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from texts import TEXTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8105745014:AAHqgQunU4gK5fWwi4bFwE1GXuludZpFz3Y")


# =====================================================================
# ADMIN SECTION — edit this dict to add/update matches & predictions.
# No other code needs to change. Keys are just unique match IDs (any
# unique string works — dates, incrementing numbers, whatever is easiest).
# =====================================================================
MATCHES = {
    "1": {
        "date": "28.08 21:45 (UTC+3)",
        "league": "England - National League",
        "home": "Barrow",
        "away": "Yeovil Town",
        "prediction": {
            "tr": (
                "📊 Form: Barrow son 5 maçta 3 galibiyet aldı, iç sahada güçlü.\n"
                "🔁 H2H: Son 3 karşılaşmada ev sahibi 2 kez kazandı.\n"
                "💡 Öneri: MS1 + 2.5 Üst\n"
                "🎯 Güven: Yüksek"
            ),
            "en": (
                "📊 Form: Barrow have won 3 of their last 5, strong at home.\n"
                "🔁 H2H: Home side won 2 of the last 3 meetings.\n"
                "💡 Tip: Home Win + Over 2.5\n"
                "🎯 Confidence: High"
            ),
        },
    },
    "2": {
        "date": "28.08 22:00 (UTC+3)",
        "league": "Sweden - Allsvenskan",
        "home": "Malmö FF",
        "away": "AIK",
        "prediction": {
            "tr": (
                "📊 Form: Malmö evinde son 6 maçta yenilmedi.\n"
                "🔁 H2H: Son 4 derbide 3 gol ortalaması üzerinde.\n"
                "💡 Öneri: KG Var + 2.5 Üst\n"
                "🎯 Güven: Orta-Yüksek"
            ),
            "en": (
                "📊 Form: Malmö are unbeaten at home in their last 6.\n"
                "🔁 H2H: Last 4 derbies averaged over 3 goals.\n"
                "💡 Tip: BTTS + Over 2.5\n"
                "🎯 Confidence: Medium-High"
            ),
        },
    },
}
# =====================================================================


# In-memory storage of each user's chosen language.
# NOTE: this resets on every restart/redeploy. Swap for SQLite/a JSON
# file/Postgres if you need it to persist (matches the approach used
# in the Kuponcent Azerbaijani bot, which uses SQLite for this).
user_lang: dict[int, str] = {}

router = Router()


def get_lang(user_id: int) -> str:
    return user_lang.get(user_id, "en")


def language_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang_tr"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            ]
        ]
    )


def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
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


def tips_inline_kb() -> InlineKeyboardMarkup:
    rows = []
    for match_id, m in MATCHES.items():
        label = f"{m['date']} {m['home']} — {m['away']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"match_{match_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def match_detail_text(match_id: str, lang: str) -> str | None:
    m = MATCHES.get(match_id)
    if not m:
        return None
    return (
        f"⚽ {m['home']} vs {m['away']}\n"
        f"🏆 {m['league']}\n"
        f"🗓 {m['date']}\n\n"
        f"{m['prediction'][lang]}"
    )


# Precompute reverse lookups so the same reply-keyboard handler works
# no matter which language a given user currently has selected.
def _labels(key: str) -> set[str]:
    return {TEXTS["tr"][key], TEXTS["en"][key]}


TIPS_LABELS = _labels("menu_tips")
HISTORY_LABELS = _labels("menu_history")
VIP_LABELS = _labels("menu_vip")
SUPPORT_LABELS = _labels("menu_support")
LANGUAGE_LABELS = _labels("menu_language")


# ---------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        TEXTS["en"]["choose_language_prompt"], reply_markup=language_inline_kb()
    )


@router.callback_query(F.data.startswith("lang_"))
async def process_language(callback: CallbackQuery) -> None:
    lang = callback.data.split("_", 1)[1]
    if lang not in TEXTS:
        lang = "en"
    user_lang[callback.from_user.id] = lang
    t = TEXTS[lang]
    name = callback.from_user.first_name or ""

    await callback.message.edit_text(t["welcome"].format(name=name))
    await callback.message.answer(t["menu_prompt"], reply_markup=main_menu_kb(lang))
    await callback.answer()


@router.message(F.text.in_(TIPS_LABELS))
async def show_tips(message: Message) -> None:
    lang = get_lang(message.from_user.id)
    t = TEXTS[lang]
    if not MATCHES:
        await message.answer(t["no_matches"])
        return
    await message.answer(t["tips_title"], reply_markup=tips_inline_kb())


@router.callback_query(F.data.startswith("match_"))
async def show_match(callback: CallbackQuery) -> None:
    match_id = callback.data.split("_", 1)[1]
    lang = get_lang(callback.from_user.id)
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
async def back_to_tips(callback: CallbackQuery) -> None:
    lang = get_lang(callback.from_user.id)
    t = TEXTS[lang]
    if not MATCHES:
        await callback.message.edit_text(t["no_matches"])
        await callback.answer()
        return
    await callback.message.edit_text(t["tips_title"], reply_markup=tips_inline_kb())
    await callback.answer()


@router.message(F.text.in_(HISTORY_LABELS))
async def show_history(message: Message) -> None:
    lang = get_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["history_text"])


@router.message(F.text.in_(VIP_LABELS))
async def show_vip(message: Message) -> None:
    lang = get_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["vip_coming_soon"])


@router.message(F.text.in_(SUPPORT_LABELS))
async def show_support(message: Message) -> None:
    lang = get_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["support_text"])


@router.message(F.text.in_(LANGUAGE_LABELS))
async def change_language(message: Message) -> None:
    await message.answer(
        TEXTS["en"]["choose_language_prompt"], reply_markup=language_inline_kb()
    )


# ---------------------------------------------------------------------
# Flask keep-alive server (so Render's Web Service health check passes
# and the free-tier instance doesn't get put to sleep for inactivity).
# ---------------------------------------------------------------------
flask_app = Flask(__name__)


@flask_app.route("/")
def health_check():
    return "Kuponcent bot is running!"


def run_flask() -> None:
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------
async def run_bot() -> None:
    if BOT_TOKEN == "PUT-YOUR-TOKEN-HERE":
        logger.warning("BOT_TOKEN is not set — set it as an environment variable.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(run_bot())
