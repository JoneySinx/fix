import gc
from aiohttp import web
from web.web_assets import build_page, form_wrapper
from utils import temp

premium_routes = web.RouteTableDef()

@premium_routes.get('/premium_expired')
async def premium_expired(req):
    content = (
        '<div style="text-align:center;">'
        '<div style="font-size:50px;margin-bottom:15px;">⏳</div>'
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
    gc.collect()
    return build_page("Premium Expired", form_wrapper("Premium Expired", content), "login-bg")
