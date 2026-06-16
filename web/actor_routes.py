import re
import time
import asyncio
import logging
import base64
import aiohttp
from aiohttp import web
from web.web_assets import build_page, get_auth
from database.ia_filterdb import primary, cloud, archive, COLLECTIONS
from database.users_chats_db import db as user_db

logger = logging.getLogger(__name__)
actor_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 📦 ACTOR DATABASE HELPER — users_chats_db के अंदर
#     actor_profiles collection इस्तेमाल करें
# ─────────────────────────────────────────────────────────
def _actor_col():
    """actor_profiles MongoDB collection का handle"""
    return user_db.db["actor_profiles"]


# ─────────────────────────────────────────────────────────
# 🎨 ACTOR PAGE CSS
# ─────────────────────────────────────────────────────────
_ACTOR_CSS = """<style>
/* ── List page ── */
.actor-hero{padding:32px 0 16px;text-align:center}
.actor-hero h1{font-size:28px;font-weight:900;margin-bottom:6px}
.actor-hero p{color:var(--muted);font-size:14px}
.actor-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:18px;margin-bottom:40px}
@media(max-width:600px){.actor-grid{grid-template-columns:repeat(2,1fr);gap:12px}}

.actor-card{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;cursor:pointer;transition:transform .2s,box-shadow .2s,border-color .2s;text-decoration:none;display:block}
.actor-card:hover{transform:translateY(-4px);box-shadow:0 14px 36px rgba(0,0,0,.6);border-color:rgba(229,9,20,.4)}
.actor-card-img{width:100%;aspect-ratio:3/4;object-fit:cover;display:block;background:var(--bg3)}
.actor-card-img.placeholder{display:flex;align-items:center;justify-content:center;font-size:48px;color:var(--muted)}
.actor-card-body{padding:12px 12px 14px}
.actor-card-name{font-size:14px;font-weight:800;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.actor-card-meta{font-size:11px;color:var(--muted)}
.add-actor-btn{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:#fff;border:none;border-radius:10px;padding:11px 22px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;transition:background .15s,transform .15s}
.add-actor-btn:hover{background:var(--accent-hover);transform:scale(1.03)}

/* ── Profile page ── */
.ap-hero{position:relative;width:100%;background:var(--bg2);border-bottom:1px solid var(--border);margin-bottom:0}
/* Mobile: Full-width cover image */
@media(max-width:767px){
  .ap-cover{width:100%;aspect-ratio:2/3;object-fit:cover;display:block;background:var(--bg3)}
  .ap-cover-placeholder{width:100%;aspect-ratio:2/3;background:linear-gradient(135deg,var(--bg3),var(--bg4));display:flex;align-items:center;justify-content:center;font-size:80px;color:var(--muted)}
  .ap-info-mobile{padding:20px 16px 0}
  .ap-name-mobile{font-size:26px;font-weight:900;margin-bottom:4px}
  .ap-info-desktop{display:none}
  .ap-pc-layout{display:none}
}
/* Desktop: Side-by-side layout */
@media(min-width:768px){
  .ap-cover,.ap-cover-placeholder,.ap-info-mobile{display:none}
  .ap-info-desktop,.ap-pc-layout{display:flex}
  .ap-pc-layout{gap:36px;padding:36px 0 28px;align-items:flex-start}
  .ap-pc-img{width:220px;flex-shrink:0;border-radius:14px;overflow:hidden;border:2px solid var(--border)}
  .ap-pc-img img{width:100%;aspect-ratio:3/4;object-fit:cover;display:block;background:var(--bg3)}
  .ap-pc-img-placeholder{width:220px;aspect-ratio:3/4;background:linear-gradient(135deg,var(--bg3),var(--bg4));display:flex;align-items:center;justify-content:center;font-size:64px;color:var(--muted);border-radius:14px;flex-shrink:0}
  .ap-pc-info{flex:1;min-width:0}
  .ap-pc-name{font-size:32px;font-weight:900;margin-bottom:8px}
}

.ap-badge-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.ap-badge{font-size:11px;font-weight:700;padding:4px 12px;border-radius:99px;border:1px solid var(--border);background:var(--bg3);color:var(--muted)}
.ap-bio{font-size:14px;color:var(--muted);line-height:1.7;margin-bottom:18px}
.ap-stat-row{display:flex;gap:24px;flex-wrap:wrap;margin-bottom:18px}
.ap-stat{text-align:center}
.ap-stat-val{font-size:22px;font-weight:900;color:var(--text)}
.ap-stat-lbl{font-size:11px;color:var(--muted);margin-top:2px}

/* ── Tabs ── */
.ap-tabs{display:flex;gap:4px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:4px;margin:24px 0 20px}
.ap-tab{flex:1;padding:9px 0;border-radius:7px;border:none;cursor:pointer;font-size:13px;font-weight:700;font-family:inherit;background:transparent;color:var(--muted);transition:all .15s}
.ap-tab.active{background:var(--bg4);color:var(--text)}
.ap-panel{display:none}.ap-panel.active{display:block}

/* ── Files list ── */
.ap-file-list{display:flex;flex-direction:column;gap:10px;margin-bottom:30px}
.ap-file-card{display:flex;align-items:center;gap:14px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;text-decoration:none;color:var(--text);transition:background .15s,border-color .15s}
.ap-file-card:hover{background:var(--bg3);border-color:rgba(229,9,20,.35)}
.ap-file-thumb{width:64px;height:42px;border-radius:6px;object-fit:cover;background:var(--bg3);flex-shrink:0}
.ap-file-name{font-size:13px;font-weight:700;margin-bottom:3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.ap-file-meta{font-size:11px;color:var(--muted)}
.ap-file-badge{font-size:10px;font-weight:800;padding:2px 7px;border-radius:4px;border:1px solid}
.ap-file-badge.primary{color:var(--accent);border-color:var(--accent)}
.ap-file-badge.cloud{color:#3399ff;border-color:#3399ff}
.ap-file-badge.archive{color:var(--muted);border-color:var(--muted)}
.ap-file-actions{margin-left:auto;display:flex;gap:8px;flex-shrink:0}
.ap-file-btn{font-size:12px;font-weight:700;padding:6px 14px;border-radius:6px;border:none;cursor:pointer;font-family:inherit;transition:background .15s}
.ap-file-btn.watch{background:var(--accent);color:#fff}
.ap-file-btn.watch:hover{background:var(--accent-hover)}
.ap-file-btn.dl{background:var(--bg4);color:var(--text)}
.ap-file-btn.dl:hover{background:var(--bg3)}

/* ── Gallery ── */
.ap-gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:30px}
@media(max-width:480px){.ap-gallery{grid-template-columns:repeat(2,1fr)}}
.ap-gal-img{width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:10px;display:block;background:var(--bg3);cursor:pointer;transition:transform .2s,opacity .2s}
.ap-gal-img:hover{transform:scale(1.03);opacity:.9}
.ap-gal-add{width:100%;aspect-ratio:3/4;border:2px dashed var(--border);border-radius:10px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:var(--muted);font-size:12px;font-weight:700;cursor:pointer;transition:border-color .15s,color .15s;background:transparent}
.ap-gal-add:hover{border-color:var(--accent);color:var(--accent)}

/* ── Lightbox ── */
.lb-overlay{position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:500;display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:opacity .2s}
.lb-overlay.open{opacity:1;pointer-events:all}
.lb-img{max-width:92vw;max-height:88vh;border-radius:10px;object-fit:contain;display:block}
.lb-close{position:absolute;top:18px;right:22px;background:none;border:none;color:#fff;font-size:32px;cursor:pointer;z-index:10;line-height:1}
.lb-del{position:absolute;bottom:22px;right:22px;background:var(--accent);color:#fff;border:none;border-radius:8px;padding:8px 18px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}

/* ── Empty state ── */
.ap-empty{text-align:center;padding:48px 20px;color:var(--muted)}
.ap-empty-icon{font-size:40px;margin-bottom:12px}

/* ── Admin controls ── */
.ap-admin-bar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.ap-edit-btn{display:inline-flex;align-items:center;gap:6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;text-decoration:none;transition:background .15s,border-color .15s}
.ap-edit-btn:hover{background:var(--bg4);border-color:var(--accent)}
.ap-del-btn{background:transparent;border:1px solid #e50914;color:#e50914;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:background .15s}
.ap-del-btn:hover{background:#e50914;color:#fff}

/* ── Modal (Create / Edit) ── */
.am-overlay{position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:300;display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:.2s;overflow-y:auto;padding:20px 10px}
.am-overlay.open{opacity:1;pointer-events:all}
.am-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:28px;width:100%;max-width:520px;box-shadow:0 10px 40px rgba(0,0,0,.6);position:relative;margin:auto}
.am-close{position:absolute;top:16px;right:18px;background:none;border:none;color:var(--muted);font-size:24px;cursor:pointer}
.am-title{font-size:18px;font-weight:800;margin-bottom:22px}
.am-label{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}
.am-input{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:11px 14px;color:var(--text);font-size:14px;font-family:inherit;outline:none;box-sizing:border-box;margin-bottom:14px;transition:border-color .15s}
.am-input:focus{border-color:var(--accent)}
.am-input::placeholder{color:var(--muted)}
.am-textarea{resize:vertical;min-height:90px}
.am-photo-preview{width:100%;aspect-ratio:3/4;max-height:220px;object-fit:cover;border-radius:10px;display:none;margin-bottom:10px;background:var(--bg3)}
.am-photo-placeholder{width:100%;height:120px;border:2px dashed var(--border);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:13px;cursor:pointer;margin-bottom:10px;transition:border-color .15s}
.am-photo-placeholder:hover{border-color:var(--accent)}
.am-save-btn{width:100%;background:var(--accent);color:#fff;border:none;border-radius:9px;padding:14px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;transition:background .15s,transform .15s;margin-top:4px}
.am-save-btn:hover{background:var(--accent-hover);transform:scale(1.01)}
.am-save-btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
.am-spinner{display:none;width:18px;height:18px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;margin:0 auto}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── No results ── */
.ap-no-files{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:30px;text-align:center;color:var(--muted);font-size:14px}
</style>"""


# ─────────────────────────────────────────────────────────
# 📄 ACTOR LIST PAGE  — /actors
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actors')
async def actors_list(req):
    role, tg_id = await get_auth(req)
    if not role:
        return web.HTTPFound('/login')

    col = _actor_col()
    actors = await col.find({}, {"_id": 1, "name": 1, "profession": 1, "photo_url": 1}).sort("name", 1).to_list(length=500)

    cards_html = ""
    for a in actors:
        actor_id = str(a['_id'])
        name = a.get('name', 'Unknown')
        prof = a.get('profession', '')
        photo = a.get('photo_url', '')
        if photo:
            img_html = f'<img class="actor-card-img" src="{photo}" alt="{name}" loading="lazy" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">'
            ph_html = f'<div class="actor-card-img placeholder" style="display:none">🎬</div>'
        else:
            img_html = ''
            ph_html = '<div class="actor-card-img placeholder">🎬</div>'

        cards_html += f'''
        <a class="actor-card" href="/actors/{actor_id}">
          {img_html}{ph_html}
          <div class="actor-card-body">
            <div class="actor-card-name">{name}</div>
            <div class="actor-card-meta">{prof}</div>
          </div>
        </a>'''

    admin_btn = ''
    if role == 'admin':
        admin_btn = '<button class="add-actor-btn" onclick="openCreateModal()">＋ Add Actor</button>'

    empty = '<div class="ap-empty"><div class="ap-empty-icon">🎭</div><p>No actor profiles yet.</p></div>' if not actors else ''

    body = f'''{_ACTOR_CSS}
<div class="main" style="padding-top:32px;">
  <div class="actor-hero">
    <h1>🎬 Actor Profiles</h1>
    <p style="margin-bottom:20px;">Explore profiles and their files</p>
    {admin_btn}
  </div>
  <div class="actor-grid">{cards_html}</div>
  {empty}
</div>
{_create_modal_html()}
{_actor_list_js()}'''

    return build_page("Actors - Fast Finder", body, "", "actors", role)


# ─────────────────────────────────────────────────────────
# 🎭 SINGLE ACTOR PROFILE PAGE  — /actors/<id>
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actors/{actor_id}')
async def actor_profile(req):
    role, tg_id = await get_auth(req)
    if not role:
        return web.HTTPFound('/login')

    from bson import ObjectId
    actor_id = req.match_info['actor_id']
    col = _actor_col()

    try:
        actor = await col.find_one({"_id": ObjectId(actor_id)})
    except Exception:
        raise web.HTTPNotFound()

    if not actor:
        raise web.HTTPNotFound()

    name       = actor.get('name', 'Unknown')
    profession = actor.get('profession', '')
    nationality= actor.get('nationality', '')
    birth_year = actor.get('birth_year', '')
    bio        = actor.get('bio', '')
    photo_url  = actor.get('photo_url', '')
    gallery    = actor.get('gallery', [])       # list of URLs
    keywords   = actor.get('keywords', [])      # list of search keywords

    # ── Search files matching actor keywords ──────────────────
    matched_files = []
    if keywords:
        import re as _re
        for kw in keywords[:5]:
            rgx = _re.compile(_re.escape(kw), _re.IGNORECASE)
            for src_name, src_col in COLLECTIONS.items():
                docs = await src_col.find(
                    {"file_name": rgx},
                    {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "thumb_url": 1}
                ).limit(50).to_list(length=50)
                for d in docs:
                    d['source'] = src_name
                    matched_files.append(d)

        # Deduplicate by _id
        seen = set()
        unique_files = []
        for f in matched_files:
            if f['_id'] not in seen:
                seen.add(f['_id'])
                unique_files.append(f)
        matched_files = unique_files[:100]

    # ── Build HTML pieces ──────────────────────────────────────
    # Photo
    if photo_url:
        cover_img_html = f'<img class="ap-cover" src="{photo_url}" alt="{name}">'
        pc_img_html    = f'<div class="ap-pc-img"><img src="{photo_url}" alt="{name}"></div>'
        ph_img_html    = ''
    else:
        cover_img_html = f'<div class="ap-cover-placeholder">🎬</div>'
        pc_img_html    = f'<div class="ap-pc-img-placeholder">🎬</div>'
        ph_img_html    = ''

    # Badges
    badges = ''
    if profession:  badges += f'<span class="ap-badge">🎭 {profession}</span>'
    if nationality: badges += f'<span class="ap-badge">🌏 {nationality}</span>'
    if birth_year:  badges += f'<span class="ap-badge">🎂 Born {birth_year}</span>'
    badges += f'<span class="ap-badge">📁 {len(matched_files)} Files</span>'
    badges += f'<span class="ap-badge">🖼️ {len(gallery)} Photos</span>'

    # Bio
    bio_html = f'<p class="ap-bio">{bio}</p>' if bio else ''

    # Keywords display
    kw_html = ''
    if keywords:
        kw_tags = ' '.join(f'<span class="ap-badge" style="background:rgba(229,9,20,.08);color:var(--accent);border-color:rgba(229,9,20,.3);">{k}</span>' for k in keywords)
        kw_html = f'<div style="margin-bottom:16px"><div class="am-label" style="margin-bottom:8px;">Search Keywords</div><div class="ap-badge-row">{kw_tags}</div></div>'

    # Files tab
    files_html = _build_files_html(matched_files) if matched_files else '<div class="ap-no-files">🎬 No files found for this actor\'s keywords.</div>'

    # Gallery tab
    gallery_html = _build_gallery_html(gallery, role == 'admin', actor_id)

    # Admin controls
    admin_bar = ''
    if role == 'admin':
        admin_bar = f'''
        <div class="ap-admin-bar">
          <button class="ap-edit-btn" onclick="openEditModal()">✏️ Edit Profile</button>
          <button class="ap-edit-btn" onclick="openGalleryUpload()">🖼️ Add Gallery Photo</button>
          <button class="ap-del-btn" onclick="deleteActor('{actor_id}')">🗑 Delete Actor</button>
        </div>'''

    body = f'''{_ACTOR_CSS}
<div class="main" style="padding-top:0; max-width:960px;">
  <!-- Mobile: full-width cover then info -->
  {cover_img_html}
  <div class="ap-info-mobile">
    <div class="ap-name-mobile">{name}</div>
    <div class="ap-badge-row" style="margin-top:10px">{badges}</div>
    {bio_html}
    {kw_html}
    {admin_bar}
  </div>

  <!-- Desktop: side-by-side -->
  <div class="ap-pc-layout">
    {pc_img_html}
    <div class="ap-pc-info">
      <div class="ap-pc-name">{name}</div>
      <div class="ap-badge-row">{badges}</div>
      {bio_html}
      {kw_html}
      {admin_bar}
    </div>
  </div>

  <!-- Tabs -->
  <div class="ap-tabs">
    <button class="ap-tab active" data-panel="files">📁 Files ({len(matched_files)})</button>
    <button class="ap-tab" data-panel="gallery">🖼️ Gallery ({len(gallery)})</button>
  </div>
  <div class="ap-panel active" id="panel-files">{files_html}</div>
  <div class="ap-panel" id="panel-gallery">{gallery_html}</div>
</div>

<!-- Lightbox -->
<div class="lb-overlay" id="lbOverlay" onclick="if(event.target===this)closeLb()">
  <button class="lb-close" onclick="closeLb()">&#10005;</button>
  <img class="lb-img" id="lbImg" src="" alt="">
  <button class="lb-del" id="lbDel" onclick="deleteGalleryPhoto()" style="display:none">🗑 Delete</button>
</div>

<!-- Gallery upload input (hidden) -->
<input type="file" id="galleryFileInput" accept="image/*" style="display:none" onchange="submitGalleryPhoto(this)">

{_edit_modal_html(actor)}
{_actor_profile_js(actor_id, role == 'admin')}'''

    return build_page(f"{name} - Actors", body, "", "actors", role)


# ─────────────────────────────────────────────────────────
# 🔧 HTML BUILDER HELPERS
# ─────────────────────────────────────────────────────────
def _build_files_html(files):
    if not files:
        return '<div class="ap-no-files">No matching files found.</div>'

    items = ''
    for f in files:
        fid       = f.get('file_ref') or f.get('_id')
        db_id     = f.get('_id')
        fname     = f.get('file_name', 'Unknown File')
        fsize     = _fmt_size(f.get('file_size', 0))
        ftype     = f.get('file_type', 'doc').upper()
        src       = f.get('source', 'primary')
        raw_thumb = f.get('thumb_url', '')
        v_salt    = raw_thumb[-8:] if (raw_thumb and raw_thumb.startswith("TG_ID:")) else "0"
        thumb_url = f'/api/thumb?file_id={db_id}&col={src}&v={v_salt}'

        items += f'''
        <div class="ap-file-card">
          <img class="ap-file-thumb" src="{thumb_url}" alt="" onerror="this.src=''">
          <div style="flex:1;min-width:0;">
            <div class="ap-file-name">{fname}</div>
            <div class="ap-file-meta">{ftype} · {fsize} &nbsp; <span class="ap-file-badge {src}">{src.upper()}</span></div>
          </div>
          <div class="ap-file-actions">
            <button class="ap-file-btn watch" onclick="window.open('/setup_stream?file_id={fid}&mode=watch','_blank')">▶ Watch</button>
            <button class="ap-file-btn dl" onclick="window.open('/setup_stream?file_id={fid}&mode=download','_blank')">↓</button>
          </div>
        </div>'''

    return f'<div class="ap-file-list">{items}</div>'


def _build_gallery_html(gallery, is_admin, actor_id):
    items = ''
    for idx, url in enumerate(gallery):
        del_attr = f'data-idx="{idx}" data-url="{url}"' if is_admin else ''
        items += f'<img class="ap-gal-img" src="{url}" alt="Gallery {idx+1}" loading="lazy" onclick="openLb(\'{url}\',{idx})" {del_attr}>'

    if is_admin:
        items += '<div class="ap-gal-add" onclick="openGalleryUpload()"><span style="font-size:24px">➕</span><span>Add Photo</span></div>'

    if not gallery and not is_admin:
        return '<div class="ap-empty"><div class="ap-empty-icon">🖼️</div><p>No gallery photos yet.</p></div>'

    return f'<div class="ap-gallery">{items}</div>'


def _fmt_size(size_bytes):
    try:
        size_bytes = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    except Exception:
        return "—"


def _create_modal_html():
    return '''
<div class="am-overlay" id="createModal" onclick="if(event.target===this)closeCreateModal()">
  <div class="am-card">
    <button class="am-close" onclick="closeCreateModal()">&#10005;</button>
    <div class="am-title">🎭 Add New Actor</div>
    <div class="am-label">Profile Photo (Upload Image)</div>
    <div id="photoPlaceholder" class="am-photo-placeholder" onclick="document.getElementById('photoFileInput').click()">
      📷 Click to select profile photo
    </div>
    <img id="photoPreview" class="am-photo-preview" src="" alt="">
    <input type="file" id="photoFileInput" accept="image/*" style="display:none" onchange="previewPhoto(this)">
    <div class="am-label">Actor Name *</div>
    <input class="am-input" id="newName" placeholder="e.g. Shah Rukh Khan" type="text">
    <div class="am-label">Profession</div>
    <input class="am-input" id="newProf" placeholder="e.g. Actor, Director" type="text">
    <div class="am-label">Nationality</div>
    <input class="am-input" id="newNat" placeholder="e.g. Indian" type="text">
    <div class="am-label">Birth Year</div>
    <input class="am-input" id="newBirth" placeholder="e.g. 1965" type="number">
    <div class="am-label">Bio (Short)</div>
    <textarea class="am-input am-textarea" id="newBio" placeholder="Short biography..."></textarea>
    <div class="am-label">Search Keywords (comma separated)</div>
    <input class="am-input" id="newKw" placeholder="e.g. Shah Rukh, SRK, Shahrukh">
    <div style="font-size:11px;color:var(--muted);margin-top:-10px;margin-bottom:14px;">Files whose names contain these keywords will appear in this actor\'s profile.</div>
    <button class="am-save-btn" id="createSaveBtn" onclick="submitCreateActor()">Create Actor Profile</button>
    <div class="am-spinner" id="createSpinner"></div>
  </div>
</div>'''


def _edit_modal_html(actor):
    aid  = str(actor['_id'])
    name = actor.get('name', '')
    prof = actor.get('profession', '')
    nat  = actor.get('nationality', '')
    by   = actor.get('birth_year', '')
    bio  = actor.get('bio', '').replace("'", "&#39;")
    kw   = ', '.join(actor.get('keywords', []))
    photo= actor.get('photo_url', '')
    prev = f'<img id="editPhotoPreview" class="am-photo-preview" src="{photo}" alt="" style="display:{"block" if photo else "none"}">'
    ph_d = f'style="display:{"none" if photo else "flex"}"'

    return f'''
<div class="am-overlay" id="editModal" onclick="if(event.target===this)closeEditModal()">
  <div class="am-card">
    <button class="am-close" onclick="closeEditModal()">&#10005;</button>
    <div class="am-title">✏️ Edit Actor Profile</div>
    <div class="am-label">Profile Photo</div>
    <div id="editPhotoPlaceholder" class="am-photo-placeholder" onclick="document.getElementById('editPhotoFile').click()" {ph_d}>
      📷 Click to change photo
    </div>
    {prev}
    <input type="file" id="editPhotoFile" accept="image/*" style="display:none" onchange="previewEditPhoto(this)">
    <div class="am-label">Actor Name *</div>
    <input class="am-input" id="editName" value="{name}" type="text">
    <div class="am-label">Profession</div>
    <input class="am-input" id="editProf" value="{prof}" type="text">
    <div class="am-label">Nationality</div>
    <input class="am-input" id="editNat" value="{nat}" type="text">
    <div class="am-label">Birth Year</div>
    <input class="am-input" id="editBirth" value="{by}" type="number">
    <div class="am-label">Bio</div>
    <textarea class="am-input am-textarea" id="editBio">{bio}</textarea>
    <div class="am-label">Search Keywords (comma separated)</div>
    <input class="am-input" id="editKw" value="{kw}">
    <button class="am-save-btn" id="editSaveBtn" onclick="submitEditActor('{aid}')">Save Changes</button>
    <div class="am-spinner" id="editSpinner"></div>
  </div>
</div>'''


def _actor_list_js():
    return '''<script>
function openCreateModal(){document.getElementById('createModal').classList.add('open');}
function closeCreateModal(){document.getElementById('createModal').classList.remove('open');resetCreateForm();}
function resetCreateForm(){
  document.getElementById('newName').value='';document.getElementById('newProf').value='';
  document.getElementById('newNat').value='';document.getElementById('newBirth').value='';
  document.getElementById('newBio').value='';document.getElementById('newKw').value='';
  document.getElementById('photoPreview').style.display='none';
  document.getElementById('photoPlaceholder').style.display='flex';
  document.getElementById('photoFileInput').value='';
}
function previewPhoto(input){
  if(!input.files||!input.files[0])return;
  var url=URL.createObjectURL(input.files[0]);
  document.getElementById('photoPreview').src=url;
  document.getElementById('photoPreview').style.display='block';
  document.getElementById('photoPlaceholder').style.display='none';
}
async function submitCreateActor(){
  var name=document.getElementById('newName').value.trim();
  if(!name){alert('Actor name is required!');return;}
  var btn=document.getElementById('createSaveBtn');
  var spin=document.getElementById('createSpinner');
  btn.disabled=true;btn.style.display='none';spin.style.display='block';
  var fd=new FormData();
  fd.append('name',name);
  fd.append('profession',document.getElementById('newProf').value.trim());
  fd.append('nationality',document.getElementById('newNat').value.trim());
  fd.append('birth_year',document.getElementById('newBirth').value.trim());
  fd.append('bio',document.getElementById('newBio').value.trim());
  fd.append('keywords',document.getElementById('newKw').value.trim());
  var file=document.getElementById('photoFileInput').files[0];
  if(file) fd.append('photo',file);
  try{
    var res=await fetch('/api/actors/create',{method:'POST',body:fd});
    var data=await res.json();
    if(data.ok){window.location.href='/actors/'+data.actor_id;}
    else{alert(data.error||'Error creating actor.');}
  }catch(e){alert('Network error.');}
  btn.disabled=false;btn.style.display='block';spin.style.display='none';
}
</script>'''


def _actor_profile_js(actor_id, is_admin):
    admin_js = ''
    if is_admin:
        admin_js = f'''
function openGalleryUpload(){{document.getElementById('galleryFileInput').click();}}
async function submitGalleryPhoto(input){{
  if(!input.files||!input.files[0])return;
  var fd=new FormData();fd.append('photo',input.files[0]);
  var res=await fetch('/api/actors/{actor_id}/gallery/add',{{method:'POST',body:fd}});
  var data=await res.json();
  if(data.ok){{location.reload();}}else{{alert(data.error||'Upload failed.');}}
}}
async function deleteGalleryPhoto(){{
  if(!currentLbIdx&&currentLbIdx!==0)return;
  if(!confirm('Delete this photo from gallery?'))return;
  var res=await fetch('/api/actors/{actor_id}/gallery/delete',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{idx:currentLbIdx}})}});
  var data=await res.json();
  if(data.ok){{closeLb();location.reload();}}else{{alert(data.error||'Delete failed.');}}
}}
async function deleteActor(id){{
  if(!confirm('Delete this actor profile permanently? This cannot be undone.'))return;
  var res=await fetch('/api/actors/'+id+'/delete',{{method:'POST'}});
  var data=await res.json();
  if(data.ok){{window.location.href='/actors';}}else{{alert(data.error||'Delete failed.');}}
}}
function openEditModal(){{document.getElementById('editModal').classList.add('open');}}
function closeEditModal(){{document.getElementById('editModal').classList.remove('open');}}
function previewEditPhoto(input){{
  if(!input.files||!input.files[0])return;
  var url=URL.createObjectURL(input.files[0]);
  document.getElementById('editPhotoPreview').src=url;
  document.getElementById('editPhotoPreview').style.display='block';
  document.getElementById('editPhotoPlaceholder').style.display='none';
}}
async function submitEditActor(id){{
  var name=document.getElementById('editName').value.trim();
  if(!name){{alert('Name required!');return;}}
  var btn=document.getElementById('editSaveBtn');
  var spin=document.getElementById('editSpinner');
  btn.disabled=true;btn.style.display='none';spin.style.display='block';
  var fd=new FormData();
  fd.append('name',name);
  fd.append('profession',document.getElementById('editProf').value.trim());
  fd.append('nationality',document.getElementById('editNat').value.trim());
  fd.append('birth_year',document.getElementById('editBirth').value.trim());
  fd.append('bio',document.getElementById('editBio').value.trim());
  fd.append('keywords',document.getElementById('editKw').value.trim());
  var file=document.getElementById('editPhotoFile').files[0];
  if(file) fd.append('photo',file);
  try{{
    var res=await fetch('/api/actors/'+id+'/update',{{method:'POST',body:fd}});
    var data=await res.json();
    if(data.ok){{location.reload();}}else{{alert(data.error||'Update failed.');}}
  }}catch(e){{alert('Network error.');}}
  btn.disabled=false;btn.style.display='block';spin.style.display='none';
}}'''

    lb_del_display = 'block' if is_admin else 'none'
    return f'''<script>
// ── Tabs ──
document.querySelectorAll('.ap-tab').forEach(function(btn){{
  btn.addEventListener('click',function(){{
    document.querySelectorAll('.ap-tab').forEach(function(b){{b.classList.remove('active')}});
    document.querySelectorAll('.ap-panel').forEach(function(p){{p.classList.remove('active')}});
    btn.classList.add('active');
    document.getElementById('panel-'+btn.dataset.panel).classList.add('active');
  }});
}});
// ── Lightbox ──
var currentLbIdx=null;
function openLb(url,idx){{
  document.getElementById('lbImg').src=url;
  currentLbIdx=idx;
  document.getElementById('lbOverlay').classList.add('open');
  var delBtn=document.getElementById('lbDel');
  if(delBtn) delBtn.style.display='{lb_del_display}';
}}
function closeLb(){{document.getElementById('lbOverlay').classList.remove('open');currentLbIdx=null;}}
{admin_js}
</script>'''


# ─────────────────────────────────────────────────────────
# 🌐 API ENDPOINTS — ADMIN ONLY
# ─────────────────────────────────────────────────────────

async def _upload_photo_to_telegram(photo_bytes, filename="actor_photo.jpg"):
    """
    Photo को Telegram के BIN_CHANNEL में भेजकर उसका file_url (direct link) return करें।
    अगर Telegram direct link न मिले तो base64 data-URL fallback इस्तेमाल करें।
    """
    try:
        from info import BIN_CHANNEL
        from utils import temp
        import io

        # Telegram को file send करो और उसका URL निकालो
        msg = await temp.BOT.send_photo(
            chat_id=BIN_CHANNEL,
            photo=photo_bytes,
            caption=f"Actor Photo: {filename}"
        )
        if msg and msg.photo:
            # सबसे बड़ी photo size लो
            largest = msg.photo[-1] if isinstance(msg.photo, list) else msg.photo
            file_obj = await temp.BOT.get_file(largest.file_id)
            file_url = f"https://api.telegram.org/file/bot{__import__('info').BOT_TOKEN}/{file_obj.file_path}"
            return file_url
    except Exception as e:
        logger.warning(f"Telegram photo upload failed: {e}")

    # Fallback: base64 data URL (works but heavy, use for small images only)
    try:
        b64 = base64.b64encode(photo_bytes).decode()
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return ""


@actor_routes.post('/api/actors/create')
async def api_actor_create(req):
    role, _ = await get_auth(req)
    if role != 'admin':
        return web.json_response({"ok": False, "error": "Admin only"}, status=403)

    from bson import ObjectId
    data = await req.post()
    name = data.get('name', '').strip()
    if not name:
        return web.json_response({"ok": False, "error": "Name required"})

    keywords_raw = data.get('keywords', '')
    keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()]

    photo_url = ''
    photo_file = data.get('photo')
    if photo_file and hasattr(photo_file, 'file'):
        photo_bytes = photo_file.file.read()
        photo_url = await _upload_photo_to_telegram(photo_bytes, name)

    doc = {
        "name": name,
        "profession": data.get('profession', '').strip(),
        "nationality": data.get('nationality', '').strip(),
        "birth_year": data.get('birth_year', '').strip(),
        "bio": data.get('bio', '').strip(),
        "keywords": keywords,
        "photo_url": photo_url,
        "gallery": [],
        "created_at": time.time(),
    }

    col = _actor_col()
    result = await col.insert_one(doc)
    return web.json_response({"ok": True, "actor_id": str(result.inserted_id)})


@actor_routes.post('/api/actors/{actor_id}/update')
async def api_actor_update(req):
    role, _ = await get_auth(req)
    if role != 'admin':
        return web.json_response({"ok": False, "error": "Admin only"}, status=403)

    from bson import ObjectId
    actor_id = req.match_info['actor_id']
    data = await req.post()
    name = data.get('name', '').strip()
    if not name:
        return web.json_response({"ok": False, "error": "Name required"})

    keywords_raw = data.get('keywords', '')
    keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()]

    update_set = {
        "name": name,
        "profession": data.get('profession', '').strip(),
        "nationality": data.get('nationality', '').strip(),
        "birth_year": data.get('birth_year', '').strip(),
        "bio": data.get('bio', '').strip(),
        "keywords": keywords,
        "updated_at": time.time(),
    }

    photo_file = data.get('photo')
    if photo_file and hasattr(photo_file, 'file'):
        photo_bytes = photo_file.file.read()
        if photo_bytes:
            photo_url = await _upload_photo_to_telegram(photo_bytes, name)
            if photo_url:
                update_set['photo_url'] = photo_url

    col = _actor_col()
    await col.update_one({"_id": ObjectId(actor_id)}, {"$set": update_set})
    return web.json_response({"ok": True})


@actor_routes.post('/api/actors/{actor_id}/delete')
async def api_actor_delete(req):
    role, _ = await get_auth(req)
    if role != 'admin':
        return web.json_response({"ok": False, "error": "Admin only"}, status=403)

    from bson import ObjectId
    actor_id = req.match_info['actor_id']
    col = _actor_col()
    await col.delete_one({"_id": ObjectId(actor_id)})
    return web.json_response({"ok": True})


@actor_routes.post('/api/actors/{actor_id}/gallery/add')
async def api_gallery_add(req):
    role, _ = await get_auth(req)
    if role != 'admin':
        return web.json_response({"ok": False, "error": "Admin only"}, status=403)

    from bson import ObjectId
    actor_id = req.match_info['actor_id']
    data = await req.post()
    photo_file = data.get('photo')

    if not photo_file or not hasattr(photo_file, 'file'):
        return web.json_response({"ok": False, "error": "No photo provided"})

    photo_bytes = photo_file.file.read()
    if not photo_bytes:
        return web.json_response({"ok": False, "error": "Empty file"})

    photo_url = await _upload_photo_to_telegram(photo_bytes, f"gallery_{actor_id}")
    if not photo_url:
        return web.json_response({"ok": False, "error": "Photo upload failed"})

    col = _actor_col()
    await col.update_one(
        {"_id": ObjectId(actor_id)},
        {"$push": {"gallery": photo_url}}
    )
    return web.json_response({"ok": True, "url": photo_url})


@actor_routes.post('/api/actors/{actor_id}/gallery/delete')
async def api_gallery_delete(req):
    role, _ = await get_auth(req)
    if role != 'admin':
        return web.json_response({"ok": False, "error": "Admin only"}, status=403)

    from bson import ObjectId
    actor_id = req.match_info['actor_id']

    try:
        body = await req.json()
        idx = int(body.get('idx', -1))
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid request"})

    col = _actor_col()
    actor = await col.find_one({"_id": ObjectId(actor_id)}, {"gallery": 1})
    if not actor:
        return web.json_response({"ok": False, "error": "Actor not found"})

    gallery = actor.get('gallery', [])
    if idx < 0 or idx >= len(gallery):
        return web.json_response({"ok": False, "error": "Invalid index"})

    gallery.pop(idx)
    await col.update_one({"_id": ObjectId(actor_id)}, {"$set": {"gallery": gallery}})
    return web.json_response({"ok": True})
