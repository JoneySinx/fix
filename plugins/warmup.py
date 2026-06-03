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
# 🧠 CORE ENGINE — Rebuilt With Strict Thumbnail Validation
# ─────────────────────────────────────────────────────────
async def start_warmup_engine(client, status_msg, user_id):
    logger.info(f"⚡ [WARMUP] Strict smart pipeline triggered by admin: {user_id}")

    # SMART FILTER: सिर्फ वही डॉक्यूमेंट्स निकालें जिनमें थंबनेल मिसिंग है और file_id मौजूद है
    query = {
        "$and": [
            {
                "$or": [
                    {"thumb_url": None},
                    {"thumb_url": {"$exists": False}},
                    {"thumb_url": {"$not": {"$regex": "^TG_ID:"}}}
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
        return await status_msg.edit("✨ <b>FAST FINDER DATABASE STATUS</b>\n\n🎉 <code>Everything is up to date!</code>\nAll files inside your library collections already possess verified active thumbnail cache locks.")

    await status_msg.edit(f"📊 <b>Smart Filter Active:</b> Found <code>{total_to_process:,}</code> files needing warmup.\nInitializing single-bot safe stream pipeline...")
    
    processed, success, skipped = 0, 0, 0
    start_time = time.time()

    for col_name, collection in COLLECTIONS.items():
        if col_counts[col_name] == 0: continue

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

                try:
                    msg = await client.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
                    thumb_id = None
                    
                    if msg.video and msg.video.thumbs:
                        thumb_id = msg.video.thumbs[0].file_id
                    elif msg.document and msg.document.thumbs:
                        thumb_id = msg.document.thumbs[0].file_id

                    # 👑 ✅ CRITICAL FIXED: सख्त ओरिजिनल थंबनेल वेरिफिकेशन गेटवे लॉक
                    # अगर थंबनेल आईडी गायब है, 'NO_THUMB' स्ट्रिंग है, या टेलीग्राम की लीगल आईडी नहीं है, तो तुरंत रिजेक्ट करो!
                    if thumb_id and isinstance(thumb_id, str) and len(str(thumb_id).strip()) > 20 and "NO_THUMB" not in str(thumb_id):
                        db_save_value = f"TG_ID:{thumb_id}"
                        res = await collection.update_one({"_id": doc["_id"]}, {"$set": {"thumb_url": db_save_value}})
                        if res.modified_count:
                            success += 1
                            print(f"💾 [LOCKED] ({processed}/{total_to_process}) ✅ SUCCESS: {file_label}", flush=True)
                    else:
                        # कचरा एंट्री को डेटाबेस में घुसने से यहीं पर ब्लॉक कर दिया गया
                        skipped += 1
                        print(f"🚫 [REJECTED FAKE THUMB] File has no real embedded poster -> Skipped DB Lock: {file_label}", flush=True)

                    # इनबॉक्स क्लींजर (No Memory Leak)
                    try: await msg.delete()
                    except: pass

                    # 🛡️ 1.0 से 5.0 सेकंड का रैंडम ह्यूमन डिले (0% Flood Wait Risk)
                    await asyncio.sleep(random.uniform(1.0, 5.0))

                except FloodWait as e:
                    print(f"⏳ [FLOOD ACTIVE] Rate limit hit! Sleeping {e.value + 10}s...", flush=True)
                    try: await status_msg.edit(f"⏳ <b>Telegram Network Overload Detected!</b>\nSleeping for <code>{e.value + 10}s</code> to bypass flood restriction safely...")
                    except: pass
                    await asyncio.sleep(e.value + 10)

                except BadRequest:
                    skipped += 1
                    print(f"❌ [BROKEN REF] Defective Telegram File Reference ID Skipped: {file_label}", flush=True)
                except Exception as e:
                    print(f"❌ [WARN] Processing error: {str(e)[:50]}", flush=True)
                    await asyncio.sleep(2)

                # हर 10 फाइल्स कंप्लीट होने पर लक्ज़री यूआई अपडेट होगा
                if processed % 10 == 0 or processed == total_to_process:
                    elapsed = time.time() - start_time
                    eta = (total_to_process - processed) * (elapsed / max(processed, 1))
                    speed = (processed / max(elapsed, 1)) * 60

                    status_text = get_warmup_ui(col_name, processed, total_to_process, success, skipped, elapsed, eta, speed)
                    try: await status_msg.edit(status_text)
                    except MessageNotModified: pass
                    except Exception: pass

                    gc.collect() # कोएब रैम फ्लश बूस्टर
        finally:
            await cursor.close() # कर्सर हमेशा बंद होगा (Zero RAM Leak Guard)

    # फाइनल कंप्लीशन रिपोर्ट
    total_elapsed = time.time() - start_time
    final_report = (
        f"🎉 <b>THUMBNAIL WARMUP SYSTEM ACCOMPLISHED</b>\n"
        f"──────────────────────────────\n\n"
        f"🎯 <b>Total Scanned Docs:</b> <code>{processed:,}</code>\n"
        f"🔒 <b>Verified Valid Locked:</b> <code>{success:,} Images</code>\n"
        f"⚠️ <b>Rejected Garbage Junk:</b> <code>{skipped:,} Files</code>\n"
        f"🕐 <b>Total Processing Time:</b> <code>{get_readable_time(total_elapsed)}</code>\n\n"
        f"⚡ <i>Web application, Mini App & streaming players will load instantly now with pure original posters!</i>"
    )
    try: await status_msg.reply(final_report)
    except: pass

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
    try: await query.message.edit_reply_markup(reply_markup=None)
    except: pass
    await start_warmup_engine(client, query.message, query.from_user.id)
