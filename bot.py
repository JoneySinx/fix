import logging
import asyncio
import os
import time
import signal
from typing import Union, AsyncGenerator
from datetime import datetime
import pytz

# ==========================================================
# 🔥 UVLOOP (High Performance Event Loop)
# ==========================================================
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

# ==========================================================
# LOGGING SETUP
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('hydrogram').setLevel(logging.ERROR)
# ✅ Suppress noisy logs from aiohttp & uptime probes (Perfect for Koyeb)
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
logging.getLogger('aiohttp.server').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ==========================================================
# IMPORTS
# ==========================================================
from aiohttp import web
from hydrogram import Client, types
from hydrogram.errors import FloodWait
from web import web_app
from info import (
    API_ID, API_HASH, BOT_TOKEN, PORT, ADMINS, 
    LOG_CHANNEL, DATABASE_URL, DATABASE_NAME
)
from utils import temp
from database.users_chats_db import db

# ⚡ IMPORTANT: Import Database Indexer
from database.ia_filterdb import ensure_indexes

# -------------------- IMPORT PREMIUM MODULE --------------------
from plugins.premium import check_premium_expired

# ==========================================================
# BOT CLASS
# ==========================================================
class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Auto_Filter_Bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )
        # ✅ Instance variables for safe cleanup
        self._runner = None 
        self._premium_task = None 

    async def start(self):
        # 1. Start Client
        await super().start()
        temp.START_TIME = time.time()

        # 2. Initialize Database Indexes
        await ensure_indexes()
        await db._ensure_indexes() # ✅ FIX: Added users_chats_db indexer here to prevent RuntimeError
        logger.info("✅ Database Indexes Checked/Created")

        # 3. Load banned users & chats (Safe Loading)
        try:
            b_users, b_chats = await db.get_banned()
            temp.BANNED_USERS = b_users
            temp.BANNED_CHATS = b_chats
        except Exception as e:
            logger.error(f"Error loading banned list: {e}")

        # 4. Restart Handler (Safe Context Manager)
        if os.path.exists("restart.txt"):
            try:
                with open("restart.txt", "r") as f:
                    content = f.read().strip().split()
                    if len(content) == 2:
                        chat_id, msg_id = map(int, content)
                        await self.edit_message_text(
                            chat_id=chat_id,
                            message_id=msg_id,
                            text="✅ Restarted Successfully!"
                        )
            except Exception as e:
                logger.error(f"Restart message error: {e}")
            finally:
                os.remove("restart.txt")

        # 5. Set Bot Identity
        temp.BOT = self
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name

        # 6. Start Web Server (Essential for Koyeb Health Checks)
        self._runner = web.AppRunner(web_app, access_log=None)
        await self._runner.setup()
        await web.TCPSite(self._runner, "0.0.0.0", PORT).start()
        logger.info(f"✅ Web Server Started on Port {PORT}")

        # 7. Start Premium Checker Task (Saved reference avoids GC)
        self._premium_task = asyncio.create_task(check_premium_expired(self))

        # 8. Send Startup Logs
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        
        startup_msg = (
            f"🤖 <b>Bot Started Successfully!</b>\n\n"
            f"📅 <b>Date:</b> {now.strftime('%d %B %Y')}\n"
            f"🕐 <b>Time:</b> {now.strftime('%I:%M:%S %p')}\n"
            f"🌏 <b>Timezone:</b> IST (Asia/Kolkata)\n"
            f"🚀 <b>Speed:</b> Koyeb Optimized (Async/Motor)\n"
            f"✅ <b>Status:</b> Online"
        )

        # ✅ Parallel Admin Notify with FloodWait protection
        async def _safe_send(admin_id):
            try:
                await self.send_message(admin_id, startup_msg)
            except FloodWait as e:
                await asyncio.sleep(e.value) # Handle rate limits
                await self.send_message(admin_id, startup_msg)
            except Exception:
                pass

        await asyncio.gather(*[_safe_send(aid) for aid in ADMINS])

        # Log Channel Notify
        if LOG_CHANNEL:
            try:
                await self.send_message(
                    LOG_CHANNEL,
                    f"<b>{me.mention} restarted successfully 🤖</b>"
                )
            except Exception as e:
                logger.warning(f"Failed to send log to LOG_CHANNEL: {e}")

        logger.info(f"@{me.username} is Online & Ready!")

    async def stop(self, *args):
        # ✅ Clean up Web Server & Background Tasks
        if getattr(self, '_runner', None):
            await self._runner.cleanup()
            logger.info("✅ Web Server Cleanup Complete")
        
        if getattr(self, '_premium_task', None):
            self._premium_task.cancel()
            logger.info("✅ Premium Task Cancelled")

        await super().stop()
        logger.info("Bot stopped Gracefully. Bye 👋")

    # ✅ Correct Return Type Annotation & NoneType handling
    async def iter_messages(
        self: Client,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0
    ) -> AsyncGenerator["types.Message", None]:
        current = offset
        while current < limit:
            diff = min(200, limit - current)
            try:
                messages = await self.get_messages(
                    chat_id,
                    list(range(current, current + diff))
                )
                for message in messages:
                    # Skip deleted/empty messages to prevent indexer crash
                    if message and not message.empty: 
                        yield message
                current += diff
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                return

# ==========================================================
# MAIN EXECUTION (Graceful Shutdown Added)
# ==========================================================
async def main():
    bot = Bot()
    await bot.start()
    
    # ✅ Catch Koyeb's Stop Signals for safe shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass # Fallback if running on Windows locally

    await stop_event.wait()
    await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # Prevents ugly traceback on Ctrl+C
