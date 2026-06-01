from aiohttp import web
import time, re, asyncio, os, json, hmac, hashlib, urllib.parse, aiohttp, logging
from utils import temp, get_size, is_rate_limited, is_premium
from info import BIN_CHANNEL, ADMINS, BOT_TOKEN
from database.ia_filterdb import COLLECTIONS

logger = logging.getLogger(__name__)

search_routes = web.RouteTableDef()

# ─────────────────────────────────────────────
# 📸 THUMBNAIL CONCURRENCY & CACHE
# ─────────────────────────────────────────────
MAX_CACHE = 500
thumb_cache = {}
thumb_semaphore = asyncio.Semaphore(1) 

# ─────────────────────────────────────────────
# 🔒 STRICT SECURITY: Telegram initData HMAC Verification
# ─────────────────────────────────────────────
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
                from info import IS_PREMIUM
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

# ─────────────────────────────────────────────
# 🔍 SEARCH API
# ─────────────────────────────────────────────
@search_routes.get("/api/search")
async def api_search(req):
    role, tg_id = await get_user_role(req)
    if not role: return web.json_response({"error": "Unauthorized Access!"}, status=403)
    if is_rate_limited(tg_id, "web_search", 1): return web.json_response({"error": "Searching too fast!"}, status=429)

    q = req.query.get("q", "").strip()
    off = req.query.get("offset", "0")
    col = req.query.get("col", "all").lower()
    mode = req.query.get("mode", "tg").lower()

    if not q: return web.json_response({"results": [], "total": 0, "next_offset": ""})
    try: off = max(0, int(off))
    except: off = 0

    flt_text = {"$text": {"$search": q}}
    flt_regex = {"file_name": re.compile(re.escape(q), re.IGNORECASE)}
    all_m, tot, lim = [], 0, 21
    tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS
    col_counts, col_filters = {}, {}

    async def get_col_count(name, collection):
        count = await collection.count_documents(flt_text)
        active_flt = flt_text if count > 0 else flt_regex
        if count == 0: count = await collection.count_documents(active_flt)
        return name, count, active_flt

    count_results = await asyncio.gather(*(get_col_count(n, c) for n, c in tgt_cols.items()))
    for name, count, active_flt in count_results:
        col_counts[name] = count
        col_filters[name] = active_flt
        tot += count

    remaining_skip = off
    for n, c in tgt_cols.items():
        if len(all_m) >= lim: break
        count = col_counts[n]
        if count == 0: continue
        if remaining_skip >= count:
            remaining_skip -= count
            continue
        local_limit = lim - len(all_m)
        docs = await c.find(col_filters[n]).sort("_id", -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
        for d in docs: d["source_col"] = n.lower()
        all_m.extend(docs)
        remaining_skip = 0

    async def process_doc(d):
        fid = d.get("file_ref", d.get("file_id"))
        db_id = d.get("_id")
        file_name = d.get("file_name", "Unknown File")
        db_thumb = d.get("thumb_url")
        
        if db_thumb and ("default-movie" in db_thumb or "placehold" in db_thumb or "ibb.co" in db_thumb):
            db_thumb = None

        tg_thumb = f"/api/thumb?file_id={db_id}"
        
        return {
            "file_id": db_id,
            "name": file_name,
            "size": get_size(d.get("file_size", 0)),
            "type": d.get("file_type", "document").upper(),
            "source": d.get("source_col", "unknown").capitalize(),
            "raw_collection": d.get("source_col", "primary"),
            "poster": "" if mode == "none" else tg_thumb, 
            "tg_thumb": tg_thumb,
            "watch": f"/setup_stream?file_id={fid}&mode=watch",
            "download": f"/setup_stream?file_id={fid}&mode=download",
        }

    results_list = await asyncio.gather(*(process_doc(d) for d in all_m))
    return web.json_response({
        "results": list(results_list),
        "total": tot,
        "next_offset": off + lim if off + lim < tot else "",
        "is_admin": role == "admin",
    })

# ─────────────────────────────────────────────
# 📸 THUMBNAIL API (Fixed Busy/Retry Bug)
# ─────────────────────────────────────────────
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

    if fid in thumb_cache:
        if thumb_cache[fid] == "NO_THUMB": return web.Response(status=404)
        return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)

    async with thumb_semaphore:
        if fid in thumb_cache:
            if thumb_cache[fid] == "NO_THUMB": return web.Response(status=404)
            return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)

        saved_thumb_id = None
        for col_name, col in COLLECTIONS.items():
            existing = await col.find_one({"$or": [{"_id": fid}, {"file_ref": fid}, {"file_id": fid}]})
            if existing and existing.get("thumb_url") and existing.get("thumb_url").startswith("TG_ID:"):
                saved_thumb_id = existing.get("thumb_url").replace("TG_ID:", "")
                break

        if saved_thumb_id:
            try:
                logger.info(f"✨ [DB HIT] Serving via internal Telegram ID for: {fid}")
                file_data = await temp.BOT.download_media(saved_thumb_id, in_memory=True)
                if file_data:
                    thumb_bytes = file_data.getvalue()
                    if len(thumb_cache) >= MAX_CACHE:
                        oldest_key = next(iter(thumb_cache))
                        thumb_cache.pop(oldest_key, None)
                    thumb_cache[fid] = thumb_bytes
                    return web.Response(body=thumb_bytes, content_type="image/jpeg", headers=headers)
            except Exception as e:
                logger.error(f"❌ Failed to download stored file_id from DB hit: {e}")

        await asyncio.sleep(0.3)
        for attempt in range(3):
            try:
                logger.info(f"📥 [TG FETCH] Fetching from Telegram for File ID: {fid} (Attempt {attempt+1})")
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
                    updated_count = 0
                    for col_name, col in COLLECTIONS.items():
                        res = await col.update_many(
                            {"$or": [{"_id": fid}, {"file_ref": fid}, {"file_id": fid}]},
                            {"$set": {"thumb_url": db_save_value}}
                        )
                        updated_count += res.modified_count
                    
                    logger.info(f"💾 [NATIVE SAVE] Successfully locked in DB documents ({updated_count}) for File ID: {fid}")
                    asyncio.create_task(msg.delete())
                    return web.Response(body=thumb_bytes, content_type="image/jpeg", headers=headers)
                else:
                    logger.warning(f"🚫 [NO THUMB] No embedded thumb: {fid}")
                    thumb_cache[fid] = "NO_THUMB"
                    asyncio.create_task(msg.delete())
                    return web.Response(status=404)

            except Exception as e:
                err_text = str(e)
                if "FLOOD_WAIT" in err_text or "420" in err_text:
                    match = re.search(r'wait of (\d+) second', err_text)
                    wait_time = int(match.group(1)) if match else 20
                    logger.warning(f"⏳ [FLOOD WAIT] Waiting {wait_time}s on attempt {attempt+1}...")
                    await asyncio.sleep(wait_time + 2)
                    continue
                
                logger.error(f"❌ [ERROR] Processing failed: {e}")
                return web.Response(status=429)
        
        return web.Response(status=429)

async def _auto_del_msg(msg, delay):
    await asyncio.sleep(delay)
    try: await msg.delete()
    except: pass

# ─────────────────────────────────────────────
# 🎥 STREAM SETUP SYSTEM (Supports GET & POST)
# ─────────────────────────────────────────────
@search_routes.get("/setup_stream")
async def setup_stream(req):
    role, _ = await get_user_role(req)
    if not role: return web.Response(text="❌ Unauthorized!", status=403)
    fid = req.query.get("file_id")
    mode = req.query.get("mode", "watch")
    if not fid: return web.Response(text="❌ Missing file_id!", status=400)
    try:
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
        asyncio.create_task(_auto_del_msg(msg, 3600))
        return web.HTTPFound(f"/{'download' if mode == 'download' else 'watch'}/{msg.id}")
    except Exception as e: return web.Response(text=f"❌ Error: {e}", status=500)

@search_routes.post("/setup_stream")
async def setup_stream_post(req):
    role, _ = await get_user_role(req)
    if not role: return web.json_response({"error": "Unauthorized Access!"}, status=403)
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
        asyncio.create_task(_auto_del_msg(msg, 3600))
        return web.json_response({"url": f"/{'download' if mode == 'download' else 'watch'}/{msg.id}"})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

# ─────────────────────────────────────────────
# ⚙️ ADMIN CONTROLS: DELETE & EDIT SEPARATE
# ─────────────────────────────────────────────
@search_routes.post("/api/delete")
async def api_delete(req):
    role, _ = await get_user_role(req)
    if role != "admin": return web.json_response({"error": "Admin only!"}, status=403)
    try:
        data = await req.json()
        fid = data.get("file_id")
        col = data.get("collection", "primary").lower()
        if col not in COLLECTIONS: return web.json_response({"error": "Invalid collection!"}, status=400)
        
        res = await COLLECTIONS[col].delete_one({"$or": [{"_id": fid}, {"file_id": fid}, {"file_ref": fid}]})
        return web.json_response({"success": bool(res.deleted_count)})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

# 📝 ONLY FILE NAME EDIT API
@search_routes.post("/api/edit_name")
async def api_edit_name(req):
    role, _ = await get_user_role(req)
    if role != "admin": return web.json_response({"error": "Admin only!"}, status=403)
    try:
        data = await req.json()
        fid = data.get("file_id")
        col = data.get("collection", "primary").lower()
        new_name = data.get("new_name", "").strip()
        
        if not fid or col not in COLLECTIONS or not new_name:
            return web.json_response({"error": "Missing input data!"}, status=400)
            
        res = await COLLECTIONS[col].update_one(
            {"$or": [{"_id": fid}, {"file_id": fid}, {"file_ref": fid}]}, 
            {"$set": {"file_name": new_name}}
        )
        print(f"📝 [NAME UPDATE] Updated file name to: {new_name} for ID: {fid}", flush=True)
        return web.json_response({"success": bool(res.modified_count)})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

# 📥 NATIVE THUMBNAIL UPLOAD & CACHE BUSTER API
@search_routes.post("/api/upload_thumb")
async def api_upload_thumb(req):
    role, _ = await get_user_role(req)
    if role != "admin": 
        return web.json_response({"error": "Admin only!"}, status=403)
        
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
            return web.json_response({"error": "Missing required fields!"}, status=400)
        if collection_field not in COLLECTIONS:
            return web.json_response({"error": "Invalid collection!"}, status=400)

        # ⚡ [RAM CACHE CLEANING] - पुराना थंबनेल रैम कैशे से तुरंत बाहर फेंकें
        from web.search_api import thumb_cache
        thumb_cache.pop(file_id_field, None)
        
        doc = await COLLECTIONS[collection_field].find_one({"_id": file_id_field})
        if doc:
            if doc.get("file_ref"): thumb_cache.pop(doc["file_ref"], None)
            if doc.get("file_id"): thumb_cache.pop(doc["file_id"], None)

        # 🚀 टेलीग्राम के BIN_CHANNEL में नई फ़ोटो सेंड करें
        logger.info(f"📤 [TG UPLOAD] Uploading latest poster bytes to BIN_CHANNEL for ID: {file_id_field}")
        import io
        img_buffer = io.BytesIO(image_bytes)
        img_buffer.name = "poster.jpg"
        
        msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=img_buffer)
        if not msg or not msg.photo:
            return web.json_response({"error": "Telegram failed to generate Photo ID!"}, status=500)
            
        # ✅ FIX ACTIVE: Hydrogram में फोटो ऑब्जेक्ट से सबसे बड़े साइज का file_id निकालने का सही तरीका
        try:
            if hasattr(msg.photo, "sizes") and msg.photo.sizes:
                new_thumb_id = msg.photo.sizes[-1].file_id
            else:
                new_thumb_id = msg.photo.file_id
        except Exception as py_err:
            logger.error(f"Fallback to direct file_id due to: {py_err}")
            new_thumb_id = msg.photo.file_id
            
        db_save_value = f"TG_ID:{new_thumb_id}"
        
        # 💾 [DB OVERRIDE] मोंगोडीबी में पुराने थंबनेल को हटाकर नया TG_ID लॉक करें
        await COLLECTIONS[collection_field].update_one(
            {"$or": [{"_id": file_id_field}, {"file_id": file_id_field}, {"file_ref": file_id_field}]},
            {"$set": {"thumb_url": db_save_value}}
        )
        
        print(f"💾 [NATIVE SAVE] Successfully cleared old cache & locked new TG_ID in DB for: {file_id_field}", flush=True)
        asyncio.create_task(msg.delete())
        
        return web.json_response({"success": True})
        
    except Exception as e:
        logger.error(f"❌ Upload thumb endpoint crash: {e}")
        return web.json_response({"error": str(e)}, status=500)

@search_routes.get("/miniapp")
async def miniapp_page(req):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, "web", "miniapp.html")
    if not os.path.exists(html_path): html_path = os.path.join(base_dir, "Web", "miniapp.html")
    if not os.path.exists(html_path): return web.Response(text="miniapp.html not found.", status=404)
    return web.FileResponse(html_path)
