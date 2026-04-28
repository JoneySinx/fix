from aiohttp import web
import time
import uuid
from info import ADMIN_USERNAME, ADMIN_PASSWORD
from utils import temp

admin_routes = web.RouteTableDef()

# ─────────────────────────
# 1. LOGIN PAGE (TOKEN VERIFICATION)
# ─────────────────────────
@admin_routes.get('/admin')
async def admin_login_page(request):
    token = request.query.get('token')

    # अगर temp में ADMIN_TOKENS नहीं है, तो बना लें (एरर से बचने के लिए)
    if not hasattr(temp, 'ADMIN_TOKENS'):
        temp.ADMIN_TOKENS = {}

    # सुरक्षा परत 1: टोकन चेक करें
    if not token or token not in temp.ADMIN_TOKENS:
        return web.Response(text="❌ Invalid or Missing Token! Generate a new link from Telegram.", status=403)

    if time.time() > temp.ADMIN_TOKENS[token]:
        del temp.ADMIN_TOKENS[token]
        return web.Response(text="⏳ Token Expired! Please generate a new link via Telegram.", status=403)

    # अगर टोकन सही है, तो लॉगिन पेज दिखाएं
    html = f"""
    <html>
        <head>
            <title>Admin Login</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .login-box {{ background: white; padding: 40px 30px; border-radius: 12px; box-shadow: 0px 8px 20px rgba(0,0,0,0.1); text-align: center; width: 100%; max-width: 320px; }}
                h2 {{ margin-bottom: 20px; color: #333; }}
                input {{ display: block; width: 100%; box-sizing: border-box; margin: 15px 0; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; outline: none; }}
                input:focus {{ border-color: #0088cc; }}
                button {{ background: #0088cc; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; margin-top: 10px; transition: background 0.3s; }}
                button:hover {{ background: #006699; }}
            </style>
        </head>
        <body>
            <div class="login-box">
                <h2>🔒 Admin Login</h2>
                <form action="/login" method="post">
                    <input type="hidden" name="token" value="{token}">
                    <input type="text" name="username" placeholder="Enter Username" required>
                    <input type="password" name="password" placeholder="Enter Password" required>
                    <button type="submit">Login</button>
                </form>
            </div>
        </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

# ─────────────────────────
# 2. PASSWORD VERIFICATION POST REQUEST
# ─────────────────────────
@admin_routes.post('/login')
async def admin_login_post(request):
    data = await request.post()
    token = data.get('token')
    username = data.get('username')
    password = data.get('password')

    if not hasattr(temp, 'ADMIN_TOKENS'):
        temp.ADMIN_TOKENS = {}
    if not hasattr(temp, 'ADMIN_SESSIONS'):
        temp.ADMIN_SESSIONS = {}

    # फिर से टोकन चेक करें
    if not token or token not in temp.ADMIN_TOKENS or time.time() > temp.ADMIN_TOKENS[token]:
        return web.Response(text="⏳ Token Expired or Invalid!", status=403)

    # सुरक्षा परत 2: यूज़रनेम और पासवर्ड चेक करें
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # लॉगिन सफल! एक सेशन ID बनाएँ
        session_id = str(uuid.uuid4())
        
        # सेशन भी उसी समय एक्सपायर होगा जब टोकन एक्सपायर होना था
        temp.ADMIN_SESSIONS[session_id] = temp.ADMIN_TOKENS[token]
        
        # सुरक्षा के लिए टोकन डिलीट कर दें ताकि वह दोबारा इस्तेमाल न हो सके
        del temp.ADMIN_TOKENS[token]

        # डैशबोर्ड पर भेजें और कुकी (Cookie) सेट करें
        response = web.HTTPFound('/dashboard')
        response.set_cookie('admin_session', session_id, max_age=3600)
        return response
    else:
        error_html = f"""
        <html>
            <body style="font-family: Arial; text-align: center; margin-top: 50px;">
                <h2 style="color: red;">❌ Invalid Username or Password!</h2>
                <br><a href='/admin?token={token}' style="text-decoration: none; background: #0088cc; color: white; padding: 10px 20px; border-radius: 5px;">Try Again</a>
            </body>
        </html>
        """
        return web.Response(text=error_html, content_type='text/html', status=401)

# ─────────────────────────
# 3. THE SECURE DASHBOARD
# ─────────────────────────
@admin_routes.get('/dashboard')
async def admin_dashboard(request):
    # ब्राउज़र की कुकी से सेशन ID निकालें
    session_id = request.cookies.get('admin_session')

    if not hasattr(temp, 'ADMIN_SESSIONS'):
        temp.ADMIN_SESSIONS = {}

    # सेशन वेरिफिकेशन
    if not session_id or session_id not in temp.ADMIN_SESSIONS:
        return web.Response(text="❌ Unauthorized Access! Please login via Telegram link.", status=403)

    if time.time() > temp.ADMIN_SESSIONS[session_id]:
        del temp.ADMIN_SESSIONS[session_id]
        return web.Response(text="⏳ Session Expired! Please generate a new link from Telegram.", status=403)

    # असली डैशबोर्ड HTML
    html = """
    <html>
        <head>
            <title>Admin Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #eef2f3; margin: 0; }
                .container { max-width: 800px; margin: auto; }
                .header { background: #0088cc; color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                .card { background: white; padding: 20px; margin-top: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
                ul { line-height: 1.8; font-size: 16px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">👋 Welcome to Admin Dashboard</h1>
                </div>
                <div class="card">
                    <h3 style="margin-top: 0; color: #333;">🔒 Security Status</h3>
                    <p>✅ Double Layer Verified (Magic Link + Credentials)</p>
                    <p style="color: green;">Your session is active and completely secure.</p>
                </div>
                <div class="card">
                    <h3 style="margin-top: 0; color: #333;">🚀 Features (Coming Soon)</h3>
                    <ul>
                        <li>📊 View Real-time Database Stats</li>
                        <li>🔍 Search, Edit & Delete Movies</li>
                        <li>💎 Manage Premium Users & Subscriptions</li>
                        <li>⚙️ Update Bot Settings</li>
                    </ul>
                </div>
            </div>
        </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')
