from info import BIN_CHANNEL, URL
from utils import temp
import urllib.parse
import html
import logging

# Logger Setup
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🎨 STREAMING TEMPLATE (Real Netflix Premium Look)
# ─────────────────────────────────────────────
watch_tmplt = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{heading}</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap">
    <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
    <style>
        :root {{
            --netflix-red: #E50914;
            --bg-dark: #141414;
            --bg-darker: #000000;
            --text-white: #ffffff;
            --text-gray: #b3b3b3;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Montserrat', sans-serif;
            background-color: var(--bg-dark);
            background-image: radial-gradient(circle at center, #1f1f1f 0%, #000000 100%);
            color: var(--text-white);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}

        /* Navbar Style */
        .navbar {{
            padding: 20px 4%;
            display: flex;
            align-items: center;
            background: linear-gradient(to bottom, rgba(0,0,0,0.7) 10%, rgba(0,0,0,0));
            position: fixed;
            width: 100%;
            z-index: 100;
            top: 0;
        }}
        
        .logo {{
            color: var(--netflix-red);
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: 2px;
            text-transform: uppercase;
            text-shadow: 0px 0px 10px rgba(229, 9, 20, 0.5);
        }}

        /* Main Content */
        .hero-container {{
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 80px 20px 40px;
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
        }}

        .player-box {{
            width: 100%;
            position: relative;
            border-radius: 12px;
            overflow: hidden;
            background: #000;
            /* Cinematic Glow Effect */
            box-shadow: 0 0 40px rgba(0, 0, 0, 0.8), 0 0 100px rgba(229, 9, 20, 0.15); 
            border: 1px solid #333;
        }}

        .video-container video {{
            width: 100%;
            height: auto;
            display: block;
        }}

        .info-section {{
            width: 100%;
            margin-top: 25px;
            text-align: left;
        }}

        .title {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}

        .controls-row {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}

        /* Netflix Style Buttons */
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 28px;
            font-size: 1.1rem;
            font-weight: 600;
            border-radius: 4px;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.2s;
            text-decoration: none;
            border: none;
        }}

        .btn-play {{
            background-color: var(--text-white);
            color: black;
        }}
        .btn-play:hover {{ opacity: 0.8; }}

        .btn-download {{
            background-color: rgba(109, 109, 110, 0.7);
            color: white;
            backdrop-filter: blur(5px);
        }}
        .btn-download:hover {{ background-color: rgba(109, 109, 110, 0.4); }}
        
        .btn-copy {{
            background-color: transparent;
            color: var(--text-gray);
            border: 1px solid var(--text-gray);
            font-size: 0.9rem;
            padding: 10px 20px;
        }}
        .btn-copy:hover {{ border-color: white; color: white; }}

        .icon {{ margin-right: 10px; width: 20px; height: 20px; }}

        /* Custom Plyr Theme */
        .plyr--video {{
            --plyr-color-main: var(--netflix-red);
            --plyr-video-background: #000;
        }}

        /* Toast */
        #toast {{
            visibility: hidden;
            min-width: 250px;
            background-color: var(--netflix-red);
            color: white;
            text-align: center;
            border-radius: 4px;
            padding: 16px;
            position: fixed;
            z-index: 99;
            right: 30px;
            bottom: 30px;
            font-weight: 600;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        #toast.show {{ visibility: visible; animation: fadein 0.5s, fadeout 0.5s 2.5s; }}

        @keyframes fadein {{ from {{bottom: 0; opacity: 0;}} to {{bottom: 30px; opacity: 1;}} }}
        @keyframes fadeout {{ from {{bottom: 30px; opacity: 1;}} to {{bottom: 0; opacity: 0;}} }}

        /* Mobile Responsive */
        @media (max-width: 768px) {{
            .logo {{ font-size: 1.5rem; }}
            .title {{ font-size: 1.4rem; }}
            .btn {{ width: 100%; margin-bottom: 10px; }}
            .hero-container {{ padding-top: 70px; }}
        }}
    </style>
</head>
<body>

    <div class="navbar">
        <div class="logo">Fast <span style="font-size: 0.8rem; color:white; font-weight:400;">Finder</span></div>
    </div>

    <div class="hero-container">
        
        <div class="player-box">
            <video id="player" playsinline poster="https://assets.nflxext.com/ffe/siteui/vlv3/f841d4c7-10e1-40af-bcae-07a3f8dc141a/f6d7434e-d6de-4185-a6d4-c77a2d08737b/US-en-20220502-popsignuptwoweeks-perspective_alpha_website_medium.jpg">
                <source src="{src}" type="{mime_type}" />
            </video>
        </div>

        <div class="info-section">
            <div class="title">{file_name}</div>
            
            <div class="controls-row">
                <a href="{src}" class="btn btn-play">
                    <svg class="icon" viewBox="0 0 24 24" fill="currentColor"><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4M12 3v12M8 11l4 4 4-4"/></svg>
                    Download
                </a>

                <button onclick="copyLink()" class="btn btn-download">
                    <svg class="icon" viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                    Copy Link
                </button>
            </div>
        </div>

    </div>

    <div id="toast">Link Copied!</div>

    <script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
    <script>
        const player = new Plyr('#player', {{
            controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'settings', 'pip', 'fullscreen'],
            settings: ['speed'],
            hideControls: true
        }});

        function copyLink() {{
            const el = document.createElement('textarea');
            el.value = "{src}";
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            
            var x = document.getElementById("toast");
            x.className = "show";
            setTimeout(function(){{ x.className = x.className.replace("show", ""); }}, 3000);
        }}
    </script>
</body>
</html>
"""

async def media_watch(message_id):
    try:
        media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
        media = getattr(media_msg, media_msg.media.value, None)
        
        if not media:
            return "<h2>❌ File Not Found or Deleted</h2>"

        src = urllib.parse.urljoin(URL, f'download/{message_id}')
        mime_type = getattr(media, 'mime_type', 'video/mp4')
        tag = mime_type.split('/')[0].strip()
        
        if tag == 'video':
            file_name = html.escape(media.file_name if hasattr(media, 'file_name') else "Netflix Movie")
            
            return watch_tmplt.format(
                heading=f"Watch {file_name}",
                file_name=file_name,
                src=src,
                mime_type=mime_type
            )
        else:
            return f"""
            <body style="background:#141414; color:white; display:flex; align-items:center; justify-content:center; height:100vh; font-family:sans-serif;">
                <div style="text-align:center;">
                    <h1>⚠️ File Format Not Supported</h1>
                    <a href="{src}" style="color:#E50914; text-decoration:none; font-size:1.2rem; border:1px solid #E50914; padding:10px 20px; border-radius:4px; margin-top:20px; display:inline-block;">Download Direct</a>
                </div>
            </body>
            """
    except Exception as e:
        logger.error(f"Template Error: {e}")
        return f"<h2>Server Error: {str(e)}</h2>"
