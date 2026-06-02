import logging
import asyncio
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from hydrogram.errors import FloodWait
from hydrogram import enums

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
    CANCEL = False 
    ADMIN_TOKENS, ADMIN_SESSIONS, FILES, PM_FILES = {}, {}, {}, {}

# ─────────────────────────────────────────────
# 🛡️ RATE LIMITER UTILITY (Memory Leak Fixed)
# ─────────────────────────────────────────────
_rate_limits = {}

def is_rate_limited(user_id, action, seconds):
    """हैवी कमांड्स पर स्पैम रोकता है और रैम लीक से सुरक्षित रखता है।"""
    key = f"{user_id}:{action}"
    now = time.time()
    
    # स्मार्ट पीरियोडिक क्लीनअप (Koyeb RAM Safe)
    if len(_rate_limits) > 500:
        cutoff = now - 60 
        expired_keys = [k for k, v in _rate_limits.items() if v < cutoff]
        for k in expired_keys:
            _rate_limits.pop(k, None)
            
    if key in _rate_limits and now - _rate_limits[key] < seconds:
        return True
        
    _rate_limits[key] = now
    return False

# ─────────────────────────────────────────────
# 👮 ADMIN CHECK
# ─────────────────────────────────────────────
async def is_check_admin(bot, chat_id, user_id):
    try:
        return (await bot.get_chat_member(chat_id, user_id)).status in (
            enums.ChatMemberStatus.ADMINISTRATOR, 
            enums.ChatMemberStatus.OWNER
        )
    except: 
        return False

# ─────────────────────────────────────────────
# 💎 PREMIUM SYSTEM (Timezone Synchronized)
# ─────────────────────────────────────────────
async def is_premium(user_id, bot=None):
    if not IS_PREMIUM or user_id in ADMINS: 
        return True
        
    mp = await db.get_plan(user_id)
    if not mp.get("premium"): 
        return False
    
    expire = mp.get("expire")
    if expire:
        if isinstance(expire, str):
            try: 
                expire = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
            except: 
                expire = None
        
        # सर्वरलेस आर्किटेक्चर और डेटाबेस सिंकिंग के लिए टाइमज़ोन मुक्त शुद्ध लोकल कॉम्पैरिजन
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
        if not expire or expire < now_ist:
            if bot:
                try: 
                    await bot.send_message(user_id, f"❌ Your premium {mp.get('plan')} plan has expired.\n\nUse /plan to renew.")
                except: 
                    pass
            
            # प्रीमियम खत्म होने पर सारे रिमाइंडर फ्लैग्स और डेटा को रीसेट करें
            await db.update_plan(user_id, {
                "expire": "", 
                "plan": "", 
                "premium": False,
                "reminded_12h": False, 
                "reminded_6h": False, 
                "reminded_3h": False, 
                "reminded_1h": False, 
                "reminded_30m": False, 
                "reminded_10m": False,
                "last_reminder_id": 0
            })
            return False
    return True

# ─────────────────────────────────────────────
# 📢 BROADCAST UTILITY
# ─────────────────────────────────────────────
async def broadcast_messages(chat_id, message, pin=False, is_group=False):
    try:
        msg = await message.copy(chat_id=chat_id)
        if pin:
            try: 
                await msg.pin(both_sides=not is_group)
            except: 
                pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(chat_id, message, pin, is_group)
    except Exception:
        # कतार लोड को नियंत्रित रखते हुए मोंगोडीबी पर केवल आवश्यक एरर फ्लैग्स अपडेट करना
        if is_group:
            try:
                await db.groups.update_one(
                    {"id": int(chat_id)},
                    {"$set": {"chat_status": {"is_disabled": True, "reason": "Bot removed from group"}}}
                )
            except: 
                pass
        else:
            try:
                await db.delete_user(int(chat_id))
            except:
                pass
        return "Error"

# ─────────────────────────────────────────────
# ⚙️ TTL CACHE FOR SETTINGS (High Performance)
# ─────────────────────────────────────────────
_settings_cache = {}
_CACHE_TTL = 300 

async def get_settings(group_id):
    now = time.time()
    if group_id in _settings_cache:
        data, ts = _settings_cache[group_id]
        if now - ts < _CACHE_TTL:
            return data
    
    data = await db.get_settings(group_id)
    _settings_cache[group_id] = (data, now)
    return data

async def save_group_settings(group_id, key, value):
    data = await get_settings(group_id)
    data[key] = value
    _settings_cache[group_id] = (data, time.time())
    await db.update_settings(group_id, data)

# ─────────────────────────────────────────────
# 📦 UTILS (Formatting & Time)
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
    h = datetime.now(ZoneInfo("Asia/Kolkata")).hour
    return "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞" if h < 12 else "ɢᴏᴏᴅ ᴀꜰᴛᴇʀɴᴏᴏ afternoon 🌗" if h < 18 else "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"

async def get_seconds(time_string):
    match = re.match(r"(\d+)(s|min|hour|day|month|year)", time_string)
    if not match: 
        return 0
    return int(match.group(1)) * {
        "s": 1, "min": 60, "hour": 3600, "day": 86400,
        "month": 2592000, "year": 31536000
    }.get(match.group(2), 0)

# 🛠️ Helpers for premium and cleanup
def parse_expire_time(e):
    if isinstance(e, datetime): 
        return e
    try: 
        return datetime.strptime(e, "%Y-%m-%d %H:%M:%S") if e else None
    except: 
        return None

def get_ist_str(dt):
    return (dt + timedelta(hours=5, minutes=30)).strftime("%d %B %Y, %I:%M %p") if dt else "Unknown"

async def safe_del(c, cid, mids):
    try: 
        await c.delete_messages(cid, mids)
    except: 
        pass
