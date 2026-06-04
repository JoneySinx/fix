import gc
from aiohttp import web
from web.web_assets import build_page, get_auth, form_wrapper, MAX_WEB_RESULTS
from database.users_chats_db import db as user_db
from utils import temp

dashboard_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 🎬 CINEMATIC HUD JAVASCRIPT ENGINE (100% Fixed Quote Sync)
# ─────────────────────────────────────────────────────────
JS_ENGINE = """
var curQ='',curOff=0,nextOff='',curCol='all',curPage=1;
var pMode=localStorage.getItem('posterMode')||'tg';
var LIMIT_VAL = __LIMIT_PLACEHOLDER__;

var activeFid = '', activeCol = '', cropperInstance = null;

function setCol(e){
    document.querySelectorAll('.ftab').forEach(t=>t.classList.remove('active'));
    e.classList.add('active');
    curCol=e.dataset.col;
    if(curQ) doSearch(0);
}
function changePosterMode(){
    pMode=document.getElementById('posterMode').value;
    localStorage.setItem('posterMode',pMode);
    if(curQ)doSearch(curOff);
}

function handleThumbError(fileId) {
    var box = document.getElementById('poster-box-' + fileId);
    if (box) {
        box.innerHTML = '<div class="no-thumb-placeholder"><span>🎬</span><span style="font-size:11px;opacity:0.6;">No Thumbnail</span></div>';
    }
}

async function reloadThumb(fileId) {
    var timestamp = new Date().getTime();
    var box = document.getElementById('poster-box-' + fileId);
    if (box) {
        box.innerHTML = '<img src="/api/thumb?file_id=' + fileId + '&retry=true&t=' + timestamp + '" class="fc-poster" onerror="handleThumbError(\''+fileId+'\')">';
    }
}

function toggleAdminOverlay(e, fileId) {
    e.preventDefault();
    e.stopPropagation();
    var overlay = document.getElementById('admin-overlay-' + fileId);
    if (overlay) {
        overlay.classList.toggle('visible');
    }
}

async function doSearch(o){
    var q=document.getElementById('q').value.trim();
    if(!q){showToast('Please enter a movie name','error');return;}
    curQ=q;curOff=o;if(o===0)curPage=1;
    
    var resDiv = document.getElementById('results');
    resDiv.className = 'res-grid mode-' + pMode;
    resDiv.innerHTML = '<div class="empty" style="color:var(--accent); font-weight:700; letter-spacing:1px;">⚡ Searching Secure Database Pipes...</div>';

    try{
        var r=await fetch('/api/search?q=' + encodeURIComponent(q) + '&offset=' + o + '&col=' + curCol + '&mode=' + pMode);
        if(!r.ok){showToast('Error fetching','error');return;}
        var d=await r.json();
        if(d.error){showToast(d.error,'error');return;}
        document.getElementById('resInfo').style.display='flex';
        document.getElementById('resCount').innerHTML='More to explore: <span style="color:var(--accent); font-weight:bold;">' + q + '</span>';
        if(!d.results||!d.results.length){
            resDiv.innerHTML='<div class="empty"><div class="empty-icon">⚠️</div><p style="font-weight:700;">No titles found for "' + q + '"</p></div>';
            document.getElementById('pageBox').style.display='none';return;
        }
        var h='';
        d.results.forEach(f=>{
            var sc=(f.source||'primary').toLowerCase();
            if(!['primary','cloud','archive'].includes(sc))sc='primary';
            
            var adminOverlay='';
            var clickHandlerHtml = '';
            if(d.is_admin){
                // ✅ सुरक्षित स्ट्रिंग एस्केपिंग सिंक
                var escapedName = f.name.replace(/'/g, "\\'");
                adminOverlay='<div class="hud-overlay" id="admin-overlay-' + f.file_id + '">' +
                    '<div style="display:flex;gap:8px;width:100%;max-width:180px;">' +
                        '<button onclick="event.stopPropagation(); editFile(\'' + f.file_id + '\',\'' + f.raw_collection + '\',\'' + escapedName + '\')" class="hud-btn hud-btn-edit">✏️ Edit</button>' +
                        '<button onclick="event.stopPropagation(); deleteFile(\'' + f.file_id + '\',\'' + f.raw_collection + '\')" class="hud-btn hud-btn-del">🗑️ Del</button>' +
                    '</div>' +
                '</div>';
                clickHandlerHtml = 'onclick="toggleAdminOverlay(event, \'' + f.file_id + '\')"';
            } else {
                clickHandlerHtml = 'onclick="window.open(\'' + f.watch + '\', \'_blank\')"';
            }
            
            var imgHtml='';
            if(pMode!=='none'){
                imgHtml='<div class="poster-box" id="poster-box-' + f.file_id + '" ' + clickHandlerHtml + '>' + 
                    adminOverlay + 
                    '<img src="' + f.tg_thumb + '" class="fc-poster" onerror="handleThumbError(\'' + f.file_id + '\')" loading="lazy">' + 
                '</div>';
            }
            
            h+='<div class="file-card">' +
                imgHtml +
                '<a href="' + f.watch + '" target="_blank" class="fc-content-link">' +
                    '<div class="fc-content-zone">' +
                        '<div class="fc-top">' +
                            '<span class="source-badge ' + sc + '">' + sc.toUpperCase() + '</span>' +
                            '<span class="type-tag">' + f.type.toUpperCase() + '</span>' +
                        '</div>' +
                        '<div class="fc-name">' + f.name + '</div>' +
                        '<div class="fc-meta">💾 Size: ' + f.size + '</div>' +
                    '</div>' +
                '</a>' +
            '</div>';
        });
        resDiv.innerHTML=h;
        nextOff=d.next_offset;
        document.getElementById('pageBox').style.display='flex';
        document.getElementById('pBtn').disabled=(o===0);
        document.getElementById('nBtn').disabled=!nextOff;
        document.getElementById('pgInfo').textContent='Page '+curPage;
    }catch(e){showToast('Network error','error');}
}

function next(){if(nextOff){curPage++;doSearch(nextOff);scrollTo(0,0);}}
function prev(){if(curPage>1){curPage--;doSearch(Math.max(0,curOff-LIMIT_VAL));scrollTo(0,0);}}
var _tt;
function showToast(m,t='success'){var x=document.getElementById('toast');x.textContent=m;x.className='toast ' + t + ' show';clearTimeout(_tt);_tt=setTimeout(()=>x.classList.remove('show'),3000);}

document.addEventListener('DOMContentLoaded',()=>{{
    var pm=document.getElementById('posterMode');if(pm)pm.value=pMode;
    var q=document.getElementById('q');if(q)q.addEventListener('keydown',e=>{if(e.key==='Enter')doSearch(0);});
}});

async function deleteFile(fid,col){
    if(!confirm('Are you sure you want to delete this file?'))return;
    try{
        var r=await fetch('/api/delete',{method:'POST',body:JSON.stringify({file_id:fid,collection:col}),headers:{'Content-Type':'application/json'}});
        var res=await r.json();
        if(res.success){showToast('✅ File deleted successfully!');doSearch(curOff);}
        else{showToast(res.error||'Delete failed!','error');}
    }catch(e){showToast('Delete failed','error');}
}

function editFile(fid, col, currentName) {
    activeFid = fid; activeCol = col;
    if(cropperInstance) { cropperInstance.destroy(); cropperInstance = null; }
    document.getElementById('emName').value = currentName;
    document.getElementById('emFile').value = '';
    document.getElementById('cropContainer').style.display = 'none';
    var prevBox = document.getElementById('emPreviewBox');
    prevBox.style.display = 'flex';
    prevBox.innerHTML = '<img src="/api/thumb?file_id=' + fid + '" class="t-prev-img" onerror="this.src=\'https://placehold.co/600x338/181818/FFF?text=No+Thumbnail\';">';
    document.getElementById('editCombinedModal').classList.add('open');
}

function closeCombinedModal() {
    document.getElementById('editCombinedModal').classList.remove('open');
    if(cropperInstance) { cropperInstance.destroy(); cropperInstance = null; }
}

function handleLocalPreview(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            if(cropperInstance) { cropperInstance.destroy(); }
            document.getElementById('emPreviewBox').style.display = 'none';
            var cropWrap = document.getElementById('cropContainer');
            cropWrap.style.display = 'block';
            cropWrap.innerHTML = '<img id="cropImage" src="' + e.target.result + '" style="max-width:100%;">';
            var imageElement = document.getElementById('cropImage');
            cropperInstance = new Cropper(imageElement, {
                aspectRatio: 16 / 9, viewMode: 1, dragMode: 'move', background: false,
                autoCropArea: 1, restore: false, guides: false, center: true, highlight: false,
                cropBoxMovable: false, cropBoxResizable: false, toggleDragModeOnDblclick: false,
                zoomable: true, movable: true
            });
        };
        reader.readAsDataURL(input.files[0]);
    }
}

async function saveAllChanges() {
    var newName = document.getElementById('emName').value.trim();
    if(!newName) { showToast('File name cannot be empty!', 'error'); return; }
    var btn = document.getElementById('emSaveBtn');
    btn.disabled = true; btn.innerText = "Processing pipeline...";
    try {
        if (cropperInstance) {
            showToast('✂️ Cropping & Uploading to Telegram...');
            var canvas = cropperInstance.getCroppedCanvas({ width: 1280, height: 720, imageSmoothingEnabled: true, imageSmoothingQuality: 'high' });
            var blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
            if (blob) {
                var formData = new FormData();
                formData.append('file_id', activeFid);
                formData.append('collection', activeCol);
                formData.append('image', blob, 'cropped_poster.jpg');
                var upRes = await fetch('/api/upload_thumb', { method: 'POST', body: formData });
                var upData = await upRes.json();
                if (!upData.success) {
                    showToast(upData.error || 'Telegram image sync failed!', 'error');
                    btn.disabled = false; btn.innerText = "Save Changes";
                    return;
                }
            }
        }
        showToast('💾 Indexing metadata to Database...');
        var r = await fetch('/api/edit_name', {
            method: 'POST',
            body: JSON.stringify({ file_id: activeFid, collection: activeCol, new_name: newName }),
            headers: {'Content-Type': 'application/json'}
        });
        var res = await r.json();
        if(res.success || cropperInstance) {
            showToast('✨ Metadata & Studio Poster saved successfully!');
            closeCombinedModal();
            reloadThumb(activeFid);
            doSearch(curOff);
        } else {
            showToast(res.error || 'Metadata save failed!', 'error');
        }
    } catch(e) {
        showToast('Network synchronization error', 'error');
    } finally {
        btn.disabled = false; btn.innerText = "Save Changes";
    }
}
""".replace("__LIMIT_PLACEHOLDER__", str(MAX_WEB_RESULTS))

@dashboard_routes.get('/dashboard')
async def dash(req):
    role, tg_id = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    if role == 'user':
        mp = await user_db.get_plan(tg_id)
        if not mp.get("premium"): return web.HTTPFound('/premium_expired')

    b = '<div class="search-zone"><div class="search-row"><div class="filter-tabs"><button class="ftab active" data-col="all" onclick="setCol(this)">📂 All Sources</button><button class="ftab" data-col="primary" onclick="setCol(this)">Primary</button><button class="ftab" data-col="cloud" onclick="setCol(this)">Cloud</button><button class="ftab" data-col="archive" onclick="setCol(this)">Archive</button></div><select id="posterMode" onchange="changePosterMode()" style="background:rgba(255,255,255,0.02);color:var(--text);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:10px 14px;font-weight:700;font-size:13px;outline:none;cursor:pointer;backdrop-filter:blur(10px);"><option value="tg">👁️‍🗨️ 🖼️ Thumbnail Mode</option><option value="none">⚡ Text Only (Fastest)</option></select><div class="search-wrap"><span class="s-icon">🔍</span><input class="search-input" id="q" placeholder="Type a movie name to search..."></div><button class="search-btn" onclick="doSearch(0)">Search</button></div></div><div class="main" style="padding-top:20px;"><div class="results-info" id="resInfo" style="margin-bottom:15px; font-size:14px; color:var(--muted);"><span class="results-count" id="resCount"></span></div><div id="results" class="res-grid"><div class="empty"><div class="empty-icon">🍿</div><p style="font-weight:600; font-size:15px; letter-spacing:0.5px;">Find your favorite movies and TV shows instantly.</p></div></div><div class="pagination" id="pageBox"><button class="pg-btn" id="pBtn" onclick="prev()" disabled>← Prev</button><span class="pg-info" id="pgInfo" style="font-weight:bold; color:var(--accent);">Page 1</span><button class="pg-btn" id="nBtn" onclick="next()">Next →</button></div></div><div class="toast" id="toast"></div>'
    
    # CSS को हुड स्टाइल के लिए री-इंजेक्ट किया गया है
    hud_style = '''
    <style>
    .poster-box { position: relative; cursor: pointer; overflow: hidden; }
    .hud-overlay {
        position: absolute; inset: 0; background: rgba(0,0,0,0.82);
        display: flex; align-items: center; justify-content: center;
        opacity: 0; pointer-events: none; z-index: 10;
        transition: opacity 0.22s ease-in-out; backdrop-filter: blur(5px);
    }
    .hud-overlay.visible { opacity: 1; pointer-events: auto; }
    .hud-btn {
        flex: 1; padding: 10px; border-radius: 8px; font-size: 12px; 
        font-weight: 700; cursor: pointer; border: none; transition: transform 0.1s;
    }
    .hud-btn:active { transform: scale(0.95); }
    .hud-btn-edit { background: #2a2a2a; color: #fff; border: 1px solid rgba(255,255,255,0.15); }
    .hud-btn-del { background: var(--accent); color: #fff; }
    .fc-content-link { text-decoration: none; color: inherit; display: block; }
    .fc-content-zone { padding: 16px; display: flex; flex-direction: column; }
    .fc-content-link:hover .fc-name { color: var(--accent); }
    .no-thumb-placeholder {
        position: absolute; inset: 0; display: flex; flex-direction: column;
        align-items: center; justify-content: center; background: #06060a; gap: 6px;
    }
    </style>
    '''
    
    custom_body_layout = hud_style + b + f"<script>{JS_ENGINE}</script>"
    return build_page("Home - Fast Finder", custom_body_layout, "", "dash", role)

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
