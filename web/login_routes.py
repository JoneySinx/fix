import uuid, random, time, logging
from aiohttp import web
from web.web_assets import build_page, form_wrapper
from utils import temp
from database.users_chats_db import web_db

logger = logging.getLogger(__name__)
login_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────────────
#  ASSETS & HELPERS (COMPRESSED)
# ─────────────────────────────────────────────────────────────────
_AUTH_CSS = """<style>
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:88px 16px 28px;position:relative;}
.login-wrap::before{content:'';position:fixed;top:-180px;left:50%;transform:translateX(-50%);width:480px;height:480px;border-radius:50%;background:radial-gradient(circle,rgba(229,9,20,.1) 0%,transparent 70%);pointer-events:none;z-index:0;}
.login-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:36px 32px;width:100%;max-width:420px;box-shadow:0 24px 64px rgba(0,0,0,.42);position:relative;z-index:1;}
.light .login-card{box-shadow:0 8px 40px rgba(0,0,0,.1);}
.login-card h2{font-size:22px;font-weight:700;margin-bottom:6px;color:var(--text);}
.lc-sub{font-size:14px;color:var(--muted);margin-bottom:22px;}
.err-box{background:rgba(229,9,20,.1);border:1px solid rgba(229,9,20,.3);border-radius:8px;padding:10px 14px;font-size:13px;color:#ff6b6b;margin-bottom:16px;}
.success-box{background:rgba(0,184,148,.1);border:1px solid rgba(0,184,148,.3);border-radius:8px;padding:10px 14px;font-size:13px;color:#00b894;margin-bottom:16px;}
.fg{display:flex;flex-direction:column;gap:14px;}
.flabel{display:block;font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;}
.iwrap{position:relative;}
.iico{position:absolute;left:13px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none;display:flex;align-items:center;font-size:14px;}
input[type=email],input[type=password],input[type=text],input[type=number]{width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:11px 14px 11px 38px;font-size:14px;color:var(--text);font-family:'DM Sans',sans-serif;outline:none;transition:border-color .2s;-webkit-appearance:none;}
input:focus{border-color:var(--accent);}
input::placeholder{color:#4a4a5a;} .light input::placeholder{color:#9a9aaa;}
input[type=number]::-webkit-inner-spin-button,input[type=number]::-webkit-outer-spin-button{-webkit-appearance:none;}
.pw-wrap input{padding-right:42px;}
.pwtog{position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--muted);cursor:pointer;padding:4px;border-radius:6px;display:flex;align-items:center;overflow:hidden;transition:color .2s;}
.pwtog:active{transform:translateY(-50%) scale(.88);}
.forgot-lnk{text-align:right;margin-top:-6px;} .forgot-lnk a{font-size:13px;color:var(--muted);text-decoration:none;transition:color .2s;} .forgot-lnk a:hover{color:var(--text);}
.sbtn{width:100%;padding:12px;border-radius:10px;background:var(--accent);border:none;color:#fff;font-size:14px;font-weight:700;cursor:pointer;font-family:'DM Sans',sans-serif;position:relative;overflow:hidden;transition:transform .12s ease,background .2s;margin-top:4px;}
.sbtn:hover{background:var(--accent-hover);} .sbtn:active{transform:scale(.97);} .sbtn:disabled{opacity:.4;cursor:not-allowed;transform:none;}
.gbtn{padding:11px 16px;border-radius:10px;background:rgba(229,9,20,.12);border:1px solid rgba(229,9,20,.28);color:var(--accent);font-size:13px;font-weight:700;cursor:pointer;font-family:'DM Sans',sans-serif;white-space:nowrap;position:relative;overflow:hidden;transition:transform .12s ease,background .2s;}
.gbtn:hover{background:rgba(229,9,20,.22);} .gbtn:active{transform:scale(.97);}
.sbtn .rpl,.gbtn .rpl{position:absolute;border-radius:50%;background:rgba(255,255,255,.28);width:8px;height:8px;pointer-events:none;transform:translate(-50%,-50%) scale(0);animation:_rpl .6s ease-out forwards;}
@keyframes _rpl{to{transform:translate(-50%,-50%) scale(30);opacity:0;}}
.cdivider{border:none;border-top:1px solid var(--border);margin:20px 0;}
.cfooter{text-align:center;font-size:14px;color:var(--muted);} .cfooter a{color:var(--accent);text-decoration:none;font-weight:600;}
.ibanner{background:rgba(229,9,20,.08);border:1px solid rgba(229,9,20,.22);border-radius:10px;padding:12px 14px;margin-bottom:20px;display:flex;gap:10px;align-items:flex-start;font-size:12px;color:var(--muted);line-height:1.5;}
.ibanner svg{flex-shrink:0;margin-top:2px;color:var(--accent);}
.steprow{display:flex;align-items:center;gap:8px;margin-bottom:10px;}
.stpbadge{width:20px;height:20px;border-radius:50%;background:var(--bg3);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:10px;font-weight:700;color:var(--muted);}
.stplabel{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}
.splitrow{display:flex;gap:8px;} .splitrow .iwrap{flex:1;}
.thendiv{display:flex;align-items:center;gap:10px;margin:16px 0;} .thendiv::before,.thendiv::after{content:'';flex:1;height:1px;background:var(--border);} .thendiv span{font-size:11px;color:var(--bg4);}
.otprow{display:flex;gap:8px;justify-content:center;margin-bottom:14px;}
.otpbox{width:44px;height:52px;text-align:center;font-size:20px;font-weight:700;background:var(--bg3);border:1px solid var(--border);border-radius:10px;color:var(--text);font-family:'DM Sans',sans-serif;outline:none;transition:all .2s;padding:0;}
.otpbox:focus{border-color:rgba(229,9,20,.6);} .otpbox.filled{background:rgba(229,9,20,.12);border-color:rgba(229,9,20,.6);color:var(--accent);}
.otpprog{display:flex;align-items:center;gap:8px;margin-bottom:14px;}
.otpbar{flex:1;height:3px;background:var(--bg3);border-radius:2px;overflow:hidden;}
.otpbarfill{height:100%;background:var(--accent);border-radius:2px;transition:width .3s;}
.otpcount{font-size:11px;color:var(--muted);}
</style>"""

_RIPPLE_JS = """<script>
document.addEventListener('click',function(e){
  var b=e.target.closest('.sbtn,.gbtn'); if(!b||b.disabled)return;
  var r=document.createElement('span'); r.className='rpl'; var rc=b.getBoundingClientRect();
  r.style.left=(e.clientX-rc.left)+'px'; r.style.top=(e.clientY-rc.top)+'px'; b.appendChild(r);
  setTimeout(function(){r.remove();},650);
});
</script>"""

_svg_mail = lambda: '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207"/></svg>'
_svg_lock = lambda: '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>'
_svg_eye = lambda: '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>'

# ───────────────────────────────────────────────
#  LOGIN & REGISTER ROUTES
# ───────────────────────────────────────────────

@login_routes.get('/login')
async def login_user(req):
    content = f'{_AUTH_CSS}<p class="lc-sub">Sign in to your dashboard</p><form action="/api/login" method="post"><div class="fg"><div><label class="flabel">Email Address</label><div class="iwrap"><span class="iico">{_svg_mail()}</span><input type="email" name="email" placeholder="you@example.com" required></div></div><div><label class="flabel">Password</label><div class="iwrap pw-wrap"><span class="iico">{_svg_lock()}</span><input type="password" name="password" id="loginPw" placeholder="••••••••" required><button type="button" class="pwtog" onclick="var f=document.getElementById(\'loginPw\');f.type=f.type===\'password\'?\'text\':\'password\';">{_svg_eye()}</button></div></div><div class="forgot-lnk"><a href="/forgot_password">Forgot password?</a></div><button class="sbtn" type="submit">Sign In</button></div></form><hr class="cdivider"><p class="cfooter">Don\'t have an account? <a href="/register">Create account</a></p>{_RIPPLE_JS}'
    return build_page("Sign In", form_wrapper("Welcome back", content, req.query.get('err', ''), req.query.get('msg', '')))

@login_routes.post('/api/login')
async def api_login_user(req):
    d = await req.post()
    if user := await web_db.verify_login(d.get('email'), d.get('password')):
        s = str(uuid.uuid4())
        if not hasattr(temp, 'USER_SESSIONS'): temp.USER_SESSIONS = {}
        temp.USER_SESSIONS[s] = {'tg_id': user['tg_id'], 'expiry': time.time() + 604800}
        res = web.HTTPFound('/dashboard')
        res.set_cookie('user_session', s, max_age=604800)
        return res
    return web.HTTPFound('/login?err=Invalid email or password. Please try again.')

@login_routes.get('/register')
async def register_user(req):
    content = f'{_AUTH_CSS}<p class="lc-sub">Link your Telegram account to get started</p><div class="ibanner"><svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Start the bot on Telegram first. A 6-digit OTP will be sent to your DM.</div><form action="/api/register_step1" method="post"><div class="fg"><div><label class="flabel">Telegram ID</label><div class="iwrap"><span class="iico">📱</span><input type="number" name="tg_id" placeholder="e.g. 123456789" required></div></div><div><label class="flabel">Email Address</label><div class="iwrap"><span class="iico">{_svg_mail()}</span><input type="email" name="email" placeholder="you@example.com" required></div></div><div><label class="flabel">Create Password</label><div class="iwrap"><span class="iico">{_svg_lock()}</span><input type="password" name="password" placeholder="••••••••" required></div></div><button class="sbtn" type="submit">Send OTP via Telegram</button></div></form><hr class="cdivider"><p class="cfooter">Already have an account? <a href="/login">Sign in</a></p>{_RIPPLE_JS}'
    return build_page("Create Account", form_wrapper("Create account", content, req.query.get('err', '')))

@login_routes.post('/api/register_step1')
async def api_register_step1(req):
    d = await req.post()
    try: tg_id = int(d.get('tg_id'))
    except: return web.HTTPFound('/register?err=Invalid Telegram ID')
    email, password = d.get('email'), d.get('password')
    if await web_db.col.find_one({"$or": [{"tg_id": tg_id}, {"email": email}]}, {"_id": 1}):
        return web.HTTPFound('/register?err=Telegram ID or Email is already registered!')
    otp = str(random.randint(100000, 999999))
    if not hasattr(temp, 'REG_PENDING'): temp.REG_PENDING = {}
    temp.REG_PENDING[tg_id] = {'email': email, 'password': password, 'otp': otp, 'expiry': time.time() + 300}
    try:
        await temp.BOT.send_message(tg_id, f"🔐 **Web Registration Verification**\n\nSomeone is trying to link your Telegram ID to: `{email}`\n\n**Your OTP is:** `{otp}`\n\n_Valid for 5 minutes._")
    except:
        return web.HTTPFound('/register?err=Failed to send OTP. Please start the Bot first in Telegram.')
    return web.HTTPFound(f'/verify_registration?tg_id={tg_id}')

# ───────────────────────────────────────────────
#  VERIFY OTP & PASSWORD RESET
# ───────────────────────────────────────────────

@login_routes.get('/verify_registration')
async def verify_registration_page(req):
    tg_id = req.query.get('tg_id', '')
    if not tg_id: return web.HTTPFound('/register')
    boxes = "".join([f'<input class="otpbox" type="text" inputmode="numeric" maxlength="1" id="o{i}" oninput="otpNext(this,{i})" onkeydown="otpBack(event,{i})">' for ibox in range(6)])
    content = f'{_AUTH_CSS}<p class="lc-sub">Check your Telegram DM for a 6-digit code</p><form action="/api/register_step2" method="post" id="otpForm"><input type="hidden" name="tg_id" value="{tg_id}"><div class="otprow">{"".join([f`<input class="otpbox" type="text" inputmode="numeric" maxlength="1" id="o{i}" oninput="otpNext(this,{i})" onkeydown="otpBack(event,{i})">` for i in range(6)])}</div><div class="otpprog"><div class="otpbar"><div class="otpbarfill" id="otpBar" style="width:0%"></div></div><span class="otpcount" id="otpCount">0 / 6</span></div><input type="hidden" name="otp" id="otpHidden"><button class="sbtn" type="submit" id="otpBtn" disabled style="opacity:.4;cursor:not-allowed;">Verify &amp; Create Account</button></form><p style="text-align:center;font-size:12px;color:var(--muted);margin-top:14px;">Didn\'t receive OTP? <a href="/register" style="color:var(--accent);text-decoration:none;">Resend</a> &nbsp;&middot;&nbsp; <a href="/register" style="color:var(--muted);text-decoration:none;">Go back</a></p><p style="text-align:center;font-size:11px;color:var(--muted);margin-top:6px;opacity:.6;">OTP expires in 5 minutes</p><script>function otpNext(el,i){{if(!/^\d?$/.test(el.value)){{el.value=\'\';return;}}el.classList.toggle(\'filled\',el.value!==\'\');syncOtp();if(el.value&&i<5)document.getElementById(\'o\'+(i+1)).focus();}}function otpBack(e,i){{if(e.key===\'Backspace\'&&!document.getElementById(\'o\'+i).value&&i>0)document.getElementById(\'o\'+(i-1)).focus();}}function syncOtp(){{var val=\'\',count=0;for(var i=0;i<6;i++){{var v=document.getElementById(\'o\'+i).value;val+=v;if(v)count++;}}document.getElementById(\'otpHidden\').value=val;document.getElementById(\'otpBar\').style.width=(count/6*100)+\'%\';document.getElementById(\'otpCount\').innerText=count+\' / 6\';var btn=document.getElementById(\'otpBtn\');btn.disabled=count<6;btn.style.opacity=count<6?\'.4\':\'1\';btn.style.cursor=count<6?\'not-allowed\':\'pointer\';}}document.getElementById(\'o0\').focus();</script>{_RIPPLE_JS}'
    return build_page("Verify OTP", form_wrapper("Verify OTP", content, req.query.get('err', '')))

@login_routes.post('/api/register_step2')
async def api_register_step2(req):
    d = await req.post()
    try: tg_id = int(d.get('tg_id'))
    except: return web.HTTPFound('/register?err=Invalid Request')
    if tg_id not in getattr(temp, 'REG_PENDING', {}): return web.HTTPFound('/register?err=Session expired. Please try again.')
    pending = temp.REG_PENDING[tg_id]
    if time.time() > pending['expiry']:
        del temp.REG_PENDING[tg_id]
        return web.HTTPFound('/register?err=OTP expired. Please restart registration.')
    if pending['otp'] != d.get('otp'):
        return web.HTTPFound(f'/verify_registration?tg_id={tg_id}&err=Invalid OTP. Please try again.')
    success, msg = await web_db.create_user(tg_id, pending['email'], pending['password'])
    del temp.REG_PENDING[tg_id]
    return web.HTTPFound('/login?msg=Account created successfully! Please sign in.' if success else f'/register?err={msg}')

@login_routes.get('/forgot_password')
async def forgot_password(req):
    content = f'{_AUTH_CSS}<p class="lc-sub">Enter your Telegram ID to receive an OTP, then reset your password below.</p><div class="steprow"><div class="stpbadge">1</div><span class="stplabel">Send OTP to Telegram</span></div><form action="/api/forgot_password" method="post"><div class="splitrow" style="margin-bottom:20px;"><div class="iwrap"><span class="iico">📱</span><input type="number" name="tg_id" placeholder="Your Telegram ID" required></div><button class="gbtn" type="submit">Send OTP</button></div></form><div class="thendiv"><span>then</span></div><div class="steprow"><div class="stpbadge">2</div><span class="stplabel" style="color:var(--bg4);">Enter OTP &amp; New Password</span></div><form action="/api/reset_password" method="post"><div class="fg"><div><div class="iwrap"><span class="iico">📱</span><input type="number" name="tg_id" placeholder="Telegram ID" required></div></div><div><div class="iwrap"><span class="iico"><svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/></svg></span><input type="text" name="otp" placeholder="6-digit OTP" required></div></div><div><div class="iwrap pw-wrap"><span class="iico">{_svg_lock()}</span><input type="password" name="new_password" id="resetPw" placeholder="New password" required><button type="button" class="pwtog" onclick="var f=document.getElementById(\'resetPw\');f.type=f.type===\'password\'?\'text\':\'password\';">{_svg_eye()}</button></div></div><button class="sbtn" type="submit">Reset Password</button></div></form><hr class="cdivider"><p class="cfooter"><a href="/login" style="color:var(--muted);">&#8592; Back to Sign In</a></p>{_RIPPLE_JS}'
    return build_page("Reset Password", form_wrapper("Reset Password", content, req.query.get('err', ''), req.query.get('msg', '')))

@login_routes.post('/api/forgot_password')
async def api_forgot_password(req):
    try: tg_id = int((await req.post()).get('tg_id'))
    except: return web.HTTPFound('/forgot_password?err=Invalid Telegram ID')
    if otp := await web_db.generate_otp(tg_id):
        try:
            await temp.BOT.send_message(tg_id, f"🔐 **Fast Finder Password Reset**\n\nYour OTP is: `{otp}`\n\nValid for 10 minutes. Do not share!")
            return web.HTTPFound('/forgot_password?msg=OTP sent to your Telegram!')
        except:
            return web.HTTPFound('/forgot_password?err=Error sending OTP. Have you started the bot?')
    return web.HTTPFound('/forgot_password?err=Telegram ID not registered!')

@login_routes.post('/api/reset_password')
async def api_reset_password(req):
    d = await req.post()
    try: tg_id = int(d.get('tg_id'))
    except: return web.HTTPFound('/forgot_password?err=Invalid Input')
    if await web_db.verify_otp_and_reset(tg_id, d.get('otp'), d.get('new_password')):
        return web.HTTPFound('/login?msg=Password updated successfully! Please sign in.')
    return web.HTTPFound('/forgot_password?err=Invalid or expired OTP.')
