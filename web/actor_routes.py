import io
import os
import re
import asyncio
import logging
from aiohttp import web
from utils import temp, get_size
from info import BIN_CHANNEL, MAX_WEB_RESULTS
from database.ia_filterdb import actors, COLLECTIONS
from database.users_chats_db import db as user_db
from web.web_assets import build_page, get_auth

logger = logging.getLogger(__name__)
actor_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 🎨 ACTOR SECTION RESPONSIVE CSS
# ─────────────────────────────────────────────────────────
ACTOR_CSS = """
<style>
.actor-container { padding: 20px; }
.actor-stats-bar { display: flex; justify-content: space-between; align-items: center; background: var(--card); padding: 16px 20px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px; }
.actor-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 16px; }
.actor-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; cursor: pointer; text-align: center; transition: transform 0.2s; -webkit-tap-highlight-color: transparent; }
.actor-card:hover { transform: translateY(-4px); border-color: var(--accent); }
.actor-card img { width: 100%; height: 145px; object-fit: cover; background: var(--bg3); }
.actor-card-name { padding: 10px; font-weight: 700; font-size: 13.5px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 📱 मोबाइल रिस्पांसिव लेआउट: डिफ़ॉल्ट रूप से फुल फोटो नीचे डिटेल्स */
.actor-profile-container { background: var(--card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 24px; overflow: hidden; }
.actor-hero-box { display: flex; flex-direction: column; }
.actor-full-pic { width: 100%; max-height: 420px; object-fit: cover; border-bottom: 1px solid var(--border); background: var(--bg3); }
.actor-details-content { padding: 20px; }
.actor-name-title { font-size: 26px; font-weight: 800; color: var(--text); margin-bottom: 8px; }
.actor-meta-row { font-size: 14px; color: var(--muted); margin-bottom: 14px; display: flex; gap: 15px; flex-wrap: wrap; }
.actor-bio { font-size: 14.5px; color: var(--text); line-height: 1.6; opacity: 0.95; }

/* 💻 पीसी / डेस्कटॉप लेआउट: आटोमेटिक गोल अवतार और साइड-बाय-साइड डिटेल्स */
@media(min-width: 768px) {
    .actor-hero-box { flex-direction: row; align-items: center; gap: 28px; padding: 24px; }
    .actor-full-pic { width: 140px; height: 140px; border-radius: 50%; border: 3px solid var(--accent); border-bottom: none; box-shadow: 0 4px 15px rgba(229,9,20,0.2); }
    .actor-details-content { padding: 0; flex: 1; text-align: left; }
}

/* 🖼️ मल्टी-इमेज गैलरी ग्रिड सिस्टम */
.actor-gallery-section { padding: 0 20px 20px; border-top: 1px solid var(--border); }
.gallery-title { font-size: 15px; font-weight: 700; margin: 16px 0 12px; color: var(--text); display: flex; align-items: center; gap: 6px; }
.gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
@media(max-width: 600px) { .gallery-grid { grid-template-columns: repeat(3, 1fr); } }
.gallery-item { position: relative; padding-top: 100%; background: var(--bg3); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
.gallery-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; cursor: pointer; transition: transform 0.25s ease; }
.gallery-img:hover { transform: scale(1.06); }
</style>
"""

# ─────────────────────────────────────────────────────────
# 🎬 ACTOR FRONTEND JS ENGINE
# ─────────────────────────────────────────────────────────
ACTOR_JS = """
async function loadActorSection() {
    var resDiv = document.getElementById('results');
    resDiv.innerHTML = '<div class="spin-wrap"><div class="spinner"></div></div>';
    resDiv.className = '';
    document.getElementById('pageBox').style.display = 'none';
    document.getElementById('resInfo').style.display = 'none';
    
    try {
        var r = await fetch('/api/actors_list');
        var d = await r.json();
        if(d.error) { showToast(d.error, 'error'); return; }
        
        var adminBtn = d.is_admin ? `<button class="search-btn" style="background:#4f46e5; padding:0 16px; height:36px; border-radius:10px; font-size:13px;" onclick="document.getElementById('actorModal').style.display='flex'">➕ Add Actor</button>` : '';
        
        var html = `<div class="actor-container">
            <div class="actor-stats-bar">
                <div><b style="font-size:15px; color:var(--text);">🎭 Actors Directory</b><br><span style="color:var(--muted); font-size:12px; font-weight:500;">Total Added: ${d.count}</span></div>
                ${adminBtn}
            </div>
            <div class="actor-grid">`;
            
        if(d.actors.length === 0) {
            html += '<p style="grid-column:1/-1; text-align:center; color:var(--muted); padding:40px; font-size:14px;">No actors found in directory.</p>';
        } else {
            d.actors.forEach(function(a) {
                html += `<div class="actor-card" onclick="viewActorProfile('${a.id}')">
                    <img src="${a.pic}" loading="lazy" onerror="this.src='https://placehold.co/150x150/1c1c24/fff?text=No+Photo'">
                    <div class="actor-card-name">${a.name}</div>
                </div>`;
            });
        }
        html += `</div></div>`;
        resDiv.innerHTML = html;
    } catch(e) { showToast('Error executing actors pipeline', 'error'); }
}

async function saveActorProfile() {
    var name = document.getElementById('actorName').value.trim();
    var bio = document.getElementById('actorBio').value.trim();
    var dob = document.getElementById('actorDob').value.trim();
    var country = document.getElementById('actorCountry').value.trim();
    var fileInput = document.getElementById('actorImageFile');
    var galInput = document.getElementById('actorGalleryFiles');
    
    if(!name || !fileInput.files[0]) { showToast('Name and Main Profile Picture are required!', 'error'); return; }
    
    var btn = document.getElementById('actorSaveBtn');
    btn.disabled = true; btn.innerText = 'Uploading assets...';
    
    var formData = new FormData();
    formData.append('name', name);
    formData.append('bio', bio);
    formData.append('dob', dob);
    formData.append('country', country);
    formData.append('image', fileInput.files[0]);
    
    for (var i = 0; i < galInput.files.length; i++) {
        formData.append('gallery_images', galInput.files[i]);
    }
    
    try {
        var r = await fetch('/api/create_actor', { method: 'POST', body: formData });
        var res = await r.json();
        if(res.success) {
            showToast('✨ Actor Profile & Portfolio Compiled!');
            document.getElementById('actorModal').style.display = 'none';
            
            // फॉर्म रीसेट
            document.getElementById('actorName').value = '';
            document.getElementById('actorBio').value = '';
            document.getElementById('actorDob').value = '';
            document.getElementById('actorCountry').value = '';
            fileInput.value = ''; galInput.value = '';
            
            loadActorSection();
        } else { showToast(res.error || 'Pipeline error', 'error'); }
    } catch(e) { showToast('Server synchronization failed', 'error'); }
    finally { btn.disabled = false; btn.innerText = 'Save Actor'; }
}

async function viewActorProfile(actorId) {
    var resDiv = document.getElementById('results');
    resDiv.innerHTML = '<div class="spin-wrap"><div class="spinner"></div></div>';
    resDiv.className = '';
    document.getElementById('pageBox').style.display = 'none';
    
    try {
        var r = await fetch('/api/actor/' + actorId);
        var d = await r.json();
        if(d.error) { showToast(d.error, 'error'); return; }
        
        var act = d.actor;
        var headerHtml = `<div class="actor-profile-container">
            <div class="actor-hero-box">
                <img src="${act.profile_pic}" class="actor-full-pic" loading="lazy" onerror="this.src='https://placehold.co/400x400/1c1c24/fff?text=Avatar'">
                <div class="actor-details-content">
                    <div class="actor-name-title">${act.name}</div>
                    <div class="actor-meta-row">
                        <span><b>🎂 Born:</b> ${act.details.dob || 'N/A'}</span>
                        <span><b>📍 Origin:</b> ${act.details.country || 'N/A'}</span>
                    </div>
                    <div class="actor-bio">${act.bio || 'No biography available.'}</div>
                </div>
            </div>`;
            
        if(act.gallery && act.gallery.length > 0) {
            headerHtml += `<div class="actor-gallery-section">
                <div class="gallery-title">📸 Portfolio Gallery</div>
                <div class="gallery-grid">`;
            act.gallery.forEach(function(gImg) {
                headerHtml += `<div class="gallery-item"><img src="${gImg}" class="gallery-img" onclick="window.open(this.src, '_blank')"></div>`;
            });
            headerHtml += `</div></div>`;
        }
        headerHtml += `</div>`;
        
        var videoHtml = `<h3 style="margin:20px 0 14px 4px; font-size:15px; font-weight:700; color:var(--text);">🎬 Videos Featuring ${act.name}</h3><div class="res-grid mode-tg">`;
        
        if(!d.results || d.results.length === 0) {
            videoHtml += '<p class="empty" style="grid-column:1/-1; padding:30px;">No matching video files indexed with this actor\'s name.</p>';
        } else {
            d.results.forEach(function(f) {
                videoHtml += `<div class="file-card">
                    <div class="poster-box">
                        <img src="${f.poster}" class="fc-poster loaded" loading="lazy" onerror="this.src='https://placehold.co/600x338/14141f/fff?text=No+Poster'">
                        <div class="poster-top">
                            <span class="type-chip">${f.type}</span>
                            <span class="size-chip">${f.size}</span>
                        </div>
                    </div>
                    <div class="fc-body">
                        <div class="fc-name" onclick="window.open('${f.watch}','_blank')">${f.name}</div>
                    </div>
                </div>`;
            });
        }
        videoHtml += '</div>';
        resDiv.innerHTML = headerHtml + videoHtml;
    } catch(e) { showToast('Error mapping profile assets', 'error'); }
}
"""

# ─────────────────────────────────────────────────────────
# ⚙️ BACKEND API ROUTE CORES
# ─────────────────────────────────────────────────────────

@actor_routes.get("/api/actor_thumb")
async def api_actor_thumb(req):
    """✅ FIX: Actors collection के लिए dedicated thumbnail endpoint"""
    actor_id = req.query.get("actor_id")
    if not actor_id:
        return web.Response(status=400)
    
    try:
        from utils import temp
        from info import BIN_CHANNEL
        from web.search_api import _get_or_fetch_thumb, thumb_cache
        
        actor_doc = await actors.find_one({"_id": actor_id}, {"thumb_url": 1})
        if not actor_doc:
            return web.Response(status=404)
        
        thumb_url = actor_doc.get("thumb_url", "")
        if not thumb_url or not thumb_url.startswith("TG_ID:"):
            return web.Response(status=404)
        
        tg_file_id = thumb_url.replace("TG_ID:", "")
        cache_key = f"actors:{actor_id}"
        
        # Cache check
        if cache_key in thumb_cache:
            cached = thumb_cache[cache_key]
            if cached != "NO_THUMB":
                from collections import OrderedDict
                thumb_cache.move_to_end(cache_key)
                return web.Response(
                    body=cached,
                    content_type="image/jpeg",
                    headers={"Cache-Control": "max-age=86400", "Content-Disposition": 'inline; filename="actor.jpg"'}
                )
            return web.Response(status=404)
        
        # Telegram से fetch करो
        file_data = await temp.BOT.download_media(tg_file_id, in_memory=True)
        if file_data:
            img_bytes = file_data.getvalue()
            thumb_cache[cache_key] = img_bytes
            return web.Response(
                body=img_bytes,
                content_type="image/jpeg",
                headers={"Cache-Control": "max-age=86400", "Content-Disposition": 'inline; filename="actor.jpg"'}
            )
        return web.Response(status=404)
    except Exception as e:
        logger.error(f"Actor thumb error: {e}")
        return web.Response(status=500)


@actor_routes.get("/api/actors_list")
async def api_actors_list(req):
    role, _ = await get_auth(req)
    if not role: return web.json_response({"error": "Unauthorized Access Engine!"}, status=403)
    
    count = await actors.count_documents({})
    # ✅ FIX: cursor chaining — reassign
    cursor = actors.find({}, {"name": 1, "_id": 1}).sort("name", 1)
    actor_docs = await cursor.to_list(length=300)
    
    # ✅ FIX: actor thumbnail के लिए dedicated endpoint use करो
    list_data = [{"id": a["_id"], "name": a["name"], "pic": f"/api/actor_thumb?actor_id={a['_id']}"} for a in actor_docs]
    return web.json_response({"count": count, "actors": list_data, "is_admin": role == "admin"})

@actor_routes.post("/api/create_actor")
async def api_create_actor(req):
    role, _ = await get_auth(req)
    if role != "admin": return web.json_response({"error": "Core Admin Authorization Required!"}, status=403)
        
    try:
        reader = await req.multipart()
        name, bio, dob, country = "", "", "", ""
        image_bytes = None
        gallery_files = []
        
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'name': name = (await part.read()).decode().strip()
            elif part.name == 'bio': bio = (await part.read()).decode().strip()
            elif part.name == 'dob': dob = (await part.read()).decode().strip()
            elif part.name == 'country': country = (await part.read()).decode().strip()
            elif part.name == 'image': image_bytes = await part.read()
            elif part.name == 'gallery_images': gallery_files.append(await part.read())

        if not name or not image_bytes:
            return web.json_response({"error": "Missing Required Structure Assets!"}, status=400)

        # 1. Main Pic Node Upload
        with io.BytesIO(image_bytes) as buf:
            buf.name = "avatar.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=buf)
        main_tg_id = msg.photo.sizes[-1].file_id if hasattr(msg.photo, "sizes") else msg.photo.file_id
        await user_db.add_to_delete_queue(BIN_CHANNEL, msg.id, 5)

        # 2. Portfolio Gallery Multi-Upload Loop
        gallery_ids = []
        for img_data in gallery_files:
            if not img_data: continue
            with io.BytesIO(img_data) as buf:
                buf.name = "portfolio.jpg"
                g_msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=buf)
                if g_msg and g_msg.photo:
                    g_id = g_msg.photo.sizes[-1].file_id if hasattr(g_msg.photo, "sizes") else g_msg.photo.file_id
                    gallery_ids.append(f"TG_ID:{g_id}")
                    await user_db.add_to_delete_queue(BIN_CHANNEL, g_msg.id, 5)

        actor_id = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip().lower())
        doc = {
            "_id": actor_id,
            "name": name.strip(),
            "bio": bio.strip(),
            "details": {"dob": dob, "country": country},
            "thumb_url": f"TG_ID:{main_tg_id}",
            "gallery": gallery_ids
        }
        await actors.replace_one({"_id": actor_id}, doc, upsert=True)
        return web.json_response({"success": True})
    except Exception as e:
        logger.error(f"❌ Actor creation pipeline crashed: {e}")
        return web.json_response({"error": str(e)}, status=500)

@actor_routes.get("/api/actor/{actor_id}")
async def api_get_actor_node(req):
    role, _ = await get_auth(req)
    if not role: return web.json_response({"error": "Unauthorized Access Denied!"}, status=403)
    
    actor_id = req.match_info.get('actor_id')
    actor = await actors.find_one({"_id": actor_id})
    if not actor: return web.json_response({"error": "Actor Profile Missing from Core!"}, status=404)
    
    # 🔍 रॉकेट स्पीड ऑटो-वीडियो मैपिंग इंजन (Case-Insensitive Regex)
    regex_flt = {"file_name": re.compile(re.escape(actor["name"]), re.IGNORECASE)}
    videos = []
    
    for name, col in COLLECTIONS.items():
        docs = await col.find(regex_flt, {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1}).sort('_id', -1).to_list(length=30)
        for d in docs:
            fid = d.get("file_ref") or d.get("_id")
            videos.append({
                "name": d.get("file_name", "Unknown File"),
                "size": get_size(d.get("file_size", 0)),
                "type": d.get("file_type", "document").upper(),
                "poster": f"/api/thumb?file_id={d.get('_id')}",
                "watch": f"/setup_stream?file_id={fid}&mode=watch"
            })
            
    # ✅ FIX: gallery thumbnails — TG_ID: strip करके actual file_id use करो
    gallery_links = []
    for img in actor.get("gallery", []):
        raw_id = img.replace("TG_ID:", "")
        gallery_links.append(f"/api/thumb?file_id={raw_id}&col=primary")
    
    return web.json_response({
        "actor": {
            "name": actor["name"],
            "bio": actor["bio"],
            "details": actor.get("details", {}),
            # ✅ FIX: dedicated actor_thumb endpoint use करो
            "profile_pic": f"/api/actor_thumb?actor_id={actor_id}",
            "gallery": gallery_links
        },
        "results": videos
    })
