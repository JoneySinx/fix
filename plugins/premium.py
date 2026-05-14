import os, io, qrcode, asyncio, traceback
from datetime import datetime, timedelta
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ✅ यहाँ db के साथ web_db को भी इम्पोर्ट किया है
from database.users_chats_db import db, web_db 

from info import IS_PREMIUM, PRE_DAY_AMOUNT, RECEIPT_SEND_USERNAME, UPI_ID, UPI_NAME, ADMINS, LOG_CHANNEL
from Script import script
# ✅ utils.py से ज़रूरी टूल्स इम्पोर्ट किए
from utils import is_premium, temp, get_readable_time, get_wish 

VERIFY_CACHE = {}

# ✅ एडमिन के लिए कॉमन मैसेज (DRY Principle)
ADMIN_MSG = "👑 **You are the Admin!**\nYou have Lifetime Premium access."
ADMIN_ALERT = "👑 You are the Admin! You have Lifetime Premium access."

# =========================
# 🔧 HELPERS
# =========================
def parse_expire_time(e):
    if isinstance(e, datetime): return e
    try: return datetime.strptime(e, "%Y-%m-%d %H:%M:%S") if e else None
    except: return None

def get_ist_str(dt):
    """Converts UTC to IST String"""
    return (dt + timedelta(hours=5, minutes=30)).strftime("%d %B %Y, %I:%M %p") if dt else "Unknown"

async def safe_del(c, cid, mids):
    try: await c.delete_messages(cid, mids)
    except: pass

# =========================
# ⏰ REMINDER SYSTEM
# =========================
async def check_premium_expired(bot):
    intervals = [
        (715, 725, "reminded_12h", "⏰ **Premium Reminder**\n\nYour plan expires in **12 Hours**.\n🗓 {}"),
        (355, 365, "reminded_6h", "⚠️ **Premium Alert**\n\nYour plan expires in **6 Hours**.\n🗓 {}"),
        (175, 185, "reminded_3h", "⚠️ **Urgent Alert**\n\nYour plan expires in **3 Hours**.\n🗓 {}"),
        (55, 65, "reminded_1h", "🚨 **Critical Alert**\n\nYour plan expires in **1 Hour**.\n🗓 {}"),
        (25, 35, "reminded_30m", "⏳ **Final Warning**\n\nYour plan expires in **30 Minutes**.\nRenew immediately!"),
        (5, 15, "reminded_10m", "🔥 **Expiring Soon**\n\nYour plan expires in **10 Minutes**.\nService will stop soon.")
    ]
    
    while True:
        try:
            now = datetime.now()
            async for p in db.premium.find({"status.premium": True}):
                uid, mp = p["id"], p.get("status", {})
                exp = parse_expire_time(mp.get("expire"))
                if not exp: continue
                
                left_mins = (exp - now).total_seconds() / 60
                
                # Expiry Handler
                if left_mins <= 0:
                    if mp.get("last_reminder_id"): await safe_del(bot, uid, [mp.get("last_reminder_id")])
                    try: await bot.send_message(uid, "❌ **Your Premium Plan has Expired!**\n\nRenew now.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", callback_data="buy_prem")]]))
                    except: pass
                    await db.update_plan(uid, {"expire": "", "plan": "", "premium": False, "reminded_12h": False, "reminded_6h": False, "reminded_3h": False, "reminded_1h": False, "reminded_30m": False, "reminded_10m": False, "last_reminder_id": 0})
                    continue

                for min_t, max_t, flag, text in intervals:
                    if min_t <= left_mins <= max_t and not mp.get(flag):
                        if mp.get("last_reminder_id"): await safe_del(bot, uid, [mp.get("last_reminder_id")])
                        try:
                            msg = await bot.send_message(uid, text.format(get_ist_str(exp)), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Renew Now", callback_data="buy_prem")]]))
                            mp.update({flag: True, "last_reminder_id": msg.id})
                            await db.update_plan(uid, mp)
                        except: pass
                        break
        except Exception as e: print(f"Premium Loop Error: {e}")
        await asyncio.sleep(60)

# =========================
# 📱 COMMANDS
# =========================
@Client.on_message(filters.command("myplan") & filters.private)
async def myplan_cmd(c, m):
    if not IS_PREMIUM: return
    if m.from_user.id in ADMINS: return await m.reply(ADMIN_MSG, quote=True)
        
    mp = await db.get_plan(m.from_user.id)
    if not mp.get("premium"):
        return await m.reply("❌ **No Active Plan**\nTap below to buy!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", callback_data="buy_prem")]]))
    
    exp = parse_expire_time(mp.get("expire"))
    left = f"{(exp - datetime.now()).days} days, {(exp - datetime.now()).seconds // 3600} hours" if exp else "Unknown"
    await m.reply(f"💎 **Premium Status**\n\n📦 **Plan:** {mp.get('plan')}\n🗓 **Expires:** {get_ist_str(exp)}\n⏲ **Time Left:** {left}", quote=True)

@Client.on_message(filters.command("plan") & filters.private)
async def plan_cmd(c, m):
    if not IS_PREMIUM: return
    if m.from_user.id in ADMINS: return await m.reply(ADMIN_MSG, quote=True)
        
    await m.reply(script.PLAN_TXT.format(PRE_DAY_AMOUNT, RECEIPT_SEND_USERNAME), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Activate Premium", callback_data="buy_prem")]]))

@Client.on_message(filters.command(["add_prm", "rm_prm"]) & filters.user(ADMINS))
async def manage_premium(c, m):
    if not IS_PREMIUM: return
    cmd, is_add = m.command, m.command[0] == "add_prm"
    if len(cmd) < 2: return await m.reply(f"Usage: `/{cmd[0]} user_id {'days' if is_add else ''}`")
    
    try: uid, days = int(cmd[1]), int(cmd[2][:-1] if cmd[2].endswith('d') else cmd[2]) if is_add and len(cmd) > 2 else 0
    except: return await m.reply("❌ Invalid Format!")

    if is_add:
        ex = datetime.now() + timedelta(days=days)
        data = {"expire": ex.strftime("%Y-%m-%d %H:%M:%S"), "plan": f"{days} Days", "premium": True, "reminded_12h": False, "reminded_6h": False, "reminded_3h": False, "reminded_1h": False, "reminded_30m": False, "reminded_10m": False, "last_reminder_id": 0}
        m_usr, m_adm = f"🎉 **Premium Activated!**\n\n🗓 **Duration:** {days} Days\n📅 **Expires:** {get_ist_str(ex)}\n\nEnjoy! ❤️", f"✅ Added {days} days premium to `{uid}`."
    else:
        data, m_usr, m_adm = {"expire": "", "plan": "", "premium": False}, "❌ **Premium Removed by Admin.**", f"🗑 Removed premium from `{uid}`."

    await db.update_plan(uid, data)
    await m.reply(m_adm)
    
    for action in (lambda: c.send_message(uid, m_usr), lambda: c.send_message(LOG_CHANNEL, f"#PremiumUpdate\nUser: `{uid}`\nAction: {cmd[0]}")):
        try: await action()
        except: pass

@Client.on_message(filters.command("prm_list") & filters.user(ADMINS))
async def prm_list(c, m):
    if not IS_PREMIUM: return
    msg, count, text = await m.reply("🔄 Fetching..."), 0, "💎 **Premium Users**\n\n"
    async for u in await db.get_premium_users():
        if u.get("status", {}).get("premium"):
            count += 1
            text += f"👤 `{u['id']}` | 🗓 {u['status'].get('plan')}\n"
    await msg.edit(text + (f"\n**Total:** {count}" if count > 0 else "📭 No premium users."))

# ✅ NAYA COMMAND: वेब यूज़र्स की लिस्ट देखने के लिए
@Client.on_message(filters.command("web_users") & filters.user(ADMINS))
async def list_web_users(c, m):
    msg = await m.reply("🔄 Fetching Web Users...")
    count = 0
    text = "🌐 **Fast Finder Web Users**\n\n"
    
    async for u in web_db.col.find():
        count += 1
        joined = u.get('joined_date')
        joined_str = joined.strftime("%d %b %Y") if joined else "Unknown"
        text += f"👤 **TG ID:** `{u['tg_id']}`\n📧 **Email:** `{u['email']}`\n📅 **Joined:** {joined_str}\n\n"
        
    if count == 0:
        await msg.edit("📭 अभी तक किसी ने वेब पर रजिस्टर नहीं किया है।")
    else:
        text += f"**Total Web Users:** {count}"
        await msg.edit(text)

# =========================
# 🔘 CALLBACKS
# =========================
@Client.on_callback_query(filters.regex("^myplan$"))
async def myplan_cb(client, query):
    if query.from_user.id in ADMINS: return await query.answer(ADMIN_ALERT, show_alert=True)

    if not IS_PREMIUM: return await query.answer("Premium disabled.", show_alert=True)
    mp = await db.get_plan(query.from_user.id)
    btn = [[InlineKeyboardButton("⬅️ Back", callback_data="back_start")]]
    
    if not mp.get('premium'):
        btn.insert(0, [InlineKeyboardButton('💎 Buy Premium', callback_data='activate_plan')])
        return await query.message.edit_caption("❌ No active plan.", reply_markup=InlineKeyboardMarkup(btn))
    
    exp = parse_expire_time(mp.get('expire'))
    left = f"{(exp - datetime.now()).days} days, {(exp - datetime.now()).seconds//3600} hours" if exp else "Unknown"
    await query.message.edit_caption(f"💎 <b>Premium Status</b>\n\n📦 Plan: {mp.get('plan')}\n⏳ Expires: {get_ist_str(exp)}\n⏱ Left: {left}\n\nUse /plan to extend.", reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^(buy_prem|activate_plan)$"))
async def buy_callback(c, q):
    if q.from_user.id in ADMINS: return await q.answer(ADMIN_ALERT, show_alert=True)

    prm_msg = await q.message.edit(f"💎 **Select Plan Duration**\n\nSend days (e.g. `30`).\nPrice: ₹{PRE_DAY_AMOUNT}/day\n\n⏳ Timeout: 60s")
    try:
        resp = await c.listen(q.message.chat.id, timeout=60)
        await safe_del(c, q.message.chat.id, [prm_msg.id, resp.id])
        days = int(resp.text)
        amount = days * int(PRE_DAY_AMOUNT)
        
        img = qrcode.make(f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR")
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        
        qr_msg = await q.message.reply_photo(photo=bio, caption=f"💳 **Pay ₹{amount}**\n\nScan & Pay. Then send screenshot here.\n\n⏳ Timeout: 5 mins")
        receipt = await c.listen(q.message.chat.id, timeout=300)
        
        if not receipt.photo: return await q.message.reply("❌ **Invalid!** Send a photo.")
        
        await safe_del(c, q.message.chat.id, [qr_msg.id])
        VERIFY_CACHE[q.from_user.id] = (await q.message.reply("✅ **Sent for Verification!**\nAdmin will activate shortly.")).id
        
        await receipt.copy(RECEIPT_SEND_USERNAME, caption=f"#Payment\n👤: {q.from_user.mention} (`{q.from_user.id}`)\n💰: ₹{amount} ({days} days)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"pay_confirm_{q.from_user.id}_{days}"), InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject_{q.from_user.id}")]]))
    except ValueError: await q.message.reply("❌ Invalid Number!")
    except asyncio.TimeoutError:
        # ✅ पेमेंट टाइमआउट होने पर VERIFY_CACHE क्लीनअप फिक्स
        VERIFY_CACHE.pop(q.from_user.id, None)
        await q.message.reply("⏳ **Timeout!** Process cancelled.")
    except Exception as e: await q.message.reply(f"❌ **Error:** `{e}`")

@Client.on_callback_query(filters.regex(r"^pay_(confirm|reject)_"))
async def pay_action(c, q):
    if q.from_user.id not in ADMINS: return await q.answer("❌ Only Admins!", show_alert=True)
    _, act, uid = q.data.split("_")[:3]
    uid = int(uid)

    if act == "confirm":
        days = int(q.data.split("_")[3])
        ex = datetime.now() + timedelta(days=days)
        await db.update_plan(uid, {"expire": ex.strftime("%Y-%m-%d %H:%M:%S"), "plan": f"{days} Days", "premium": True, "reminded_12h": False, "reminded_6h": False, "reminded_3h": False, "reminded_1h": False, "reminded_30m": False, "reminded_10m": False, "last_reminder_id": 0})
        await q.message.edit_caption(caption=q.message.caption + f"\n\n✅ **Approved by** {q.from_user.mention}", reply_markup=None)
        try: await c.send_message(uid, f"🎉 **Congratulations!**\n\n✅ Your premium of **{days} Days** is Active.\n📅 **Expires:** {get_ist_str(ex)}\n\nEnjoy our service! ❤️")
        except: pass
    else:
        await q.message.edit_caption(caption=q.message.caption + f"\n\n❌ **Rejected by** {q.from_user.mention}", reply_markup=None)
        try: await c.send_message(uid, "❌ **Payment Rejected!**\nContact admin manually.")
        except: pass
        
    if uid in VERIFY_CACHE:
        await safe_del(c, uid, [VERIFY_CACHE.pop(uid)])
