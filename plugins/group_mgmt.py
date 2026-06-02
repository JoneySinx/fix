import asyncio
import time
import logging
from hydrogram import Client, filters, enums
from hydrogram.types import ChatPermissions
from database.users_chats_db import db
from utils import get_settings, save_group_settings, is_check_admin, get_seconds

logger = logging.getLogger(__name__)

# =========================================
# 🛡️ LOCAL SECURITY GUARD
# =========================================
async def is_admin(c, m):
    if m.sender_chat and m.sender_chat.id == m.chat.id: 
        return True
    if not m.from_user: 
        return False
    return await is_check_admin(c, m.chat.id, m.from_user.id)

# =========================================
# 🔨 ADMIN ACTIONS (Auto-Ban on 3rd Warn Added)
# =========================================
@Client.on_message(filters.group & filters.reply & filters.command(["mute", "unmute", "ban", "warn", "resetwarn"]))
async def admin_action(c, m):
    if not await is_admin(c, m): return
    target = m.reply_to_message.from_user
    if not target: 
        return await m.reply("❌ Cannot perform action on anonymous/channel message.")

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
            
            if data["count"] >= 3:
                # 3 चेतावनियाँ पूरी होने पर ऑटो-बैन एक्शन एक्जीक्यूट करें
                await c.ban_chat_member(cid, tid)
                await db.clear_warn(tid, cid)
                await m.reply(f"🚨 {mention} received 3/3 warnings and has been **BANNED** from the group!")
            else:
                await db.set_warn(tid, cid, data)
                await m.reply(f"⚠️ {mention} warned ({data['count']}/3).")
                
        elif cmd == "resetwarn":
            await db.clear_warn(tid, cid)
            await m.reply(f"♻️ Warnings reset for {mention}.")
            
    except Exception as e:
        logger.error(f"Admin action failed: {e}")
        await m.reply("❌ Action failed! Check bot permissions.")

# =========================================
# ⚙️ CONFIGURATION (Blacklist & DLink)
# =========================================
@Client.on_message(filters.group & filters.command(["addblacklist", "removeblacklist", "blacklist", "dlink", "removedlink", "dlinklist"]))
async def config_handler(c, m):
    if not await is_admin(c, m): return
    cmd = m.command[0]
    data = await get_settings(m.chat.id)
    
    try:
        args = m.text.split(maxsplit=1)[1].strip()
    except IndexError:
        args = ""

    # --- View Lists ---
    if cmd in ["blacklist", "dlinklist"]:
        if cmd == "blacklist":
            items = "\n".join(f"• `{w}`" for w in data.get("blacklist", [])) or "📭 Empty"
            return await m.reply(f"🚫 **Group Blacklist:**\n{items}")
        items = "\n".join(f"• `{k}` ({v}s)" for k, v in data.get("dlink", {}).items()) or "📭 Empty"
        return await m.reply(f"🕒 **Timed DLinks Queue:**\n{items}")

    if not args: 
        return await m.reply("❗ Please provide a word/trigger.")

    # --- Modify Lists ---
    if "blacklist" in cmd:
        bl = data.get("blacklist", [])
        args_lower = args.lower()
        if cmd == "addblacklist" and args_lower not in bl: 
            bl.append(args_lower)
        elif cmd == "removeblacklist" and args_lower in bl: 
            bl.remove(args_lower)
        
        await db.update_settings(m.chat.id, {**data, "blacklist": bl})
        await m.reply(f"✅ Blacklist updated for: `{args_lower}`")

    elif "dlink" in cmd:
        dl = data.get("dlink", {})
        if cmd == "dlink":
            parts = args.split()
            delay = 300  # Default 5 mins
            
            # 's', 'min', 'hour', 'day' आदि सभी टाइमर फ़ॉर्मेट्स को सिंक किया गया
            if len(parts) > 1 and parts[0][0].isdigit():
                time_string = parts[0].lower()
                parsed_seconds = await get_seconds(time_string)
                if parsed_seconds > 0:
                    delay = parsed_seconds
                    args = " ".join(parts[1:])
                
            dl[args.lower()] = delay
            await db.update_settings(m.chat.id, {**data, "dlink": dl})
            await m.reply(f"🕒 DLink set: `{args.lower()}` -> จะถูกลบใน {delay}s")
        else:
            dl.pop(args.lower(), None)
            await db.update_settings(m.chat.id, {**data, "dlink": dl})
            await m.reply(f"🗑️ DLink removed: `{args.lower()}`")
