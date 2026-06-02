class script(object):

    # 🍿 आपके लाइव फीचर्स के अनुसार पूरी तरह बदला गया स्टार्ट टेक्स्ट
    START_TXT = """<b>ʜᴇʏ {}, <i>{}</i>
    
ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ & ꜱᴍᴀʀᴛ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ʙᴏᴛ! ɪ ᴄᴀɴ ᴘʀᴏᴠɪᴅᴇ ᴍᴏᴠɪᴇꜱ ᴀɴᴅ ꜱᴇʀɪᴇꜱ ᴡɪᴛʜ ᴅɪʀᴇᴄᴛ ꜱᴛʀᴇᴀᴍ & ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ. 🚀

🍿 <u>ᴍʏ ᴍᴀɪɴ ғᴇᴀᴛᴜʀᴇꜱ:</u>
• ꜱᴍᴀʀᴛ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ɪɴ ᴄʜᴀᴛ ɢʀᴏᴜᴘꜱ
• 📱 ᴀᴅᴠᴀɴᴄᴇᴅ ᴍɪɴɪ ᴀᴘᴘ ꜰᴏʀ ᴄɪɴᴇᴍᴀᴛɪᴄ ꜱᴇᴀʀᴄʜ
• 🎬 ɪɴ-ʙᴜɪʟᴛ ᴘʟᴀʏᴇʀ ᴡɪᴛʜ 10ꜱ ᴅᴏᴜʙʟᴇ-ᴛᴀᴘ ꜱᴋɪᴘ
• ⚡ ꜱᴜᴘᴇʀғᴀꜱᴛ ᴅɪʀᴇᴄᴛ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ
• 🧠 ɢᴇᴍɪɴɪ 2.5 ғʟᴀsʜ ᴀɪ ᴄʜᴀᴛ ᴀssɪsᴛᴀɴᴛ
• 🛡️ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ ꜰᴏʀ ꜱᴛorage sᴀꜰᴇᴛʏ

ᴊᴜꜱᴛ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀꜱ ᴀᴅᴍɪɴ ᴏʀ ᴛʏᴘᴇ ʏᴏᴜʀ ϙᴜᴇʀʏ ʜᴇʀᴇ ᴛᴏ sᴛᴀʀᴛ! ✨</b>"""

    STATUS_TXT = """📊 <b>Bot Statistics</b>

🦹 <b>Total Users:</b> <code>{}</code>
👫 <b>Total Groups:</b> <code>{}</code>
💰 <b>Premium Users:</b> <code>{}</code>

🗂️ <b>Total Files:</b> <code>{}</code>
 • ⚡ Primary: <code>{}</code>
 • ☁️ Cloud: <code>{}</code>
 • ♻️ Archive: <code>{}</code>

⏰ <b>Uptime:</b> <code>{}</code>"""

    # ✅ सिर्फ प्रीमियम यूज़र्स के लिए लिमिटेड स्टेट्स
    USER_STATUS_TXT = """📊 <b>Bot Statistics</b>

🗂️ <b>Total Files:</b> <code>{}</code>
 • ⚡ Primary: <code>{}</code>
 • ☁️ Cloud: <code>{}</code>
 • ♻️ Archive: <code>{}</code>

⏰ <b>Uptime:</b> <code>{}</code>"""

    NEW_GROUP_TXT = """#NewGroup
Title - {}
ID - <code>{}</code>
Username - {}
Total - <code>{}</code>"""

    NEW_USER_TXT = """#NewUser
★ Name: {}
★ ID: <code>{}</code>"""

    NOT_FILE_TXT = """👋 Hello {},

I can't find <b>{}</b> in my database! 🥲

👉 Google Search and check if your spelling is correct.
👉 Please read the Instructions to get better results.
👉 Or maybe it hasn't been released yet."""

    # ✅ अब सिर्फ फाइल का नाम बोल्ड में दिखेगा
    FILE_CAPTION = """<b>{file_name}</b>"""

    WELCOME_TEXT = """👋 Hello {mention}, Welcome to {title} group! 💞"""

    HELP_TXT = """<b>👋 Hello {},
    
I can filter any movie and series you want.
Just type the movie or series name in my PM, open our Mini App, or add me into your group!

I have many more features for you.
Please check the commands below 👇</b>"""

    ADMIN_COMMAND_TXT = """<b>👮‍♂️ <u>Bot Admin Commands:</u> 👇

• /stats - Get bot statistics (Users, Files, Uptime)
• /delete - Delete specific files from DB
• /delete_all - Clear an entire collection (Primary/Cloud/Archive)
• /link - Generate direct stream/download links
• /add_prm - Add premium days to a user (e.g. /add_prm id days)
• /rm_prm - Remove premium access from a user
• /prm_list - View list of all active premium users
• /web_users - View list of users registered on Web Dashboard

🛠️ <u>Group Admin Commands:</u> 👇

• /search on | off - Toggle Auto Filter on/off in group
• /button_style - Switch results between Simple and Full mode
• /mute | /unmute - Restrict user from sending messages
• /ban - Ban user permanently from group
• /warn | /resetwarn - Manage warnings (Auto-Ban on 3/3 warns)
• /addblacklist | /removeblacklist - Manage blocked words
• /blacklist - View group's blacklisted keywords
• /dlink | /removedlink - Manage timed auto-delete words
• /dlinklist - View persistent auto-delete triggers</b>"""
    
    # ✅ pre day को per day किया गया
    PLAN_TXT = """💎 <b>Fast Finder Premium Plans</b> 💎

Activate a premium plan to unlock exclusive, high-speed features!

⚡ <b>Price:</b> <code>₹{} / Per Day</code> ⚡

🚀 <b>Premium Features Include:</b>
» 🍿 Ad-Free Experience (No interruptions)
» 🎬 Online Streaming & Superfast Downloads
» 🔓 No Need to Join Extra Channels (No FSUB)
» ⚡ Zero Verification / Shortlinks Required
» 👑 Dedicated Admin Support

👨‍🚒 <b>Support & Verification:</b> {}"""

    USER_COMMAND_TXT = """<b>👨‍💻 <u>Bot User Commands:</u> 👇

• /start - Check if bot is alive and open Main Menu
• /plan - View premium membership plan details
• /myplan - Check your remaining premium duration
• /id - Extract User ID, Chat ID, and Telegram File ID
• /ai | /ask - Conversational Gemini 2.5 Flash AI Assistant (with 10m memory)</b>"""
