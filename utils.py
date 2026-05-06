import logging, asyncio, re
from datetime import datetime
from zoneinfo import ZoneInfo
from hydrogram.errors import FloodWait
from hydrogram import enums
from hydrogram.types import InlineKeyboardButton

from info import ADMINS, IS_PREMIUM, LOG_CHANNEL
from database.users_chats_db import db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🧠 TEMP RUNTIME STORAGE
# ─────────────────────────────────────────────
class temp(object):
    START_TIME = 0
    BANNED_USERS, BANNED_CHATS = [], []
    ME, BOT, U_NAME, B_NAME = None, None, None, None
    CANCEL, USERS_CANCEL, GROUPS_CANCEL = False, False, False
    SETTINGS, ADMIN_TOKENS, ADMIN_SESSIONS, FILES, PREMIUM, PM_FILES = {}, {}, {}, {}, {}, {}

# ─────────────────────────────────────────────
# 👮 ADMIN CHECK
# ─────────────────────────────────────────────
async def is_check_admin(bot, chat_id, user_id):
    try:
        return (await bot.get_chat_member(chat_id, user_id)).status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
    except: return False

# ─────────────────────────────────────────────
# 💎 PREMIUM SYSTEM (Optimized)
# ─────────────────────────────────────────────
async def is_premium(user_id, bot):
    if not IS_PREMIUM or user_id in ADMINS: return True
    mp = await db.get_plan(user_id)
    if not mp.get("premium"): return False
    
    expire = mp.get("expire")
    if expire:
        if isinstance(expire, str):
            try: expire = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
            except: expire = None
        
        if not expire or expire < datetime.now():
            try: 
                await bot.send_message(user_id, f"❌ Your premium {mp.get('plan')} plan has expired.\n\nUse /plan to renew.")
            except: pass
            await db.update_plan(user_id, {"expire": "", "plan": "", "premium": False})
            return False
    return True

def get_premium_button():
    return InlineKeyboardButton('💎 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium")

# ─────────────────────────────────────────────
# 📢 BROADCAST (Unified Logic)
# ─────────────────────────────────────────────
async def broadcast_messages(chat_id, message, pin=False, is_group=False):
    try:
        msg = await message.copy(chat_id=chat_id)
        if pin:
            try: await msg.pin(both_sides=not is_group)
            except: pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(chat_id, message, pin, is_group)
    except Exception:
        if is_group:
            try:
                await db.groups.update_one(
                    {"id": int(chat_id)},
                    {"$set": {"chat_status": {"is_disabled": True, "reason": "Bot removed from group"}}}
                )
            except Exception as ex: logger.error(f"Failed to disable chat {chat_id}: {ex}")
        else:
            await db.delete_user(int(chat_id))
        return "Error"

async def groups_broadcast_messages(chat_id, message, pin=False):
    return await broadcast_messages(chat_id, message, pin, is_group=True)

# ─────────────────────────────────────────────
# ⚙️ GROUP SETTINGS (Fast Cache)
# ─────────────────────────────────────────────
async def get_settings(group_id):
    if group_id not in temp.SETTINGS:
        temp.SETTINGS[group_id] = await db.get_settings(group_id)
    return temp.SETTINGS[group_id]

async def save_group_settings(group_id, key, value):
    temp.SETTINGS[group_id] = await get_settings(group_id)
    temp.SETTINGS[group_id][key] = value
    await db.update_settings(group_id, temp.SETTINGS[group_id])

# ─────────────────────────────────────────────
# 🚫 COMPATIBILITY
# ─────────────────────────────────────────────
async def is_subscribed(bot, query): return []

# ─────────────────────────────────────────────
# 📦 UTILS (Fast Math & IST Time)
# ─────────────────────────────────────────────
def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    size, i = float(size), 0
    while size >= 1024 and i < 4:
        size, i = size / 1024, i + 1
    return f"{size:.2f} {units[i]}"

def get_readable_time(seconds):
    res, periods = "", [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    for name, sec in periods:
        if seconds >= sec:
            val, seconds = divmod(seconds, sec)
            res += f"{int(val)}{name}"
    return res or "0s"

def get_wish():
    # 🇮🇳 Always IST Time
    h = datetime.now(ZoneInfo("Asia/Kolkata")).hour
    return "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞" if h < 12 else "ɢᴏᴏᴅ ᴀꜰᴛᴇʀɴᴏᴏɴ 🌗" if h < 18 else "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"

async def get_seconds(time_string):
    match = re.match(r"(\d+)(s|min|hour|day|month|year)", time_string)
    if not match: return 0
    return int(match.group(1)) * {
        "s": 1, "min": 60, "hour": 3600, "day": 86400,
        "month": 2592000, "year": 31536000
    }.get(match.group(2), 0)
