from aiohttp import web
import time
import uuid
from info import ADMIN_USERNAME, ADMIN_PASSWORD
from utils import temp, get_size
from database.users_chats_db import db as user_db
from database.ia_filterdb import db_count_documents, get_search_results, COLLECTIONS

admin_routes = web.RouteTableDef()

# ─────────────────────────────────────────────
# 🔒 AUTHENTICATION HELPERS
# ─────────────────────────────────────────────
def is_logged_in(request):
    session_id = request.cookies.get('admin_session')
    if not hasattr(temp, 'ADMIN_SESSIONS'): return False
    return session_id in temp.ADMIN_SESSIONS and time.time() < temp.ADMIN_SESSIONS[session_id]

# ─────────────────────────────────────────────
# 🔑 LOGIN ROUTES
# ─────────────────────────────────────────────
@admin_routes.get('/admin')
async def login_page(request):
    token = request.query.get('token')
    if not hasattr(temp, 'ADMIN_TOKENS'): temp.ADMIN_TOKENS = {}
    if not token or token not in temp.ADMIN_TOKENS or time.time() > temp.ADMIN_TOKENS[token]:
        return web.Response(text="❌ Invalid or Expired Token! Generate a new link from Telegram.", status=403)
    
    html = f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; margin: 0; }}
        .box {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); width: 320px; text-align: center; }}
        input {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; outline: none; }}
        button {{ width: 100%; padding: 12px; background: #0088cc; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 16px; }}
        button:hover {{ background: #006699; }}
    </style></head><body><div class="box"><h2>🔒 Admin Login</h2>
    <form action="/login" method="post"><input type="hidden" name="token" value="{token}">
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
        temp.ADMIN_SESSIONS[session_id] = time.time() + 3600 
        res = web.HTTPFound('/dashboard')
        res.set_cookie('admin_session', session_id)
        return res
    return web.Response(text="❌ Invalid Credentials. Try again.")

# ─────────────────────────────────────────────
# 📝 EDIT & DELETE API (FIXED FOR MULTI-COLLECTIONS)
# ─────────────────────────────────────────────
@admin_routes.post('/api/edit_file')
async def edit_file_api(request):
    if not is_logged_in(request): return web.json_response({"error": "Unauthorized"}, status=403)
    data = await request.json()
    file_id = data.get('id')
    new_name = data.get('name')
    
    if file_id and new_name:
        for name, col in COLLECTIONS.items():
            result = await col.update_one({"_id": file_id}, {"$set": {"file_name": new_name}})
            if result.modified_count > 0:
                return web.json_response({"status": "success"})
    return web.json_response({"error": "File not found"}, status=400)

@admin_routes.post('/api/delete_file')
async def delete_file_api(request):
    if not is_logged_in(request): return web.json_response({"error": "Unauthorized"}, status=403)
    data = await request.json()
    file_id = data.get('id')
    
    if file_id:
        for name, col in COLLECTIONS.items():
            result = await col.delete_one({"_id": file_id})
            if result.deleted_count > 0:
                return web.json_response({"status": "success"})
    return web.json_response({"error": "File not found"}, status=400)

# ─────────────────────────────────────────────
# 📊 MAIN DASHBOARD UI
# ─────────────────────────────────────────────
@admin_routes.get('/dashboard')
async def admin_dashboard(request):
    if not is_logged_in(request): return web.HTTPFound('/admin')

    stats = await db_count_documents()
    total_u = await user_db.total_users_count()
    db_size = get_size(await user_db.get_data_db_size())

    # Premium Users List
    p_users = []
    async for u in await user_db.get_premium_users():
        if u.get('status', {}).get('premium'):
            p_users.append(f"<li>👤 <code>{u['id']}</code> | Plan: {u['status'].get('plan')}</li>")
    p_list = "".join(p_users) if p_users else "<li>No active premium users.</li>"

    html = f"""
    <!DOCTYPE html><html><head>
    <title>Bot Admin Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #eef2f3; margin: 0; padding: 15px; color: #333; }}
        .container {{ max-width: 1000px; margin: auto; }}
        .header {{ background: linear-gradient(135deg, #0088cc, #00d2ff); color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        h3 {{ margin-top: 0; color: #0088cc; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .stat-val {{ font-size: 22px; font-weight: bold; color: #444; margin: 10px 0; }}
        .search-box {{ display: flex; gap: 10px; margin-top: 15px; }}
        .search-box input {{ flex: 1; padding: 12px 20px; border-radius: 30px; border: 1px solid #ddd; outline: none; }}
        .search-box button {{ padding: 10px 25px; border-radius: 30px; border: none; background: #0088cc; color: white; font-weight: bold; cursor: pointer; }}
        
        .res-item {{ display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #eee; gap: 10px; }}
        .res-name {{ flex: 1; font-size: 14px; word-break: break-all; }}
        .btn {{ padding: 6px 12px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px; color: white; font-weight: bold; text-decoration: none; }}
        .btn-edit {{ background: #ffc107; color: black; }}
        .btn-del {{ background: #dc3545; }}
        .btn-play {{ background: #28a745; }}

        #editModal {{ display: none; position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); justify-content: center; align-items: center; z-index: 1000; }}
        .modal-content {{ background: white; padding: 25px; border-radius: 12px; width: 90%; max-width: 400px; }}
        .modal-content input {{ width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ddd; border-radius: 8px; }}
        .p-list {{ list-style: none; padding: 0; max-height: 150px; overflow-y: auto; }}
        .p-list li {{ padding: 8px; border-bottom: 1px dotted #ccc; font-size: 13px; }}
    </style>
    </head><body>
    
    <div class="container">
        <div class="header"><h1>🚀 Admin Control Center</h1></div>

        <div class="grid">
            <div class="card">
                <h3>📊 Database Stats</h3>
                <div class="stat-val">📂 {stats['total']} <small>Files</small></div>
                <div class="stat-val">👥 {total_u} <small>Users</small></div>
                <p>🗄️ Size: <b>{db_size}</b></p>
            </div>

            <div class="card">
                <h3>💎 Premium Users</h3>
                <ul class="p-list">{p_list}</ul>
            </div>

            <div class="card" style="grid-column: 1 / -1;">
                <h3>🔍 Live File Manager</h3>
                <div class="search-box">
                    <input type="text" id="q" placeholder="Search file to Edit or Delete...">
                    <button onclick="search(0)">Search 🔍</button>
                </div>
                <div id="results"></div>
            </div>
        </div>
    </div>

    <div id="editModal">
        <div class="modal-content">
            <h3 style="color:#333">📝 Edit File Name</h3>
            <input type="text" id="newNameInput">
            <input type="hidden" id="editFileId">
            <div style="display:flex; gap:10px;">
                <button onclick="saveEdit()" style="flex:1; background:#28a745; color:white; border:none; padding:12px; border-radius:8px; cursor:pointer; font-weight:bold;">Save Changes</button>
                <button onclick="closeModal()" style="flex:1; background:#6c757d; color:white; border:none; padding:12px; border-radius:8px; cursor:pointer; font-weight:bold;">Cancel</button>
            </div>
        </div>
    </div>

    <script>
    async function search(off) {{
        let q = document.getElementById('q').value;
        if(!q) return;
        let res = await fetch(`/api/search?q=${{encodeURIComponent(q)}}&offset=${{off}}`);
        let data = await res.json();
        let out = "";
        data.results.forEach(f => {{
            let fid = f.watch.split('file_id=')[1].split('&')[0];
            out += `
            <div class="res-item" id="row-${{fid}}">
                <div class="res-name" id="name-${{fid}}">${{f.name}}</div>
                <div class="action-btns">
                    <a href="${{f.watch}}" target="_blank" class="btn btn-play">Play</a>
                    <button class="btn btn-edit" onclick="openEdit('${{fid}}', '${{f.name.replace(/'/g, "\\'")}}')">Edit</button>
                    <button class="btn btn-del" onclick="deleteFile('${{fid}}')">Del</button>
                </div>
            </div>`;
        }});
        document.getElementById('results').innerHTML = out || "No files found.";
    }}

    function openEdit(id, name) {{
        document.getElementById('editFileId').value = id;
        document.getElementById('newNameInput').value = name;
        document.getElementById('editModal').style.display = 'flex';
    }}

    function closeModal() {{ document.getElementById('editModal').style.display = 'none'; }}

    async function saveEdit() {{
        let id = document.getElementById('editFileId').value;
        let newName = document.getElementById('newNameInput').value;
        let res = await fetch('/api/edit_file', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{id: id, name: newName}})
        }});
        let data = await res.json();
        if(data.status === 'success') {{
            document.getElementById('name-'+id).innerText = newName;
            closeModal();
        }} else {{ alert("Error updating name!"); }}
    }}

    async function deleteFile(id) {{
        if(!confirm("Are you sure you want to delete this?")) return;
        let res = await fetch('/api/delete_file', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{id: id}})
        }});
        let data = await res.json();
        if(data.status === 'success') {{ document.getElementById('row-'+id).remove(); }}
    }}
    </script>
    </body></html>
    """
    return web.Response(text=html, content_type='text/html')
