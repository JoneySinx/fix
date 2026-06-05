import io
import os
import re
import json
import time
import hmac
import gc
import hashlib
import asyncio
import logging
import urllib.parse
from aiohttp import web

# कस्टमाइज्ड कोर यूटिल्स और कन्फर्म कंट्रोल्स इम्पोर्ट्स
from utils import temp, get_size, is_rate_limited, is_premium
from info import BIN_CHANNEL, ADMINS, BOT_TOKEN, MAX_WEB_RESULTS, MAX_THUMB_CACHE, IS_PREMIUM
from database.ia_filterdb import COLLECTIONS
from database.users_chats_db import db

logger = logging.getLogger(__name__)

search_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 📸 THUMBNAIL CONCURRENCY & info.py CACHE BALANCER
# ─────────────────────────────────────────────────────────
# कोएब रैम की पूर्ण सुरक्षा के लिए इसे info.py के थ्रेशोल्ड वेरिएबल से लिंक रखा गया है
MAX_CACHE = MAX_THUMB_CACHE             
thumb_cache = {}
thumb_semaphore = asyncio.Semaphore(5) 

# ─────────────────────────────────────────────────────────
# 🔒 STRICT SECURITY: Telegram initData HMAC Verification
# ─────────────────────────────────────────────────────────
def verify_telegram_init_data(init_data: str) -> dict | None:
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash: return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash): return None
        user_str = parsed.get("user", "{}")
        return json.loads(user_str)
    except Exception: return None

async def get_user_role(req):
    init_data = req.headers.get("X-Telegram-Init-Data", "").strip()
    if init_data:
        user = verify_telegram_init_data(init_data)
        if user:
            tg_id = int(user.get("id", 0))
            if tg_id:
                if tg_id in ADMINS: return "admin", tg_id
                if await is_premium(tg_id): return "user", tg_id
                if not IS_PREMIUM: return "user", tg_id
        return None, None
        
    s_user = req.cookies.get("user_session")
    if s_user and hasattr(temp, "USER_SESSIONS"):
        session = temp.USER_SESSIONS.get(s_user, {})
        if session.get("expiry", 0) > time.time():
            tg_id = session["tg_id"]
            if tg_id in ADMINS: return "admin", tg_id
            if await is_premium(tg_id): return "user", tg_id
    return None, None

# ─────────────────────────────────────────────────────────
# 🔍 SEARCH API — Rebuilt Grid Engine (With Cache Buster Sync)
# ─────────────────────────────────────────────────────────
@search_routes.get("/api/search")
async def api_search(req):
    role, tg_id = await get_user_role(req)
    if not role: return web.json_response({"error": "Unauthorized Access! Please login through Mini App."}, status=403)
    if is_rate_limited(tg_id, "web_search", 1): 
        return web.json_response({"error": "Spam Protection: Searching too fast!"}, status=429)

    q = req.query.get("q", "").strip()
    off = req.query.get("offset", "0")
    col = req.query.get("col", "all").lower()
    mode = req.query.get("mode", "tg").lower()

    if not q: return web.json_response({"results": [], "total": 0, "next_offset": ""})
    try: off = max(0, int(off))
    except: off = 0

    flt_text = {"$text": {"$search": q}}
    flt_regex = {"file_name": re.compile(re.escape(q), re.IGNORECASE)}
    
    # ✅ ३-कॉलम नेटफ्लिक्स ग्रिड को परफेक्ट अलाइन रखने के लिए २१ रिज़ल्ट्स पर सख्त लॉक (MAX_WEB_RESULTS)
    all_m, lim = [], MAX_WEB_RESULTS
    tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS

    # 🚀 SPEED UP: बिना भारी काउंट किए सीधे कलेक्शन्स से डेटा फेच करें
    remaining_skip = off
    for n, c in tgt_cols.items():
        if len(all_m) >= lim: break
        
        local_limit = lim - len(all_m)
        # पहले तेज़ टेक्स्ट सर्च ट्राई करें
        docs = await c.find(flt_text, {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "thumb_url": 1}).sort("_id", -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
        
        # अगर टेक्स्ट सर्च से कुछ न मिले, तो फ़ॉलबैक regex सर्च करें
        if not docs and remaining_skip == 0:
            docs = await c.find(flt_regex, {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "thumb_url": 1}).sort("_id", -1).limit(local_limit).to_list(length=local_limit)
            
        if docs:
            for d in docs: d["source_col"] = n.lower()
            all_m.extend(docs)
            remaining_skip = max(0, remaining_skip - len(docs))

    # 🚀 SPEED UP: process_doc को बिना asyncio.gather के डायरेक्ट सिंक लूप में प्रोसेस करें
    results_list = []
    thumb_salt = int(time.time() * 100)
    
    for d in all_m:
        fid = d.get("file_ref") or d.get("_id")
        db_id = d.get("_id")
        tg_thumb = f"/api/thumb?file_id={db_id}&v={thumb_salt}"
        
        results_list.append({
            "file_id": db_id,
            "name": d.get("file_name", "Unknown File"),
            "size": get_size(d.get("file_size", 0)),
            "type": d.get("file_type", "document").upper(),
            "source": d.get("source_col", "unknown").capitalize(),
            "raw_collection": d.get("source_col", "primary"),
            "poster": "" if mode == "none" else tg_thumb, 
            "tg_thumb": tg_thumb,
            "watch": f"/setup_stream?file_id={fid}&mode=watch",
            "download": f"/setup_stream?file_id={fid}&mode=download",
        })

    # 🚀 PAGINATION LOGIC: अगर पूरे 21 रिज़ल्ट्स मिले हैं, मतलब अगला पेज उपलब्ध है
    has_more = len(results_list) == lim
    next_offset = off + lim if has_more else ""

    # रैम फ्लश बूस्टर
    gc.collect()
    
    return web.json_response({
        "results": results_list,
        "total": off + len(results_list) + (1 if has_more else 0), # फ्रंटएंड कंपैटिबिलिटी के लिए वर्चुअल टोटल
        "next_offset": next_offset,
        "is_admin": role == "admin",
    })

# ─────────────────────────────────────────────────────────
# 📸 THUMBNAIL API — Rebuilt With Strict Wait-On-Flood Protocol
# ─────────────────────────────────────────────────────────
@search_routes.get("/api/thumb")
async def get_telegram_thumb(req):
    fid = req.query.get("file_id")
    is_retry = req.query.get("retry", "false").lower() == "true"
    if not fid: return web.Response(status=400)

    headers = {
        "Content-Disposition": 'inline; filename="poster.jpg"',
        "Cache-Control": "max-age=86400"
    }
    
    if is_retry and fid in thumb_cache:
        if thumb_cache[fid] == "NO_THUMB": thumb_cache.pop(fid, None)

    # 1. इन-मेमोरी रैम कैशे लुकअप
    if fid in thumb_cache:
        if thumb_cache[fid] == "NO_THUMB": return web.Response(status=404)
        return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)

    async with thumb_semaphore:
        if len(thumb_cache) >= MAX_CACHE:
            thumb_cache.clear()
            gc.collect() # एग्रेसिव ओओएम प्रोटेक्शन रैम वाइपआउट

        if fid in thumb_cache:
            if thumb_cache[fid] == "NO_THUMB": return web.Response(status=404)
            return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)

        # 2. मोंगोडीबी कैशे लुकअप (अगर थंबनेल आईडी पहले से लॉक है तो बिना टेलीग्राम को परेशान किए तुरंत दें)
        saved_thumb_id = None
        for col_name, col in COLLECTIONS.items():
            existing = await col.find_one({"_id": fid}, {"thumb_url": 1})
            if existing and existing.get("thumb_url") and existing.get("thumb_url").startswith("TG_ID:"):
                saved_thumb_id = existing.get("thumb_url").replace("TG_ID:", "")
                break

        if saved_thumb_id:
            try:
                logger.info(f"✨ [DB THUMB HIT] Serving stored File ID: {fid}")
                file_data = await temp.BOT.download_media(saved_thumb_id, in_memory=True)
                if file_data:
                    thumb_bytes = file_data.getvalue()
                    thumb_cache[fid] = thumb_bytes
                    return web.Response(body=thumb_bytes, content_type="image/jpeg", headers=headers)
            except Exception as e:
                logger.error(f"❌ Failed to download cached file_id: {e}")

        # 3. 🛡️ सख्त नियम: टेलीग्राम लाइव फ़ेचिंग विथ सख्त फ़्लडवेट लूप (No Fallback Allowed)
        await asyncio.sleep(0.2)
        
        # ओरिजिनल पोस्टर हर हाल में लाने के लिए हमने मैक्सिमम अटैम्प्स को ५ पर सेट किया है
        for attempt in range(5): 
            try:
                logger.info(f"📥 [TG THUMB FETCH] Fetching Telegram Node for File ID: {fid} (Attempt {attempt+1})")
                msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
                thumb_id = None
                
                if msg.video and msg.video.thumbs and len(msg.video.thumbs) > 0:
                    thumb_id = msg.video.thumbs[0].file_id
                elif msg.document and msg.document.thumbs and len(msg.document.thumbs) > 0:
                    thumb_id = msg.document.thumbs[0].file_id

                if thumb_id:
                    file_data = await temp.BOT.download_media(thumb_id, in_memory=True)
                    thumb_bytes = file_data.getvalue()
                    thumb_cache[fid] = thumb_bytes
                    
                    # डेटाबेस में हमेशा के लिए सेव करें ताकि अगली बार तुरंत लोड हो
                    db_save_value = f"TG_ID:{thumb_id}"
                    for col_name, col in COLLECTIONS.items():
                        await col.update_one({"_id": fid}, {"$set": {"thumb_url": db_save_value}})
                    
                    await db.add_to_delete_queue(BIN_CHANNEL, msg.id, 5)
                    return web.Response(body=thumb_bytes, content_type="image/jpeg", headers=headers)
                else:
                    # फ़ाइल में थंबनेल एम्बेडेड ही नहीं है, तो डेटाबेस मॉडिफाई नहीं करेंगे, केवल फॉलबैक एरर देंगे
                    logger.warning(f"🚫 [NO THUMB EMBED] File has no embedded thumbnail inside telegram: {fid}")
                    thumb_cache[fid] = "NO_THUMB"
                    await db.add_to_delete_queue(BIN_CHANNEL, msg.id, 5)
                    return web.Response(status=404)

            except Exception as e:
                err_text = str(e)
                # ✅ सख्त नियम सिंक: अगर टेलीग्राम FloodWait फेंकता है, तो एपीआई हार मानकर नकली पोस्टर नहीं दिखाएगी,
                # बल्कि चुपचाप लूप को रोककर स्लीप मोड में चली जाएगी और रास्ता साफ़ होने पर ओरिजिनल ही डाउनलोड करेगी।
                if "FLOOD_WAIT" in err_text or "420" in err_text:
                    match = re.search(r'wait of (\d+) second', err_text)
                    wait_time = int(match.group(1)) if match else 20
                    logger.warning(f"⏳ [FLOOD WAIT ENCOUNTERED] API Loop Sleeping for {wait_time + 2}s to get original poster...")
                    await asyncio.sleep(wait_time + 2)
                    continue # अगला अटैम्प ऑटोमैटिकली बिना क्रैश हुए फ्रेश रूट से ट्रिगर होगा
                
                logger.error(f"❌ [THUMB CRASH] Processing failed: {e}")
                await asyncio.sleep(2)
                continue
        
        return web.Response(status=429)

# ─────────────────────────────────────────────────────────
# 🎥 STREAM SETUP PIPELINE
# ─────────────────────────────────────────────────────────
@search_routes.get("/setup_stream")
async def setup_stream(req):
    role, _ = await get_user_role(req)
    if not role: return web.Response(text="❌ Unauthorized Access Denied!", status=403)
    fid = req.query.get("file_id")
    mode = req.query.get("mode", "watch")
    if not fid: return web.Response(text="❌ Missing structural file_id!", status=400)
    try:
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
        await db.add_to_delete_queue(BIN_CHANNEL, msg.id, 3600)
        return web.HTTPFound(f"/{'download' if mode == 'download' else 'watch'}/{msg.id}")
    except Exception as e: return web.Response(text=f"❌ Error Tunneling Stream: {e}", status=500)

@search_routes.post("/setup_stream")
async def setup_stream_post(req):
    role, _ = await get_user_role(req)
    if not role: return web.json_response({"error": "Unauthorized Web Access!"}, status=403)
    try:
        data = await req.json()
        fid = data.get("file_id")
        mode = data.get("mode", "watch")
    except:
        fid = req.query.get("file_id")
        mode = req.query.get("mode", "watch")
        
    if not fid: return web.json_response({"error": "Missing file_id!"}, status=400)
    try:
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
        await db.add_to_delete_queue(BIN_CHANNEL, msg.id, 3600)
        return web.json_response({"url": f"/{'download' if mode == 'download' else 'watch'}/{msg.id}"})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

# ─────────────────────────────────────────────────────────
# ⚙️ ADMIN CONTROLS: EDIT & WIPE PIPELINE
# ─────────────────────────────────────────────────────────
@search_routes.post("/api/delete")
async def api_delete(req):
    role, _ = await get_user_role(req)
    if role != "admin": return web.json_response({"error": "Core Admin Authorization Required!"}, status=403)
    try:
        data = await req.json()
        fid = data.get("file_id")
        col = data.get("collection", "primary").lower()
        if col not in COLLECTIONS: return web.json_response({"error": "Invalid target collection!"}, status=400)
        
        res = await COLLECTIONS[col].delete_one({"_id": fid})
        return web.json_response({"success": bool(res.deleted_count)})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

@search_routes.post("/api/edit_name")
async def api_edit_name(req):
    role, _ = await get_user_role(req)
    if role != "admin": return web.json_response({"error": "Core Admin Authorization Required!"}, status=403)
    try:
        data = await req.json()
        fid = data.get("file_id")
        col = data.get("collection", "primary").lower()
        new_name = data.get("new_name", "").strip()
        
        if not fid or col not in COLLECTIONS or not new_name:
            return web.json_response({"error": "Missing structural inputs!"}, status=400)
            
        res = await COLLECTIONS[col].update_one({"_id": fid}, {"$set": {"file_name": new_name, "caption": new_name}})
        return web.json_response({"success": bool(res.modified_count)})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

# ─────────────────────────────────────────────────────────
# 📥 NATIVE THUMBNAIL UPLOAD & CACHE BUSTER API
# ─────────────────────────────────────────────────────────
@search_routes.post("/api/upload_thumb")
async def api_upload_thumb(req):
    role, _ = await get_user_role(req)
    if role != "admin": 
        return web.json_response({"error": "Core Admin Authorization Required!"}, status=403)
        
    try:
        reader = await req.multipart()
        file_id_field = None
        collection_field = None
        image_bytes = None
        
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'file_id':
                file_id_field = (await part.read()).decode().strip()
            elif part.name == 'collection':
                collection_field = (await part.read()).decode().strip().lower()
            elif part.name == 'image':
                image_bytes = await part.read()

        if not file_id_field or not collection_field or not image_bytes:
            return web.json_response({"error": "Missing required multipart assets!"}, status=400)
        if collection_field not in COLLECTIONS:
            return web.json_response({"error": "Target collection missing!"}, status=400)

        # [RAM CACHE BUSTER SYNC]
        thumb_cache.pop(file_id_field, None)

        # context block का उपयोग करके BytesIO बफर को इमेज अपलोड होते ही पूरी तरह फ्लश किया गया
        with io.BytesIO(image_bytes) as img_buffer:
            img_buffer.name = "poster.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=img_buffer)
            
        if not msg or not msg.photo:
            return web.json_response({"error": "Telegram Node failed to compile Photo ID!"}, status=500)
            
        try:
            if hasattr(msg.photo, "sizes") and msg.photo.sizes:
                new_thumb_id = msg.photo.sizes[-1].file_id
            else:
                new_thumb_id = msg.photo.file_id
        except:
            new_thumb_id = msg.photo.file_id
            
        db_save_value = f"TG_ID:{new_thumb_id}"
        
        await COLLECTIONS[collection_field].update_one(
            {"_id": file_id_field},
            {"$set": {"thumb_url": db_save_value}}
        )
        
        await db.add_to_delete_queue(BIN_CHANNEL, msg.id, 5)
        
        # फ़ोर्स रैम गारबेज क्लीनअप
        gc.collect()
        return web.json_response({"success": True})
        
    except Exception as e:
        logger.error(f"❌ Upload thumb endpoint crash: {e}")
        return web.json_response({"error": str(e)}, status=500)

@search_routes.get("/miniapp")
async def miniapp_page(req):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, "web", "miniapp.html")
    if not os.path.exists(html_path): html_path = os.path.join(base_dir, "Web", "miniapp.html")
    if not os.path.exists(html_path): return web.Response(text="miniapp.html page template not found.", status=404)
    return web.FileResponse(html_path)
