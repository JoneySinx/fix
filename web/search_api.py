from aiohttp import web
import time, re, asyncio, os
from utils import temp, get_size, is_rate_limited, is_premium
from helpers.tmdb import get_poster
from info import BIN_CHANNEL, ADMINS
from database.ia_filterdb import COLLECTIONS

search_routes = web.RouteTableDef()
thumb_cache = {} 
# 🔥 NEW FEATURE: Traffic Controller (एक बार में सिर्फ 4 टेलीग्राम फोटो लोड होंगी)
thumb_semaphore = asyncio.Semaphore(4) 

# ✅ Unified Auth Check (Admins और Premium Users के लिए)
async def get_user_role(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and temp.USER_SESSIONS.get(s_user, {}).get('expiry', 0) > time.time():
        tg_id = temp.USER_SESSIONS[s_user]['tg_id']
        if tg_id in ADMINS:
            return 'admin', tg_id
        if await is_premium(tg_id):
            return 'user', tg_id
    return None, None

@search_routes.get('/api/search')
async def api_search(req):
    role, tg_id = await get_user_role(req)
    if not role: 
        return web.json_response({"error": "Unauthorized Access or Premium Expired"}, status=403)

    if is_rate_limited(tg_id, "web_search", 1):
        return web.json_response({"error": "Searching too fast! Please slow down."}, status=429)

    q = req.query.get('q', '').strip()
    off = req.query.get('offset', '0')
    col = req.query.get('col', 'all').lower()
    
    if not q: return web.json_response({"results": [], "total": 0, "next_offset": ""})
    
    off = int(off) if off.isdigit() else 0
    
    flt_text = {"$text": {"$search": q}}
    flt_regex = {"file_name": re.compile(q, re.IGNORECASE)}
    
    res, all_m, tot, lim = [], [], 0, 20
    tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS

    col_counts = {}
    col_filters = {}

    for n, c in tgt_cols.items():
        count = await c.count_documents(flt_text)
        active_flt = flt_text
        if count == 0:
            count = await c.count_documents(flt_regex)
            active_flt = flt_regex
            
        col_counts[n] = count
        col_filters[n] = active_flt
        tot += count

    remaining_skip = off
    for n, c in tgt_cols.items():
        if len(all_m) >= lim:
            break
        count = col_counts[n]
        if count == 0: continue
            
        if remaining_skip >= count:
            remaining_skip -= count
            continue
            
        local_limit = lim - len(all_m)
        docs = await c.find(col_filters[n]).sort('_id', -1).skip(remaining_skip).limit(local_limit).to_list(length=local_limit)
        
        for d in docs: 
            d['source_col'] = n.lower()
        all_m.extend(docs)
        
        remaining_skip = 0 

    # रिज़ल्ट्स को फॉर्मेट करना
    for d in all_m:
        fid = d.get("file_ref", d.get("file_id"))
        file_name = d.get("file_name", "Unknown File")
        
        # 🌟 PRO FEATURE 1: Database से फास्ट Telegraph लिंक निकालना
        db_thumb = d.get("thumb_url")
        if not db_thumb or db_thumb == "https://i.ibb.co/30B3RcS/default-movie.png":
            tg_thumb = f"/api/thumb?file_id={fid}" # पुरानी फाइलों के लिए Fallback
        else:
            tg_thumb = db_thumb # नई फाइलों के लिए सुपरफास्ट Telegraph लिंक!
        
        poster_url = await get_poster(file_name)
        if not poster_url:
            poster_url = tg_thumb
            
        res.append({
            "file_id": fid,
            "name": file_name,
            "size": get_size(d.get("file_size", 0)),
            "type": d.get("file_type", "document").upper(),
            "source": d.get("source_col", "unknown").capitalize(),
            "raw_collection": d.get("source_col", "primary"),
            "poster": poster_url, 
            "tg_thumb": tg_thumb, # ✅ NAYA FEATURE: फ्रंटएंड को फास्ट लिंक देना
            "watch": f"/setup_stream?file_id={fid}&mode=watch",
            "download": f"/setup_stream?file_id={fid}&mode=download"
        })

    return web.json_response({
        "results": res, 
        "total": tot, 
        "next_offset": off + lim if off + lim < tot else "",
        "is_admin": role == 'admin' 
    })

# 📸 PRO FEATURE 2: असली टेलीग्राम थंबनेल डाउनलोड करने वाला API (With Semaphore & .bin FIX)
@search_routes.get('/api/thumb')
async def get_telegram_thumb(req):
    fid = req.query.get('file_id')
    if not fid: return web.Response(status=400)
    
    # ✅ FIX: Chrome को बताना कि यह .bin नहीं, बल्कि .jpg है
    headers = {"Content-Disposition": 'inline; filename="poster.jpg"'}
    
    if fid in thumb_cache:
        if thumb_cache[fid] == "NO_THUMB":
            raise web.HTTPFound("https://i.ibb.co/30B3RcS/default-movie.png")
        return web.Response(body=thumb_cache[fid], content_type="image/jpeg", headers=headers)
        
    # 🚦 Semaphore - सिर्फ 4 रिक्वेस्ट अंदर जाएंगी, बाकी इंतज़ार करेंगी
    async with thumb_semaphore:
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
    try: 
        await msg.delete()
    except Exception: 
        pass

@search_routes.get('/setup_stream')
async def setup_stream(req):
    role, _ = await get_user_role(req)
    if not role: return web.Response(text="❌ Unauthorized Access!", status=403)
    
    fid, mode = req.query.get('file_id'), req.query.get('mode', 'watch')
    if not fid: return web.Response(text="Invalid Request", status=400)
    
    try:
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
        asyncio.create_task(_auto_del_msg(msg, 3600))
        return web.HTTPFound(f"/{'download' if mode == 'download' else 'watch'}/{msg.id}")
    except Exception as e: 
        return web.Response(text=f"❌ Error: {e}", status=500)

@search_routes.post('/api/delete')
async def api_delete(req):
    role, _ = await get_user_role(req)
    if role != 'admin': return web.json_response({"error": "Only Admins can delete files!"}, status=403)
    try:
        data = await req.json()
        file_id = data.get("file_id")
        collection = data.get("collection", "primary").lower()
        if collection in COLLECTIONS:
            result = await COLLECTIONS[collection].delete_one({"$or": [{"file_id": file_id}, {"file_ref": file_id}]})
            if result.deleted_count > 0: return web.json_response({"success": True, "message": "File deleted successfully!"})
        return web.json_response({"error": "File not found!"}, status=404)
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

@search_routes.post('/api/edit')
async def api_edit(req):
    role, _ = await get_user_role(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized! Admin only."}, status=403)
    try:
        data = await req.json()
        file_id = data.get("file_id")
        collection = data.get("collection", "primary").lower()
        new_name = data.get("new_name")
        if not new_name: return web.json_response({"error": "Name cannot be empty!"}, status=400)
        if collection in COLLECTIONS:
            result = await COLLECTIONS[collection].update_one({"$or": [{"file_id": file_id}, {"file_ref": file_id}]}, {"$set": {"file_name": new_name}})
            if result.modified_count > 0: return web.json_response({"success": True, "message": "File updated successfully!"})
        return web.json_response({"error": "File not found or no changes made!"}, status=404)
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

@search_routes.get('/miniapp')
async def miniapp_page(req):
    file_path = os.path.join("Web", "miniapp.html") 
    return web.FileResponse(file_path)
