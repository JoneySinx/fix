import re
import os
from os import environ
import logging
from Script import script

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🧠 HELPERS
# ─────────────────────────────────────────────
def is_enabled(key, default=False):
    val = environ.get(key, str(default)).lower()
    if val in ("true", "1", "yes", "y", "enable"): return True
    if val in ("false", "0", "no", "n", "disable"): return False
    logger.error(f"{key} has invalid value")
    exit(1)

def is_valid_ip(ip):
    ip_pattern = (
        r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    )
    return re.match(ip_pattern, ip) is not None

def get_channels(env_var):
    val = environ.get(env_var, "").replace(",", " ").strip()
    if not val: return []
    return [int(x) for x in val.split() if x.replace("-", "").isdigit()]

# ─────────────────────────────────────────────
# 🤖 BOT CREDENTIALS
# ─────────────────────────────────────────────
API_ID = int(environ.get("API_ID", "0"))
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.error("API_ID / API_HASH / BOT_TOKEN missing")
    exit(1)

BOT_ID = int(BOT_TOKEN.split(":")[0])
PORT = int(environ.get("PORT", 8000)) # कोएब के लिए 8000 पोर्ट सबसे बेस्ट और स्टेबल है

# ─────────────────────────────────────────────
# 👑 ADMINS
# ─────────────────────────────────────────────
ADMINS = environ.get("ADMINS", "")
if not ADMINS:
    logger.error("ADMINS missing")
    exit(1)
ADMINS = [int(x) for x in ADMINS.split()]

# ─────────────────────────────────────────────
# 🖼️ IMAGES
# ─────────────────────────────────────────────
PICS = environ.get("PICS", "https://i.postimg.cc/8C15CQ5y/1.png").split()
TMDB_API_KEY = environ.get("TMDB_API_KEY", "")

# ─────────────────────────────────────────────
# 📢 CHANNELS
# ─────────────────────────────────────────────
PRIMARY_CHANNEL = get_channels("PRIMARY_CHANNEL")
CLOUD_CHANNEL = get_channels("CLOUD_CHANNEL")
ARCHIVE_CHANNEL = get_channels("ARCHIVE_CHANNEL")

LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "0"))
if not LOG_CHANNEL:
    logger.error("LOG_CHANNEL missing")
    exit(1)

# ─────────────────────────────────────────────
# 🗄️ DATABASE
# ─────────────────────────────────────────────
DATABASE_URL = environ.get("DATABASE_URL", "")
DATABASE_NAME = environ.get("DATABASE_NAME", "Cluster0")

if not DATABASE_URL:
    logger.error("DATABASE_URL missing")
    exit(1)

# ─────────────────────────────────────────────
# ⚙️ BOT SETTINGS
# ─────────────────────────────────────────────
TIME_ZONE = environ.get("TIME_ZONE", "Asia/Kolkata")
DELETE_TIME = int(environ.get("DELETE_TIME", 3600))
CACHE_TIME = int(environ.get("CACHE_TIME", 300))
MAX_BTN = int(environ.get("MAX_BTN", 12)) # पेजिनेशन को सही रखने के लिए 21 बेस्ट है
PM_FILE_DELETE_TIME = int(environ.get("PM_FILE_DELETE_TIME", 3600))

GEMINI_API_KEY = environ.get("GEMINI_API_KEY", "")

# ─────────────────────────────────────────────
# 🧩 FEATURE FLAGS
# ─────────────────────────────────────────────
USE_CAPTION_FILTER = is_enabled("USE_CAPTION_FILTER", True)
AUTO_DELETE = is_enabled("AUTO_DELETE", True)
PROTECT_CONTENT = is_enabled("PROTECT_CONTENT", False)
SPELL_CHECK = is_enabled("SPELL_CHECK", True)
IS_STREAM = is_enabled("IS_STREAM", True)
IS_PREMIUM = is_enabled("IS_PREMIUM", True)

# ─────────────────────────────────────────────
# 📝 TEXT / CAPTION
# ─────────────────────────────────────────────
FILE_CAPTION = environ.get("FILE_CAPTION", script.FILE_CAPTION)

# ─────────────────────────────────────────────
# 🎥 STREAM CONFIG
# ─────────────────────────────────────────────
BIN_CHANNEL = int(environ.get("BIN_CHANNEL", "0"))
if not BIN_CHANNEL:
    logger.error("BIN_CHANNEL missing")
    exit(1)

URL = environ.get("URL", "").strip()
if not URL:
    logger.error("URL missing")
    exit(1)

# ✅ HTTPS Auto-Convert Logic
if URL.startswith("http://"):
    logger.warning(f"URL is HTTP, auto-converting to HTTPS: {URL}")
    URL = "https://" + URL[len("http://"):]

if URL.startswith("https://"):
    if not URL.endswith("/"): URL += "/"
elif is_valid_ip(URL):
    URL = f"https://{URL}/"
    logger.warning("IP-based URL detected. Telegram WebApp requires a valid HTTPS domain, not a plain IP.")
else:
    # कोएब डार्क डोमेन के लिए ऑटो-फॉर्मैटिंग बिल्ड पैच ताकि exit(1) क्रैश न हो
    if not URL.startswith("https://") and "." in URL:
        URL = "https://" + URL.rstrip("/") + "/"
    else:
        logger.error("Invalid URL - must start with https:// for Telegram WebApp support")
        exit(1)

# ─────────────────────────────────────────────
# 🎭 REACTIONS
# ─────────────────────────────────────────────
REACTIONS = environ.get("REACTIONS", "👍 ❤️ 🔥 😍 🤝").split()

# ─────────────────────────────────────────────
# 💎 PREMIUM CONFIG
# ─────────────────────────────────────────────
PRE_DAY_AMOUNT = int(environ.get("PRE_DAY_AMOUNT", 10))
UPI_ID = environ.get("UPI_ID", "").strip()
UPI_NAME = environ.get("UPI_NAME", "").strip()
RECEIPT_SEND_USERNAME = environ.get("RECEIPT_SEND_USERNAME", "").strip()

# ✅ SAFE FIX: UPI क्रेडेंशियल्स गायब होने पर प्रीमियम बंद नहीं होगा, 
# बल्कि बोट केवल लॉग्स में वार्निंग देगा ताकि आपका बोट हमेशा चलता रहे।
if not UPI_ID or not UPI_NAME:
    logger.warning("⚠️ UPI_ID or UPI_NAME is missing in environment variables. QR Code payment won't display correctly until set.")
