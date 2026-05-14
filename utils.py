import logging, asyncio, re, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from hydrogram.errors import FloodWait
from hydrogram import enums

from info import ADMINS, IS_PREMIUM, LOG_CHANNEL
from database.users_chats_db import db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🧠 TEMP RUNTIME STORAGE (Cleaned)
# ─────────────────────────────────────────────
class temp(object):
    START_TIME = 0
    BANNED_USERS, BANNED_CHATS = [], []
    ME, BOT, U_NAME, B_NAME = None, None, None, None
    CANCEL = False # फालतू CANCEL वेरिएबल्स हटा दिए गए
    ADMIN_TOKENS, ADMIN_SESSIONS, FILES, PM_FILES = {}, {}, {}, {}

# ─────────────────────────────────────────────
# 🛡️ RATE LIMITER UTILITY (Anti-Abuse & Memory Leak Fixed)
# ─────────────────────────────────────────────
_rate_limits = {}

def is_rate_limited(user_id, action, seconds):
    """हैवी कमांड्स जैसे /ask, spell check, और /link पर स्पैम रोकता है।"""
    key = f"{user_id}:{action}"
    now = time.time()
    
    # 🧹 Auto-Cleanup: अगर 1000 से ज़्यादा एंट्रीज़ हों, तो 1 घंटे पुरानी हटा दो
    if len(_rate_limits) > 1000:
        cutoff = now - 3600 
        for k in [k for k, v in _rate_limits.items() if v < cutoff]:
            del _rate_limits[k]
            
    if key in _rate_limits and now - _rate_limits[key] < seconds:
        return True
        
    _rate_limits[key] = now
    return False

# ─────────────────────────────────────────────
# 👮 ADMIN CHECK
# ─────────────────────────────────────────────
async def is_check_admin(bot, chat_id, user_id):
    try:
        return (await bot.get_chat_member(chat_id, user_id)).status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
    except: return False

# ─────────────────────────────────────────────
# 💎 PREMIUM SYSTEM (Centralized & Crash-Proof)
# ─────────────────────────────────────────────
# ✅ FIX: bot पैरामीटर को डिफ़ॉल्ट रूप से None कर दिया गया है
async def is_premium(user_id, bot=None):
    if not IS_PREMIUM or user_id in ADMINS: return True
    mp = await db.get_plan(user_id)
    if not mp.get("premium"): return False
    
    expire = mp.get("expire")
    if expire:
        if isinstance(expire, str):
            try: expire = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
            except: expire = None
        
        if not expire or expire < datetime.now():
            # ✅ CRITICAL FIX: अगर bot None हुआ (जैसे बैकग्राउंड टास्क में) तो यहाँ क्रैश नहीं होगा
            if bot:
                try: 
                    await bot.send_message(user_id, f"❌ Your premium {mp.get('plan')} plan has expired.\n\nUse /plan to renew.")
                except: pass
            
            await db.update_plan(user_id, {"expire": "", "plan": "", "premium": False})
            return False
    return True

# ─────────────────────────────────────────────
# 📢 BROADCAST
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
            except: pass
        else:
            await db.delete_user(int(chat_id))
        return "Error"

# ─────────────────────────────────────────────
# ⚙️ TTL CACHE FOR SETTINGS (High Performance)
# ─────────────────────────────────────────────
_settings_cache = {}
_CACHE_TTL = 300 # 5 मिनट

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
    # 🇮🇳 IST समय के अनुसार विश
    h = datetime.now(ZoneInfo("Asia/Kolkata")).hour
    return "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞" if h < 12 else "ɢᴏᴏᴅ ᴀꜰᴛᴇʀɴᴏᴏɴ 🌗" if h < 18 else "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"

async def get_seconds(time_string):
    match = re.match(r"(\d+)(s|min|hour|day|month|year)", time_string)
    if not match: return 0
    return int(match.group(1)) * {
        "s": 1, "min": 60, "hour": 3600, "day": 86400,
        "month": 2592000, "year": 31536000
    }.get(match.group(2), 0)

# 🛠️ Helpers for premium and cleanup
def parse_expire_time(e):
    if isinstance(e, datetime): return e
    try: return datetime.strptime(e, "%Y-%m-%d %H:%M:%S") if e else None
    except: return None

def get_ist_str(dt):
    return (dt + timedelta(hours=5, minutes=30)).strftime("%d %B %Y, %I:%M %p") if dt else "Unknown"

async def safe_del(c, cid, mids):
    try: await c.delete_messages(cid, mids)
    except: pass
