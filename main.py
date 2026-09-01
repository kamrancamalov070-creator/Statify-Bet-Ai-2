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
