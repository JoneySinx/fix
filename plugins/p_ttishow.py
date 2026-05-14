import os, sys, random
from hydrogram import Client, filters, enums
from info import ADMINS, LOG_CHANNEL, PICS
from database.users_chats_db import db
from utils import temp
from Script import script

# ======================================================
# 👋 WELCOME MESSAGE & LOGGER
# ======================================================
@Client.on_chat_member_updated()
async def welcome(c, m):
    if m.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP) and m.new_chat_member and not m.old_chat_member:
        if m.new_chat_member.user.id == temp.ME:
            u = m.from_user.mention if m.from_user else "Admin"
            await c.send_photo(m.chat.id, random.choice(PICS), f"👋 Hello {u},\n\nThanks for adding me to **{m.chat.title}**!\nDon't forget to make me Admin.")
            
            if not await db.get_chat(m.chat.id):
                uname = f'@{m.chat.username}' if m.chat.username else 'Private'
                total = await c.get_chat_members_count(m.chat.id)
                await c.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(m.chat.title, m.chat.id, uname, total))       
                await db.add_chat(m.chat.id, m.chat.title)

# ======================================================
# 🔄 RESTART, LEAVE & INVITE (Merged)
# ======================================================
@Client.on_message(filters.command('restart') & filters.user(ADMINS))
async def restart_bot(c, m):
    msg = await m.reply("🔄 Restarting...")
    with open('restart.txt', 'w') as f: f.write(f"{m.chat.id} {msg.id}")
    os.execl(sys.executable, sys.executable, "bot.py")

@Client.on_message(filters.command(['leave', 'invite_link']) & filters.user(ADMINS))
async def chat_actions(c, m):
    if len(m.command) < 2: return await m.reply(f'Usage: `/{m.command[0]} chat_id`')
    try:
        cid = int(m.command[1])
        if m.command[0] == 'leave':
            await c.leave_chat(cid)
            await m.reply(f"✅ Left chat `{cid}`")
        else:
            link = await c.create_chat_invite_link(cid)
            await m.reply(f"🔗 Invite Link: {link.invite_link}")
    except Exception as e: await m.reply(f"❌ Error: {e}")

# ======================================================
# 🚫 BAN / UNBAN SYSTEM (Users & Groups Merged)
# ======================================================
@Client.on_message(filters.command(['ban_grp', 'unban_grp', 'ban_user', 'unban_user']) & filters.user(ADMINS))
async def ban_system(c, m):
    cmd = m.command[0]
    if len(m.command) < 2: return await m.reply(f'Usage: `/{cmd} id [reason]`')
    try: tgt_id = int(m.command[1])
    except: return await m.reply("❌ Invalid ID")
    
    rsn = " ".join(m.command[2:]) or "Violation of Rules / Admin Action"
    
    if 'user' in cmd:
        if tgt_id in ADMINS: return await m.reply("❌ Cannot ban Admin!")
        if 'unban' in cmd:
            await db.unban_user(tgt_id)
            if tgt_id in temp.BANNED_USERS: temp.BANNED_USERS.remove(tgt_id)
            await m.reply(f"✅ User `{tgt_id}` Unbanned.")
        else:
            await db.ban_user(tgt_id, rsn)
            temp.BANNED_USERS.append(tgt_id)
            await m.reply(f"✅ User `{tgt_id}` Banned.\nReason: {rsn}")
    else:
        if 'unban' in cmd:
            await db.re_enable_chat(tgt_id)
            if tgt_id in temp.BANNED_CHATS: temp.BANNED_CHATS.remove(tgt_id)
            await m.reply(f"✅ Chat `{tgt_id}` re-enabled.")
        else:
            await db.disable_chat(tgt_id, rsn)
            temp.BANNED_CHATS.append(tgt_id)
            await m.reply(f"✅ Chat `{tgt_id}` disabled.\nReason: {rsn}")
            try: await c.leave_chat(tgt_id)
            except: pass

# ======================================================
# 📜 DATABASE EXPORT & STATS (Merged & Optimized)
# ======================================================
@Client.on_message(filters.command(['users', 'chats']) & filters.user(ADMINS))
async def export_db(c, m):
    is_user = m.command[0] == 'users'
    typ, fn = ('User', 'users.txt') if is_user else ('Chat', 'chats.txt')
    
    msg = await m.reply(f'🔄 Generating {typ} List...')
    cnt = 0
    with open(fn, 'w') as f:
        # ✅ Optimized Database Calls 
        cursor = await db.get_all_users() if is_user else await db.get_all_chats()
        async for x in cursor:
            f.write(f"ID: {x['id']} | Name/Title: {x.get('name' if is_user else 'title', 'N/A')}\n")
            cnt += 1
            
    if cnt == 0:
        os.remove(fn)
        return await msg.edit("📭 Database Empty.")

    await m.reply_document(fn, caption=f"👥 Total {typ}s: {cnt}")
    await msg.delete()
    os.remove(fn)

@Client.on_message(filters.command('stats') & filters.user(ADMINS))
async def quick_stats(c, m):
    msg = await m.reply('🔄 Fetching stats...')
    # ✅ Optimized Database Calls
    u_count = await db.total_users_count()
    c_count = await db.total_chat_count()
    await msg.edit(f"📊 **BOT DATABASE STATS**\n\n👤 **Total Users:** `{u_count}`\n👥 **Total Groups:** `{c_count}`")
