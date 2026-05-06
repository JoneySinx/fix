import asyncio
import time
from hydrogram import Client, filters, enums
from hydrogram.types import ChatPermissions
from database.users_chats_db import db

# =========================
# 🧠 SMART CACHE SYSTEM
# =========================
SETTINGS_CACHE = {}
CACHE_TTL = 300  

async def get_settings(chat_id):
    now = time.time()
    # 🧹 Auto-clean expired cache (RAM Saver)
    if len(SETTINGS_CACHE) > 500:
        for k in [k for k, (v, ts) in SETTINGS_CACHE.items() if now - ts > CACHE_TTL]:
            del SETTINGS_CACHE[k]

    if chat_id in SETTINGS_CACHE and (now - SETTINGS_CACHE[chat_id][1]) < CACHE_TTL:
        return SETTINGS_CACHE[chat_id][0]

    data = await db.get_settings(chat_id) or {}
    SETTINGS_CACHE[chat_id] = (data, now)
    return data

async def update_settings(chat_id, data):
    SETTINGS_CACHE[chat_id] = (data, time.time())
    await db.update_settings(chat_id, data)

async def is_admin(c, m):
    # 🔒 SUPER SECURE: Only real anonymous admins of THIS group, not random channels
    if m.sender_chat and m.sender_chat.id == m.chat.id: return True
    if not m.from_user: return False
    try:
        user = await c.get_chat_member(m.chat.id, m.from_user.id)
        return user.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
    except:
        return False

# =========================
# 🛡️ ADMIN ACTIONS
# =========================

@Client.on_message(filters.group & filters.reply & filters.command(["mute", "unmute", "ban", "warn", "resetwarn"]))
async def admin_action(c, m):
    if not await is_admin(c, m): return
    target = m.reply_to_message.from_user
    if not target: return await m.reply("❌ Cannot perform action on anonymous/channel message.")

    cmd = m.command[0]
    cid, tid, mention = m.chat.id, target.id, target.mention

    try:
        if cmd == "mute":
            await c.restrict_chat_member(cid, tid, ChatPermissions(), until_date=int(time.time() + 600))
            await m.reply(f"🔇 {mention} muted for 10m.")
        elif cmd == "unmute":
            await c.restrict_chat_member(cid, tid, ChatPermissions(can_send_messages=True))
            await m.reply(f"🔊 {mention} unmuted.")
        elif cmd == "ban":
            await c.ban_chat_member(cid, tid)
            await m.reply(f"🚫 {mention} banned.")
        elif cmd == "warn":
            data = await db.get_warn(tid, cid) or {"count": 0}
            data["count"] += 1
            await db.set_warn(tid, cid, data)
            await m.reply(f"⚠️ {mention} warned ({data['count']}/3).")
        elif cmd == "resetwarn":
            await db.clear_warn(tid, cid)
            await m.reply(f"♻️ Warnings reset for {mention}.")
    except Exception:
        await m.reply("❌ Action failed! Am I admin? Do I have the right permissions?")

# =========================
# ⚙️ CONFIGURATION (Blacklist & DLink)
# =========================

@Client.on_message(filters.group & filters.command(["addblacklist", "removeblacklist", "blacklist", "dlink", "removedlink", "dlinklist"]))
async def config_handler(c, m):
    if not await is_admin(c, m): return
    cmd = m.command[0]
    data = await get_settings(m.chat.id)
    args = m.text.split(maxsplit=1)[1].lower() if len(m.command) > 1 else ""

    # --- View Lists ---
    if cmd in ["blacklist", "dlinklist"]:
        if cmd == "blacklist":
            items = "\n".join(f"• `{w}`" for w in data.get("blacklist", [])) or "📭 Empty"
            return await m.reply(f"🚫 **Blacklist:**\n{items}")
        items = "\n".join(f"• `{k}` ({v}s)" for k, v in data.get("dlink", {}).items()) or "📭 Empty"
        return await m.reply(f"🕒 **DLinks:**\n{items}")

    if not args: return await m.reply("❗ Please provide a word.")

    # --- Modify Lists ---
    if "blacklist" in cmd:
        bl = data.get("blacklist", [])
        if cmd == "addblacklist" and args not in bl: bl.append(args)
        elif cmd == "removeblacklist" and args in bl: bl.remove(args)
        data["blacklist"] = bl
        await m.reply(f"✅ Blacklist updated for: `{args}`")

    elif "dlink" in cmd:
        dl = data.get("dlink", {})
        if cmd == "dlink":
            parts = args.split()
            delay = 300 # Default 5 mins
            if len(parts) > 1 and parts[0][-1] in "mh" and parts[0][:-1].isdigit():
                delay = int(parts[0][:-1]) * (60 if parts[0][-1] == "m" else 3600)
                args = " ".join(parts[1:])
            dl[args] = delay
            await m.reply(f"🕒 DLink set: `{args}` -> {delay}s")
        else:
            dl.pop(args, None)
            await m.reply(f"🗑️ DLink removed: `{args}`")
        data["dlink"] = dl

    await update_settings(m.chat.id, data)

# =========================
# 👁️ SMART WATCHER
# =========================

# ✅ टाइमर वाला फंक्शन (Background deletion के लिए)
async def delayed_delete(msg, delay):
    await asyncio.sleep(delay)
    try: await msg.delete()
    except: pass

@Client.on_message(filters.group & filters.text, group=10)
async def chat_watcher(c, m):
    text = m.text.lower()
    data = await get_settings(m.chat.id)
    
    # ----------------------------------------------------
    # Block A: DLink (APPLIES TO EVERYONE - Even Admins)
    # ----------------------------------------------------
    dlinks = data.get("dlink", {})
    for w, delay in dlinks.items():
        # Match word exactly OR match word with wildcard prefix 
        if w in text or (w.endswith("*") and text.startswith(w[:-1])):
            # Task को background में डाल दिया ताकि बॉट रुके नहीं
            asyncio.create_task(delayed_delete(m, delay))
            return 

    # ----------------------------------------------------
    # Block B: Blacklist (ONLY FOR MEMBERS, Ignore Admins)
    # ----------------------------------------------------
    if await is_admin(c, m): return
    
    for w in data.get("blacklist", []):
        if w in text or (w.endswith("*") and text.startswith(w[:-1])):
            try: await m.delete()
            except: pass
            return

# =========================
# 🤖 ANTI BOT & HELP
# =========================

@Client.on_message(filters.group & filters.new_chat_members)
async def anti_bot(c, m):
    # If the person adding the bot is an admin, allow it. Otherwise, ban the bot.
    if await is_admin(c, m): return
    for u in m.new_chat_members:
        if u.is_bot:
            try: await c.ban_chat_member(m.chat.id, u.id)
            except: pass

@Client.on_message(filters.group & filters.command("help"))
async def help_cmd(c, m):
    if await is_admin(c, m):
        await m.reply(
            "🛠️ **Admin Menu**\n"
            "• `/mute`, `/unmute`, `/ban`, `/warn`, `/resetwarn` (Reply to user)\n"
            "• `/addblacklist <word>`, `/removeblacklist <word>`, `/blacklist`\n"
            "• `/dlink [time] <word>` (e.g. `/dlink 10m link`), `/removedlink <word>`, `/dlinklist`"
        )
