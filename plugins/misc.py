import time, sys, platform, asyncio
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB
from hydrogram.errors import FloodWait
from utils import temp, get_readable_time
from info import IS_PREMIUM

# ======================================================
# 🆔 ID COMMAND (Compact)
# ======================================================
@Client.on_message(filters.command("id"))
async def get_id(c, m):
    r = m.reply_to_message
    u = r.from_user if r and r.from_user else m.from_user
    
    b = "👤 Member"
    if m.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        try:
            # ✅ BUG FIX: Corrected get_chat_member syntax
            st = (await c.get_chat_member(m.chat.id, u.id)).status
            b = "👑 Owner" if st == enums.ChatMemberStatus.OWNER else "🛡 Admin" if st in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.ADMIN) else b
        except: pass

    t = (f"🆔 <b>ID INFORMATION</b>\n\n👤 <b>Name:</b> {u.first_name or ''} {u.last_name or ''}\n🦹 <b>User ID:</b> <code>{u.id}</code>\n"
         f"🏷 <b>Username:</b> @{u.username or 'N/A'}\n🌐 <b>DC ID:</b> <code>{u.dc_id or 'Unknown'}</code>\n🤖 <b>Bot:</b> {'Yes' if u.is_bot else 'No'}\n"
         f"{b}\n🔗 <b>Profile:</b> <a href='tg://user?id={u.id}'>Open</a>\n\n💬 <b>CHAT & MESSAGE</b>\n🆔 <b>Chat ID:</b> <code>{m.chat.id}</code>\n"
         f"📩 <b>Msg ID:</b> <code>{m.id}</code>\n")

    if m.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        t += f"📛 <b>Title:</b> {m.chat.title}\n🔗 <b>Link:</b> @{m.chat.username or 'Private'}\n"

    if r and r.sticker:
        t += (f"\n🎭 <b>STICKER DETAILS</b>\n🆔 <b>File ID:</b> <code>{r.sticker.file_id}</code>\n📦 <b>Set:</b> <code>{r.sticker.set_name or 'N/A'}</code>\n"
              f"🔖 <b>Emoji:</b> {r.sticker.emoji or 'N/A'}\n🎞 <b>Anim:</b> {'Yes' if r.sticker.is_animated else 'No'} | <b>Vid:</b> {'Yes' if r.sticker.is_video else 'No'}\n")

    await m.reply_text(t, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)

# ======================================================
# 🚨 REPORT SYSTEM (Anti-Spam Fixed & Minified)
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
    # ✅ BUG FIX: Corrected get_chat_members async loop syntax
    async for x in c.get_chat_members(m.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
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
    # ✅ OPTIMIZED: utils.py से get_readable_time का इस्तेमाल किया गया
    uptime = get_readable_time(time.time() - temp.START_TIME)
    t = (f"🤖 <b>BOT STATUS</b>\n\n⏱️ <b>Uptime:</b> <code>{uptime}</code>\n🐍 <b>Python:</b> <code>{sys.version.split()[0]}</code>\n"
         f"⚙️ <b>OS:</b> <code>{platform.system()}</code>\n📦 <b>Lib:</b> <code>Hydrogram</code>\n💎 <b>Premium:</b> <code>{'Yes' if IS_PREMIUM else 'No'}</code>")
    await m.reply_text(t, parse_mode=enums.ParseMode.HTML)
