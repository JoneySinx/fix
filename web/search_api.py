from aiohttp import web
import time, re, asyncio, os, json, hmac, hashlib, urllib.parse
from utils import temp, get_size, is_rate_limited, is_premium
from info import BIN_CHANNEL, ADMINS, BOT_TOKEN
from database.ia_filterdb import COLLECTIONS

search_routes = web.RouteTableDef()

MAX_CACHE = 500
thumb_cache = {}
thumb_semaphore = asyncio.Semaphore(4)

# ─────────────────────────────────────────────
# 🔒 STRICT SECURITY: Telegram initData HMAC Verification
# इसे कोई बायपास नहीं कर सकता क्योंकि यह BOT_TOKEN से वेरीफाई होता है
# ─────────────────────────────────────────────
def verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Telegram WebApp का initData verify करता है।
    Returns: user dict अगर valid है, वरना None।
    """
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            return None

        user_str = parsed.get("user", "{}")
        return json.loads(user_str)

    except Exception:
        return None

# ─────────────────────────────────────────────
# 🔒 AUTHENTICATION: Check Admin / Premium status
# ─────────────────────────────────────────────
async def get_user_role(req):
    # 1️⃣ पहले Telegram initData check करो (Mini App के लिए)
    init_data = req.headers.get("X-Telegram-Init-Data", "").strip()
    if init_data:
        user = verify_telegram_init_data(init_data)
        if user:
            tg_id = int(user.get("id", 0))
            if tg_id:
                if tg_id in ADMINS:
                    return "admin", tg_id
                if await is_premium(tg_id):
                    return "user", tg_id
                
                # Check global premium flag
                from info import IS_PREMIUM
                if not IS_PREMIUM:
                    return "user", tg_id
        return None, None

    # 2️⃣ Cookie session check करो (Web browser login के लिए)
    s_user = req.cookies.get("user_session")
    if s_user and hasattr(temp, "USER_SESSIONS"):
        session = temp.USER_SESSIONS.get(s_user, {})
        if session.get("expiry", 0) > time.time():
            tg_id = session["tg_id"]
            if tg_id in ADMINS:
                return "admin", tg_id
            if await is_premium(tg_id):
                return "user", tg_id

    return None, None

# ─────────────────────────────────────────────
# 🔍 SEARCH API (TMDb Removed)
# ─────────────────────────────────────────────
@search_routes.get("/api/search")
async def api_search(req):
    role, tg_id = await get_user_role(req)
    if not role:
        return web.json_response({"error": "Unauthorized Access! Admin or Premium only."}, status=403)
    if is_rate_limited(tg_id, "web_search", 1):
        return web.json_response({"error": "Searching too fast!"}, status=429)

    q = req.query.get("q", "").strip()
    off = req.query.get("offset", "0")
    col = req.query.get("col", "all").lower()
    mode = req.query.get("mode", "tg").lower()

    if not q:
        return web.json_response({"results": [], "total": 0, "next_offset": ""})

    try:
        off = max(0, int(off))
    except (ValueError, TypeError):
        off = 0

    flt_text = {"$text": {"$search": q}}
    flt_regex = {"file_name": re.compile(re.escape(q), re.IGNORECASE)}
    all_m, tot, lim = [], 0, 21
    tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS
    col_counts, col_filters = {}, {}

    async def get_col_count(name, collection):
        count = await collection.count_documents(flt_text)
        active_flt = flt_text if count > 0 else flt_regex
        if count == 0:
            count = await collection.count_documents(active_flt)
        return name, count, active_flt

    count_results = await asyncio.gather(*(get_col_count(n, c) for n, c in tgt_cols.items()))
    for name, count, active_flt in count_results:
        col_counts[name] = count
        col_filters[name] = active_flt
        tot += count

    remaining_skip = off
    for n, c in tgt_cols.items():
        if len(all_m) >= lim:
            break
        count = col_counts[n]
        if count == 0:
            continue
        if remaining_skip >= count:
            remaining_skip -= count
            continue
        local_limit = lim - len(all_m)
        docs = await c.find(col_filters[n]).sort("_id", -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
        for d in docs:
            d["source_col"] = n.lower()
        all_m.extend(docs)
        remaining_skip = 0

    async def process_doc(d):
        fid = d.get("file_ref", d.get("file_id"))
        file_name = d.get("file_name", "Unknown File")
        db_thumb = d.get("thumb_url")
        
        # ✅ FIX: अगर डेटाबेस में पुरानी imgbb वाली खराब लिंक सेव है, तो उसे इग्नोर करें
        if db_thumb and ("ibb.co" in db_thumb or "default-movie" in db_thumb):
            db_thumb = None

        tg_thumb = db_thumb if db_thumb else f"/api/thumb?file_id={fid}"
        
        return {
            "file_id": fid,
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
# 📸 THUMBNAIL API
# ─────────────────────────────────────────────
@search_routes.get("/api/thumb")
async def get_telegram_thumb(req):
    fid = req.query.get("file_id")
    if not fid:
        return web.Response(status=400)

    headers = {"Content-Disposition": 'inline; filename="poster.jpg"'}
    
    # ✅ FIX: नई काम करने वाली डिफ़ॉल्ट इमेज (Professional Dark Theme)
    DEFAULT_THUMB = "https://placehold.co/400x600/141414/e50914?text=No+Poster"

    if fid in thumb_cache:
        if thumb_cache[fid] == "NO_THUMB":
            raise web.HTTPFound(DEFAULT_THUMB)
        return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)

    async with thumb_semaphore:
        if fid in thumb_cache:
            if thumb_cache[fid] == "NO_THUMB":
                raise web.HTTPFound(DEFAULT_THUMB)
            return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)

        try:
            msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
            thumb_id = None
            if msg.video and msg.video.thumbs:
                thumb_id = msg.video.thumbs[0].file_id
            elif msg.document and msg.document.thumbs:
                thumb_id = msg.document.thumbs[0].file_id

            if thumb_id:
                file_data = await temp.BOT.download_media(thumb_id, in_memory=True)
                thumb_bytes = file_data.getvalue()
                if len(thumb_cache) >= MAX_CACHE:
                    oldest_key = next(iter(thumb_cache))
                    del thumb_cache[oldest_key]
                thumb_cache[fid] = thumb_bytes
                asyncio.create_task(msg.delete())
                return web.Response(body=thumb_bytes, content_type="image/jpeg", headers=headers)
            else:
                thumb_cache[fid] = "NO_THUMB"
                asyncio.create_task(msg.delete())
                raise web.HTTPFound(DEFAULT_THUMB)
        except web.HTTPFound:
            raise
        except Exception:
            raise web.HTTPFound(DEFAULT_THUMB)

async def _auto_del_msg(msg, delay):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass

# ─────────────────────────────────────────────
# ▶️ STREAM SETUP
# ─────────────────────────────────────────────
@search_routes.get("/setup_stream")
async def setup_stream(req):
    role, _ = await get_user_role(req)
    if not role:
        return web.Response(text="❌ Unauthorized! Premium Required.", status=403)
    fid = req.query.get("file_id")
    mode = req.query.get("mode", "watch")
    if not fid:
        return web.Response(text="❌ Missing file_id!", status=400)
    try:
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
        asyncio.create_task(_auto_del_msg(msg, 3600))
        return web.HTTPFound(f"/{'download' if mode == 'download' else 'watch'}/{msg.id}")
    except Exception as e:
        return web.Response(text=f"❌ Error: {e}", status=500)

# ─────────────────────────────────────────────
# 🗑️ DELETE & EDIT APIs
# ─────────────────────────────────────────────
@search_routes.post("/api/delete")
async def api_delete(req):
    role, _ = await get_user_role(req)
    if role != "admin":
        return web.json_response({"error": "Admin only!"}, status=403)
    try:
        data = await req.json()
        col = data.get("collection", "primary").lower()
        if col not in COLLECTIONS:
            return web.json_response({"error": "Invalid collection!"}, status=400)
        res = await COLLECTIONS[col].delete_one(
            {"$or": [{"file_id": data.get("file_id")}, {"file_ref": data.get("file_id")}]}
        )
        return web.json_response({"success": bool(res.deleted_count)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@search_routes.post("/api/edit")
async def api_edit(req):
    role, _ = await get_user_role(req)
    if role != "admin":
        return web.json_response({"error": "Admin only!"}, status=403)
    try:
        data = await req.json()
        col = data.get("collection", "primary").lower()
        if col not in COLLECTIONS:
            return web.json_response({"error": "Invalid collection!"}, status=400)
        new_name = data.get("new_name", "").strip()
        if not new_name:
            return web.json_response({"error": "New name cannot be empty!"}, status=400)
        res = await COLLECTIONS[col].update_one(
            {"$or": [{"file_id": data.get("file_id")}, {"file_ref": data.get("file_id")}]},
            {"$set": {"file_name": new_name}},
        )
        return web.json_response({"success": bool(res.modified_count)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ─────────────────────────────────────────────
# 🍿 MINI APP PAGE
# ─────────────────────────────────────────────
@search_routes.get("/miniapp")
async def miniapp_page(req):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, "web", "miniapp.html")

    if not os.path.exists(html_path):
        html_path = os.path.join(base_dir, "Web", "miniapp.html")

    if not os.path.exists(html_path):
        return web.Response(text="miniapp.html not found. Check your folder structure.", status=404)

    return web.FileResponse(html_path)
