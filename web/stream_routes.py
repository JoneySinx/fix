import math
import secrets
import mimetypes
import logging
from urllib.parse import quote
from aiohttp import web
from info import BIN_CHANNEL
from utils import temp
from web.utils.custom_dl import TGCustomYield, chunk_size, offset_fix
from web.utils.render_template import media_watch

routes = web.RouteTableDef()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🏠 ROOT ROUTE (FAST FINDER UI — ULTRA PREMIUM)
# ─────────────────────────────────────────────
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    bot_username = getattr(temp, 'U_NAME', 'AutoFilterBot')

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Fast Finder — Stream & Download</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:        #060612;
      --surface:   rgba(255,255,255,0.04);
      --border:    rgba(255,255,255,0.08);
      --accent1:   #6c63ff;
      --accent2:   #00e5ff;
      --accent3:   #ff6584;
      --text:      #e8e8f0;
      --muted:     #6b6b8a;
      --glow1:     rgba(108,99,255,0.35);
      --glow2:     rgba(0,229,255,0.25);
    }}

    html, body {{ height: 100%; overflow: hidden; }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'DM Sans', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    /* ── CANVAS BACKGROUND ── */
    #canvas {{
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
    }}

    /* ── NOISE OVERLAY ── */
    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
      pointer-events: none;
      z-index: 1;
      opacity: 0.5;
    }}

    /* ── RADIAL GLOW BLOBS ── */
    .blob {{
      position: fixed;
      border-radius: 50%;
      filter: blur(100px);
      pointer-events: none;
      z-index: 0;
      animation: blobDrift 18s ease-in-out infinite alternate;
    }}
    .blob-1 {{ width: 520px; height: 520px; background: var(--glow1); top: -180px; left: -150px; animation-duration: 20s; }}
    .blob-2 {{ width: 400px; height: 400px; background: var(--glow2); bottom: -120px; right: -100px; animation-duration: 25s; animation-delay: -8s; }}
    .blob-3 {{ width: 300px; height: 300px; background: rgba(255,101,132,0.15); top: 50%; left: 55%; animation-duration: 15s; animation-delay: -4s; }}

    @keyframes blobDrift {{
      from {{ transform: translate(0, 0) scale(1); }}
      to   {{ transform: translate(40px, 30px) scale(1.12); }}
    }}

    /* ── ADMIN BUTTON ── */
    .admin-btn {{
      position: fixed;
      top: 22px;
      right: 24px;
      z-index: 100;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 18px;
      border-radius: 50px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--muted);
      font-family: 'DM Sans', sans-serif;
      font-size: 13px;
      font-weight: 500;
      text-decoration: none;
      backdrop-filter: blur(16px);
      transition: all 0.3s ease;
    }}
    .admin-btn svg {{ width: 15px; height: 15px; }}
    .admin-btn:hover {{
      color: var(--accent2);
      border-color: var(--accent2);
      box-shadow: 0 0 20px rgba(0,229,255,0.2);
    }}

    /* ── MAIN CARD ── */
    .card {{
      position: relative;
      z-index: 10;
      width: 94%;
      max-width: 480px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 48px 40px 40px;
      backdrop-filter: blur(40px);
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.03),
        0 30px 80px rgba(0,0,0,0.6),
        0 0 120px var(--glow1);
      animation: cardIn 0.8s cubic-bezier(0.16,1,0.3,1) both;
    }}

    @keyframes cardIn {{
      from {{ opacity: 0; transform: translateY(32px) scale(0.97); }}
      to   {{ opacity: 1; transform: translateY(0)   scale(1); }}
    }}

    /* ── LOGO BADGE ── */
    .logo-wrap {{
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 28px;
    }}
    .logo-ring {{
      position: relative;
      width: 72px;
      height: 72px;
    }}
    .logo-ring svg {{
      position: absolute;
      inset: 0;
      animation: spinRing 8s linear infinite;
    }}
    @keyframes spinRing {{
      to {{ transform: rotate(360deg); }}
    }}
    .logo-icon {{
      position: absolute;
      inset: 12px;
      background: linear-gradient(135deg, var(--accent1), var(--accent2));
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      box-shadow: 0 0 30px var(--glow1);
    }}

    /* ── HEADING ── */
    .headline {{
      font-family: 'Syne', sans-serif;
      font-weight: 800;
      font-size: 2.4rem;
      line-height: 1.1;
      text-align: center;
      background: linear-gradient(135deg, #ffffff 20%, var(--accent2) 80%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 8px;
      letter-spacing: -0.5px;
    }}
    .sub {{
      text-align: center;
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 36px;
      letter-spacing: 0.2px;
    }}

    /* ── STATS ROW ── */
    .stats {{
      display: flex;
      gap: 12px;
      margin-bottom: 28px;
    }}
    .stat {{
      flex: 1;
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px 10px;
      text-align: center;
    }}
    .stat-num {{
      font-family: 'Syne', sans-serif;
      font-size: 17px;
      font-weight: 700;
      color: var(--accent2);
    }}
    .stat-label {{
      font-size: 10px;
      color: var(--muted);
      margin-top: 2px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    /* ── SEARCH INPUT ── */
    .input-wrap {{
      position: relative;
      margin-bottom: 14px;
    }}
    .input-icon {{
      position: absolute;
      left: 18px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
      transition: color 0.3s;
      pointer-events: none;
    }}
    .input-wrap:focus-within .input-icon {{ color: var(--accent2); }}

    input[type="text"] {{
      width: 100%;
      padding: 16px 20px 16px 50px;
      background: rgba(255,255,255,0.05);
      border: 1.5px solid var(--border);
      border-radius: 50px;
      color: var(--text);
      font-family: 'DM Sans', sans-serif;
      font-size: 15px;
      outline: none;
      transition: border-color 0.3s, box-shadow 0.3s, background 0.3s;
    }}
    input[type="text"]::placeholder {{ color: var(--muted); }}
    input[type="text"]:focus {{
      border-color: var(--accent1);
      background: rgba(108,99,255,0.06);
      box-shadow: 0 0 0 4px rgba(108,99,255,0.12), 0 0 30px rgba(108,99,255,0.1);
    }}

    /* ── SEARCH BUTTON ── */
    .btn {{
      width: 100%;
      padding: 16px;
      border: none;
      border-radius: 50px;
      background: linear-gradient(90deg, var(--accent1) 0%, var(--accent2) 100%);
      color: #fff;
      font-family: 'Syne', sans-serif;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.3px;
      cursor: pointer;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .btn::after {{
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(90deg, transparent 30%, rgba(255,255,255,0.2) 50%, transparent 70%);
      transform: translateX(-100%);
      transition: transform 0.6s ease;
    }}
    .btn:hover {{ transform: translateY(-2px); box-shadow: 0 12px 40px rgba(108,99,255,0.45); }}
    .btn:hover::after {{ transform: translateX(100%); }}
    .btn:active {{ transform: translateY(0); }}

    /* ── TAGS ── */
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 22px;
      justify-content: center;
    }}
    .tag {{
      padding: 5px 13px;
      border-radius: 50px;
      font-size: 12px;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border);
      color: var(--muted);
      cursor: pointer;
      transition: all 0.2s;
    }}
    .tag:hover {{
      background: rgba(108,99,255,0.15);
      border-color: var(--accent1);
      color: var(--text);
    }}

    /* ── DIVIDER ── */
    .divider {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 22px 0 18px;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    .divider::before, .divider::after {{
      content: '';
      flex: 1;
      height: 1px;
      background: var(--border);
    }}

    /* ── FOOTER ── */
    .footer {{
      margin-top: 28px;
      text-align: center;
      font-size: 12px;
      color: var(--muted);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }}
    .footer a {{
      color: var(--accent1);
      text-decoration: none;
      font-weight: 500;
      transition: color 0.2s;
    }}
    .footer a:hover {{ color: var(--accent2); }}

    /* ── PULSE DOT ── */
    .live-dot {{
      display: inline-block;
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #1ddb6a;
      box-shadow: 0 0 8px #1ddb6a;
      animation: pulse 1.6s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.5; transform: scale(1.4); }}
    }}
  </style>
</head>
<body>
  <!-- Background -->
  <canvas id="canvas"></canvas>
  <div class="blob blob-1"></div>
  <div class="blob blob-2"></div>
  <div class="blob blob-3"></div>

  <!-- Admin -->
  <div class="theme-toggle" id="themeToggle">
    <div class="knob" id="knob">🌙</div>
  </div>

  <a href="/admin" class="admin-btn">
    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round"
        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944
           a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591
           3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622
           0-1.042-.133-2.052-.382-3.016z"/>
    </svg>
    Admin Panel
  </a>

  <!-- Card -->
  <div class="card">

    <!-- Logo -->
    <div class="logo-wrap">
      <div class="logo-ring">
        <svg viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="36" cy="36" r="33" stroke="url(#ringGrad)" stroke-width="1.5"
                  stroke-dasharray="6 4" stroke-linecap="round"/>
          <defs>
            <linearGradient id="ringGrad" x1="0" y1="0" x2="72" y2="72" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#6c63ff"/>
              <stop offset="100%" stop-color="#00e5ff"/>
            </linearGradient>
          </defs>
        </svg>
        <div class="logo-icon">⚡</div>
      </div>
    </div>

    <h1 class="headline">Fast Finder</h1>
    <p class="sub">Movies · Series · Anime — Instant Telegram Access</p>

    <!-- Stats -->
    <div class="stats">
      <div class="stat">
        <div class="stat-num">50K+</div>
        <div class="stat-label">Files</div>
      </div>
      <div class="stat">
        <div class="stat-num">4K</div>
        <div class="stat-label">Quality</div>
      </div>
      <div class="stat">
        <div class="stat-num"><span class="live-dot"></span></div>
        <div class="stat-label">Live</div>
      </div>
    </div>

    <!-- Input -->
    <div class="input-wrap">
      <span class="input-icon">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8"/><path stroke-linecap="round" d="M21 21l-4.35-4.35"/>
        </svg>
      </span>
      <input type="text" id="searchInput" placeholder="Movie, Series ya Anime ka naam likho…" autocomplete="off"/>
    </div>

    <button class="btn" onclick="startSearch()">
      Search on Telegram &nbsp;→
    </button>

    <!-- Tags -->
    <div class="divider">Quick picks</div>
    <div class="tags">
      <span class="tag" onclick="fillAndSearch('Action Movies')">💥 Action</span>
      <span class="tag" onclick="fillAndSearch('Thriller Series')">🔪 Thriller</span>
      <span class="tag" onclick="fillAndSearch('Romantic Movies')">❤️ Romance</span>
      <span class="tag" onclick="fillAndSearch('Comedy Films')">😂 Comedy</span>
      <span class="tag" onclick="fillAndSearch('Anime Series')">🎌 Anime</span>
      <span class="tag" onclick="fillAndSearch('Horror Movies')">👻 Horror</span>
      <span class="tag" onclick="fillAndSearch('Sci-Fi Films')">🚀 Sci-Fi</span>
      <span class="tag" onclick="fillAndSearch('4K Web Series')">📺 Web Series</span>
    </div>

    <!-- Footer -->
    <div class="footer">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
      </svg>
      Powered by
      <a href="https://t.me/{bot_username}" target="_blank">@{bot_username}</a>
    </div>
  </div>

  <script>
    /* ── PARTICLE CANVAS ── */
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    let W, H, particles = [];

    function resize() {{
      W = canvas.width  = window.innerWidth;
      H = canvas.height = window.innerHeight;
    }}
    resize();
    window.addEventListener('resize', () => {{ resize(); init(); }});

    function rand(a, b) {{ return Math.random() * (b - a) + a; }}

    function init() {{
      particles = [];
      const count = Math.floor((W * H) / 9000);
      for (let i = 0; i < count; i++) {{
        particles.push({{
          x: rand(0, W), y: rand(0, H),
          vx: rand(-0.15, 0.15), vy: rand(-0.25, -0.05),
          r: rand(0.5, 1.6),
          alpha: rand(0.2, 0.7),
          color: Math.random() > 0.5 ? '108,99,255' : '0,229,255'
        }});
      }}
    }}
    init();

    function draw() {{
      ctx.clearRect(0, 0, W, H);
      for (const p of particles) {{
        p.x += p.vx; p.y += p.vy;
        if (p.y < -2) {{ p.y = H + 2; p.x = rand(0, W); }}
        if (p.x < -2) p.x = W + 2;
        if (p.x > W + 2) p.x = -2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${{p.color}},${{p.alpha}})`;
        ctx.fill();
      }}
      requestAnimationFrame(draw);
    }}
    draw();

    /* ── SEARCH LOGIC ── */
    function startSearch() {{
      const q = document.getElementById('searchInput').value.trim();
      const base = `https://t.me/{bot_username}`;
      window.open(q ? `${{base}}?start=${{encodeURIComponent(q)}}` : base, '_blank');
    }}

    function fillAndSearch(q) {{
      document.getElementById('searchInput').value = q;
      startSearch();
    }}

    document.getElementById('searchInput').addEventListener('keydown', e => {{
      if (e.key === 'Enter') startSearch();
    }});
  </script>
</body>
</html>"""
    return web.Response(text=html_content, content_type='text/html')

# ─────────────────────────────────────────────
# 📺 STREAM / WATCH ROUTE
# ─────────────────────────────────────────────
@routes.get("/watch/{message_id}")
async def watch_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        return web.Response(text=await media_watch(message_id), content_type='text/html')
    except ValueError:
        return web.Response(status=400, text="Invalid Message ID")
    except Exception as e:
        logger.error(f"Watch Error: {e}")
        return web.Response(status=500, text="Internal Server Error")

# ─────────────────────────────────────────────
# 📥 DOWNLOAD ROUTE
# ─────────────────────────────────────────────
@routes.get("/download/{message_id}")
async def download_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        return await media_download(request, message_id)
    except ValueError:
        return web.Response(status=400, text="Invalid Message ID")
    except Exception as e:
        logger.error(f"Download Error: {e}")
        return web.Response(status=500, text="Internal Server Error")

# ─────────────────────────────────────────────
# 🚀 CORE STREAMING LOGIC (KOYEB OPTIMIZED)
# ─────────────────────────────────────────────
async def media_download(request, message_id: int):
    try:
        media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
        if not media_msg or not media_msg.media:
            return web.Response(status=404, text="File Not Found or Removed")

        media = getattr(media_msg, media_msg.media.value, None)
        if not media:
            return web.Response(status=404, text="Media Not Supported")

        file_size = media.file_size

        file_name = getattr(media, 'file_name', None)
        if not file_name:
            if getattr(media_msg, 'video', None):
                file_name = f"video_{secrets.token_hex(3)}.mp4"
            elif getattr(media_msg, 'audio', None):
                file_name = f"audio_{secrets.token_hex(3)}.mp3"
            else:
                file_name = f"file_{secrets.token_hex(3)}.bin"

        mime_type = getattr(media, 'mime_type', None)
        if not mime_type:
            mime_guess = mimetypes.guess_type(file_name)[0]
            mime_type = mime_guess if mime_guess else "application/octet-stream"

        range_header = request.headers.get('Range', 0)
        try:
            if range_header:
                from_bytes, until_bytes = range_header.replace('bytes=', '').split('-')
                from_bytes  = int(from_bytes)
                until_bytes = int(until_bytes) if until_bytes else file_size - 1
            else:
                from_bytes  = 0
                until_bytes = file_size - 1
        except Exception:
            from_bytes  = 0
            until_bytes = file_size - 1

        if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
            return web.Response(
                status=416,
                body="416: Range Not Satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        req_length    = until_bytes - from_bytes + 1
        new_chunk_size = await chunk_size(req_length)
        offset        = await offset_fix(from_bytes, new_chunk_size)
        first_part_cut = from_bytes - offset
        last_part_cut  = (until_bytes % new_chunk_size) + 1
        part_count    = math.ceil(req_length / new_chunk_size)

        body = TGCustomYield().yield_file(
            media_msg, offset, first_part_cut, last_part_cut, part_count, new_chunk_size
        )

        encoded_filename = quote(file_name)
        headers = {
            "Content-Type":        mime_type,
            "Content-Range":       f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Disposition": f'attachment; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}',
            "Accept-Ranges":       "bytes",
            "Content-Length":      str(req_length),
        }

        return web.Response(
            status=206 if range_header else 200,
            body=body,
            headers=headers,
        )

    except Exception as e:
        logger.error(f"Stream Error: {e}")
        return web.Response(status=500, text="Server Error during streaming")
