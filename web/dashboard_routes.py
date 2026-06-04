import gc
from aiohttp import web
from web.web_assets import build_page, get_auth, form_wrapper
from database.users_chats_db import db as user_db
from utils import temp

dashboard_routes = web.RouteTableDef()

@dashboard_routes.get('/dashboard')
async def dash(req):
    role, tg_id = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    if role == 'user':
        mp = await user_db.get_plan(tg_id)
        if not mp.get("premium"): return web.HTTPFound('/premium_expired')

    b = '<div class="search-zone"><div class="search-row"><div class="filter-tabs"><button class="ftab active" data-col="all" onclick="setCol(this)">All</button><button class="ftab" data-col="primary" onclick="setCol(this)">Primary</button><button class="ftab" data-col="cloud" onclick="setCol(this)">Cloud</button><button class="ftab" data-col="archive" onclick="setCol(this)">Archive</button></div><select id="posterMode" onchange="changePosterMode()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:8px;font-weight:700;outline:none;cursor:pointer;"><option value="tg">📸 Original TG Thumb</option><option value="none">⚡ Text Only (Fastest)</option></select><div class="search-wrap"><span class="s-icon">&#9906;</span><input class="search-input" id="q" placeholder="Titles, people, genres"></div><button class="search-btn" onclick="doSearch(0)">Search</button></div></div><div class="main" style="padding-top:20px;"><div class="results-info" id="resInfo"><span class="results-count" id="resCount"></span></div><div id="results" class="res-grid"><div class="empty"><div class="empty-icon">&#8981;</div><p>Find your favorite movies and TV shows.</p></div></div><div class="pagination" id="pageBox"><button class="pg-btn" id="pBtn" onclick="prev()" disabled>Previous</button><span class="pg-info" id="pgInfo">Page 1</span><button class="pg-btn" id="nBtn" onclick="next()">Next</button></div></div><div class="toast" id="toast"></div>'
    return build_page("Home - Fast Finder", b, "", "dash", role)

@dashboard_routes.get('/logout')
async def logout(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and s_user in temp.USER_SESSIONS: 
        del temp.USER_SESSIONS[s_user]
    res = web.HTTPFound('/login')
    res.del_cookie('user_session')
    gc.collect()
    return res

@dashboard_routes.get('/premium_expired')
async def premium_expired(req):
    role, tg_id = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    content = f'<div style="text-align:center;"><div style="font-size:50px; margin-bottom:15px;">⏳</div><p style="color:var(--muted); margin-bottom:30px;">Your access to Fast Finder Web has expired. Please renew your plan via our Telegram Bot.</p><div class="scard red" style="text-align:left; margin-bottom:25px; padding:15px;"><div class="scard-label">How to Renew?</div><div class="scard-sub" style="color:var(--text)">1. Go to Telegram Bot</div><div class="scard-sub" style="color:var(--text)">2. Use command <b>/plan</b></div><div class="scard-sub" style="color:var(--text)">3. Pay & Activate instantly</div></div><a href="https://t.me/{temp.U_NAME}" class="submit-btn" style="text-decoration:none; display:block;">Open Telegram Bot</a><a href="/logout" style="display:block; margin-top:20px; color:var(--muted); text-decoration:none;">Sign Out</a></div>'
    return build_page("Premium Expired", form_wrapper("Premium Expired", content), "login-bg")
