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
# 🏠 ROOT ROUTE (FAST FINDER UI)
# ─────────────────────────────────────────────
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    bot_username = getattr(temp, 'U_NAME', 'AutoFilterBot')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fast Finder | Streaming & Downloads</title>
        <style>
            body {{
                background-color: #0f0f1a;
                color: #e0e0e0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                text-align: center;
                background: #1a1a2e;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.6);
                width: 90%;
                max-width: 450px;
            }}
            h1 {{
                margin: 0 0 10px 0;
                font-size: 2.5rem;
                background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            p {{ color: #a0a0b0; margin-bottom: 30px; }}
            
            .search-box {{
                position: relative;
                width: 100%;
            }}
            input[type="text"] {{
                width: 100%;
                padding: 15px 20px;
                box-sizing: border-box;
                border-radius: 30px;
                border: 2px solid #333;
                background-color: #16213e;
                color: white;
                font-size: 16px;
                outline: none;
                transition: border-color 0.3s, box-shadow 0.3s;
            }}
            input[type="text"]:focus {{
                border-color: #3a7bd5;
                box-shadow: 0 0 10px rgba(58, 123, 213, 0.4);
            }}
            
            button {{
                margin-top: 20px;
                width: 100%;
                padding: 15px;
                border-radius: 30px;
                border: none;
                background: linear-gradient(90deg, #3a7bd5, #00d2ff);
                color: white;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(0, 210, 255, 0.4);
            }}
            
            .footer {{ margin-top: 25px; font-size: 13px; color: #555; }}
            a {{ text-decoration: none; color: #3a7bd5; transition: color 0.2s; }}
            a:hover {{ color: #00d2ff; }}
            
            /* Hidden Admin Link */
            .secret-admin {{ color: #1a1a2e; cursor: default; }}
            .secret-admin:hover {{ color: #333; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚡ Fast Finder</h1>
            <p>Search Movies, Series & Anime Instantly</p>
            
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Type name here (e.g. Pushpa 2)...">
            </div>
            
            <button onclick="startSearch()">🔍 Search on Telegram</button>
            
            <div class="footer">
                Powered by <a href="https://t.me/{bot_username}">Auto Filter Bot</a> 
                | <a href="/admin" class="secret-admin">Admin</a>
            </div>
        </div>

        <script>
            function startSearch() {{
                var query = document.getElementById("searchInput").value;
                if(query) {{
                    // Telegram पर रीडायरेक्ट करेगा जहाँ यूज़र सीधे सर्च कर सकता है
                    window.location.href = "https://t.me/{bot_username}?start=" + encodeURIComponent(query);
                }} else {{
                    window.location.href = "https://t.me/{bot_username}";
                }}
            }}

            document.getElementById("searchInput").addEventListener("keypress", function(event) {{
                if (event.key === "Enter") {{
                    startSearch();
                }}
            }});
        </script>
    </body>
    </html>
    """
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
        # 1. Fetch Message safely
        media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
        if not media_msg or not media_msg.media:
            return web.Response(status=404, text="File Not Found or Removed")
            
        media = getattr(media_msg, media_msg.media.value, None)
        if not media:
            return web.Response(status=404, text="Media Not Supported")

        file_size = media.file_size
        
        # 2. ✅ FIX: Smart Filename Generator (बचाएगा .jpg वाले बग से)
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

        # 3. Handle Range Headers Safely
        range_header = request.headers.get('Range', 0)
        
        try:
            if range_header:
                from_bytes, until_bytes = range_header.replace('bytes=', '').split('-')
                from_bytes = int(from_bytes)
                until_bytes = int(until_bytes) if until_bytes else file_size - 1
            else:
                from_bytes = 0
                until_bytes = file_size - 1
        except Exception:
            from_bytes = 0
            until_bytes = file_size - 1

        if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
            return web.Response(
                status=416,
                body="416: Range Not Satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        # 4. Calculate Chunks
        req_length = until_bytes - from_bytes + 1
        new_chunk_size = await chunk_size(req_length)
        offset = await offset_fix(from_bytes, new_chunk_size)
        
        first_part_cut = from_bytes - offset
        last_part_cut = (until_bytes % new_chunk_size) + 1
        part_count = math.ceil(req_length / new_chunk_size)

        # 5. Generate Stream Body
        body = TGCustomYield().yield_file(
            media_msg, offset, first_part_cut, last_part_cut, part_count, new_chunk_size
        )

        # 6. Return Response
        encoded_filename = quote(file_name)
        
        headers = {
            "Content-Type": mime_type,
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Disposition": f'attachment; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}',
            "Accept-Ranges": "bytes",
            "Content-Length": str(req_length)
        }

        return web.Response(
            status=206 if range_header else 200,
            body=body,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Stream Error: {e}")
        return web.Response(status=500, text="Server Error during streaming")
