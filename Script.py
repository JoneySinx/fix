class script(object):

    START_TXT = """<b>ʜᴇʏ {}, <i>{}</i>
    
ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ & ꜱᴍᴀʀᴛ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ʙᴏᴛ! ɪ ᴄᴀɴ ᴘʀᴏᴠɪᴅᴇ ᴍᴏᴠɪᴇꜱ ᴀɴᴅ ꜱᴇʀɪᴇꜱ ᴡɪᴛʜ ᴅɪʀᴇᴄᴛ ꜱᴛʀᴇᴀᴍ & ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ. 🚀

🌟 <u>ᴍʏ ᴍᴀɪɴ ғᴇᴀᴛᴜʀᴇꜱ:</u>
• ꜱᴍᴀʀᴛ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ɪɴ ɢʀᴏᴜᴘꜱ
• ᴅɪʀᴇᴄᴛ ᴡᴀᴛᴄʜ / ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ
• ɢʀᴏᴜᴘ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ (ᴍᴜᴛᴇ/ʙᴀɴ)
• ꜱᴜᴘᴇʀғᴀꜱᴛ ꜱᴇᴀʀᴄʜ

ᴊᴜꜱᴛ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀꜱ ᴀᴅᴍɪɴ ᴀɴᴅ ꜱᴇᴇ ᴛʜᴇ ᴍᴀɢɪᴄ! ✨</b>"""

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
Just type the movie or series name in my PM or add me into your group!

I have many more features for you.
Please check the commands below 👇</b>"""

    ADMIN_COMMAND_TXT = """<b>👮‍♂️ <u>Bot Admin Commands:</u> 👇

/stats - Get bot statistics (Users, Files, Uptime)
/delete - Delete specific files from DB
/delete_all - Clear an entire collection
/web - Generate Dashboard Magic Link
/link - Generate direct stream/download links

🛠️ <u>Group Admin Commands:</u> 👇

/search on | off - Toggle Auto Filter in group
/mute | /unmute | /ban - Manage users
/warn | /resetwarn - Manage user warnings
/addblacklist | /removeblacklist - Manage blocked words
/blacklist - View blacklisted words
/dlink | /removedlink - Manage auto-delete words
/dlinklist - View auto-delete words</b>"""
    
    # ✅ FIX: 'pre day' को 'per day' किया और टेक्स्ट को आकर्षक बनाया गया
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

/start - Check if bot is alive and get main menu
/plan - View premium plan details
/myplan - Check your premium status</b>"""
