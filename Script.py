class script(object):

    START_TXT = """<b>ʜᴇʏ {}, <i>{}</i>
    
ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ & ꜱᴍᴀʀᴛ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ʙᴏᴛ! ɪ ᴄᴀɴ ᴘʀᴏᴠɪᴅᴇ ᴍᴏᴠɪᴇꜱ ᴀɴᴅ ꜱᴇʀɪᴇꜱ ᴡɪᴛʜ ᴅɪʀᴇᴄᴛ ꜱᴛʀᴇᴀᴍ & ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ. 🚀

🌟 <u>ᴍʏ ᴍᴀɪɴ ғᴇᴀᴛᴜʀᴇꜱ:</u>
• ꜱᴍᴀʀᴛ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ɪɴ ɢʀᴏᴜᴘꜱ
• ᴅɪʀᴇᴄᴛ ᴡᴀᴛᴄʜ / ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋꜱ
• ɢʀᴏᴜᴘ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ (ᴍᴜᴛᴇ/ʙᴀɴ)
• ꜱᴜᴘᴇʀғᴀꜱᴛ ꜱᴇᴀʀᴄʜ

ᴊᴜꜱᴛ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀꜱ ᴀᴅᴍɪɴ ᴀɴᴅ ꜱᴇᴇ ᴛʜᴇ ᴍᴀɢɪᴄ! ✨</b>"""

    MY_ABOUT_TXT = """<b>📚 ᴀʙᴏᴜᴛ ᴍᴇ

★ Server: <a href=https://www.koyeb.com>Koyeb</a>
★ Database: <a href=https://www.mongodb.com>MongoDB</a>
★ Language: <a href=https://www.python.org>Python 3</a>
★ Library: <a href=https://t.me/HydrogramNews>Hydrogram</a>
★ Type: Smart Auto Filter & Stream Bot</b>"""

    STATUS_TXT = """📊 <b>Bot Statistics</b>

👥 <b>Total Users:</b> <code>{}</code>
👥 <b>Total Groups:</b> <code>{}</code>
💎 <b>Premium Users:</b> <code>{}</code>

📁 <b>Total Files:</b> <code>{}</code>
 • 📁 Primary: <code>{}</code>
 • ☁️ Cloud: <code>{}</code>
 • 📦 Archive: <code>{}</code>

⏱ <b>Bot Uptime:</b> <code>{}</code>"""

    NEW_GROUP_TXT = """#NewGroup
Title - {}
ID - <code>{}</code>
Username - {}
Total - <code>{}</code>"""

    NEW_USER_TXT = """#NewUser
★ Name: {}
★ ID: <code>{}</code>"""

    NOT_FILE_TXT = """👋 Hello {},

I can't find the <b>{}</b> in my database! 🥲

👉 Google Search and check your spelling is correct.
👉 Please read the Instructions to get better results.
👉 Or not been released yet."""

    FILE_CAPTION = """<i>{file_name}</i>

🚫 ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ᴄʟᴏsᴇ ʙᴜᴛᴛᴏɴ ɪꜰ ʏᴏᴜ ʜᴀᴠᴇ sᴇᴇɴ ᴛʜᴇ ᴍᴏᴠɪᴇ 🚫"""

    WELCOME_TEXT = """👋 Hello {mention}, Welcome to {title} group! 💞"""

    HELP_TXT = """<b>👋 Hello {},
    
I can filter movie and series you want.
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
    
    PLAN_TXT = """Activate any premium plan to get exclusive features.

You can activate any premium plan and then you can get exclusive features.

- INR {} for pre day -

Basic premium features:
Ad free experience
Online watch and fast download
No need joind channels
No need verify
No shortlink
Admins support
And more...

Support: {}"""

    USER_COMMAND_TXT = """<b>👨‍💻 <u>Bot User Commands:</u> 👇

/start - Check if bot is alive and get main menu
/plan - View premium plan details
/myplan - Check your premium status</b>"""
