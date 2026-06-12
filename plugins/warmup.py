import re
import time
import random
import asyncio
import gc
import logging
from hydrogram import Client, filters
from hydrogram.errors import FloodWait, MessageNotModified, BadRequest
from info import ADMINS, BIN_CHANNEL
from utils import get_readable_time
from database.ia_filterdb import COLLECTIONS

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# 🎨 LUXURY MINIMALIST UI PANEL GENERATOR
# ─────────────────────────────────────────────────────────
def get_warmup_ui(col_name, processed, total, success, skipped, elapsed, eta, speed):
    percent = int((processed / max(total, 1)) * 100)
    dot = "🔴" if percent < 30 else ("🟡" if percent < 70 else "🟢")
    
    lines = [
        f"🎬 <b>FAST FINDER - THUMBNAIL WARMUP CONSOLE</b>",
        f"──────────────────────────────",
        f"📁 <b>Repository Hub :</b> <code>{col_name.upper()}</code>",
        f"📈 <b>Pipeline Index :</b> <code>{processed:,} / {total:,}</code>",
        f"🔒 <b>Strict Locked  :</b> <code>{success:,} Thumbs</code>",
        f"⚠️ <b>Rejected Junk  :</b> <code>{skipped:,} Files</code>",
        f"⏱️ <b>Time Remaining :</b> <code>{get_readable_time(eta)}</code>",
        f"⚡ <b>Stream Velocity:</b> <code>{speed:.1f} f/min</code>",
        f"──────────────────────────────",
        f"{dot} <b>Core Progress Matrix:</b> <code>| {percent}% Synced |</code>",
        f"\n<i>📡 Logs are streaming live on Koyeb Console!</i>"
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────
# 🧠 CORE ENGINE
# ─────────────────────────────────────────────────────────
async def start_warmup_engine(client, status_msg, user_id):
    logger.info(f"⚡ [WARMUP] Strict smart pipeline triggered by admin: {user_id}")

    # SMART FILTER: सिर्फ वही docs जिनमें thumb missing है, file_id मौजूद है
    # FIX: $not के अंदर compiled re.compile() — plain {"$regex":...} dict Motor में silently fail करती है
    query = {
        "$and": [
            {
                "$or": [
                    {"thumb_url": {"$exists": False}},
                    {"thumb_url": None},
                    {"thumb_url": "NO_THUMB"},
                    {"thumb_url": {"$not": re.compile(r"^TG_ID:")}},
                ]
            },
            {
                "$or": [
                    {"file_ref": {"$exists": True, "$ne": None}},
                    {"file_id": {"$exists": True, "$ne": None}}
                ]
            }
        ]
    }

    # पेंडिंग काउंट्स सिंक फेज
    total_to_process = 0
    col_counts = {}
    for name, collection in COLLECTIONS.items():
        count = await collection.count_documents(query)
        col_counts[name] = count
        total_to_process += count

    if total_to_process == 0:
        return await status_msg.edit(
            "✨ <b>FAST FINDER DATABASE STATUS</b>\n\n"
            "🎉 <code>Everything is up to date!</code>\n"
            "All files inside your library collections already possess verified active thumbnail cache locks."
        )

    await status_msg.edit(
        f"📊 <b>Smart Filter Active:</b> Found <code>{total_to_process:,}</code> files needing warmup.\n"
        f"Initializing single-bot safe stream pipeline..."
    )

    processed, success, skipped = 0, 0, 0
    start_time = time.time()

    # ─── Adaptive delay state ───────────────────────────────
    # Flood आने पर delay बढ़ता है, smooth रहने पर धीरे-धीरे घटता है
    # Min: 0.4s  |  Max: 3.0s  |  Start: 0.8s
    DELAY_MIN   = 0.4
    DELAY_MAX   = 3.0
    DELAY_STEP_UP   = 0.5   # FloodWait के बाद बढ़ाव
    DELAY_STEP_DOWN = 0.05  # हर सफल file पर घटाव
    cur_delay = 0.8
    # ────────────────────────────────────────────────────────

    for col_name, collection in COLLECTIONS.items():
        if col_counts[col_name] == 0:
            continue

        logger.info(f"📁 [WARMUP] Running secure loop over: {col_name.upper()}")
        cursor = collection.find(query, {"_id": 1, "file_ref": 1, "file_id": 1, "file_name": 1})

        try:
            async for doc in cursor:
                fid = doc.get("file_ref") or doc.get("file_id")
                if not fid:
                    skipped += 1
                    continue

                processed += 1
                file_label = doc.get("file_name", "Unknown File")[:35]
                msg = None  # guard — FloodWait/Exception पर msg कभी None रहे

                try:
                    msg = await client.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
                    thumb_id = None

                    if msg.video and msg.video.thumbs:
                        thumb_id = msg.video.thumbs[0].file_id
                    elif msg.document and msg.document.thumbs:
                        thumb_id = msg.document.thumbs[0].file_id

                    # ✅ Strict thumb validation — NO_THUMB/garbage DB में घुसने नहीं देना
                    if (
                        thumb_id
                        and isinstance(thumb_id, str)
                        and len(thumb_id.strip()) > 20
                        and "NO_THUMB" not in thumb_id
                    ):
                        db_val = f"TG_ID:{thumb_id}"
                        res = await collection.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {"thumb_url": db_val}}
                        )
                        if res.modified_count:
                            success += 1
                            print(f"💾 [LOCKED] ({processed}/{total_to_process}) ✅ {file_label}", flush=True)
                    else:
                        # thumb नहीं है — DB को हाथ मत लगाओ, बस skip
                        skipped += 1
                        print(f"🚫 [NO POSTER] Skipped (no real thumb): {file_label}", flush=True)

                    # Message delete — background में, pipeline block नहीं होगा
                    asyncio.ensure_future(_safe_delete(msg))

                    # Adaptive delay — smooth चले तो थोड़ा और घटाओ
                    cur_delay = max(DELAY_MIN, cur_delay - DELAY_STEP_DOWN)
                    await asyncio.sleep(cur_delay)

                except FloodWait as e:
                    # ⚠️ CRITICAL: FloodWait पर thumb_url को TOUCH नहीं करना — NO_THUMB save नहीं होगा
                    # Message delete करो अगर भेजा था
                    if msg:
                        asyncio.ensure_future(_safe_delete(msg))

                    wait_sec = e.value + 10
                    cur_delay = min(DELAY_MAX, cur_delay + DELAY_STEP_UP)
                    print(f"⏳ [FLOOD] Rate limit! Sleeping {wait_sec}s, next delay={cur_delay:.2f}s", flush=True)
                    try:
                        await status_msg.edit(
                            f"⏳ <b>Telegram Rate Limit Hit!</b>\n"
                            f"Sleeping <code>{wait_sec}s</code> — pipeline will auto-resume.\n"
                            f"📈 Progress so far: <code>{processed:,}/{total_to_process:,}</code>"
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(wait_sec)
                    # इस file को re-process नहीं करेंगे (processed count already बढ़ा)
                    # अगली बार warmup चलाने पर यह file फिर से pick होगी

                except BadRequest:
                    skipped += 1
                    if msg:
                        asyncio.ensure_future(_safe_delete(msg))
                    print(f"❌ [BAD REF] Broken file_id skipped: {file_label}", flush=True)

                except Exception as e:
                    if msg:
                        asyncio.ensure_future(_safe_delete(msg))
                    print(f"❌ [WARN] Processing error: {str(e)[:80]}", flush=True)
                    await asyncio.sleep(2)

                # हर 10 files पर UI update
                if processed % 10 == 0 or processed == total_to_process:
                    elapsed = time.time() - start_time
                    eta     = (total_to_process - processed) * (elapsed / max(processed, 1))
                    speed   = (processed / max(elapsed, 1)) * 60
                    status_text = get_warmup_ui(col_name, processed, total_to_process, success, skipped, elapsed, eta, speed)
                    try:
                        await status_msg.edit(status_text)
                    except MessageNotModified:
                        pass
                    except Exception:
                        pass

                    gc.collect()

        finally:
            await cursor.close()

    # Final completion report
    total_elapsed = time.time() - start_time
    final_report = (
        f"🎉 <b>THUMBNAIL WARMUP SYSTEM ACCOMPLISHED</b>\n"
        f"──────────────────────────────\n\n"
        f"🎯 <b>Total Scanned Docs:</b> <code>{processed:,}</code>\n"
        f"🔒 <b>Verified Valid Locked:</b> <code>{success:,} Images</code>\n"
        f"⚠️ <b>Rejected / No Poster:</b> <code>{skipped:,} Files</code>\n"
        f"🕐 <b>Total Processing Time:</b> <code>{get_readable_time(total_elapsed)}</code>\n\n"
        f"⚡ <i>Web app, Mini App & streaming players will load instantly with original posters!</i>"
    )
    try:
        await status_msg.reply(final_report)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# 🗑 BACKGROUND DELETE HELPER — Pipeline block नहीं होगा
# ─────────────────────────────────────────────────────────
async def _safe_delete(msg):
    try:
        await msg.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# 📢 COMMAND ROUTE — /warmup_thumbs (ADMIN ONLY)
# ─────────────────────────────────────────────────────────
@Client.on_message(filters.command("warmup_thumbs") & filters.user(ADMINS))
async def warmup_thumbs_cmd(client, message):
    status_msg = await message.reply("⚙️ <b>Warmup Initialization Core Starting...</b>")
    await start_warmup_engine(client, status_msg, message.from_user.id)


# ─────────────────────────────────────────────────────────
# 🔘 BUTTON ROUTE — 🔄 WARMUP THUMBNAILS BUTTON CALLBACK
# ─────────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^warmup_trigger_all$"))
async def warmup_callback_handler(client, query):
    if query.from_user.id not in ADMINS:
        return await query.answer("❌ Verification Access Denied! Admin credentials required.", show_alert=True)
    await query.answer("⚙️ Thumbnail Warmup Initiated! Starting Background Pipeline...", show_alert=False)
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await start_warmup_engine(client, query.message, query.from_user.id)
