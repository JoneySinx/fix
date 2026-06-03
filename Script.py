class script(object):

    # 🍿 आपके लाइव फीचर्स और प्रीमियम मॉडल के अनुसार स्टार्ट टेक्स्ट (DM locked logic ready)
    START_TXT = """<b>ʜᴇʏ {}, <i>{}</i>
    
ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ & ꜱᴍᴀʀᴛ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ʙᴏᴛ! ɪ ᴄᴀɴ ᴘʀᴏᴠɪᴅᴇ ᴍᴏᴠɪᴇꜱ ᴀɴᴅ ꜱᴇʀɪᴇꜱ ᴡɪᴛʜ ᴅɪʀᴇᴄᴛ ꜱᴛʀᴇᴀᴍ & ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ. 🚀

🍿 <u>ᴍʏ ᴍᴀɪɴ ғᴇᴀᴛᴜʀᴇꜱ:</u>
• ꜱᴍᴀʀᴛ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ɪɴ ᴄʜᴀᴛ ɢʀᴏᴜᴘꜱ
• 📱 ᴀᴅᴠᴀɴᴄᴇᴅ ᴍɪɴɪ ᴀᴘᴘ ꜰᴏʀ ᴄɪɴᴇᴍᴀᴛɪᴄ ꜱᴇᴀʀᴄʜ
• 🎬 ɪɴ-ʙᴜɪʟᴛ ᴘʟᴀʏᴇʀ ᴡɪᴛʜ 10ꜱ ᴅᴏᴜʙʟᴇ-ᴛᴀᴘ ꜱᴋɪᴘ
• ⚡ ꜱᴜᴘᴇʀғᴀꜱᴛ ᴅɪʀᴇᴄᴛ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ
• 🧠 ɢᴇᴍɪɴɪ 2.5 ғʟᴀsʜ ᴀɪ ᴄʜᴀᴛ ᴀssɪsᴛᴀɴᴛ
• 🛡️ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ǫᴜᴇᴜᴇ (ʀᴇꜱᴛᴀʀᴛ-ᴘʀᴏᴏғ)

✨ <i>ᴊᴏɪɴ ᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ꜰᴏʀ ᴀɴ ᴀᴅ-ꜰʀᴇᴇ ᴇxᴘᴇʀɪᴇɴᴄᴇ!</i></b>"""

    # 📊 ✅ FIXED: आपके स्क्रीनशॉट के अनुसार बिल्कुल हूबहू पर्पल नियॉन थीम आधारित स्टैट्स लेआउट
    STATUS_TXT = """
📊 <b>FAST FINDER SYSTEM STATS</b>
<blockquote>
🤵 Total Users: <b>{}</b>
👥 Connected Groups: <b>{}</b>
💎 Premium Members: <b>{}</b>
</blockquote>
🌐 <b>Data Centre</b>
<blockquote>
📁 Total Files: <b>{}</b>
</blockquote>
<blockquote>
⚡ Primary : <b>{}</b> ✅ <b>{}</b>
☁️ Cloud : <b>{}</b> ✅ <b>{}</b>
♻️ Archive : <b>{}</b> ✅ <b>{}</b>
</blockquote>
<blockquote>
🖼️ Total Cached Thumbs: <b>{}</b>
</blockquote>
⏰ <b>System Live Uptime:</b> <code>{}</code>
"""

    # ✅ सिर्फ प्रीमियम यूज़र्स के लिए ग्लोबल लाइब्रेरी स्टैट्स
    USER_STATUS_TXT = """📊 <b><u>FAST FINDER GLOBAL DATABASE</u></b>

🗂️ <b>Available Library:</b>
» Total Titles Locked: <code>{}</code>
» Primary Storage: <code>{}</code>
» Cloud Library: <code>{}</code>
» Archive Backup: <code>{}</code>

⏰ <b>System Running Since:</b> <code>{}</code>"""

    NEW_GROUP_TXT = """<b>#NewGroup 👥\n\n• Title: {}\n• ID: <code>{}</code>\n• Username: {}\n• Total Members: <code>{}</code></b>"""

    NEW_USER_TXT = """<b>#NewUser 👤\n\n• Name: {}\n• ID: <code>{}</code></b>"""

    NOT_FILE_TXT = """<b>❌ ʜᴇʏ {}, "{}" ɪꜱ ɴᴏᴛ ꜰᴏᴜɴᴅ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀꜱᴇ. 

💡 <u>ᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ:</u>
» sᴘᴇʟʟɪɴɢ sʜᴏᴜʟᴅ ʙᴇ ᴄᴏʀʀᴇᴄᴛ (ᴄʜᴇᴄᴋ ɢᴏᴏɢʟᴇ)
» sᴇᴀʀᴄʜ ᴡɪᴛʜ ᴍᴏᴠɪᴇ ɴᴀᴍᴇ ᴏɴʟʏ ( things like 4k, Bluray, Season, Year हटा दें)</b>"""

    # ✅ सिर्फ फाइल का नाम बोल्ड में क्लीन दिखेगा (No unwanted parameters)
    FILE_CAPTION = """<b>{file_name}</b>"""

    WELCOME_TEXT = """👋 Hello {mention}, Welcome to {title} group! 💞"""

    HELP_TXT = """<b>👋 Hello {},
    
I can filter any movie and series you want.
Just type the movie or series name in my PM, open our Mini App, or add me into your group!

I have many more features for you.
Please check the commands below 👇</b>"""

    # ✅ ब्रॉडकास्ट हटाकर बिल्कुल साफ एडमिन लिस्ट और ग्रुप कंट्रोल्स का सिंक
    ADMIN_COMMAND_TXT = """<b>👑 <u>Bot Admin Commands:</u> 👇

• /stats - View detailed database & user population statistics
• /delete - Delete specific files from collections
• /delete_all - Wipe out an entire storage collection
• /add_prm - Grant premium access to a user manually
• /rm_prm - Revoke premium status from a user
• /prm_list - Export document list of all active premium users
• /web_users - View list of users registered on Web Dashboard
• /warmup_thumbs - Lock missing thumbnails into Database
• /restart - Hard restart the bot application session

⚙️ <u>Group Management Guide:</u> 👇

• /search on | off - Toggle Auto Filter on/off in group
• /settings - Open Inline Button UI Center for Group Settings 
• /button_style - Switch results between Simple and Full mode
• /mute | /unmute - Restrict user from sending messages
• /ban - Ban user permanently from group
• /warn | /resetwarn - Manage warnings (Auto-Ban on 3/3 warns)
• /addblacklist | /removeblacklist - Manage blocked words
• /blacklist - View group's blacklisted keywords
• /dlink | /removedlink - Manage timed auto-delete words
• /dlinklist - View persistent auto-delete triggers</b>"""
    
    # ✅ प्रीमियम案 की डिटेल्स (Price / Per Day fixed)
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
• /id - Extract User ID, Chat ID, and message details
• /fileid - Reply to media to extract its Telegram File ID
• /ask or /ai - Chat with Gemini 2.5 Flash AI Assistant (10m Memory)</b>"""

    # 📢 ✅ NEW: आपके नियमानुसार इंडेक्सिंग खत्म होने पर LOG_CHANNEL में भेजी जाने वाली सुपर रिपोर्ट टेम्पलेट
    LOG_INDEX_TXT = """📢 <b>#Indexing_Report 📊</b>

<b>📂 Storage Parameters:</b>
» Chat Title: <code>{}</code>
» Chat ID: <code>{}</code>
» Collection Targeted: <code>{}</code>

<b>📈 Execution Statistics:</b>
» Total Processed: <code>{}</code> Files
» Successfully Saved: <code>{}</code> Files
» Duplicates Skipped: <code>{}</code> Files
» Unsupported Format: <code>{}</code> Files
» Errors Intercepted: <code>{}</code> Files

<b>⏱️ Engine Performance:</b>
» Status: <code>Completed Successfully ✅</code>
» Triggered By: <code>Authorized Bot Admin 👮‍♂️</code>"""
