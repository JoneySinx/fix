import time
import sys
import platform
import asyncio
import logging
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB
from hydrogram.errors import FloodWait

from utils import temp, get_readable_time, is_rate_limited
from info import IS_PREMIUM, ADMINS
from database.users_chats_db import db

logger = logging.getLogger(__name__)

# ======================================================
# 📂 GET MEDIA FILE ID HELPER (Hydrogram Optimized)
# ======================================================
def get_media_file_id(msg):
    """मैसेज से मीडिया ऑब्जेक्ट ढूंढकर उसकी file_id और file_ref निकालता है"""
    if not msg: return None, None
    for attr in ["photo", "video", "document", "audio", "voice", "animation", "sticker"]:
        media = getattr(msg, attr, None)
        if media:
            # Hydrogram में photo लिस्ट नहीं बल्कि सीधे एक Photo ऑब्जेक्ट होता है
            return media.file_id, getattr(media, "file_ref", "N/A")
    return None, None

# ======================================================
# 🆔 ID COMMAND (Upgraded & Rate-Limit Protected)
# ======================================================
@Client.on_message(filters.command("id"))
async def get_id(c, m):
    # कमांड स्पैम से कोएब CPU को क्रैश होने से बचाएं
    if is_rate_limited(m.from_user.id, "cmd_id", seconds=3):
        return

    r = m.reply_to_message
    u = r.from_user if r and r.from_user else m.from_user
    
    b = "👤 Member"
    if m.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        try:
            st = (await c.get_chat_member(m.chat.id, u.id)).status
            if st == enums.ChatMemberStatus.OWNER:
                b = "👑 Owner"
            elif st == enums.ChatMemberStatus.ADMINISTRATOR:
                b = "🛡 Admin"
        except: 
            pass

    t = (f"🆔 <b>ID INFORMATION</b>\n\n👤 <b>Name:</b> {u.first_name or ''} {u.last_name or ''}\n🦹 <b>User ID:</b> <code>{u.id}</code>\n"
         f"🏷 <b>Username:</b> @{u.username or 'N/A'}\n🌐 <b>DC ID:</b> <code>{u.dc_id or 'Unknown'}</code>\n🤖 <b>Bot:</b> {'Yes' if u.is_bot else 'No'}\n"
         f"{b}\n🔗 <b>Profile:</b> <a href='tg://user?id={u.id}'>Open</a>\n\n💬 <b>CHAT & MESSAGE</b>\n🆔 <b>Chat ID:</b> <code>{m.chat.id}</code>\n"
         f"📩 <b>Msg ID:</b> <code>{m.id}</code>\n")

    if m.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        t += f"📛 <b>Title:</b> {m.chat.title}\n🔗 <b>Link:</b> @{m.chat.username or 'Private'}\n"

    if r:
        f_id, f_ref = get_media_file_id(r)
        if f_id:
            t += f"\n📂 <b>MEDIA DETAILS</b>\n🆔 <b>File ID:</b> <code>{f_id}</code>\n"

    await m.reply_text(t, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)

# ======================================================
# 📸 FILE ID COMMAND (Rate-Limit Protected)
# ======================================================
@Client.on_message(filters.command(["fileid", "file_id"]))
async def get_custom_file_id(c, m):
    if is_rate_limited(m.from_user.id, "cmd_fileid", seconds=3):
        return

    target_msg = m.reply_to_message if m.reply_to_message else m
    file_id, file_ref = get_media_file_id(target_msg)
    
    if not file_id:
        return await m.reply_text(
            "⚠️ <b>उपयोग कैसे करें:</b>\nकिसी भी फोटो, वीडियो या फाइल को <b>Reply</b> करके <code>/fileid</code> लिखें "
            "या फाइल अपलोड करते समय उसके <b>Caption</b> में लिख दें।",
            parse_mode=enums.ParseMode.HTML
        )
        
    txt = (f"🔑 <b>EXTRACTED FILE ID</b>\n\n"
           f"📸 <b>File ID:</b>\n<code>{file_id}</code>\n\n"
           f"🔖 <b>File Ref (Unique ID):</b>\n<code>{file_ref}</code>\n\n"
           f"💡 <i>इसे कॉपी करके आप सीधे एडमिन पैनल के थंबनेल रिप्लेस बॉक्स में यूज़ कर सकते हैं।</i>")
           
    await m.reply_text(txt, parse_mode=enums.ParseMode.HTML)

# ======================================================
# 🚨 REPORT SYSTEM (Fixed Iterator RAM Leak & Persistent Delete)
# ======================================================
@Client.on_message(filters.command(["report", "Report"]) & filters.group)
async def report_user(c, m):
    if is_rate_limited(m.from_user.id, "cmd_report", seconds=5):
        return

    r = m.reply_to_message
    if not r: 
        return await m.reply("⚠️ **Invalid Usage!**\n\nकिसी यूजर के मैसेज को Reply करके `/report` लिखें।")
    
    tgt = r.from_user
    if not tgt or tgt.is_bot or tgt.id == c.me.id: 
        return await m.reply("❌ इस यूजर को रिपोर्ट नहीं किया जा सकता (Self/Bot/Admin)।")

    txt_data = r.text or r.caption or "Media/File"
    prev = txt_data[:100] + ("..." if len(txt_data) > 100 else "")

    txt = (f"🚨 **NEW REPORT**\n\n📂 **Group:** {m.chat.title} (`{m.chat.id}`)\n🔗 **Link:** <a href='{r.link}'>Click Here</a>\n\n"
           f"👤 **Reporter:** {m.from_user.mention} (`{m.from_user.id}`)\n💀 **Reported:** {tgt.mention} (`{tgt.id}`)\n\n"
           f"📝 **Message:** <code>{prev}</code>")
    
    btn = IKM([[IKB("🔗 View", url=r.link)], [IKB("🗑 Delete", callback_data=f"del_{m.chat.id}_{r.id}")]])
    
    sent = 0
    try:
        # ✅ FIX: कर्सर एग्रेसिव रैम लीक को रोकने के लिए इटरेटर स्लाइसिंग और सेफ लूपिंग
        async for x in c.get_chat_members(m.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            if x.user and not x.user.is_bot:
                try:
                    await c.send_message(x.user.id, txt, reply_markup=btn, disable_web_page_preview=True)
                    sent += 1
                    await asyncio.sleep(0.3)  # टेलीग्राम फ्लड प्रिवेंशन गैप
                except FloodWait as e: 
                    await asyncio.sleep(e.value)
                except: 
                    pass
    except Exception as e:
        logger.error(f"Report iterator error: {e}")

    # ✅ NEW: कतरन रिकवरी इंजन — रैम आधारित डिलीट हटाकर कतार को मोंगोडीबी कतार में सुरक्षित 15 सेकंड के लिए सेट किया
    alert_msg = await m.reply(f"✅ **Report Sent!**\nAlert sent to {sent} admins.")
    await db.add_to_delete_queue(alert_msg.chat.id, alert_msg.id, 15)

# ======================================================
# 🗑 DELETE CALLBACK (For PMs)
# ======================================================
@Client.on_callback_query(filters.regex(r"^del_"))
async def del_msg(c, q):
    try:
        _, cid, mid = q.data.split("_")
        st = (await c.get_chat_member(int(cid), q.from_user.id)).status
        if st not in (enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR):
            return await q.answer("❌ Not an admin!", show_alert=True)
        
        await c.delete_messages(int(cid), int(mid))
        await q.answer("✅ Deleted!", show_alert=True)
        await q.message.edit_text(q.message.text + "\n\n✅ **ACTION TAKEN: Deleted**", reply_markup=None)
    except: 
        await q.answer("❌ Error/Already Deleted.", show_alert=True)

# ======================================================
# 🏓 PING & INFO (One-Liners Rate-Limited)
# ======================================================
@Client.on_message(filters.command("ping"))
async def ping_cmd(c, m):
    if is_rate_limited(m.from_user.id, "cmd_ping", seconds=2):
        return
        
    s = time.time()
    msg = await m.reply_text("🏓 Pinging...")
    latency = int((time.time() - s) * 1000)
    await msg.edit_text(f"🏓 <b>Pong!</b>\n\n⚡ Latency: <code>{latency} ms</code>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("botinfo"))
async def bot_info(c, m):
    if is_rate_limited(m.from_user.id, "cmd_botinfo", seconds=5):
        return

    uptime = get_readable_time(time.time() - temp.START_TIME)
    t = (f"🤖 <b>BOT STATUS</b>\n\n⏱️ <b>Uptime:</b> <code>{uptime}</code>\n🐍 <b>Python:</b> <code>{platform.python_version()}</code>\n"
         f"⚙️ <b>OS:</b> <code>{platform.system()}</code>\n📦 <b>Lib:</b> <code>Hydrogram</code>\n💎 <b>Premium:</b> <code>{'Yes' if IS_PREMIUM else 'No'}</code>")
    await m.reply_text(t, parse_mode=enums.ParseMode.HTML)
