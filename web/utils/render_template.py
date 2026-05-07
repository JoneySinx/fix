# web/utils/render_template.py

from info import BIN_CHANNEL, URL
from utils import temp
import urllib.parse
import html
import logging

# Logger Setup
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🎬 FAST FINDER PREMIUM STREAM TEMPLATE
# ─────────────────────────────────────────────
watch_tmplt = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{heading}</title>

    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap">

    <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />

    <style>

        :root {{
            --primary-red: #e50914; /* Updated to match screenshot */
            --bg-dark: #0b0b0b;
            --card-dark: #141414;
            --text-light: #ffffff;
            --text-gray: #b3b3b3;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background: linear-gradient(to bottom, #000000, #111111);
            font-family: 'Montserrat', sans-serif;
            color: white;
            min-height: 100vh;
        }}

        /* ───────── NAVBAR ───────── */

        .navbar {{
            width: 100%;
            padding: 16px 4%;
            display: flex;
            align-items: center;
            position: fixed;
            top: 0;
            z-index: 999;
            background: linear-gradient(to bottom, rgba(0,0,0,0.95), rgba(0,0,0,0.4), transparent);
            backdrop-filter: blur(6px);
        }}

        /* CUSTOM CSS LOGO (Matches Screenshot Exactly) */
        .ff-logo {{
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
            transition: 0.3s ease;
        }}

        .ff-logo:hover {{
            transform: scale(1.03);
        }}

        .ff-icon {{
            background-color: var(--primary-red);
            color: #ffffff;
            font-size: 26px;
            font-weight: 800;
            width: 42px;
            height: 42px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
        }}

        .ff-text {{
            color: var(--primary-red);
            font-size: 28px;
            font-weight: 900;
            letter-spacing: 1px;
            text-shadow: 0 0 15px rgba(229, 9, 20, 0.4);
        }}

        /* ───────── MAIN ───────── */

        .hero-container {{
            width: 100%;
            max-width: 1350px;
            margin: auto;
            padding: 110px 20px 40px;
        }}

        .player-box {{
            width: 100%;
            overflow: hidden;
            border-radius: 18px;
            background: #000;
            border: 1px solid rgba(255,255,255,0.08);

            box-shadow:
                0 0 20px rgba(255,0,0,0.15),
                0 0 80px rgba(255,0,0,0.10),
                0 20px 60px rgba(0,0,0,0.8);
        }}

        .video-container video {{
            width: 100%;
            height: auto;
            display: block;
        }}

        video {{
            width: 100%;
            height: auto;
        }}

        /* ───────── INFO ───────── */

        .info-section {{
            margin-top: 24px;
        }}

        .title {{
            font-size: 2rem;
            font-weight: 700;
            line-height: 1.4;
            margin-bottom: 22px;
            word-break: break-word;
        }}

        .controls-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
        }}

        /* ───────── BUTTONS ───────── */

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;

            padding: 13px 26px;
            border-radius: 10px;

            text-decoration: none;
            font-size: 1rem;
            font-weight: 600;

            cursor: pointer;
            transition: 0.25s ease;

            border: none;
        }}

        .btn svg {{
            width: 20px;
            height: 20px;
        }}

        .btn-download {{
            background: var(--primary-red);
            color: white;
            box-shadow: 0 0 18px rgba(229,9,20,0.35);
        }}

        .btn-download:hover {{
            transform: translateY(-2px);
            background: #ff1a1a;
        }}

        .btn-copy {{
            background: rgba(255,255,255,0.08);
            color: white;
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(6px);
        }}

        .btn-copy:hover {{
            background: rgba(255,255,255,0.15);
        }}

        /* ───────── PLYR CUSTOM ───────── */

        .plyr--video {{
            --plyr-color-main: #e50914;
            --plyr-video-background: #000000;
            border-radius: 18px;
            overflow: hidden;
        }}

        .plyr__control--overlaid {{
            background: rgba(229,9,20,0.9) !important;
        }}

        .plyr__control:hover {{
            background: rgba(229,9,20,0.8) !important;
        }}

        /* ───────── TOAST ───────── */

        #toast {{
            visibility: hidden;
            min-width: 220px;

            background: var(--primary-red);
            color: white;

            text-align: center;
            border-radius: 10px;

            padding: 15px;

            position: fixed;
            right: 30px;
            bottom: 30px;

            z-index: 9999;

            font-weight: 600;

            box-shadow: 0 10px 30px rgba(0,0,0,0.45);
        }}

        #toast.show {{
            visibility: visible;
            animation: fadein 0.4s, fadeout 0.4s 2.6s;
        }}

        @keyframes fadein {{
            from {{
                opacity: 0;
                bottom: 0;
            }}
            to {{
                opacity: 1;
                bottom: 30px;
            }}
        }}

        @keyframes fadeout {{
            from {{
                opacity: 1;
                bottom: 30px;
            }}
            to {{
                opacity: 0;
                bottom: 0;
            }}
        }}

        /* ───────── MOBILE ───────── */

        @media (max-width: 768px) {{

            .hero-container {{
                padding-top: 95px;
            }}

            .ff-icon {{
                width: 36px;
                height: 36px;
                font-size: 22px;
            }}

            .ff-text {{
                font-size: 22px;
            }}

            .title {{
                font-size: 1.3rem;
            }}

            .controls-row {{
                flex-direction: column;
            }}

            .btn {{
                width: 100%;
            }}

        }}

    </style>
</head>

<body>

    <div class="navbar">

        <div class="ff-logo">
            <div class="ff-icon">F</div>
            <div class="ff-text">FAST FINDER</div>
        </div>

    </div>

    <div class="hero-container">

        <div class="player-box">

            <video
                id="player"
                playsinline
                controls
            >
                <source src="{src}" type="{mime_type}">
            </video>

        </div>

        <div class="info-section">

            <div class="title">{file_name}</div>

            <div class="controls-row">

                <a href="{src}" class="btn btn-download">

                    <svg fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 16L7 11H10V4H14V11H17L12 16ZM5 20V18H19V20H5Z"/>
                    </svg>

                    Download

                </a>

                <button onclick="copyLink()" class="btn btn-copy">

                    <svg fill="currentColor" viewBox="0 0 24 24">
                        <path d="M16 1H4C2.9 1 2 1.9 2 3V17H4V3H16V1ZM19 5H8C6.9 5 6 5.9 6 7V21C6 22.1 6.9 23 8 23H19C20.1 23 21 22.1 21 21V7C21 5.9 20.1 5 19 5ZM19 21H8V7H19V21Z"/>
                    </svg>

                    Copy Link

                </button>

            </div>

        </div>

    </div>

    <div id="toast">
        Link Copied Successfully!
    </div>

    <script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>

    <script>

        const player = new Plyr('#player', {{

            // Added 'mute' back, but left out 'volume'
            controls: [
                'play-large',
                'play',
                'progress',
                'current-time',
                'mute',
                'settings',
                'pip',
                'fullscreen'
            ],

            settings: ['quality', 'speed'],
            autoplay: false

        }});

        // COPY LINK
        function copyLink() {{

            navigator.clipboard.writeText("{src}");

            let toast = document.getElementById("toast");

            toast.className = "show";

            setTimeout(() => {{
                toast.className = toast.className.replace("show", "");
            }}, 3000);

        }}

    </script>

</body>
</html>
"""

# ─────────────────────────────────────────────
# 🎬 MEDIA WATCH FUNCTION
# ─────────────────────────────────────────────

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

            file_name = html.escape(
                media.file_name if hasattr(media, 'file_name')
                else "Fast Finder Movie"
            )

            return watch_tmplt.format(
                heading=f"Watch {file_name}",
                file_name=file_name,
                src=src,
                mime_type=mime_type
            )

        else:

            return f"""

            <body style="
                background:#000;
                color:white;
                display:flex;
                align-items:center;
                justify-content:center;
                height:100vh;
                font-family:Montserrat,sans-serif;
            ">

                <div style="
                    text-align:center;
                    background:#141414;
                    padding:40px;
                    border-radius:18px;
                    border:1px solid rgba(255,255,255,0.08);
                ">

                    <h1 style="margin-bottom:20px;">
                        ⚠️ Unsupported File
                    </h1>

                    <a
                        href="{src}"
                        style="
                            background:#e50914;
                            color:white;
                            padding:14px 24px;
                            border-radius:10px;
                            text-decoration:none;
                            display:inline-block;
                            font-weight:600;
                        "
                    >
                        Download Direct
                    </a>

                </div>

            </body>

            """

    except Exception as e:

        logger.error(f"Template Error: {e}")

        return f"<h2>Server Error: {str(e)}</h2>"
