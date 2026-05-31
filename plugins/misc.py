import time, sys, platform, asyncio
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB
from hydrogram.errors import FloodWait
from utils import temp, get_readable_time
from info import IS_PREMIUM

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
# 🆔 ID COMMAND (Upgraded for Media support)
# ======================================================
@Client.on_message(filters.command("id"))
async def get_id(c, m):
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

    # अगर किसी मीडिया मैसेज पर रिप्लाई करके /id मारा गया है
    if r:
        f_id, f_ref = get_media_file_id(r)
        if f_id:
            t += f"\n📂 <b>MEDIA DETAILS</b>\n🆔 <b>File ID:</b> <code>{f_id}</code>\n"

    await m.reply_text(t, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)

# ======================================================
# 📸 FILE ID COMMAND (New Feature for Admin Panel)
# ======================================================
@Client.on_message(filters.command(["fileid", "file_id"]))
async def get_custom_file_id(c, m):
    # रिप्लाई वाला मैसेज चेक करें, नहीं तो खुद का मैसेज (अगर कैप्शन में कमांड है)
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
# 🚨 REPORT SYSTEM (Fixed Iterator Crash)
# ======================================================
@Client.on_message(filters.command(["report", "Report"]) & filters.group)
async def report_user(c, m):
    r = m.reply_to_message
    if not r: return await m.reply("⚠️ **Invalid Usage!**\n\nकिसी यूजर के मैसेज को Reply करके `/report` लिखें।")
    
    tgt = r.from_user
    if not tgt or tgt.is_bot or tgt.id == c.me.id: 
        return await m.reply("❌ इस यूजर को रिपोर्ट नहीं किया जा सकता (Self/Bot/Admin)।")

    txt_data = r.text or r.caption or "Media/File"
    prev = txt_data[:100] + ("..." if len(txt_data) > 100 else "")

    txt = (f"🚨 **NEW REPORT**\n\n📂 **Group:** {m.chat.title} (`{m.chat.id}`)\n🔗 **Link:** <a href='{r.link}'>Click Here</a>\n\n"
           f"👤 **Reporter:** {m.from_user.mention} (`{m.from_user.id}`)\n💀 **Reported:** {tgt.mention} (`{tgt.id}`)\n\n📝 **Message:** <code>{prev}</code>")
    
    btn = IKM([[IKB("🔗 View", url=r.link)], [IKB("🗑 Delete", callback_data=f"del_{m.chat.id}_{r.id}")]])
    
    sent = 0
    async for x in c.get_chat_members(m.chat.id, filter="administrators"):
        if not x.user.is_bot:
            try:
                await c.send_message(x.user.id, txt, reply_markup=btn, disable_web_page_preview=True)
                sent += 1
                await asyncio.sleep(0.3)
            except FloodWait as e: await asyncio.sleep(e.value)
            except: pass

    await m.reply(f"✅ **Report Sent!**\nAlert sent to {sent} admins.")

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
    except: await q.answer("❌ Error/Already Deleted.", show_alert=True)

# ======================================================
# 🏓 PING & INFO (One-Liners)
# ======================================================
@Client.on_message(filters.command("ping"))
async def ping_cmd(c, m):
    s = time.time()
    msg = await m.reply_text("🏓 Pinging...")
    await msg.edit_text(f"🏓 <b>Pong!</b>\n\n⚡ Latency: <code>{int((time.time() - s) * 1000)} ms</code>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("botinfo"))
async def bot_info(c, m):
    uptime = get_readable_time(time.time() - temp.START_TIME)
    t = (f"🤖 <b>BOT STATUS</b>\n\n⏱️ <b>Uptime:</b> <code>{uptime}</code>\n🐍 <b>Python:</b> <code>{sys.version.split()[0]}</code>\n"
         f"⚙️ <b>OS:</b> <code>{platform.system()}</code>\n📦 <b>Lib:</b> <code>Hydrogram</code>\n💎 <b>Premium:</b> <code>{'Yes' if IS_PREMIUM else 'No'}</code>")
    await m.reply_text(t, parse_mode=enums.ParseMode.HTML)
