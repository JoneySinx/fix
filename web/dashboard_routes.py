import gc
from aiohttp import web
from web.web_assets import build_page, get_auth, form_wrapper, MAX_WEB_RESULTS
from database.users_chats_db import db as user_db
from utils import temp

dashboard_routes = web.RouteTableDef()

CARD_CSS = """
<style>
.search-zone{padding:16px 4% 0}
.search-row1{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.search-row2{display:flex;align-items:center;gap:8px;margin-bottom:16px}
.search-wrap{flex:1;display:flex;align-items:center;background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:0 12px;gap:8px}
.s-icon{color:var(--muted);font-size:16px}
.search-input{flex:1;background:transparent;border:none;outline:none;color:var(--text);font-size:13px;padding:11px 0;font-family:inherit}
.search-btn{background:linear-gradient(135deg,var(--accent),var(--accent-hover));color:#fff;border:none;border-radius:8px;padding:11px 22px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;box-shadow:0 4px 14px rgba(229,9,20,0.35)}
.search-btn:hover{opacity:0.92}
.filter-select{background:var(--bg3);color:var(--text);border:1px solid var(--border);border-radius:7px;padding:9px 10px;font-size:12px;font-weight:700;outline:none;cursor:pointer;font-family:inherit}
.res-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:14px;margin-bottom:24px}
.res-grid.mode-none .poster-box{display:none}
.file-card{background:var(--card);border-radius:10px;overflow:hidden;border:1px solid var(--border);transition:transform .22s cubic-bezier(.4,0,.2,1),box-shadow .22s,border-color .22s;cursor:pointer}
.file-card:hover{transform:translateY(-4px);border-color:rgba(229,9,20,.4);box-shadow:0 14px 36px rgba(0,0,0,.6),0 0 0 1px rgba(229,9,20,.2)}
.poster-box{position:relative;padding-top:56.25%;background:var(--bg3);overflow:hidden}
.fc-poster{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .35s ease}
.file-card:hover .fc-poster{transform:scale(1.05)}
.thumb-error{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:#1f1f1f}
.poster-top{position:absolute;top:0;left:0;right:0;display:flex;align-items:center;gap:5px;padding:8px}
.type-chip{background:rgba(0,0,0,.72);backdrop-filter:blur(8px);color:#fff;border-radius:5px;padding:3px 8px;font-size:10px;font-weight:800;letter-spacing:.8px;border:1px solid rgba(255,255,255,.14);line-height:1.4}
.size-chip{background:rgba(0,0,0,.60);backdrop-filter:blur(8px);color:#e0e0e0;border-radius:5px;padding:3px 8px;font-size:10px;font-weight:600;border:1px solid rgba(255,255,255,.08);line-height:1.4}
.source-pill{margin-left:auto;border-radius:20px;padding:3px 8px;font-size:9px;font-weight:700;letter-spacing:.4px;display:inline-flex;align-items:center;gap:4px;backdrop-filter:blur(8px)}
.source-pill.primary{background:rgba(34,197,94,.15);color:#22c55e;border:1px solid rgba(34,197,94,.28)}
.source-pill.cloud{background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.28)}
.source-pill.archive{background:rgba(251,146,60,.15);color:#fb923c;border:1px solid rgba(251,146,60,.28)}
.source-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0}
.primary .source-dot{background:#22c55e;box-shadow:0 0 4px #22c55e}
.cloud .source-dot{background:#60a5fa;box-shadow:0 0 4px #60a5fa}
.archive .source-dot{background:#fb923c;box-shadow:0 0 4px #fb923c}
.poster-admin{position:absolute;bottom:0;left:0;right:0;display:flex;gap:6px;padding:7px 8px;opacity:0;transform:translateY(8px);transition:opacity .2s ease,transform .22s ease;pointer-events:none}
.file-card:hover .poster-admin{opacity:1;transform:translateY(0);pointer-events:all}
.btn-edit,.btn-del{flex:1;padding:6px 0;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;transition:background .12s,transform .1s;border:none}
.btn-edit{background:rgba(42,42,48,.90);backdrop-filter:blur(10px);color:#fff;border:1px solid rgba(255,255,255,.18)}
.btn-edit:hover{background:rgba(80,80,88,.95)}
.btn-edit:active{transform:scale(.93)}
.btn-del{background:rgba(160,8,8,.78);backdrop-filter:blur(10px);color:#fff;border:1px solid rgba(229,9,20,.45)}
.btn-del:hover{background:rgba(229,9,20,.92)}
.btn-del:active{transform:scale(.93)}
.fc-body{padding:10px 11px 12px}
.fc-name{color:var(--text);font-size:12.5px;font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;cursor:pointer;transition:color .18s;text-decoration:none}
.fc-name:hover{color:var(--accent);text-decoration:underline;text-decoration-color:var(--accent);text-underline-offset:2px}
.fc-text-info{display:flex;align-items:center;gap:6px;padding:10px 11px 0;flex-wrap:wrap;margin-bottom:4px}
.tc-type{background:var(--bg4);color:var(--muted);border-radius:5px;padding:2px 7px;font-size:9px;font-weight:800;letter-spacing:.8px;border:1px solid var(--border)}
.tc-size{color:var(--muted);font-size:11px}
.pagination{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:8px}
.pg-btn{background:var(--bg4);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px 18px;font-size:12px;font-weight:700;cursor:pointer;transition:background .15s}
.pg-btn:disabled{background:var(--bg3);color:var(--muted);cursor:not-allowed}
.pg-btn:not(:disabled):hover{background:var(--bg3)}
.pg-info{color:var(--muted);font-size:12px;font-weight:600}
.empty{text-align:center;padding:60px 20px;color:var(--muted)}
.empty-icon{font-size:36px;margin-bottom:12px}
.spin-wrap{display:flex;flex-direction:column;align-items:center;gap:16px;padding:60px 20px;color:var(--muted)}
.spinner{width:36px;height:36px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
"""

JS_PART1 = """
var curQ='',curOff=0,nextOff='',curCol='all',curPage=1;
var pMode=localStorage.getItem('posterMode')||'tg';
var LIMIT_VAL=__LIMIT_VAL__;
var activeFid='',activeCol='',activeTgRef='',cropperInstance=null;

function changeCol(val){curCol=val;if(curQ)doSearch(0);}
function changePosterMode(){pMode=document.getElementById('posterMode').value;localStorage.setItem('posterMode',pMode);if(curQ)doSearch(curOff);}

function handleThumbError(fileId){
    var box=document.getElementById('poster-box-'+fileId);
    if(box){box.innerHTML='<div class=\"thumb-error\"><span style=\"font-size:11px;color:var(--muted)\">थंबनेल लोड नहीं हुआ</span></div>';}
}
async function reloadThumb(fileId){
    var box=document.getElementById('poster-box-'+fileId);
    if(box){box.innerHTML='<img src=\"/api/thumb?file_id='+fileId+'&t='+Date.now()+'\" class=\"fc-poster\" onerror=\"handleThumbError('+fileId+')\">';}
}
""".replace("__LIMIT_VAL__", str(MAX_WEB_RESULTS))

JS_PART2 = r"""
async function doSearch(o){
    var q=document.getElementById('q').value.trim();
    if(!q){showToast('Please enter a movie name','error');return;}
    curQ=q;curOff=o;if(o===0)curPage=1;
    var resDiv=document.getElementById('results');
    resDiv.className='res-grid mode-'+pMode;
    resDiv.innerHTML='<div class="spin-wrap"><div class="spinner"></div><span>Searching...</span></div>';
    try{
        var r=await fetch('/api/search?q='+encodeURIComponent(q)+'&offset='+o+'&col='+curCol+'&mode='+pMode);
        if(!r.ok){showToast('Error fetching','error');return;}
        var d=await r.json();
        if(d.error){showToast(d.error,'error');return;}
        document.getElementById('resInfo').style.display='flex';
        document.getElementById('resCount').innerHTML='More to explore: <span style="color:var(--text);font-weight:600">'+q+'</span>';
        if(!d.results||!d.results.length){
            resDiv.innerHTML='<div class="empty"><div class="empty-icon">&#9888;</div><p>No titles found for "'+q+'"</p></div>';
            document.getElementById('pageBox').style.display='none';return;
        }
        var h='';
        d.results.forEach(function(f){
            var sc=(f.source||'primary').toLowerCase();
            if(!['primary','cloud','archive'].includes(sc))sc='primary';
            var tgRef=(f.tg_file_ref||f.file_id);

            var adminBtns='';
            if(d.is_admin){
                var sn=f.name.replace(/\/g,'\\').replace(/'/g,"\'");
                adminBtns='<div class="poster-admin">'
                    +'<button class="btn-edit" onclick="editFile(''+f.file_id+'',''+f.raw_collection+'',''+sn+'',''+tgRef+'')">&#9999; Edit</button>'
                    +'<button class="btn-del" onclick="deleteFile(''+f.file_id+'',''+f.raw_collection+'')">&#128465; Delete</button>'
                    +'</div>';
            }

            var posterHtml='';
            if(pMode!=='none'){
                posterHtml='<div class="poster-box" id="poster-box-'+f.file_id+'">'
                    +'<img src="'+f.tg_thumb+'" class="fc-poster" onerror="handleThumbError(''+f.file_id+'')" loading="lazy">'
                    +'<div class="poster-top">'
                        +'<span class="type-chip">'+f.type.toUpperCase()+'</span>'
                        +'<span class="size-chip">'+f.size+'</span>'
                        +'<span class="source-pill '+sc+'"><span class="source-dot"></span>'+sc.toUpperCase()+'</span>'
                    +'</div>'
                    +adminBtns
                    +'</div>';
            }

            var textInfo='';
            if(pMode==='none'){
                textInfo='<div class="fc-text-info">'
                    +'<span class="tc-type">'+f.type.toUpperCase()+'</span>'
                    +'<span class="tc-size">'+f.size+'</span>'
                    +'<span class="source-pill '+sc+'" style="margin-left:auto"><span class="source-dot"></span>'+sc.toUpperCase()+'</span>'
                    +'</div>';
                if(d.is_admin){
                    var sn2=f.name.replace(/\/g,'\\').replace(/'/g,"\'");
                    textInfo+='<div style="display:flex;gap:5px;padding:5px 11px 0">'
                        +'<button class="btn-edit" onclick="editFile(''+f.file_id+'',''+f.raw_collection+'',''+sn2+'',''+tgRef+'')">&#9999; Edit</button>'
                        +'<button class="btn-del" onclick="deleteFile(''+f.file_id+'',''+f.raw_collection+'')">&#128465; Delete</button>'
                        +'</div>';
                }
            }

            h+='<div class="file-card">'
                +posterHtml+textInfo
                +'<div class="fc-body"><div class="fc-name" onclick="window.open(''+f.watch+'','_blank')">'+f.name+'</div></div>'
                +'</div>';
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
function showToast(m,t){t=t||'success';var x=document.getElementById('toast');x.textContent=m;x.className='toast '+t+' show';clearTimeout(_tt);_tt=setTimeout(function(){x.classList.remove('show');},3000);}

document.addEventListener('DOMContentLoaded',function(){
    var pm=document.getElementById('posterMode');if(pm)pm.value=pMode;
    var q=document.getElementById('q');if(q)q.addEventListener('keydown',function(e){if(e.key==='Enter')doSearch(0);});
    var cs=document.getElementById('colSelect');if(cs)cs.value=curCol;
});

async function deleteFile(fid,col){
    if(!confirm('Are you sure you want to delete this file?'))return;
    try{
        var r=await fetch('/api/delete',{method:'POST',body:JSON.stringify({file_id:fid,collection:col}),headers:{'Content-Type':'application/json'}});
        var res=await r.json();
        if(res.success){showToast('\u2705 File deleted!');doSearch(curOff);}
        else{showToast(res.error||'Delete failed!','error');}
    }catch(e){showToast('Delete failed','error');}
}

function editFile(fid,col,currentName,tgRef){
    activeFid=fid;activeCol=col;activeTgRef=tgRef||fid;
    if(cropperInstance){cropperInstance.destroy();cropperInstance=null;}
    document.getElementById('emName').value=currentName;
    document.getElementById('emFile').value='';
    document.getElementById('cropContainer').style.display='none';
    var prevBox=document.getElementById('emPreviewBox');
    prevBox.style.display='flex';
    prevBox.innerHTML='<img src="/api/thumb?file_id='+fid+'&t='+Date.now()+'" class="t-prev-img" onerror="this.src='https://placehold.co/600x338/181818/FFF?text=No+Thumbnail';">';
    document.getElementById('editCombinedModal').classList.add('open');
}

function closeCombinedModal(){
    document.getElementById('editCombinedModal').classList.remove('open');
    if(cropperInstance){cropperInstance.destroy();cropperInstance=null;}
}

function handleLocalPreview(input){
    if(input.files&&input.files[0]){
        var reader=new FileReader();
        reader.onload=function(e){
            if(cropperInstance){cropperInstance.destroy();}
            document.getElementById('emPreviewBox').style.display='none';
            var cropWrap=document.getElementById('cropContainer');
            cropWrap.style.display='block';
            cropWrap.innerHTML='<img id="cropImage" src="'+e.target.result+'" style="max-width:100%;">';
            cropperInstance=new Cropper(document.getElementById('cropImage'),{
                aspectRatio:16/9,viewMode:1,dragMode:'move',background:false,
                autoCropArea:1,restore:false,guides:false,center:true,highlight:false,
                cropBoxMovable:false,cropBoxResizable:false,toggleDragModeOnDblclick:false,
                zoomable:true,movable:true
            });
        };
        reader.readAsDataURL(input.files[0]);
    }
}

async function saveAllChanges(){
    var newName=document.getElementById('emName').value.trim();
    if(!newName){showToast('File name cannot be empty!','error');return;}
    var btn=document.getElementById('emSaveBtn');
    btn.disabled=true;btn.innerText='Processing pipeline...';
    try{
        if(cropperInstance){
            showToast('Cropping & Uploading...');
            var canvas=cropperInstance.getCroppedCanvas({width:1280,height:720,imageSmoothingEnabled:true,imageSmoothingQuality:'high'});
            var blob=await new Promise(function(resolve){canvas.toBlob(resolve,'image/jpeg',0.9);});
            if(blob){
                var fd=new FormData();
                fd.append('file_id',activeFid);
                fd.append('collection',activeCol);
                fd.append('image',blob,'poster.jpg');
                var ur=await fetch('/api/upload_thumb',{method:'POST',body:fd});
                var ud=await ur.json();
                if(!ud.success){showToast(ud.error||'Upload failed!','error');btn.disabled=false;btn.innerText='Save Changes';return;}
            }
        }
        showToast('Saving metadata...');
        var r=await fetch('/api/edit_name',{method:'POST',body:JSON.stringify({file_id:activeFid,collection:activeCol,new_name:newName}),headers:{'Content-Type':'application/json'}});
        var res=await r.json();
        if(res.success||cropperInstance){
            showToast('\u2728 Saved successfully!');
            closeCombinedModal();reloadThumb(activeFid);doSearch(curOff);
        }else{showToast(res.error||'Save failed!','error');}
    }catch(e){showToast('Network error','error');}
    finally{btn.disabled=false;btn.innerText='Save Changes';}
}
"""

SEARCH_ZONE = (
    '<div class="search-zone">'
        '<div class="search-row1">'
            '<div class="search-wrap"><span class="s-icon">&#9906;</span>'
            '<input class="search-input" id="q" placeholder="Titles, people, genres\u2026"></div>'
            '<button class="search-btn" onclick="doSearch(0)">Search</button>'
        '</div>'
        '<div class="search-row2">'
            '<select class="filter-select" id="colSelect" onchange="changeCol(this.value)">'
                '<option value="all">\U0001f4c2 All Collections</option>'
                '<option value="primary">\U0001f7e2 Primary</option>'
                '<option value="cloud">\U0001f535 Cloud</option>'
                '<option value="archive">\U0001f7e0 Archive</option>'
            '</select>'
            '<select id="posterMode" onchange="changePosterMode()" class="filter-select">'
                '<option value="tg">\U0001f4f8 Original TG Thumb</option>'
                '<option value="none">\u26a1 Text Only (Fastest)</option>'
            '</select>'
        '</div>'
    '</div>'
    '<div class="main" style="padding-top:4px;">'
        '<div class="results-info" id="resInfo" style="padding:0 4% 12px;">'
            '<span class="results-count" id="resCount"></span>'
        '</div>'
        '<div style="padding:0 4%">'
            '<div id="results" class="res-grid">'
                '<div class="empty"><div class="empty-icon">&#8981;</div>'
                '<p>Find your favorite movies and TV shows.</p></div>'
            '</div>'
            '<div class="pagination" id="pageBox" style="display:none;">'
                '<button class="pg-btn" id="pBtn" onclick="prev()" disabled>Previous</button>'
                '<span class="pg-info" id="pgInfo">Page 1</span>'
                '<button class="pg-btn" id="nBtn" onclick="next()">Next</button>'
            '</div>'
        '</div>'
    '</div>'
    '<div class="toast" id="toast"></div>'
)

JS_ENGINE = JS_PART1 + JS_PART2


@dashboard_routes.get('/dashboard')
async def dash(req):
    role, tg_id = await get_auth(req)
    if not role:
        return web.HTTPFound('/login')
    if role == 'user':
        mp = await user_db.get_plan(tg_id)
        if not mp.get("premium"):
            return web.HTTPFound('/premium_expired')
    body = CARD_CSS + SEARCH_ZONE + f"<script>{JS_ENGINE}</script>"
    return build_page("Home - Fast Finder", body, "", "dash", role)


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
    if not role:
        return web.HTTPFound('/login')
    content = (
        '<div style="text-align:center;">'
        '<div style="font-size:50px;margin-bottom:15px;">&#9203;</div>'
        '<p style="color:var(--muted);margin-bottom:30px;">Your access to Fast Finder Web has expired. '
        'Please renew your plan via our Telegram Bot.</p>'
        '<div class="scard red" style="text-align:left;margin-bottom:25px;padding:15px;">'
        '<div class="scard-label">How to Renew?</div>'
        '<div class="scard-sub" style="color:var(--text)">1. Go to Telegram Bot</div>'
        '<div class="scard-sub" style="color:var(--text)">2. Use command <b>/plan</b></div>'
        '<div class="scard-sub" style="color:var(--text)">3. Pay & Activate instantly</div>'
        '</div>'
        f'<a href="https://t.me/{temp.U_NAME}" class="submit-btn" style="text-decoration:none;display:block;">Open Telegram Bot</a>'
        '<a href="/logout" style="display:block;margin-top:20px;color:var(--muted);text-decoration:none;">Sign Out</a>'
        '</div>'
    )
    return build_page("Premium Expired", form_wrapper("Premium Expired", content), "login-bg")
