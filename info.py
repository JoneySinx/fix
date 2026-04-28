import re
from os import environ
import logging
import os
from Script import script

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🧠 HELPERS
# ─────────────────────────────────────────────
def is_enabled(key, default=False):
    val = environ.get(key, str(default)).lower()
    if val in ("true", "1", "yes", "y", "enable"):
        return True
    if val in ("false", "0", "no", "n", "disable"):
        return False
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
PORT = int(environ.get("PORT", 80))

# वेब पैनल के लिए (info.py में जोड़ें)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "yourx")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin143")



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
PICS = environ.get(
    "PICS",
    "https://i.postimg.cc/8C15CQ5y/1.png"
).split()


# ─────────────────────────────────────────────
# 📢 CHANNELS
# ─────────────────────────────────────────────
INDEX_CHANNELS = [
    int(x) if x.startswith("-") else x
    for x in environ.get("INDEX_CHANNELS", "").split()
]

LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "0"))
if not LOG_CHANNEL:
    logger.error("LOG_CHANNEL missing")
    exit(1)

SUPPORT_GROUP = int(environ.get("SUPPORT_GROUP", "0"))
if not SUPPORT_GROUP:
    logger.error("SUPPORT_GROUP missing")
    exit(1)


# ─────────────────────────────────────────────
# 🗄️ DATABASE (SINGLE DB – FINAL)
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
MAX_BTN = int(environ.get("MAX_BTN", 12))

LANGUAGES = environ.get(
    "LANGUAGES", "hindi english"
).lower().split()

QUALITY = environ.get(
    "QUALITY", "360p 480p 720p 1080p"
).lower().split()

# info.py के अंदर कहीं भी पेस्ट करें
GEMINI_API_KEY = environ.get("GEMINI_API_KEY", "Yaha_Apni_API_Key_Dalein")


PM_FILE_DELETE_TIME = int(environ.get("PM_FILE_DELETE_TIME", 3600))


# ─────────────────────────────────────────────
# 🧩 FEATURE FLAGS (CLEAN)
# ─────────────────────────────────────────────
USE_CAPTION_FILTER = is_enabled("USE_CAPTION_FILTER", True)
AUTO_DELETE = is_enabled("AUTO_DELETE", False)
WELCOME = is_enabled("WELCOME", False)
PROTECT_CONTENT = is_enabled("PROTECT_CONTENT", False)
SPELL_CHECK = is_enabled("SPELL_CHECK", True)
IS_STREAM = is_enabled("IS_STREAM", True)
IS_PREMIUM = is_enabled("IS_PREMIUM", True)


# ─────────────────────────────────────────────
# 📝 TEXT / CAPTION
# ─────────────────────────────────────────────
WELCOME_TEXT = environ.get("WELCOME_TEXT", script.WELCOME_TEXT)
FILE_CAPTION = environ.get("FILE_CAPTION", script.FILE_CAPTION)


# ─────────────────────────────────────────────
# 🎥 STREAM CONFIG
# ─────────────────────────────────────────────
BIN_CHANNEL = int(environ.get("BIN_CHANNEL", "0"))
if not BIN_CHANNEL:
    logger.error("BIN_CHANNEL missing")
    exit(1)

URL = environ.get("URL", "")
if not URL:
    logger.error("URL missing")
    exit(1)

if URL.startswith(("http://", "https://")):
    if not URL.endswith("/"):
        URL += "/"
elif is_valid_ip(URL):
    URL = f"http://{URL}/"
else:
    logger.error("Invalid URL")
    exit(1)


# ─────────────────────────────────────────────
# 🎭 REACTIONS / STICKERS
# ─────────────────────────────────────────────
REACTIONS = environ.get(
    "REACTIONS",
    "👍 ❤️ 🔥 😍 🤝"
).split()

STICKERS = environ.get(
    "STICKERS", ""
).split()


# ─────────────────────────────────────────────
# 💎 PREMIUM
# ─────────────────────────────────────────────
PRE_DAY_AMOUNT = int(environ.get("PRE_DAY_AMOUNT", 10))
UPI_ID = environ.get("UPI_ID", "")
UPI_NAME = environ.get("UPI_NAME", "")
RECEIPT_SEND_USERNAME = environ.get(
    "RECEIPT_SEND_USERNAME", ""
)

if not UPI_ID or not UPI_NAME:
    IS_PREMIUM = False
