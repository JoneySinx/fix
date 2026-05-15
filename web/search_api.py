from aiohttp import web
import time, re, asyncio, os
from utils import temp, get_size, is_rate_limited, is_premium
from helpers.tmdb import get_poster
from info import BIN_CHANNEL, ADMINS
from database.ia_filterdb import COLLECTIONS

search_routes = web.RouteTableDef()

# ✅ FIX 1: thumb_cache को LRU-style बनाया - memory leak रोकने के लिए
MAX_CACHE = 500
thumb_cache = {}

# ✅ Semaphore: एक बार में 4 टेलीग्राम फोटो
thumb_semaphore = asyncio.Semaphore(4)

# ✅ FIX 2: TMDb poster cache - हर search पर same movie के लिए API call रोकना
poster_cache = {}
POSTER_CACHE_TTL = 3600  # 1 घंटे तक cache valid


# ✅ Unified Auth Check
async def get_user_role(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and temp.USER_SESSIONS.get(s_user, {}).get('expiry', 0) > time.time():
        tg_id = temp.USER_SESSIONS[s_user]['tg_id']
        if tg_id in ADMINS: return 'admin', tg_id
        if await is_premium(tg_id): return 'user', tg_id
    return None, None


# ✅ FIX 3: Cached TMDb poster lookup
async def get_poster_cached(file_name: str) -> str:
    now = time.time()
    if file_name in poster_cache:
        cached_url, cached_at = poster_cache[file_name]
        if now - cached_at < POSTER_CACHE_TTL:
            return cached_url
    url = await get_poster(file_name)
    # Cache size limit
    if len(poster_cache) >= MAX_CACHE:
        # पुराना entry हटाओ
        oldest = min(poster_cache, key=lambda k: poster_cache[k][1])
        del poster_cache[oldest]
    poster_cache[file_name] = (url or "", now)
    return url or ""


@search_routes.get('/api/search')
async def api_search(req):
    role, tg_id = await get_user_role(req)
    if not role: return web.json_response({"error": "Unauthorized Access"}, status=403)
    if is_rate_limited(tg_id, "web_search", 1): return web.json_response({"error": "Searching too fast!"}, status=429)

    q = req.query.get('q', '').strip()
    off = req.query.get('offset', '0')
    col = req.query.get('col', 'all').lower()
    mode = req.query.get('mode', 'smart').lower()

    if not q: return web.json_response({"results": [], "total": 0, "next_offset": ""})

    # ✅ FIX 4: offset validation सही किया - isdigit() negative numbers handle नहीं करता
    try:
        off = max(0, int(off))
    except (ValueError, TypeError):
        off = 0

    flt_text = {"$text": {"$search": q}}
    flt_regex = {"file_name": re.compile(re.escape(q), re.IGNORECASE)}  # ✅ FIX 5: re.escape() - user input से regex injection रोकना
    all_m, tot, lim = [], 0, 20
    tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS
    col_counts, col_filters = {}, {}

    # ✅ FIX 6: सभी collections की count एक साथ (Concurrent) - पहले sequential था
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
        if len(all_m) >= lim: break
        count = col_counts[n]
        if count == 0: continue
        if remaining_skip >= count:
            remaining_skip -= count
            continue
        local_limit = lim - len(all_m)
        docs = await c.find(col_filters[n]).sort('_id', -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
        for d in docs: d['source_col'] = n.lower()
        all_m.extend(docs)
        remaining_skip = 0

    # ✅ FIX 7: process_doc - TMDb cached version use करना
    async def process_doc(d):
        fid = d.get("file_ref", d.get("file_id"))
        file_name = d.get("file_name", "Unknown File")

        db_thumb = d.get("thumb_url")
        tg_thumb = (
            db_thumb if db_thumb and db_thumb != "https://i.ibb.co/30B3RcS/default-movie.png"
            else f"/api/thumb?file_id={fid}"
        )

        if mode == 'smart':
            poster_url = await get_poster_cached(file_name)
            if not poster_url:
                poster_url = tg_thumb
        else:
            poster_url = tg_thumb

        return {
            "file_id": fid,
            "name": file_name,
            "size": get_size(d.get("file_size", 0)),
            "type": d.get("file_type", "document").upper(),
            "source": d.get("source_col", "unknown").capitalize(),
            "raw_collection": d.get("source_col", "primary"),
            "poster": poster_url,
            "tg_thumb": tg_thumb,
            "watch": f"/setup_stream?file_id={fid}&mode=watch",
            "download": f"/setup_stream?file_id={fid}&mode=download"
        }

    results_list = await asyncio.gather(*(process_doc(d) for d in all_m))

    return web.json_response({
        "results": list(results_list),
        "total": tot,
        "next_offset": off + lim if off + lim < tot else "",
        "is_admin": role == 'admin'
    })


# 📸 Telegram Thumbnail API
@search_routes.get('/api/thumb')
async def get_telegram_thumb(req):
    fid = req.query.get('file_id')
    if not fid: return web.Response(status=400)

    headers = {"Content-Disposition": 'inline; filename="poster.jpg"'}

    if fid in thumb_cache:
        if thumb_cache[fid] == "NO_THUMB":
            raise web.HTTPFound("https://i.ibb.co/30B3RcS/default-movie.png")
        return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)

    async with thumb_semaphore:
        # ✅ FIX 8: Double-check cache (race condition) - semaphore wait में दूसरा request आ सकता है
        if fid in thumb_cache:
            if thumb_cache[fid] == "NO_THUMB":
                raise web.HTTPFound("https://i.ibb.co/30B3RcS/default-movie.png")
            return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)

        try:
            msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
            thumb_id = None
            if msg.video and msg.video.thumbs: thumb_id = msg.video.thumbs[0].file_id
            elif msg.document and msg.document.thumbs: thumb_id = msg.document.thumbs[0].file_id

            if thumb_id:
                file_data = await temp.BOT.download_media(thumb_id, in_memory=True)
                thumb_bytes = file_data.getvalue()
                # ✅ FIX 9: Cache size limit - पुरानी entries हटाना
                if len(thumb_cache) >= MAX_CACHE:
                    oldest_key = next(iter(thumb_cache))
                    del thumb_cache[oldest_key]
                thumb_cache[fid] = thumb_bytes
                asyncio.create_task(msg.delete())
                return web.Response(body=thumb_bytes, content_type="image/jpeg", headers=headers)
            else:
                thumb_cache[fid] = "NO_THUMB"
                asyncio.create_task(msg.delete())
                raise web.HTTPFound("https://i.ibb.co/30B3RcS/default-movie.png")
        except web.HTTPFound:
            raise
        except Exception:
            raise web.HTTPFound("https://i.ibb.co/30B3RcS/default-movie.png")


async def _auto_del_msg(msg, delay):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


@search_routes.get('/setup_stream')
async def setup_stream(req):
    role, _ = await get_user_role(req)
    if not role: return web.Response(text="❌ Unauthorized!", status=403)
    fid, mode = req.query.get('file_id'), req.query.get('mode', 'watch')
    # ✅ FIX 10: fid=None check - missing file_id पर crash रोकना
    if not fid: return web.Response(text="❌ Missing file_id!", status=400)
    try:
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
        asyncio.create_task(_auto_del_msg(msg, 3600))
        return web.HTTPFound(f"/{'download' if mode == 'download' else 'watch'}/{msg.id}")
    except Exception as e:
        return web.Response(text=f"❌ Error: {e}", status=500)


@search_routes.post('/api/delete')
async def api_delete(req):
    role, _ = await get_user_role(req)
    if role != 'admin': return web.json_response({"error": "Admin only!"}, status=403)
    try:
        data = await req.json()
        col = data.get("collection", "primary").lower()
        # ✅ FIX 11: Invalid collection name पर KeyError crash रोकना
        if col not in COLLECTIONS:
            return web.json_response({"error": "Invalid collection!"}, status=400)
        res = await COLLECTIONS[col].delete_one(
            {"$or": [{"file_id": data.get("file_id")}, {"file_ref": data.get("file_id")}]}
        )
        return web.json_response({"success": bool(res.deleted_count)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@search_routes.post('/api/edit')
async def api_edit(req):
    role, _ = await get_user_role(req)
    if role != 'admin': return web.json_response({"error": "Admin only!"}, status=403)
    try:
        data = await req.json()
        col = data.get("collection", "primary").lower()
        # ✅ FIX 12: Invalid collection name पर KeyError crash रोकना
        if col not in COLLECTIONS:
            return web.json_response({"error": "Invalid collection!"}, status=400)
        # ✅ FIX 13: new_name empty/None check - blank name से DB corrupt होना रोकना
        new_name = data.get("new_name", "").strip()
        if not new_name:
            return web.json_response({"error": "New name cannot be empty!"}, status=400)
        res = await COLLECTIONS[col].update_one(
            {"$or": [{"file_id": data.get("file_id")}, {"file_ref": data.get("file_id")}]},
            {"$set": {"file_name": new_name}}
        )
        return web.json_response({"success": bool(res.modified_count)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@search_routes.get('/miniapp')
async def miniapp_page(req):
    return web.FileResponse(os.path.join("Web", "miniapp.html"))
