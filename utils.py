import logging
import asyncio
import re
import aiohttp
import os
from datetime import datetime
from zoneinfo import ZoneInfo # 🚀 Python 3.9+ Fast Timezone
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
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CANCEL = False
    U_NAME = None
    B_NAME = None
    SETTINGS = {}
    FILES = {}
    USERS_CANCEL = False
    GROUPS_CANCEL = False
    BOT = None
    PREMIUM = {}
    PM_FILES = {}

# ─────────────────────────────────────────────
# 👮 ADMIN CHECK
# ─────────────────────────────────────────────
async def is_check_admin(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in (
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER
        )
    except Exception:
        return False

# ─────────────────────────────────────────────
# 💎 PREMIUM SYSTEM (Optimized & Async)
# ─────────────────────────────────────────────
async def is_premium(user_id, bot):
    """Check if user has active premium subscription"""
    if not IS_PREMIUM:
        return True
    if user_id in ADMINS:
        return True

    mp = await db.get_plan(user_id)
    
    if mp.get("premium"):
        expire = mp.get("expire")
        
        if expire:
            if isinstance(expire, str):
                try:
                    expire = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
                except:
                    # Invalid format, remove premium
                    await db.update_plan(user_id, {"expire": "", "plan": "", "premium": False})
                    return False
            
            # Check if expired
            if expire < datetime.now():
                try:
                    await bot.send_message(
                        user_id,
                        f"❌ Your premium {mp.get('plan')} plan has expired.\n\nUse /plan to renew."
                    )
                except Exception:
                    pass

                await db.update_plan(user_id, {"expire": "", "plan": "", "premium": False})
                return False
        
        return True
    return False

def get_premium_button():
    """Get standard premium button"""
    return InlineKeyboardButton('💎 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium")

# ─────────────────────────────────────────────
# 📢 BROADCAST (Async DB Fixed)
# ─────────────────────────────────────────────
async def broadcast_messages(user_id, message, pin=False):
    try:
        msg = await message.copy(chat_id=user_id)
        if pin:
            try: await msg.pin(both_sides=True)
            except: pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message, pin)
    except Exception:
        # ✅ User ने बॉट ब्लॉक कर दिया है या अकाउंट डिलीट हो गया है
        await db.delete_user(int(user_id))
        return "Error"

async def groups_broadcast_messages(chat_id, message, pin=False):
    try:
        msg = await message.copy(chat_id=chat_id)
        if pin:
            try: await msg.pin()
            except: pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await groups_broadcast_messages(chat_id, message, pin)
    except Exception:
        # 🛠️ CRITICAL BUG FIX: `delete_chat` फंक्शन मौजूद नहीं था।
        # अब हम डेटाबेस में चैट को "Disabled" मार्क कर देंगे।
        try:
            await db.groups.update_one(
                {"id": int(chat_id)},
                {"$set": {"chat_status": {"is_disabled": True, "reason": "Bot removed from group"}}}
            )
        except Exception as e:
            logger.error(f"Failed to disable chat {chat_id}: {e}")
        return "Error"

# ─────────────────────────────────────────────
# ⚙️ GROUP SETTINGS (CACHE + ASYNC)
# ─────────────────────────────────────────────
async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings
    return settings

async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current[key] = value
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)

# ─────────────────────────────────────────────
# 🚫 COMPATIBILITY
# ─────────────────────────────────────────────
async def is_subscribed(bot, query):
    return []

# ─────────────────────────────────────────────
# 🖼 IMAGE UPLOAD (Non-Blocking AIOHTTP)
# ─────────────────────────────────────────────
async def upload_image(file_path: str):
    """
    Uploads image using aiohttp (Non-Blocking)
    """
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field('files[]', f)
                
                async with session.post("https://uguu.se/upload", data=data) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        return res["files"][0]["url"].replace("\\/", "/")
    except Exception as e:
        logger.error(f"Upload Error: {e}")
    return None

# ─────────────────────────────────────────────
# 📦 UTILS (Fast Math & Time)
# ─────────────────────────────────────────────
def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    size = float(size)
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for name, sec in periods:
        if seconds >= sec:
            val, seconds = divmod(seconds, sec)
            result += f"{int(val)}{name}"
    return result or "0s"

def get_wish():
    # 🛠️ FIX: Server Timezone Issue (अब यह हमेशा Indian Time के हिसाब से विश करेगा)
    ist_time = datetime.now(ZoneInfo("Asia/Kolkata"))
    hour = ist_time.hour
    
    if hour < 12: return "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞"
    elif hour < 18: return "ɢᴏᴏᴅ ᴀꜰᴛᴇʀɴᴏᴏɴ 🌗"
    return "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"

async def get_seconds(time_string):
    match = re.match(r"(\d+)(s|min|hour|day|month|year)", time_string)
    if not match: return 0
    
    value, unit = int(match.group(1)), match.group(2)
    multipliers = {
        "s": 1, "min": 60, "hour": 3600, "day": 86400,
        "month": 2592000, "year": 31536000
    }
    return value * multipliers.get(unit, 0)
