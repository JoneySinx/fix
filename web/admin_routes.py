from aiohttp import web
import time, uuid, random
from info import ADMINS
from utils import temp
from database.users_chats_db import db as user_db, web_db
from database.ia_filterdb import db_count_documents
from hydrogram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB

admin_routes = web.RouteTableDef()

# रजिस्ट्रेशन OTP को स्टोर करने के लिए टेम्पररी डिक्शनरी
if not hasattr(temp, 'REG_PENDING'):
    temp.REG_PENDING = {}

# ----------------- MINIFIED ASSETS -----------------
# ✅ CSS FIX: "body.light" की जगह ".light" कर दिया गया है
CSS = "*{box-sizing:border-box;margin:0;padding:0}:root{--bg:#141414;--bg2:#000;--bg3:#2b2b2b;--bg4:#333;--accent:#e50914;--accent-hover:#b30710;--text:#fff;--muted:#808080;--border:#404040;--card:#181818;--sidebar-w:260px}.light{--bg:#f3f3f3;--bg2:#fff;--bg3:#e6e6e6;--bg4:#ccc;--text:#141414;--muted:#666;--border:#ccc;--card:#fff}body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;transition:.2s}.topbar{background:var(--bg2);padding:0 4%;display:flex;align-items:center;height:68px;position:sticky;top:0;z-index:100;gap:15px;box-shadow:0 2px 10px rgba(0,0,0,.5)}.ham-btn{background:0 0;border:0;cursor:pointer;color:var(--text);display:flex;flex-direction:column;gap:5px;padding:6px}.ham-line{width:22px;height:2px;background:currentColor;transition:.2s}.ham-btn.open .ham-line:nth-child(1){transform:translateY(7px) rotate(45deg)}.ham-btn.open .ham-line:nth-child(2){opacity:0}.ham-btn.open .ham-line:nth-child(3){transform:translateY(-7px) rotate(-45deg)}.logo{font-size:18px;font-weight:900;letter-spacing:1px;color:var(--accent);display:flex;align-items:center;gap:8px;text-decoration:none;flex:1}.nf-icon{background:var(--accent);color:#fff;padding:2px 7px;border-radius:3px;font-size:18px;line-height:1}.theme-btn{margin-left:auto;background:0 0;border:1px solid var(--border);border-radius:4px;padding:6px 12px;font-size:12px;font-weight:700;color:var(--text);cursor:pointer}.theme-btn:hover{background:var(--bg3)}.sidebar-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:150;opacity:0;pointer-events:none;transition:.2s}.sidebar-overlay.open{opacity:1;pointer-events:all}.sidebar{position:fixed;top:0;left:0;height:100%;width:var(--sidebar-w);background:var(--bg2);border-right:1px solid var(--border);z-index:160;display:flex;flex-direction:column;transform:translateX(-100%);transition:.3s}.sidebar.open{transform:translateX(0)}.sb-header{padding:20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between}.sb-logo{font-size:14px;font-weight:900;color:var(--accent);display:flex;align-items:center;gap:8px}.sb-close{background:0 0;border:0;color:var(--muted);font-size:22px;cursor:pointer}.sb-nav{padding:15px 10px;flex:1}.sb-section{font-size:11px;font-weight:700;color:var(--muted);padding:8px 12px}.sb-link{display:flex;padding:12px 15px;border-radius:4px;text-decoration:none;color:var(--muted);font-size:15px;font-weight:500;margin-bottom:4px}.sb-link.active{background:var(--accent);color:#fff}.sb-footer{padding:15px 10px;border-top:1px solid var(--border)}.sb-logout{display:block;padding:12px;border-radius:4px;text-align:center;text-decoration:none;color:var(--text);font-weight:700;border:1px solid var(--border)}.search-zone{padding:20px 4%;background:var(--bg)}.search-row{display:flex;gap:10px;flex-wrap:wrap}.filter-tabs{display:flex;gap:4px;background:var(--bg2);border:1px solid var(--border);padding:4px;border-radius:4px}.ftab{background:0 0;border:0;padding:8px 16px;font-weight:700;color:var(--muted);cursor:pointer}.ftab.active{background:var(--bg3);color:var(--text)}.search-wrap{flex:1;position:relative;min-width:200px}.s-icon{position:absolute;left:15px;top:50%;transform:translateY(-50%);color:var(--muted)}.search-input{width:100%;background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:12px 15px 12px 42px;color:var(--text);font-size:15px;outline:0}.search-btn{background:var(--accent);color:#fff;border:0;border-radius:4px;padding:12px 24px;font-weight:700;cursor:pointer}.main{padding:0 4% 40px;max-width:1400px;margin:0 auto}.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:30px}.scard{background:var(--card);padding:20px;border-radius:4px;position:relative;box-shadow:0 4px 6px rgba(0,0,0,.3)}.scard::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px}.scard.red::after{background:var(--accent)}.scard.white::after{background:#fff}.scard.grey::after{background:#808080}.scard-label{font-size:12px;font-weight:700;color:var(--muted);margin-bottom:10px}.scard-val{font-size:32px;font-weight:900;color:var(--text)}.scard-sub{font-size:12px;color:var(--muted)}.results-info{display:none;justify-content:space-between;padding:10px 0 20px;font-weight:700}.file-card{background:var(--card);border-radius:4px;padding:18px;display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:12px;border:1px solid var(--bg3)}.fc-left{flex:1}.fc-top{display:flex;gap:8px;margin-bottom:8px}.source-badge{font-size:10px;font-weight:900;padding:2px 6px;border-radius:2px;border:1px solid}.source-badge.primary{color:var(--accent);border-color:var(--accent)}.source-badge.cloud{color:#3399ff;border-color:#3399ff}.source-badge.archive{color:var(--muted);border-color:var(--muted)}.type-tag{font-size:12px;font-weight:700;color:var(--muted)}.fc-name{font-size:16px;font-weight:500;margin-bottom:6px}.fc-meta{font-size:13px;color:var(--muted)}.btn-play{background:var(--text);color:var(--card);padding:10px 24px;border-radius:4px;font-weight:800;text-decoration:none;display:flex;gap:8px;transition:0.2s}.btn-play:hover{opacity:0.8}.empty{text-align:center;padding:80px 20px;color:var(--muted)}.empty-icon{font-size:40px;margin-bottom:15px}.pagination{display:none;justify-content:center;gap:15px;padding:30px 0;align-items:center}.pg-btn{background:var(--bg3);border:0;color:var(--text);padding:10px 20px;border-radius:4px;font-weight:700;cursor:pointer}.pg-btn:disabled{opacity:.3}.toast{position:fixed;bottom:20px;right:20px;background:var(--accent);color:#fff;padding:12px 20px;border-radius:4px;font-weight:700;z-index:300;transform:translateX(150%);transition:.3s}.toast.show{transform:translateX(0)}.toast.error{background:#000;border:1px solid var(--accent)}.login-bg{background:linear-gradient(rgba(0,0,0,.8) 0,rgba(0,0,0,.4) 50%,rgba(0,0,0,.8) 100%),url('https://assets.nflxext.com/ffe/siteui/vlv3/f841d4c7-10e1-40af-bcae-07a3f8dc141a/f6d7434e-d6de-4185-a6d4-c77a2d08737b/IN-en-20220502-popsignuptwoweeks-perspective_alpha_website_medium.jpg') center/cover;min-height:100vh;display:flex;flex-direction:column}.login-top{padding:20px 4%; display:flex; justify-content:space-between; align-items:center;}.login-logo-big{font-size:32px;font-weight:900;color:var(--accent);display:flex;gap:8px;text-decoration:none;}.login-wrap{flex:1;display:flex;align-items:center;justify-content:center;padding:20px}.login-card{background:rgba(0,0,0,.75);padding:60px;border-radius:4px;width:100%;max-width:450px}.login-card h2{font-size:32px;margin-bottom:28px}.login-card input{width:100%;background:#333;border:0;padding:16px;color:#fff;margin-bottom:16px;border-radius:4px}.login-card .submit-btn{width:100%;background:var(--accent);color:#fff;border:0;padding:16px;font-weight:700;margin-top:24px;border-radius:4px;cursor:pointer}.err-box{background:#e87c03;color:#fff;padding:10px 20px;border-radius:4px;margin-bottom:16px}.success-box{background:#28a745;color:#fff;padding:10px 20px;border-radius:4px;margin-bottom:16px}.big-stat{background:var(--card);padding:40px 20px;border-radius:4px;text-align:center;margin-bottom:30px}.big-stat-val{font-size:64px;font-weight:900;color:var(--accent);margin-bottom:10px}.big-stat-label{font-size:16px;color:var(--muted);font-weight:700;letter-spacing:2px}"

# ✅ JS FIX: document.documentElement का उपयोग किया गया है
JS = """
(function(){if(localStorage.getItem('theme')==='light')document.documentElement.classList.add('light')})();
function toggleTheme(){var l=document.documentElement.classList.toggle('light');localStorage.setItem('theme',l?'light':'dark');}
function openSidebar(){document.getElementById('sidebar').classList.add('open');document.getElementById('sbOverlay').classList.add('open');document.getElementById('hamBtn').classList.add('open');}
function closeSidebar(){document.getElementById('sidebar').classList.remove('open');document.getElementById('sbOverlay').classList.remove('open');document.getElementById('hamBtn').classList.remove('open');}
var curQ='',curOff=0,nextOff='',curCol='all',curPage=1;
function setCol(e){document.querySelectorAll('.ftab').forEach(t=>t.classList.remove('active'));e.classList.add('active');curCol=e.dataset.col;}

async function doSearch(o){
    var q=document.getElementById('q').value.trim();
    if(!q){showToast('Please enter a movie name','error');return;}
    curQ=q;curOff=o;if(o===0)curPage=1;
    try{
        var r=await fetch(`/api/search?q=${encodeURIComponent(q)}&offset=${o}&col=${curCol}`);
        if(!r.ok){showToast('Error fetching','error');return;}
        var d=await r.json();
        if(d.error){showToast(d.error,'error');return;}
        document.getElementById('resInfo').style.display='flex';
        document.getElementById('resCount').innerHTML=`More to explore: <span style="color:var(--text)">${q}</span>`;
        if(!d.results||!d.results.length){
            document.getElementById('results').innerHTML=`<div class="empty"><div class="empty-icon">&#9888;</div><p>No titles found for "${q}"</p></div>`;
            document.getElementById('pageBox').style.display='none';return;
        }
        var h='';
        d.results.forEach(f=>{
            var sc=(f.source||'primary').toLowerCase();
            if(!['primary','cloud','archive'].includes(sc))sc='primary';
            
            var adminControls='';
            if(d.is_admin){
                adminControls=`<div style="display:flex;gap:5px;margin-top:10px;">
                    <button onclick="editFile('${f.file_id}','${f.raw_collection}','${f.name.replace(/'/g,"\\\\'")}')" style="background:#444;color:#fff;border:0;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:12px;">Edit</button>
                    <button onclick="deleteFile('${f.file_id}','${f.raw_collection}')" style="background:var(--accent);color:#fff;border:0;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:12px;">Delete</button>
                </div>`;
            }
            
            h+=`<div class="file-card"><div class="fc-left"><div class="fc-top"><span class="source-badge ${sc}">${sc.toUpperCase()}</span><span class="type-tag">${f.type.toUpperCase()}</span></div><div class="fc-name">${f.name}</div><div class="fc-meta">Size: ${f.size}</div>${adminControls}</div><a href="${f.watch}" target="_blank" class="btn-play">&#9654; Play</a></div>`;
        });
        document.getElementById('results').innerHTML=h;
        nextOff=d.next_offset;
        document.getElementById('pageBox').style.display='flex';
        document.getElementById('pBtn').disabled=(o===0);
        document.getElementById('nBtn').disabled=!nextOff;
        document.getElementById('pgInfo').textContent='Page '+curPage;
    }catch(e){showToast('Network error','error');}
}

function next(){if(nextOff){curPage++;doSearch(nextOff);scrollTo(0,0);}}
function prev(){if(curPage>1){curPage--;doSearch(Math.max(0,curOff-20));scrollTo(0,0);}}
var _tt;
function showToast(m,t='success'){var x=document.getElementById('toast');x.textContent=m;x.className=`toast ${t} show`;clearTimeout(_tt);_tt=setTimeout(()=>x.classList.remove('show'),3000);}

document.addEventListener('DOMContentLoaded',()=>{var q=document.getElementById('q');if(q)q.addEventListener('keydown',e=>{if(e.key==='Enter')doSearch(0);});});

async function deleteFile(fid,col){
    if(!confirm('Are you sure you want to delete this file?'))return;
    try{
        var r=await fetch('/api/delete',{method:'POST',body:JSON.stringify({file_id:fid,collection:col}),headers:{'Content-Type':'application/json'}});
        var res=await r.json();
        if(res.success){showToast(res.message);doSearch(curOff);}
        else{showToast(res.error,'error');}
    }catch(e){showToast('Delete failed','error');}
}

async function editFile(fid,col,oldName){
    var newName=prompt("Enter new file name:",oldName);
    if(!newName||newName===oldName)return;
    try{
        var r=await fetch('/api/edit',{method:'POST',body:JSON.stringify({file_id:fid,collection:col,new_name:newName}),headers:{'Content-Type':'application/json'}});
        var res=await r.json();
        if(res.success){showToast(res.message);doSearch(curOff);}
        else{showToast(res.error,'error');}
    }catch(e){showToast('Edit failed','error');}
}
"""

# ----------------- UTILS & BUILDERS -----------------
def _h(html): return web.Response(text=html.encode('utf-8','replace').decode('utf-8'), content_type='text/html', charset='utf-8')

async def get_auth(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and s_user in temp.USER_SESSIONS and temp.USER_SESSIONS[s_user]['expiry'] > time.time():
        tg_id = temp.USER_SESSIONS[s_user]['tg_id']
        if tg_id in ADMINS:
            return 'admin', tg_id
        return 'user', tg_id
    return None, None

# ✅ BUILD_PAGE FIX: <body> से class="{cls}" हटा दिया गया है
def build_page(title, body, active_tab="", role=None):
    if role == 'admin':
        nav_links = f'<a href="/dashboard" class="sb-link {"active" if active_tab=="dash" else ""}">Home</a><a href="/stats" class="sb-link {"active" if active_tab=="stats" else ""}">Database Stats</a><a href="/profile" class="sb-link {"active" if active_tab=="profile" else ""}">Profile Settings</a>'
    elif role == 'user':
        nav_links = f'<a href="/dashboard" class="sb-link {"active" if active_tab=="dash" else ""}">Home</a><a href="/profile" class="sb-link {"active" if active_tab=="profile" else ""}">Profile Settings</a>'
    else: nav_links = ""

    if role:
        nav = f'<div class="sidebar-overlay" id="sbOverlay" onclick="closeSidebar()"></div><div class="sidebar" id="sidebar"><div class="sb-header"><div class="sb-logo"><span class="nf-icon">F</span> FAST FINDER</div><button class="sb-close" onclick="closeSidebar()">&#10005;</button></div><nav class="sb-nav"><div class="sb-section">Menu</div>{nav_links}</nav><div class="sb-footer"><a href="/logout" class="sb-logout">Sign Out</a></div></div><div class="topbar"><button class="ham-btn" id="hamBtn" onclick="openSidebar()"><span class="ham-line"></span><span class="ham-line"></span><span class="ham-line"></span></button><a class="logo" href="/dashboard"><span class="nf-icon">F</span> FAST FINDER</a><div class="topbar-right"><button class="theme-btn" onclick="toggleTheme()">Theme</button></div></div>'
    else:
        nav = '<div class="topbar" style="position:absolute; width:100%; box-shadow:none; background:transparent;"><a class="logo" href="/" style="font-size:24px"><span class="nf-icon" style="font-size:24px">F</span> FAST FINDER</a><div class="topbar-right"><button class="theme-btn" onclick="toggleTheme()">Theme</button></div></div>'
        
    return _h(f'<!DOCTYPE html><html><head><title>{title}</title><meta name="viewport" content="width=device-width,initial-scale=1"><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&display=swap" rel="stylesheet"><style>{CSS}</style><script>{JS}</script></head><body>{nav}{body}</body></html>')

def form_wrapper(title, content, err="", msg=""):
    e = f'<div class="err-box">{err}</div>' if err else ""
    m = f'<div class="success-box">{msg}</div>' if msg else ""
    return f'<div class="login-wrap"><div class="login-card"><h2>{title}</h2>{e}{m}{content}</div></div>'

# ----------------- UNIFIED ROUTES -----------------
@admin_routes.get('/admin')
async def old_admin_route(req):
    return web.HTTPFound('/login')

@admin_routes.get('/login')
async def login_user(req):
    role, _ = await get_auth(req)
    if role: return web.HTTPFound('/dashboard')
    content = '<form action="/api/login" method="post"><input type="email" name="email" placeholder="Email Address" required><input type="password" name="password" placeholder="Password" required><button class="submit-btn" type="submit">Sign In</button></form><div style="margin-top:20px; display:flex; justify-content:space-between; font-size:14px;"><a href="/forgot_password" style="color:var(--muted); text-decoration:none;">Forgot Password?</a><a href="/register" style="color:#fff; text-decoration:none;">New? Join Now</a></div>'
    return build_page("Sign In", f'<div class="login-bg">{form_wrapper("Sign In", content, req.query.get("err",""), req.query.get("msg",""))}</div>', "login-bg")

@admin_routes.post('/api/login')
async def api_login_user(req):
    d = await req.post()
    user = await web_db.verify_login(d.get('email'), d.get('password'))
    if user:
        s = str(uuid.uuid4())
        if not hasattr(temp, 'USER_SESSIONS'): temp.USER_SESSIONS = {}
        temp.USER_SESSIONS[s] = {'tg_id': user['tg_id'], 'expiry': time.time() + 86400 * 7}
        res = web.HTTPFound('/dashboard')
        res.set_cookie('user_session', s, max_age=86400 * 7)
        return res
    return web.HTTPFound('/login?err=Invalid Email or Password')

# ----------------- 🔒 SECURE REGISTRATION (WITH OTP) -----------------
@admin_routes.get('/register')
async def register_user(req):
    role, _ = await get_auth(req)
    if role: return web.HTTPFound('/dashboard')
    
    content = '<form action="/api/register_step1" method="post"><input type="number" name="tg_id" placeholder="Telegram ID (e.g. 123456)" required><input type="email" name="email" placeholder="Email Address" required><input type="password" name="password" placeholder="Create Password" required><button class="submit-btn" type="submit">Send OTP via Telegram</button></form><p style="margin-top:15px; font-size:14px; color:var(--muted)">Already have an account? <a href="/login" style="color:#fff; text-decoration:none">Sign In</a></p>'
    return build_page("Sign Up", f'<div class="login-bg">{form_wrapper("Create Account", content, req.query.get("err",""))}</div>', "login-bg")

@admin_routes.post('/api/register_step1')
async def api_register_step1(req):
    d = await req.post()
    try: tg_id = int(d.get('tg_id'))
    except: return web.HTTPFound('/register?err=Invalid Telegram ID')
    email = d.get('email')
    password = d.get('password')
    
    if await web_db.col.find_one({"$or": [{"tg_id": tg_id}, {"email": email}]}):
        return web.HTTPFound('/register?err=Telegram ID or Email already registered!')
        
    otp = str(random.randint(100000, 999999))
    
    temp.REG_PENDING[tg_id] = {
        'email': email, 
        'password': password, 
        'otp': otp, 
        'expiry': time.time() + 300 
    }
    
    msg_text = f"🔐 **Web Registration Verification**\n\nSomeone is trying to link your Telegram ID to this email: `{email}`\n\n**Your OTP is:** `{otp}`\n\n_Valid for 5 mins. If this wasn't you, just ignore this message._"
    try:
        await temp.BOT.send_message(tg_id, msg_text)
    except Exception:
        return web.HTTPFound('/register?err=Failed to send OTP. Please start the Bot first.')
        
    return web.HTTPFound(f'/verify_registration?tg_id={tg_id}')

@admin_routes.get('/verify_registration')
async def verify_registration_page(req):
    tg_id = req.query.get('tg_id', '')
    if not tg_id: return web.HTTPFound('/register')
    
    content = f'<p style="color:var(--muted); margin-bottom:15px; font-size:14px;">We sent a 6-digit OTP to your Telegram bot.</p><form action="/api/register_step2" method="post"><input type="hidden" name="tg_id" value="{tg_id}"><input type="text" name="otp" placeholder="Enter 6-digit OTP" required><button class="submit-btn" type="submit">Verify & Create Account</button></form>'
    return build_page("Verify Registration", f'<div class="login-bg">{form_wrapper("Verify OTP", content, req.query.get("err",""))}</div>', "login-bg")

@admin_routes.post('/api/register_step2')
async def api_register_step2(req):
    d = await req.post()
    try: tg_id = int(d.get('tg_id'))
    except: return web.HTTPFound('/register?err=Invalid Request')
    otp = d.get('otp')
    
    if tg_id not in getattr(temp, 'REG_PENDING', {}):
        return web.HTTPFound('/register?err=Session expired. Try again.')
        
    pending = temp.REG_PENDING[tg_id]
    
    if time.time() > pending['expiry']:
        del temp.REG_PENDING[tg_id]
        return web.HTTPFound('/register?err=OTP Expired. Please restart registration.')
        
    if pending['otp'] != otp:
        return web.HTTPFound(f'/verify_registration?tg_id={tg_id}&err=Invalid OTP')
        
    success, msg = await web_db.create_user(tg_id, pending['email'], pending['password'])
    del temp.REG_PENDING[tg_id]
    
    if success:
        try:
            await temp.BOT.send_message(tg_id, "✅ **Web Account Successfully Created!**\n*You can now log in to the website.*")
        except: pass
        return web.HTTPFound('/login?msg=Account created successfully! Please login.')
        
    return web.HTTPFound(f'/register?err={msg}')

# ----------------- OTP & FORGOT PASSWORD -----------------
@admin_routes.get('/forgot_password')
async def forgot_password(req):
    content = '<p style="color:var(--muted); margin-bottom:15px; font-size:14px;">Enter your Telegram ID to receive an OTP.</p><form action="/api/forgot_password" method="post"><input type="number" name="tg_id" placeholder="Telegram ID" required><button class="submit-btn" type="submit">Send OTP to Telegram</button></form><hr style="border:0; border-top:1px solid var(--border); margin:25px 0;"><form action="/api/reset_password" method="post"><input type="number" name="tg_id" placeholder="Confirm TG ID" required><input type="text" name="otp" placeholder="Enter OTP" required><input type="password" name="new_password" placeholder="New Password" required><button class="submit-btn" style="background:#333;" type="submit">Update Password</button></form>'
    return build_page("Reset Password", f'<div class="login-bg">{form_wrapper("Reset Password", content, req.query.get("err",""), req.query.get("msg",""))}</div>', "login-bg")

@admin_routes.post('/api/forgot_password')
async def api_forgot_password(req):
    try: tg_id = int((await req.post()).get('tg_id'))
    except: return web.HTTPFound('/forgot_password?err=Invalid Telegram ID')
    
    otp = await web_db.generate_otp(tg_id)
    if otp:
        try:
            await temp.BOT.send_message(tg_id, f"🔐 **Fast Finder Password Reset**\n\nYour Password Reset OTP is: `{otp}`\n\nValid for 10 minutes. Do not share!")
            return web.HTTPFound('/forgot_password?msg=OTP sent to your Telegram!')
        except: return web.HTTPFound('/forgot_password?err=Error sending OTP. Have you started the bot?')
    return web.HTTPFound('/forgot_password?err=Telegram ID not registered!')

@admin_routes.post('/api/reset_password')
async def api_reset_password(req):
    d = await req.post()
    try: tg_id = int(d.get('tg_id'))
    except: return web.HTTPFound('/forgot_password?err=Invalid Input')
    
    if await web_db.verify_otp_and_reset(tg_id, d.get('otp'), d.get('new_password')):
        return web.HTTPFound('/login?msg=Password updated successfully! Please login.')
    return web.HTTPFound('/forgot_password?err=Invalid or Expired OTP.')

# ----------------- DASHBOARD & PROFILE -----------------
@admin_routes.get('/dashboard')
async def dash(req):
    role, tg_id = await get_auth(req)
    if not role: return web.HTTPFound('/login')

    if role == 'user':
        mp = await user_db.get_plan(tg_id)
        if not mp.get("premium"):
            return web.HTTPFound('/premium_expired')

    b = '<div class="search-zone"><div class="search-row"><div class="filter-tabs"><button class="ftab active" data-col="all" onclick="setCol(this)">All</button><button class="ftab" data-col="primary" onclick="setCol(this)">Primary</button><button class="ftab" data-col="cloud" onclick="setCol(this)">Cloud</button><button class="ftab" data-col="archive" onclick="setCol(this)">Archive</button></div><div class="search-wrap"><span class="s-icon">&#9906;</span><input class="search-input" id="q" placeholder="Titles, people, genres"></div><button class="search-btn" onclick="doSearch(0)">Search</button></div></div><div class="main" style="padding-top:20px;"><div class="results-info" id="resInfo"><span class="results-count" id="resCount"></span></div><div id="results"><div class="empty"><div class="empty-icon">&#8981;</div><p>Find your favorite movies and TV shows.</p></div></div><div class="pagination" id="pageBox"><button class="pg-btn" id="pBtn" onclick="prev()" disabled>Previous</button><span class="pg-info" id="pgInfo">Page 1</span><button class="pg-btn" id="nBtn" onclick="next()">Next</button></div></div><div class="toast" id="toast"></div>'
    return build_page("Home - Fast Finder", b, "dash", role)

@admin_routes.get('/profile')
async def profile_page(req):
    role, tg_id = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    
    user = await web_db.col.find_one({"tg_id": tg_id})
    email = user.get('email', '') if user else ''
    err, msg = req.query.get('err',''), req.query.get('msg','')
    
    mp = await user_db.get_plan(tg_id)
    if role == 'admin':
        status_text = "👑 Admin (Lifetime Access)"
        exp_text = "Never (Lifetime)"
        status_color = "#e50914" 
    else:
        status_text = "💎 Premium User"
        exp_text = mp.get('expire', 'Unknown')
        status_color = "#3399ff" 

    e = f'<div class="err-box">{err}</div>' if err else ""
    m = f'<div class="success-box">{msg}</div>' if msg else ""
    
    b = f'''<div class="main" style="padding-top:40px; max-width:700px;">
        <div class="scard">{e}{m}
        <h2 style="margin-bottom:25px;">Account Settings</h2>
        
        <div style="background:var(--bg3); padding:15px; border-radius:4px; margin-bottom:25px; border-left:4px solid {status_color};">
            <div style="font-size:12px; color:var(--muted); margin-bottom:5px;">Account Status</div>
            <div style="font-size:18px; font-weight:700; color:{status_color}; margin-bottom:10px;">{status_text}</div>
            <div style="font-size:12px; color:var(--muted); margin-bottom:2px;">Premium Expires:</div>
            <div style="font-size:15px; font-weight:500;">{exp_text}</div>
        </div>

        <form action="/api/update_profile" method="post">
            <div class="scard-label">Telegram ID (Non-changeable)</div>
            <input type="text" value="{tg_id}" class="search-input" style="margin-bottom:20px; opacity:0.6" disabled>
            <div class="scard-label">Email Address</div>
            <input type="email" name="new_email" value="{email}" class="search-input" style="margin-bottom:20px;" required>
            <div class="scard-label">New Password (Leave blank to keep current)</div>
            <input type="password" name="new_pass" placeholder="Enter New Password" class="search-input" style="margin-bottom:30px;">
            <button class="search-btn" style="width:100%" type="submit">Save Changes</button>
        </form>
        </div>
    </div>'''
    return build_page("Profile - Fast Finder", b, "profile", role)

@admin_routes.post('/api/update_profile')
async def update_profile(req):
    role, tg_id = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    
    d = await req.post()
    await web_db.update_profile(tg_id, d.get('new_email'), d.get('new_pass') if d.get('new_pass') else None)
    return web.HTTPFound('/profile?msg=Profile Updated Successfully!')

@admin_routes.get('/premium_expired')
async def premium_expired(req):
    role, tg_id = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    
    content = f'<div style="text-align:center;"><div style="font-size:50px; margin-bottom:15px;">⏳</div><p style="color:var(--muted); margin-bottom:30px;">Your access to Fast Finder Web has expired. Please renew your plan via our Telegram Bot.</p><div class="scard red" style="text-align:left; margin-bottom:25px; padding:15px;"><div class="scard-label">How to Renew?</div><div class="scard-sub" style="color:#fff">1. Go to Telegram Bot</div><div class="scard-sub" style="color:#fff">2. Use command <b>/plan</b></div><div class="scard-sub" style="color:#fff">3. Pay & Activate instantly</div></div><a href="https://t.me/{temp.U_NAME}" class="submit-btn" style="text-decoration:none; display:block;">Open Telegram Bot</a><a href="/logout" style="display:block; margin-top:20px; color:var(--muted); text-decoration:none;">Sign Out</a></div>'
    return build_page("Premium Expired", f'<div class="login-bg">{form_wrapper("Premium Expired", content)}</div>', "login-bg")

@admin_routes.get('/stats')
async def stats(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.HTTPFound('/dashboard')
    
    try: s = await db_count_documents(); s = s if isinstance(s, dict) else {'total':s,'primary':s,'cloud':0,'archive':0}
    except: s = {'total':0,'primary':0,'cloud':0,'archive':0}
    try: u = await user_db.total_users_count()
    except: u = 0
    
    b = f'<div class="main" style="padding-top:40px;"><div class="big-stat"><div class="big-stat-val">{s.get("total",0):,}</div><div class="big-stat-label">Total Titles Available</div></div><div class="stats-row"><div class="scard red"><div class="scard-label">Movies</div><div class="scard-val">{s.get("primary",0):,}</div><div class="scard-sub">Primary source</div></div><div class="scard white"><div class="scard-label">Series</div><div class="scard-val">{s.get("cloud",0):,}</div><div class="scard-sub">Cloud storage</div></div><div class="scard grey"><div class="scard-label">Archive</div><div class="scard-val">{s.get("archive",0):,}</div><div class="scard-sub">Backup library</div></div><div class="scard red"><div class="scard-label">Bot Profiles</div><div class="scard-val">{u:,}</div><div class="scard-sub">Active watchers</div></div></div></div>'
    return build_page("Stats - Fast Finder", b, "stats", role)

@admin_routes.get('/logout')
async def logout(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and s_user in temp.USER_SESSIONS: del temp.USER_SESSIONS[s_user]
    
    res = web.HTTPFound('/login')
    res.del_cookie('user_session')
    return res
