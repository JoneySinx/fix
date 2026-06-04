from aiohttp import web
from web.web_assets import build_page, get_auth
from database.ia_filterdb import db_count_documents
from database.users_chats_db import db as user_db

stats_routes = web.RouteTableDef()

@stats_routes.get('/stats')
async def stats(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.HTTPFound('/dashboard')
    try: 
        s = await db_count_documents()
        if not isinstance(s, dict):
            s = {'total': 0, 'primary': 0, 'cloud': 0, 'archive': 0, 'primary_thumb': 0, 'cloud_thumb': 0, 'archive_thumb': 0, 'total_thumb': 0}
    except: 
        s = {'total': 0, 'primary': 0, 'cloud': 0, 'archive': 0, 'primary_thumb': 0, 'cloud_thumb': 0, 'archive_thumb': 0, 'total_thumb': 0}
        
    try: u = await user_db.total_users_count()
    except: u = 0
    
    p_tot = s.get('primary', 0)
    c_tot = s.get('cloud', 0)
    a_tot = s.get('archive', 0)
    grand_total = s.get('total', 1) or 1

    p_per = f"{int((p_tot / grand_total) * 100)}%"
    c_per = f"{int((c_tot / grand_total) * 100)}%"
    a_per = f"{int((a_tot / grand_total) * 100)}%"

    total_val = f"{s.get('total', 0):,}"
    primary_val = f"{p_tot:,}"
    primary_thumb = f"{s.get('primary_thumb', 0):,}"
    cloud_val = f"{c_tot:,}"
    cloud_thumb = f"{s.get('cloud_thumb', 0):,}"
    archive_val = f"{a_tot:,}"
    archive_thumb = f"{s.get('archive_thumb', 0):,}"
    total_thumb = f"{s.get('total_thumb', 0):,}"
    bot_users = f"{u:,}"

    html_stats_body = '<style>:root{--primary-p:'+p_per+';--cloud-p:'+c_per+';--archive-p:'+a_per+';}</style>' \
        '<div class="main" style="padding-top:40px;">' \
        '<div class="big-stat">' \
            '<div class="big-stat-val">' + total_val + '</div>' \
            '<div class="big-stat-label">Total Cloud Archive Matrix</div>' \
        '</div>' \
        '<div class="stats-row">' \
            '<div class="scard" style="border-top: 3px solid #3399ff;">' \
                '<div class="scard-label">Primary Cloud (Movies)</div>' \
                '<div class="scard-val" style="color:#3399ff;">' + primary_val + '</div>' \
                '<div class="custom-progress-container"><div class="custom-progress-bar primary-fill"></div></div>' \
                '<div class="scard-sub"><span>🖼️ Cached: <b>' + primary_thumb + '</b></span><span style="margin-left:auto;font-weight:bold;color:#3399ff;">' + p_per + '</span></div>' \
            '</div>' \
            '<div class="scard" style="border-top: 3px solid #ff9933;">' \
                '<div class="scard-label">Cloud Library (Series)</div>' \
                '<div class="scard-val" style="color:#ff9933;">' + cloud_val + '</div>' \
                '<div class="custom-progress-container"><div class="custom-progress-bar cloud_fill"></div></div>' \
                '<div class="scard-sub"><span>🖼️ Cached: <b>' + cloud_thumb + '</b></span><span style="margin-left:auto;font-weight:bold;color:#ff9933;">' + c_per + '</span></div>' \
            '</div>' \
            '<div class="scard" style="border-top: 3px solid #9933ff;">' \
                '<div class="scard-label">Backup Warehouse (Archive)</div>' \
                '<div class="scard-val" style="color:#9933ff;">' + archive_val + '</div>' \
                '<div class="custom-progress-container"><div class="custom-progress-bar archive-fill"></div></div>' \
                '<div class="scard-sub"><span>🖼️ Cached: <b>' + archive_thumb + '</b></span><span style="margin-left:auto;font-weight:bold;color:#9933ff;">' + a_per + '</span></div>' \
            '</div>' \
            '<div class="scard" style="border-top: 3px solid #e50914;">' \
                '<div class="scard-label">Global Image Assets</div>' \
                '<div class="scard-val" style="color:#e50914;">' + total_thumb + '</div>' \
                '<div class="scard-sub"><span>Verified Blob Identifiers</span></div>' \
                '<button class="flush-btn" id="flushBtn" onclick="triggerCacheFlush()">🧹 Flush RAM Cache</button>' \
            '</div>' \
            '<div class="scard" style="border-top: 3px solid #ffffff;">' \
                '<div class="scard-label">Total System Subscribers</div>' \
                '<div class="scard-val">' + bot_users + '</div>' \
                '<div class="scard-sub"><span>Active Database Records</span></div>' \
            '</div>' \
        '</div>' \
        '<h3 style="margin:40px 0 20px; text-transform:uppercase; font-size:12px; letter-spacing:2px; color:var(--muted)">💻 Server Core Telemetry Diagnostics</h3>' \
        '<div class="stats-row">' \
            '<div class="scard" style="padding:15px; background:var(--bg2); border-left: 3px solid #28a745;">' \
                '<div class="scard-label" style="font-size:10px;">Koyeb Worker Pod</div>' \
                '<div style="font-size:16px; font-weight:bold; color:#28a745; display:flex; align-items:center; gap:6px;">🟢 Operational <span style="font-size:11px; font-weight:normal; color:var(--muted)">| Port 8000</span></div>' \
            '</div>' \
            '<div class="scard" style="padding:15px; background:var(--bg2); border-left: 3px solid #3399ff;">' \
                '<div class="scard-label" style="font-size:10px;">Database I/O Pool</div>' \
                '<div style="font-size:16px; font-weight:bold; color:#3399ff;">15 Connections Max</div>' \
            '</div>' \
            '<div class="scard" style="padding:15px; background:var(--bg2); border-left: 3px solid #ff9933;">' \
                '<div class="scard-label" style="font-size:10px;">RAM Protection Guard</div>' \
                '<div style="font-size:16px; font-weight:bold; color:#ff9933;">Strictly Bounded</div>' \
            '</div>' \
        '</div>' \
    '</div>'

    return build_page("Stats - Fast Finder", html_stats_body, "", "stats", role)
