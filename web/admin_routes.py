from aiohttp import web
import time
import uuid
import asyncio
from info import ADMIN_USERNAME, ADMIN_PASSWORD, BIN_CHANNEL
from utils import temp, get_size
from database.users_chats_db import db as user_db
from database.ia_filterdb import db_count_documents, get_search_results

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
        return web.Response(text="❌ Invalid/Expired Token. Get new link from Telegram.", status=403)
    
    html = f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>
    body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; margin: 0; }}
    .box {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); width: 300px; text-align: center; }}
    input {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }}
    button {{ width: 100%; padding: 10px; background: #0088cc; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }}
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
    return web.Response(text="❌ Invalid Credentials")

# ─────────────────────────────────────────────
# 📊 MAIN DASHBOARD
# ─────────────────────────────────────────────
@admin_routes.get('/dashboard')
async def admin_dashboard(request):
    if not is_logged_in(request): return web.HTTPFound('/admin')

    # Fetch Data
    stats = await db_count_documents()
    total_u = await user_db.total_users_count()
    total_c = await user_db.total_chat_count()
    db_size = get_size(await user_db.get_data_db_size())

    # Premium Users List
    p_users = []
    async for u in await user_db.get_premium_users():
        if u.get('status', {}).get('premium'):
            p_users.append(f"<li>👤 <code>{u['id']}</code> | Plan: {u['status'].get('plan')}</li>")
    p_list = "".join(p_users) if p_users else "<li>No premium users</li>"

    html = f"""
    <!DOCTYPE html><html><head>
    <title>Admin Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #eef2f3; margin: 0; padding: 20px; }}
        .container {{ max-width: 1000px; margin: auto; }}
        .header {{ background: #0088cc; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
        h3 {{ margin-top: 0; color: #0088cc; border-bottom: 20px; }}
        .stat-val {{ font-size: 24px; font-weight: bold; color: #333; }}
        .search-box {{ display: flex; gap: 10px; margin: 15px 0; }}
        .search-box input {{ flex: 1; padding: 12px; border-radius: 25px; border: 1px solid #ddd; outline: none; }}
        .search-box button {{ padding: 10px 20px; border-radius: 25px; border: none; background: #0088cc; color: white; cursor: pointer; }}
        #results {{ margin-top: 15px; }}
        .res-item {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .btn-s {{ padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 12px; color: white; }}
        .p-list {{ list-style: none; padding: 0; max-height: 200px; overflow-y: auto; }}
        .p-list li {{ padding: 8px; border-bottom: 1px dotted #ccc; font-size: 14px; }}
    </style>
    </head><body>
    <div class="container">
        <div class="header"><h1>🚀 Bot Admin Dashboard</h1></div>
        
        <div class="grid">
            <div class="card">
                <h3>📊 Database Stats</h3>
                <div class="stat-val">{stats['total']} <small>Files</small></div>
                <div class="stat-val">{total_u} <small>Users</small></div>
                <div class="stat-val">{total_c} <small>Groups</small></div>
                <p>🗄️ Size: {db_size}</p>
            </div>

            <div class="card">
                <h3>💎 Premium Users</h3>
                <ul class="p-list">{p_list}</ul>
            </div>

            <div class="card" style="grid-column: 1 / -1;">
                <h3>🔍 Live Search & Manage</h3>
                <div class="search-box">
                    <input type="text" id="q" placeholder="Search file name...">
                    <button onclick="search(0)">Search</button>
                </div>
                <div id="loader" style="display:none">Searching...</div>
                <div id="results"></div>
                <div id="page" style="margin-top:15px; display:none; gap:10px;">
                    <button id="pBtn" onclick="prev()">⬅️ Prev</button>
                    <button id="nBtn" onclick="next()">Next ➡️</button>
                </div>
            </div>
        </div>
    </div>

    <script>
    let curQ = "", curOff = 0, nextOff = "";
    async def search(off) {{
        let q = document.getElementById('q').value;
        if(!q) return;
        curQ = q; curOff = off;
        document.getElementById('loader').style.display = 'block';
        let res = await fetch(`/api/search?q=${{encodeURIComponent(q)}}&offset=${{off}}`);
        let data = await res.json();
        document.getElementById('loader').style.display = 'none';
        
        let out = "";
        data.results.forEach(f => {{
            out += `<div class="res-item">
                <b>${{f.name}}</b> (${{f.size}})<br>
                <a href="${{f.watch}}" target="_blank" style="color:green">[PLAY]</a> 
                <a href="${{f.download}}" style="color:blue">[DL]</a>
            </div>`;
        }});
        document.getElementById('results').innerHTML = out || "No results";
        nextOff = data.next_offset;
        document.getElementById('page').style.display = data.total > 20 ? 'flex' : 'none';
        document.getElementById('pBtn').style.display = off > 0 ? 'block' : 'none';
        document.getElementById('nBtn').style.display = nextOff ? 'block' : 'none';
    }}
    function next() {{ if(nextOff) search(nextOff); }}
    function prev() {{ search(Math.max(0, curOff-20)); }}
    </script>
    </body></html>
    """
    return web.Response(text=html, content_type='text/html')
