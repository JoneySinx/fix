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
MAX_CACHE = MAX_THUMB_CACHE             
thumb_cache = {}
thumb_semaphore = asyncio.Semaphore(5) 

# 🔮 GLOBAL PRE-FETCH ENGINE CACHE
PREFETCH_CACHE = {}  # Structural Format: {'user_id_query_col_mode_offset': [...]}

# 🔥 TRENDING & RECENT QUERY IN-MEMORY CACHE (RAM Speed Booster)
TRENDING_CACHE = {}  # Format: {'col_mode_query': {'data': [...], 'next_offset': '...', 'expiry': timestamp}}
TRENDING_CACHE_TTL = 300  # 5 मिनट तक रैम में डेटा लॉक रहेगा

# ─────────────────────────────────────────────────────────
# 📸 CORE THUMBNAIL ENGINE (Shared by Web API & BG Prefetcher)
# ─────────────────────────────────────────────────────────
async def _get_or_fetch_thumb(fid, is_retry=False):
    """थंबनेल को रैम कैशे से देने या टेलीग्राम से बैकग्राउंड में फेच करने का सेंट्रलाइज्ड कोर"""
    if is_retry and fid in thumb_cache:
        if thumb_cache[fid] == "NO_THUMB": thumb_cache.pop(fid, None)

    if fid in thumb_cache:
        return thumb_cache[fid]

    async def _fetch():
        if len(thumb_cache) >= MAX_CACHE:
            thumb_cache.clear()
            gc.collect() 

        if fid in thumb_cache:
            return thumb_cache[fid]

        saved_thumb_id = None
        for col_name, col in COLLECTIONS.items():
            existing = await col.find_one({"_id": fid}, {"thumb_url": 1})
            if existing and existing.get("thumb_url") and existing.get("thumb_url").startswith("TG_ID:"):
                saved_thumb_id = existing.get("thumb_url").replace("TG_ID:", "")
                break

        if saved_thumb_id:
            try:
                file_data = await temp.BOT.download_media(saved_thumb_id, in_memory=True)
                if file_data:
                    thumb_bytes = file_data.getvalue()
                    thumb_cache[fid] = thumb_bytes
                    return thumb_bytes
            except Exception:
                pass

        await asyncio.sleep(0.2)
        
        for attempt in range(5): 
            try:
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
                    
                    db_save_value = f"TG_ID:{thumb_id}"
                    for col_name, col in COLLECTIONS.items():
                        await col.update_one({"_id": fid}, {"$set": {"thumb_url": db_save_value}})
                    
                    await db.add_to_delete_queue(BIN_CHANNEL, msg.id, 5)
                    return thumb_bytes
                else:
                    thumb_cache[fid] = "NO_THUMB"
                    await db.add_to_delete_queue(BIN_CHANNEL, msg.id, 5)
                    return "NO_THUMB"

            except Exception as e:
                err_text = str(e)
                if "FLOOD_WAIT" in err_text or "420" in err_text:
                    match = re.search(r'wait of (\d+) second', err_text)
                    wait_time = int(match.group(1)) if match else 20
                    await asyncio.sleep(wait_time + 2)
                    continue 
                await asyncio.sleep(2)
                continue
        return None

    async with thumb_semaphore:
        return await _fetch()

# ─────────────────────────────────────────────────────────
# 🔄 BACKGROUND PRE-FETCH WORKER (With Full Thumbnail Warming)
# ─────────────────────────────────────────────────────────
async def bg_prefetch_worker(tg_id, q, col, mode, prefetch_offset, lim):
    """यह वर्कर बैकग्राउंड में अगले पेज का डेटा और थंबनेल्स दोनों रैम में लॉक कर देगा"""
    try:
        cache_key = f"{tg_id}_{q}_{col}_{mode}_{prefetch_offset}"
        if cache_key in PREFETCH_CACHE:
            return

        if mode == "none":
            projection = {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1}
        else:
            projection = {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "thumb_url": 1}

        flt_text = {"$text": {"$search": q}}
        flt_regex = {"file_name": re.compile(re.escape(q), re.IGNORECASE)}
        tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS
        
        bg_docs = []
        remaining_skip = prefetch_offset

        for n, c in tgt_cols.items():
            if len(bg_docs) >= lim: 
                break
            local_limit = lim - len(bg_docs)
            docs = []
            try:
                docs = await c.find(flt_text, projection).sort("_id", -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
            except Exception: 
                pass
            
            if not docs:
                try:
                    docs = await c.find(flt_regex, projection).sort("_id", -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
                except Exception:
                    pass
                
            if docs:
                for d in docs: 
                    d["source_col"] = n.lower()
                bg_docs.extend(docs)
                remaining_skip = max(0, remaining_skip - len(docs))

        if bg_docs:
            PREFETCH_CACHE[cache_key] = bg_docs
            logger.info(f"🔮 [PREFETCH ENGINE] Background loaded {len(bg_docs)} results for next offset: {prefetch_offset}")
            
            # ✅ POINT 5 FIX: अगर Text Only मोड नहीं है, तो चुपचाप बैकग्राउंड में ही थंबनेल्स को कैशे में वार्मअप (Warming) कर लो
            if mode != "none":
                for doc in bg_docs:
                    asyncio.create_task(_get_or_fetch_thumb(doc["_id"]))
                    
    except Exception as e:
        logger.error(f"❌ Prefetch worker execution failed: {e}")

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
# 🔍 SEARCH API — Smart Pre-fetch Grid Engine
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

    lim = MAX_WEB_RESULTS  
    
    # 🛑 स्टेप 1: ट्रेंडिंग/हालिया इन-मेमोरी रैम कैशे चेक (POINT 2)
    if off == 0:
        trend_key = f"{col}_{mode}_{q.lower()}"
        now_ts = time.time()
        if trend_key in TRENDING_CACHE and TRENDING_CACHE[trend_key]["expiry"] > now_ts:
            cached = TRENDING_CACHE[trend_key]
            logger.info(f"🔥 [TRENDING RAM HIT] Instantly serving raw payload for: {q}")
            
            if cached["next_offset"]:
                asyncio.create_task(bg_prefetch_worker(tg_id, q, col, mode, cached["next_offset"], lim))
                
            return web.json_response({
                "results": cached["results"],
                "total": len(cached["results"]) + (1 if cached["next_offset"] else 0),
                "next_offset": cached["next_offset"],
                "is_admin": role == "admin"
            })

    current_cache_key = f"{tg_id}_{q}_{col}_{mode}_{off}"
    all_m = []

    # 🛑 स्टेप 2: चेक करें कि क्या इस पेज का डेटा पहले से बैकग्राउंड प्री-फेच में उपलब्ध है?
    if current_cache_key in PREFETCH_CACHE:
        all_m = PREFETCH_CACHE.pop(current_cache_key) 
        logger.info(f"⚡ [PREFETCH HIT] Serving Page Pipeline directly from Cache for offset {off}")

    # 🛑 स्टेप 3: अगर कैशे मिस हुआ, तो तुरंत डेटाबेस से लोड करें
    if not all_m:
        if mode == "none":
            projection = {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1}
        else:
            projection = {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "thumb_url": 1}

        flt_text = {"$text": {"$search": q}}
        flt_regex = {"file_name": re.compile(re.escape(q), re.IGNORECASE)}
        tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS

        remaining_skip = off
        for n, c in tgt_cols.items():
            if len(all_m) >= lim: 
                break
            
            local_limit = lim - len(all_m)
            docs = []
            try:
                docs = await c.find(flt_text, projection).sort("_id", -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
            except Exception: 
                pass
            
            if not docs:
                try:
                    docs = await c.find(flt_regex, projection).sort("_id", -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
                except Exception:
                    pass
                
            if docs:
                for d in docs: d["source_col"] = n.lower()
                all_m.extend(docs)
                remaining_skip = max(0, remaining_skip - len(docs))

    # 🚀 स्टेप 4: करंट पेज का डेटा फाइनल होते ही, अगले पेज के लिए प्री-फेच वर्कर बैकग्राउंड में डाल दें
    has_more = len(all_m) == lim
    next_offset = off + lim if has_more else ""
    
    if has_more:
        asyncio.create_task(bg_prefetch_worker(tg_id, q, col, mode, next_offset, lim))

    # फ्रंटएंड रिस्पॉन्स की मैपिंग (POINT 3)
    results_list = []
    thumb_salt = int(time.time() * 100) if mode != "none" else 0
    
    for d in all_m:
        fid = d.get("file_ref") or d.get("_id")
        db_id = d.get("_id")
        
        if mode == "none":
            tg_thumb = ""
            poster_url = ""
        else:
            tg_thumb = f"/api/thumb?file_id={db_id}&v={thumb_salt}"
            poster_url = tg_thumb
        
        results_list.append({
            "file_id": db_id,
            "name": d.get("file_name", "Unknown File"),
            "size": get_size(d.get("file_size", 0)),
            "type": d.get("file_type", "document").upper(),
            "source": d.get("source_col", "unknown").capitalize(),
            "raw_collection": d.get("source_col", "primary"),
            "poster": poster_url, 
            "tg_thumb": tg_thumb,
            "watch": f"/setup_stream?file_id={fid}&mode=watch",
            "download": f"/setup_stream?file_id={fid}&mode=download",
        })

    if off == 0 and results_list:
        trend_key = f"{col}_{mode}_{q.lower()}"
        TRENDING_CACHE[trend_key] = {
            "results": results_list,
            "next_offset": next_offset,
            "expiry": time.time() + TRENDING_CACHE_TTL
        }

    if len(PREFETCH_CACHE) > 150:
        old_keys = list(PREFETCH_CACHE.keys())[:50]
        for k in old_keys: PREFETCH_CACHE.pop(k, None)
        gc.collect()

    if len(TRENDING_CACHE) > 200:
        now_ts = time.time()
        expired = [k for k, v in TRENDING_CACHE.items() if v["expiry"] < now_ts]
        for k in expired: TRENDING_CACHE.pop(k, None)
        if len(TRENDING_CACHE) > 200:
            old_trends = list(TRENDING_CACHE.keys())[:50]
            for k in old_trends: TRENDING_CACHE.pop(k, None)
        gc.collect()
    
    return web.json_response({
        "results": results_list,
        "total": off + len(results_list) + (1 if has_more else 0), 
        "next_offset": next_offset,
        "is_admin": role == "admin",
    })

# ─────────────────────────────────────────────────────────
# 📸 THUMBNAIL API 
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
    
    res = await _get_or_fetch_thumb(fid, is_retry)
    if res == "NO_THUMB" or res is None:
        return web.Response(status=404 if res == "NO_THUMB" else 429)
        
    return web.Response(body=res, content_type="image/jpeg", headers=headers)

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
        data = await db.json() if hasattr(db, 'json') else await req.json()
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
    if role != "admin": return web.json_response({"error": "Core Admin Authorization Required!"}, status=403)
        
    try:
        reader = await req.multipart()
        file_id_field, collection_field, image_bytes = None, None, None
        
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'file_id': file_id_field = (await part.read()).decode().strip()
            elif part.name == 'collection': collection_field = (await part.read()).decode().strip().lower()
            elif part.name == 'image': image_bytes = await part.read()

        if not file_id_field or not collection_field or not image_bytes:
            return web.json_response({"error": "Missing required multipart assets!"}, status=400)
        if collection_field not in COLLECTIONS:
            return web.json_response({"error": "Target collection missing!"}, status=400)

        thumb_cache.pop(file_id_field, None)

        with io.BytesIO(image_bytes) as img_buffer:
            img_buffer.name = "poster.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=img_buffer)
            
        if not msg or not msg.photo: return web.json_response({"error": "Telegram Node failed to compile Photo ID!"}, status=500)
            
        try: new_thumb_id = msg.photo.sizes[-1].file_id if hasattr(msg.photo, "sizes") and msg.photo.sizes else msg.photo.file_id
        except: new_thumb_id = msg.photo.file_id
            
        db_save_value = f"TG_ID:{new_thumb_id}"
        await COLLECTIONS[collection_field].update_one({"_id": file_id_field}, {"$set": {"thumb_url": db_save_value}})
        await db.add_to_delete_queue(BIN_CHANNEL, msg.id, 5)
        
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
