from aiohttp import web
import time, re
from utils import temp, get_size
from info import BIN_CHANNEL
from database.ia_filterdb import COLLECTIONS

search_routes = web.RouteTableDef()

def is_auth(req):
    s = req.cookies.get('admin_session')
    return bool(s and hasattr(temp, 'ADMIN_SESSIONS') and temp.ADMIN_SESSIONS.get(s, 0) > time.time())

@search_routes.get('/api/search')
async def api_search(req):
    if not is_auth(req): 
        return web.json_response({"error": "Unauthorized Access"}, status=403)

    q, off, col = req.query.get('q', '').strip(), req.query.get('offset', '0'), req.query.get('col', 'all').lower()
    if not q: return web.json_response({"results": [], "total": 0, "next_offset": ""})
    
    off = int(off) if off.isdigit() else 0
    flt = {"file_name": re.compile(q, re.IGNORECASE)}
    
    res, all_m, tot, lim = [], [], 0, 20
    tgt_cols = {col: COLLECTIONS[col]} if col in COLLECTIONS else COLLECTIONS

    for n, c in tgt_cols.items():
        tot += await c.count_documents(flt)
        # 🚀 FIX: Motor's .to_list() is 10x faster than async for loop
        if len(all_m) < off + lim:
            docs = await c.find(flt).sort('_id', -1).limit(off + lim).to_list(off + lim)
            for d in docs: d['source_col'] = n.capitalize()
            all_m.extend(docs)

    for d in all_m[off : off + lim]:
        fid = d.get("file_ref", d.get("file_id"))
        res.append({
            "name": d.get("file_name", "Unknown File"),
            "size": get_size(d.get("file_size", 0)),
            "type": d.get("file_type", "document").upper(),
            "source": d.get("source_col", "Unknown"),
            "watch": f"/setup_stream?file_id={fid}&mode=watch",
            "download": f"/setup_stream?file_id={fid}&mode=download"
        })

    return web.json_response({
        "results": res, 
        "total": tot, 
        "next_offset": off + lim if off + lim < tot else ""
    })

@search_routes.get('/setup_stream')
async def setup_stream(req):
    if not is_auth(req): return web.Response(text="❌ Unauthorized Access!", status=403)
    
    fid, mode = req.query.get('file_id'), req.query.get('mode', 'watch')
    if not fid: return web.Response(text="Invalid Request", status=400)
    
    try:
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=fid)
        # 🚀 FIX: Directly returning HTTPFound is cleaner than raising it as an exception
        return web.HTTPFound(f"/{'download' if mode == 'download' else 'watch'}/{msg.id}")
    except Exception as e: 
        return web.Response(text=f"❌ Error: {e}", status=500)
