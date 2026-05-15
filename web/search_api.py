from aiohttp import web
import time, re, asyncio, os
from utils import temp, get_size, is_rate_limited, is_premium
from helpers.tmdb import get_poster
from info import BIN_CHANNEL, ADMINS
from database.ia_filterdb import COLLECTIONS

search_routes = web.RouteTableDef()
thumb_cache = {} 
# 🔥 Traffic Controller (एक बार में सिर्फ 4 टेलीग्राम फोटो लोड होंगी)
thumb_semaphore = asyncio.Semaphore(4) 

# ✅ Unified Auth Check
async def get_user_role(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and temp.USER_SESSIONS.get(s_user, {}).get('expiry', 0) > time.time():
        tg_id = temp.USER_SESSIONS[s_user]['tg_id']
        if tg_id in ADMINS: return 'admin', tg_id
        if await is_premium(tg_id): return 'user', tg_id
    return None, None

@search_routes.get('/api/search')
async def api_search(req):
    role, tg_id = await get_user_role(req)
    if not role: return web.json_response({"error": "Unauthorized Access"}, status=403)
    if is_rate_limited(tg_id, "web_search", 1): return web.json_response({"error": "Searching too fast!"}, status=429)

    q = req.query.get('q', '').strip()
    off = req.query.get('offset', '0')
    col = req.query.get('col', 'all').lower()
    mode = req.query.get('mode', 'smart').lower() # ✅ FIX: Frontend से Mode लेना
    
    if not q: return web.json_response({"results": [], "total": 0, "next_offset": ""})
    
    off = int(off) if off.isdigit() else 0
    flt_text, flt_regex = {"$text": {"$search": q}}, {"file_name": re.compile(q, re.IGNORECASE)}
    all_m, tot, lim = [], 0, 20
    tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS
    col_counts, col_filters = {}, {}

    for n, c in tgt_cols.items():
        count = await c.count_documents(flt_text)
        active_flt = flt_text if count > 0 else flt_regex
        count = await c.count_documents(active_flt) if count == 0 else count
        col_counts[n], col_filters[n] = count, active_flt
        tot += count

    remaining_skip = off
    for n, c in tgt_cols.items():
        if len(all_m) >= lim: break
        count = col_counts[n]
        if count == 0: continue
        if remaining_skip >= count: remaining_skip -= count; continue
        local_limit = lim - len(all_m)
        docs = await c.find(col_filters[n]).sort('_id', -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
        for d in docs: d['source_col'] = n.lower()
        all_m.extend(docs)
        remaining_skip = 0 

    # 🚀 Concurrent Processing Logic (Superfast)
    async def process_doc(d):
        fid = d.get("file_ref", d.get("file_id"))
        file_name = d.get("file_name", "Unknown File")
        
        db_thumb = d.get("thumb_url")
        tg_thumb = db_thumb if db_thumb and db_thumb != "https://i.ibb.co/30B3RcS/default-movie.png" else f"/api/thumb?file_id={fid}"
        
        poster_url = ""
        # ✅ FIX: Smart Mode होने पर ही TMDb से पोस्टर मँगाना
        if mode == 'smart':
            poster_url = await get_poster(file_name)
            if not poster_url: poster_url = tg_thumb
        else:
            poster_url = tg_thumb
            
        return {
            "file_id": fid, "name": file_name, "size": get_size(d.get("file_size", 0)),
            "type": d.get("file_type", "document").upper(), "source": d.get("source_col", "unknown").capitalize(),
            "raw_collection": d.get("source_col", "primary"), "poster": poster_url, 
            "tg_thumb": tg_thumb, "watch": f"/setup_stream?file_id={fid}&mode=watch",
            "download": f"/setup_stream?file_id={fid}&mode=download"
        }

    # ✅ एक साथ सारे रिजल्ट्स प्रोसेस करना (Concurrent)
    results_list = await asyncio.gather(*(process_doc(d) for d in all_m))

    return web.json_response({
        "results": list(results_list), 
        "total": tot, 
        "next_offset": off + lim if off + lim < tot else "", 
        "is_admin": role == 'admin'
    })

# 📸 Telegram Thumbnail API (With Semaphore & .bin FIX)
@search_routes.get('/api/thumb')
async def get_telegram_thumb(req):
    fid = req.query.get('file_id')
    if not fid: return web.Response(status=400)
    
    headers = {"Content-Disposition": 'inline; filename="poster.jpg"'}
    
    if fid in thumb_cache:
        if thumb_cache[fid] == "NO_THUMB": raise web.HTTPFound("https://i.ibb.co/30B3RcS/default-movie.png")
        return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)
        
    async with thumb_semaphore:
        try:
            msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
            thumb_id = None
            if msg.video and msg.video.thumbs: thumb_id = msg.video.thumbs[0].file_id
            elif msg.document and msg.document.thumbs: thumb_id = msg.document.thumbs[0].file_id
                
            if thumb_id:
                file_data = await temp.BOT.download_media(thumb_id, in_memory=True)
                thumb_bytes = file_data.getvalue()
                thumb_cache[fid] = thumb_bytes
                asyncio.create_task(msg.delete())
                return web.Response(body=thumb_bytes, content_type="image/jpeg", headers=headers)
            else:
                thumb_cache[fid] = "NO_THUMB"
                asyncio.create_task(msg.delete())
                raise web.HTTPFound("https://i.ibb.co/30B3RcS/default-movie.png")
        except Exception:
            raise web.HTTPFound("https://i.ibb.co/30B3RcS/default-movie.png")

async def _auto_del_msg(msg, delay):
    await asyncio.sleep(delay)
    try: await msg.delete()
    except Exception: pass

@search_routes.get('/setup_stream')
async def setup_stream(req):
    role, _ = await get_user_role(req)
    if not role: return web.Response(text="❌ Unauthorized!", status=403)
    fid, mode = req.query.get('file_id'), req.query.get('mode', 'watch')
    try:
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
        asyncio.create_task(_auto_del_msg(msg, 3600))
        return web.HTTPFound(f"/{'download' if mode == 'download' else 'watch'}/{msg.id}")
    except Exception as e: return web.Response(text=f"❌ Error: {e}", status=500)

@search_routes.post('/api/delete')
async def api_delete(req):
    role, _ = await get_user_role(req)
    if role != 'admin': return web.json_response({"error": "Admin only!"}, status=403)
    try:
        data = await req.json()
        col = data.get("collection", "primary").lower()
        res = await COLLECTIONS[col].delete_one({"$or": [{"file_id": data.get("file_id")}, {"file_ref": data.get("file_id")}]})
        return web.json_response({"success": True if res.deleted_count else False})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

@search_routes.post('/api/edit')
async def api_edit(req):
    role, _ = await get_user_role(req)
    if role != 'admin': return web.json_response({"error": "Admin only!"}, status=403)
    try:
        data = await req.json()
        col = data.get("collection", "primary").lower()
        res = await COLLECTIONS[col].update_one({"$or": [{"file_id": data.get("file_id")}, {"file_ref": data.get("file_id")}]}, {"$set": {"file_name": data.get("new_name")}})
        return web.json_response({"success": True if res.modified_count else False})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

@search_routes.get('/miniapp')
async def miniapp_page(req):
    return web.FileResponse(os.path.join("Web", "miniapp.html"))
