from aiohttp import web
import time
import uuid
from info import ADMIN_USERNAME, ADMIN_PASSWORD, ADMINS
from utils import temp, get_size
from database.users_chats_db import db as user_db
from database.ia_filterdb import db_count_documents, get_search_results, COLLECTIONS
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

admin_routes = web.RouteTableDef()

# ─────────────────────────────────────────────
# 🔒 AUTH HELPERS
# ─────────────────────────────────────────────
def is_logged_in(request):
    session_id = request.cookies.get('admin_session')
    if not hasattr(temp, 'ADMIN_SESSIONS'): return False
    return session_id in temp.ADMIN_SESSIONS and time.time() < temp.ADMIN_SESSIONS[session_id]

# ─────────────────────────────────────────────
# 🔑 LOGIN & API LOGIC
# ─────────────────────────────────────────────
@admin_routes.get('/admin')
async def login_page(request):
    # टोकन सिस्टम हटा दिया गया है, सीधे लॉगिन फॉर्म खुलेगा
    html = f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #0f0f1a; margin: 0; color: white; }}
        .box {{ background: #1a1a2e; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 300px; text-align: center; }}
        input {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #333; border-radius: 8px; background: #16213e; color: white; box-sizing: border-box; outline: none; }}
        button {{ width: 100%; padding: 12px; background: #00d2ff; color: #0f0f1a; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px; margin-top: 10px; }}
    </style></head><body><div class="box"><h2>🔐 Admin Login</h2><form action="/login" method="post">
    <input type="text" name="user" placeholder="Username" required><input type="password" name="pass" placeholder="Password" required>
    <button type="submit">Login</button></form></div></body></html>
    """
    return web.Response(text=html, content_type='text/html')

@admin_routes.post('/login')
async def login_post(request):
    data = await request.post()
    if data.get('user') == ADMIN_USERNAME and data.get('pass') == ADMIN_PASSWORD:
        session_id = str(uuid.uuid4())
        if not hasattr(temp, 'ADMIN_SESSIONS'): temp.ADMIN_SESSIONS = {}
        
        # ⏱️ 1 Hour Limit (3600 seconds)
        temp.ADMIN_SESSIONS[session_id] = time.time() + 3600
        
        res = web.HTTPFound('/dashboard')
        res.set_cookie('admin_session', session_id, max_age=3600)
        
        # 🛑 Telegram Alert & Disconnect Button
        try:
            btn = [[InlineKeyboardButton("🛑 Disconnect Web Session", callback_data=f"logout_{session_id}")]]
            await temp.BOT.send_message(
                chat_id=ADMINS[0], 
                text="✅ **Web Login Detected!**\n\nYour session is active for 1 hour. If this wasn't you, disconnect immediately.",
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except Exception as e:
            print(f"Login Alert Error: {e}")

        return res
    return web.Response(text="<html><body style='background:#0f0f1a;color:red;text-align:center;padding:50px;'><h2>❌ Wrong Credentials!</h2><a href='/admin' style='color:white;'>Try Again</a></body></html>", content_type='text/html')

@admin_routes.post('/api/edit_file')
async def edit_file_api(request):
    if not is_logged_in(request): return web.json_response({"err": "no"}, status=403)
    data = await request.json()
    fid, name = data.get('id'), data.get('name')
    for col in COLLECTIONS.values():
        res = await col.update_one({"_id": fid}, {"$set": {"file_name": name}})
        if res.modified_count > 0: return web.json_response({"status": "success"})
    return web.json_response({"status": "fail"})

@admin_routes.post('/api/delete_file')
async def delete_file_api(request):
    if not is_logged_in(request): return web.json_response({"err": "no"}, status=403)
    data = await request.json()
    fid = data.get('id')
    for col in COLLECTIONS.values():
        res = await col.delete_one({"_id": fid})
        if res.deleted_count > 0: return web.json_response({"status": "success"})
    return web.json_response({"status": "fail"})

# ─────────────────────────────────────────────
# 📊 SMART DASHBOARD UI
# ─────────────────────────────────────────────
@admin_routes.get('/dashboard')
async def admin_dashboard(request):
    if not is_logged_in(request): return web.HTTPFound('/admin')
    stats = await db_count_documents()

    html = f"""
    <!DOCTYPE html><html><head>
    <title>Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: white; margin: 0; padding: 15px; }}
        .container {{ max-width: 800px; margin: auto; }}
        .header {{ text-align: center; margin-bottom: 25px; background: #1a1a2e; padding: 20px; border-radius: 15px; }}
        .search-box {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        .search-box input {{ flex: 1; padding: 15px 20px; border-radius: 30px; border: 1px solid #333; background: #16213e; color: white; outline: none; }}
        .search-box button {{ padding: 12px 25px; border-radius: 30px; border: none; background: #00d2ff; color: #0f0f1a; font-weight: bold; cursor: pointer; }}
        
        #results-info {{ color: #00d2ff; font-weight: bold; margin-bottom: 15px; display: none; text-align: center; }}
        
        /* 📱 CARD LOOK LIKE PHOTO */
        .card {{ background: #1a1a2e; padding: 20px; border-radius: 15px; margin-bottom: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); border-left: 4px solid #00d2ff; }}
        .card-title {{ font-weight: bold; margin-bottom: 8px; font-size: 16px; line-height: 1.4; }}
        .card-meta {{ font-size: 13px; color: #a0a0b0; margin-bottom: 15px; }}
        
        .btn-group {{ display: flex; gap: 10px; }}
        .btn-play {{ flex: 1; background: #28a745; color: white; text-align: center; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; }}
        
        /* ⚙️ SMART ACTION BUTTON */
        .btn-action {{ background: #3a3a5e; color: white; padding: 10px 15px; border-radius: 8px; cursor: pointer; border: none; position: relative; }}
        .dropdown {{ display: none; position: absolute; right: 0; top: 45px; background: white; border-radius: 8px; min-width: 120px; box-shadow: 0 5px 20px rgba(0,0,0,0.5); z-index: 10; }}
        .dropdown button {{ display: block; width: 100%; padding: 12px; border: none; background: none; text-align: left; cursor: pointer; font-size: 14px; color: #333; }}
        .dropdown button:hover {{ background: #f0f0f0; }}
        .drop-del {{ color: #dc3545 !important; font-weight: bold; border-top: 1px solid #eee !important; }}

        .pagination {{ display: none; justify-content: center; gap: 15px; margin-top: 25px; }}
        .pagination button {{ padding: 10px 20px; background: #16213e; color: white; border-radius: 8px; border: 1px solid #333; cursor: pointer; }}
        
        #editModal {{ display: none; position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); justify-content: center; align-items: center; z-index: 100; }}
        .modal-content {{ background: white; padding: 25px; border-radius: 12px; width: 90%; max-width: 400px; color: #333; }}
        .modal-content input {{ width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ddd; border-radius: 8px; }}
    </style>
    </head><body>
    
    <div class="container">
        <div class="header">
            <h1>🍿 Admin Control</h1>
            <p>Total Files: <b>{stats['total']}</b></p>
        </div>

        <div class="search-box">
            <input type="text" id="q" placeholder="Search file name...">
            <button onclick="search(0)">Search</button>
        </div>
        
        <div id="results-info"></div>
        <div id="results"></div>

        <div class="pagination" id="page-box">
            <button id="pBtn" onclick="prev()">⬅️ Previous</button>
            <button id="nBtn" onclick="next()">Next ➡️</button>
        </div>
    </div>

    <div id="editModal"><div class="modal-content">
        <h3>📝 Edit File Name</h3>
        <input type="text" id="newName">
        <input type="hidden" id="editFid">
        <div style="display:flex; gap:10px;">
            <button onclick="saveEdit()" style="flex:1; background:#28a745; color:white; border:none; padding:12px; border-radius:8px;">Save</button>
            <button onclick="closeModal()" style="flex:1; background:#6c757d; color:white; border:none; padding:12px; border-radius:8px;">Cancel</button>
        </div>
    </div></div>

    <script>
    let curQ = "", curOff = 0, nextOff = "";

    async function search(off) {{
        let q = document.getElementById('q').value;
        if(!q) return;
        curQ = q; curOff = off;
        let res = await fetch(`/api/search?q=${{encodeURIComponent(q)}}&offset=${{off}}`);
        let data = await res.json();
        
        document.getElementById('results-info').style.display = 'block';
        document.getElementById('results-info').innerText = `📊 Found ${{data.total}} Results`;

        let out = "";
        data.results.forEach(f => {{
            let fid = f.watch.split('file_id=')[1].split('&')[0];
            out += `
            <div class="card" id="row-${{fid}}">
                <div class="card-title">${{f.name}}</div>
                <div class="card-meta">💾 ${{f.size}} | 📁 ${{f.type}}</div>
                <div class="btn-group">
                    <a href="${{f.watch}}" target="_blank" class="btn-play">▶️ Play</a>
                    <div style="position:relative">
                        <button class="btn-action" onclick="toggleDrop('${{fid}}')"><i class="fas fa-ellipsis-v"></i> Action</button>
                        <div class="dropdown" id="drop-${{fid}}">
                            <button onclick="openEdit('${{fid}}', '${{f.name.replace(/'/g, "\\'")}}')"><i class="fas fa-edit"></i> Edit</button>
                            <button class="drop-del" onclick="deleteFile('${{fid}}')"><i class="fas fa-trash"></i> Delete</button>
                        </div>
                    </div>
                </div>
            </div>`;
        }});
        document.getElementById('results').innerHTML = out || "Not Found";
        
        nextOff = data.next_offset;
        document.getElementById('page-box').style.display = 'flex';
        document.getElementById('pBtn').style.display = off > 0 ? 'block' : 'none';
        document.getElementById('nBtn').style.display = nextOff ? 'block' : 'none';
    }}

    function toggleDrop(id) {{
        let d = document.getElementById('drop-'+id);
        document.querySelectorAll('.dropdown').forEach(x => {{ if(x.id !== 'drop-'+id) x.style.display = 'none'; }});
        d.style.display = (d.style.display === 'block') ? 'none' : 'block';
    }}

    function openEdit(id, name) {{
        document.getElementById('editFid').value = id;
        document.getElementById('newName').value = name;
        document.getElementById('editModal').style.display = 'flex';
    }}

    function closeModal() {{ document.getElementById('editModal').style.display = 'none'; }}

    async function saveEdit() {{
        let id = document.getElementById('editFid').value;
        let name = document.getElementById('newName').value;
        let res = await fetch('/api/edit_file', {{ method:'POST', body:JSON.stringify({{id: id, name: name}}) }});
        if((await res.json()).status === 'success') {{
            location.reload(); 
        }}
    }}

    async function deleteFile(id) {{
        if(!confirm("⚠️ Delete this file permanently?")) return;
        let res = await fetch('/api/delete_file', {{ method:'POST', body:JSON.stringify({{id: id}}) }});
        if((await res.json()).status === 'success') {{ document.getElementById('row-'+id).remove(); }}
    }}

    function next() {{ if(nextOff) search(nextOff); window.scrollTo(0,0); }}
    function prev() {{ search(Math.max(0, curOff-20)); window.scrollTo(0,0); }}
    </script>
    </body></html>
    """
    return web.Response(text=html, content_type='text/html')
