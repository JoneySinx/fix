import os
import io
import qrcode
import asyncio
import traceback
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ─────────────────────────────────────────────────────────
# 🔥 CRITICAL NATIVE PATCH: Forced Event Loop for Sync
# ─────────────────────────────────────────────────────────
try:
    asyncio.get_running_loop()
except RuntimeError:
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import pyromod.listen 
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# डेटाबेस इम्पोर्ट्स
from database.users_chats_db import db, web_db 
from info import IS_PREMIUM, PRE_DAY_AMOUNT, RECEIPT_SEND_USERNAME, UPI_ID, UPI_NAME, ADMINS, LOG_CHANNEL
from Script import script
from utils import temp, get_readable_time, get_wish 

logger = logging.getLogger(__name__)
VERIFY_CACHE = {}

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
# 💎 PREMIUM CHECKER
# =========================
async def is_premium(uid, bot):
    if not IS_PREMIUM or uid in ADMINS: return True
    mp = await db.get_plan(uid)[span_6](start_span)[span_6](end_span)[span_7](start_span)[span_7](end_span)
    if mp.get("premium"):[span_8](start_span)[span_8](end_span)[span_9](start_span)[span_9](end_span)
        exp = parse_expire_time(mp.get("expire"))[span_10](start_span)[span_10](end_span)[span_11](start_span)[span_11](end_span)
        if exp and exp < datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None):[span_12](start_span)[span_12](end_span)[span_13](start_span)[span_13](end_span)
            try: 
                await bot.send_message(
                    uid, 
                    "❌ **Plan Expired!**\nRenew with /plan", 
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", callback_data="buy_prem")]])
                )
            except: pass
            await db.update_plan(uid, {"expire": "", "plan": "", "premium": False})[span_14](start_span)[span_14](end_span)[span_15](start_span)[span_15](end_span)
            return False
        return True
    return False

# =========================
# ⏰ REMINDER SYSTEM (CPU Spike & RAM Leak Fixed)
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
            now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)[span_16](start_span)[span_16](end_span)[span_17](start_span)[span_17](end_span)
            limit_time = (now + timedelta(hours=13)).strftime("%Y-%m-%d %H:%M:%S")[span_18](start_span)[span_18](end_span)
            
            # ✅ FIX: कर्सर रैम लीक को रोकने के लिए केवल आवश्यक फील्ड्स मंगवाईं (Projection Added)
            cursor = db.premium.find(
                {"status.premium": True, "status.expire": {"$lte": limit_time}},
                {"id": 1, "status": 1}
            )
            
            async for p in cursor:
                uid, mp = p["id"], p.get("status", {})[span_19](start_span)[span_19](end_span)
                exp = parse_expire_time(mp.get("expire"))[span_20](start_span)[span_20](end_span)
                if not exp: continue
                
                left_mins = (exp - now).total_seconds() / 60[span_21](start_span)[span_21](end_span)
                
                # Expiry Handler
                if left_mins <= 0:[span_22](start_span)[span_22](end_span)
                    if mp.get("last_reminder_id"): await safe_del(bot, uid, [mp.get("last_reminder_id")])[span_23](start_span)[span_23](end_span)
                    try: 
                        await bot.send_message(
                            uid, 
                            "❌ **Your Premium Plan has Expired!**\n\nRenew now.", 
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", callback_data="buy_prem")]])
                        )
                    except: pass
                    await db.update_plan(uid, {"expire": "", "plan": "", "premium": False, "reminded_12h": False, "reminded_6h": False, "reminded_3h": False, "reminded_1h": False, "reminded_30m": False, "reminded_10m": False, "last_reminder_id": 0})[span_24](start_span)[span_24](end_span)[span_25](start_span)[span_25](end_span)
                    continue

                for min_t, max_t, flag, text in intervals:[span_26](start_span)[span_26](end_span)
                    if min_t <= left_mins <= max_t and not mp.get(flag):[span_27](start_span)[span_27](end_span)
                        if mp.get("last_reminder_id"): await safe_del(bot, uid, [mp.get("last_reminder_id")])[span_28](start_span)[span_28](end_span)
                        try:
                            msg = await bot.send_message(uid, text.format(get_ist_str(exp)), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Renew Now", callback_data="buy_prem")]]))[span_29](start_span)[span_29](end_span)
                            mp.update({flag: True, "last_reminder_id": msg.id})[span_30](start_span)[span_30](end_span)
                            await db.update_plan(uid, mp)[span_31](start_span)[span_31](end_span)[span_32](start_span)[span_32](end_span)
                        except: pass
                        break
        except Exception as e: 
            logger.error(f"Premium Loop Error: {e}")[span_33](start_span)[span_33](end_span)
        
        # ✅ FIX: चाहे एरर आए या न आए, 60 सेकंड का स्लीप हमेशा अंत में सिक्योर रहेगा ताकि CPU ब्लास्ट न हो
        await asyncio.sleep(60)[span_34](start_span)[span_34](end_span)

# =========================
# 📱 COMMANDS
# =========================
@Client.on_message(filters.command("myplan") & filters.private)
async def myplan_cmd(c, m):
    if not IS_PREMIUM: return
    if m.from_user.id in ADMINS: return await m.reply(ADMIN_MSG, quote=True)[span_35](start_span)[span_35](end_span)
        
    mp = await db.get_plan(m.from_user.id)[span_36](start_span)[span_36](end_span)[span_37](start_span)[span_37](end_span)
    if not mp.get("premium"):[span_38](start_span)[span_38](end_span)[span_39](start_span)[span_39](end_span)
        return await m.reply("❌ **No Active Plan**\nTap below to buy!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", callback_data="buy_prem")]]))[span_40](start_span)[span_40](end_span)
    
    exp = parse_expire_time(mp.get("expire"))[span_41](start_span)[span_41](end_span)[span_42](start_span)[span_42](end_span)
    now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)[span_43](start_span)[span_43](end_span)
    left = f"{(exp - now).days} days, {(exp - now).seconds // 3600} hours" if exp else "Unknown[span_44](start_span)"[span_44](end_span)
    await m.reply(f"💎 **Premium Status**\n\n📦 **Plan:** {mp.get('plan')}\n🗓 **Expires:** {get_ist_str(exp)}\n⏲ **Time Left:** {left}", quote=True)[span_45](start_span)[span_45](end_span)[span_46](start_span)[span_46](end_span)

@Client.on_message(filters.command("plan") & filters.private)
async def plan_cmd(c, m):
    if not IS_PREMIUM: return
    if m.from_user.id in ADMINS: return await m.reply(ADMIN_MSG, quote=True)[span_47](start_span)[span_47](end_span)
        
    await m.reply(script.PLAN_TXT.format(PRE_DAY_AMOUNT, RECEIPT_SEND_USERNAME), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Activate Premium", callback_data="buy_prem")]]))[span_48](start_span)[span_48](end_span)

@Client.on_message(filters.command(["add_prm", "rm_prm"]) & filters.user(ADMINS))
async def manage_premium(c, m):
    if not IS_PREMIUM: return
    cmd, is_add = m.command, m.command[0] == "add_prm[span_49](start_span)"[span_49](end_span)
    if len(cmd) < 2: return await m.reply(f"Usage: `/{cmd[0]} user_id {'days' if is_add else ''}`")[span_50](start_span)[span_50](end_span)
    
    try: uid, days = int(cmd[1]), int(cmd[2][:-1] if cmd[2].endswith('d') else cmd[2]) if is_add and len(cmd) > 2 else 0[span_51](start_span)[span_51](end_span)
    except: return await m.reply("❌ Invalid Format!")[span_52](start_span)[span_52](end_span)

    if is_add:
        if days <= 0:
            return await m.reply("❌ **Error:** Days must be at least 1.")[span_53](start_span)[span_53](end_span)
            
        ex = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None) + timedelta(days=days)[span_54](start_span)[span_54](end_span)
        data = {"expire": ex.strftime("%Y-%m-%d %H:%M:%S"), "plan": f"{days} Days", "premium": True, "reminded_12h": False, "reminded_6h": False, "reminded_3h": False, "reminded_1h": False, "reminded_30m": False, "reminded_10m": False, "last_reminder_id": 0}[span_55](start_span)[span_55](end_span)
        m_usr, m_adm = f"🎉 **Premium Activated!**\n\n🗓 **Duration:** {days} Days\n📅 **Expires:** {get_ist_str(ex)}\n\nEnjoy! ❤️", f"✅ Added {days} days premium to `{uid}`.[span_56](start_span)"[span_56](end_span)
    else:
        data, m_usr, m_adm = {"expire": "", "plan": "", "premium": False}, "❌ **Premium Removed by Admin.**", f"🗑 Removed premium from `{uid}`.[span_57](start_span)"[span_57](end_span)

    await db.update_plan(uid, data)[span_58](start_span)[span_58](end_span)[span_59](start_span)[span_59](end_span)
    await m.reply(m_adm)[span_60](start_span)[span_60](end_span)
    
    for action in (lambda: c.send_message(uid, m_usr), lambda: c.send_message(LOG_CHANNEL, f"#PremiumUpdate\nUser: `{uid}`\nAction: {cmd[0]}")):[span_61](start_span)[span_61](end_span)
        try: await action()
        except: pass

@Client.on_message(filters.command("prm_list") & filters.user(ADMINS))
async def prm_list(c, m):
    if not IS_PREMIUM: return
    msg, count, text = await m.reply("🔄 Fetching..."), 0, "💎 **Premium Users**\n\n[span_62](start_span)"[span_62](end_span)
    async for u in db.get_premium_users():[span_63](start_span)[span_63](end_span)[span_64](start_span)[span_64](end_span)
        if u.get("status", {}).get("premium"):[span_65](start_span)[span_65](end_span)[span_66](start_span)[span_66](end_span)
            count += 1
            text += f"👤 `{u['id']}` | 🗓 {u['status'].get('plan')}\n[span_67](start_span)[span_68](start_span)"[span_67](end_span)[span_68](end_span)
    await msg.edit(text + (f"\n**Total:** {count}" if count > 0 else "📭 No premium users."))[span_69](start_span)[span_69](end_span)

@Client.on_message(filters.command("web_users") & filters.user(ADMINS))
async def list_web_users(c, m):
    msg = await m.reply("🔄 Fetching Web Users...")[span_70](start_span)[span_70](end_span)
    count = 0
    text = "🌐 **Fast Finder Web Users**\n\n[span_71](start_span)"[span_71](end_span)
    async for u in web_db.col.find({}, {"tg_id": 1, "email": 1, "joined_date": 1}): # ✅ PROJECTION फिक्स: रैम लोड से बचने के लिए केवल जरूरी फ़ील्ड मंगवाईं
        count += 1
        joined = u.get('joined_date')[span_72](start_span)[span_72](end_span)
        joined_str = joined.strftime("%d %b %Y") if joined else "Unknown[span_73](start_span)"[span_73](end_span)
        text += f"👤 **TG ID:** `{u['tg_id']}`\n📧 **Email:** `{u['email']}`\n📅 **Joined:** {joined_str}\n\n[span_74](start_span)"[span_74](end_span)
        
    if count == 0:
        await msg.edit("📭 अभी तक किसी ने वेब पर रजिस्टर नहीं किया है।")[span_75](start_span)[span_75](end_span)
    else:
        text += f"**Total Web Users:** {count}[span_76](start_span)[span_77](start_span)"[span_76](end_span)[span_77](end_span)
        await msg.edit(text)[span_78](start_span)[span_78](end_span)

# =========================
# 🔘 CALLBACKS
# =========================
@Client.on_callback_query(filters.regex("^myplan$"))
async def myplan_cb(client, query):
    if query.from_user.id in ADMINS: return await query.answer(ADMIN_ALERT, show_alert=True)[span_79](start_span)[span_79](end_span)
    if not IS_PREMIUM: return await query.answer("Premium disabled.", show_alert=True)[span_80](start_span)[span_80](end_span)
    
    mp = await db.get_plan(query.from_user.id)[span_81](start_span)[span_81](end_span)[span_82](start_span)[span_82](end_span)
    btn = [[InlineKeyboardButton("⬅️ Back", callback_data="back_start")]][span_83](start_span)[span_83](end_span)
    
    if not mp.get('premium'):[span_84](start_span)[span_84](end_span)[span_85](start_span)[span_85](end_span)
        btn.insert(0, [InlineKeyboardButton('💎 Buy Premium', callback_data='activate_plan')])[span_86](start_span)[span_86](end_span)
        return await query.message.edit_caption("❌ No active plan.", reply_markup=InlineKeyboardMarkup(btn))[span_87](start_span)[span_87](end_span)
    
    exp = parse_expire_time(mp.get('expire'))[span_88](start_span)[span_88](end_span)[span_89](start_span)[span_89](end_span)
    now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)[span_90](start_span)[span_90](end_span)
    left = f"{(exp - now).days} days, {(exp - now).seconds//3600} hours" if exp else "Unknown[span_91](start_span)"[span_91](end_span)
    await query.message.edit_caption(f"💎 <b>Premium Status</b>\n\n📦 Plan: {mp.get('plan')}\n⏳ Expires: {get_ist_str(exp)}\n⏱ Left: {left}\n\nUse /plan to extend.", reply_markup=InlineKeyboardMarkup(btn))[span_92](start_span)[span_92](end_span)[span_93](start_span)[span_93](end_span)

@Client.on_callback_query(filters.regex(r"^(buy_prem|activate_plan)$"))
async def buy_callback(c, q):
    if q.from_user.id in ADMINS: return await q.answer(ADMIN_ALERT, show_alert=True)[span_94](start_span)[span_94](end_span)

    prm_msg = await q.message.edit(f"💎 **Select Plan Duration**\n\nSend days (e.g. `30`).\nPrice: ₹{PRE_DAY_AMOUNT}/day\n\n⏳ Timeout: 60s")[span_95](start_span)[span_95](end_span)
    try:
        resp = await c.listen(q.message.chat.id, timeout=60)[span_96](start_span)[span_96](end_span)
        await safe_del(c, q.message.chat.id, [prm_msg.id, resp.id])[span_97](start_span)[span_97](end_span)
        days = int(resp.text)[span_98](start_span)[span_98](end_span)
        
        if days <= 0:
            return await q.message.reply("❌ **Invalid Duration!** Days must be at least 1.")[span_99](start_span)[span_99](end_span)
            
        amount = days * int(PRE_DAY_AMOUNT)[span_100](start_span)[span_100](end_span)
        
        img = qrcode.make(f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR")[span_101](start_span)[span_101](end_span)
        bio = io.BytesIO()[span_102](start_span)[span_102](end_span)
        img.save(bio, format="PNG")[span_103](start_span)[span_103](end_span)
        bio.seek(0)[span_104](start_span)[span_104](end_span)
        
        qr_msg = await q.message.reply_photo(photo=bio, caption=f"💳 **Pay ₹{amount}**\n\nScan & Pay. Then send screenshot here.\n\n⏳ Timeout: 5 mins")[span_105](start_span)[span_105](end_span)
        receipt = await c.listen(q.message.chat.id, timeout=300)[span_106](start_span)[span_106](end_span)
        
        if not receipt.photo: return await q.message.reply("❌ **Invalid!** Send a photo.")[span_107](start_span)[span_107](end_span)
        
        await safe_del(c, q.message.chat.id, [qr_msg.id])[span_108](start_span)[span_108](end_span)
        VERIFY_CACHE[q.from_user.id] = (await q.message.reply("✅ **Sent for Verification!**\nAdmin will activate shortly.")).id[span_109](start_span)[span_109](end_span)
        
        await receipt.copy(RECEIPT_SEND_USERNAME, caption=f"#Payment\n👤: {q.from_user.mention} (`{q.from_user.id}`)\n💰: ₹{amount} ({days} days)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"pay_confirm_{q.from_user.id}_{days}"), InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject_{q.from_user.id}")]]))[span_110](start_span)[span_110](end_span)
    except ValueError: await q.message.reply("❌ Invalid Number!")[span_111](start_span)[span_111](end_span)
    except asyncio.TimeoutError:
        VERIFY_CACHE.pop(q.from_user.id, None)[span_112](start_span)[span_112](end_span)
        await q.message.reply("⏳ **Timeout!** Process cancelled.")[span_113](start_span)[span_113](end_span)
    except Exception as e: await q.message.reply(f"❌ **Error:** `{e}`")[span_114](start_span)[span_114](end_span)

@Client.on_callback_query(filters.regex(r"^pay_(confirm|reject)_"))
async def pay_action(c, q):
    if q.from_user.id not in ADMINS: return await q.answer("❌ Only Admins!", show_alert=True)[span_115](start_span)[span_115](end_span)
    _, act, uid = q.data.split("_")[:3][span_116](start_span)[span_116](end_span)
    uid = int(uid)[span_117](start_span)[span_117](end_span)

    if act == "confirm":
        days = int(q.data.split("_")[3])[span_118](start_span)[span_118](end_span)
        ex = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None) + timedelta(days=days)[span_119](start_span)[span_119](end_span)
        await db.update_plan(uid, {"expire": ex.strftime("%Y-%m-%d %H:%M:%S"), "plan": f"{days} Days", "premium": True, "reminded_12h": False, "reminded_6h": False, "reminded_3h": False, "reminded_1h": False, "reminded_30m": False, "reminded_10m": False, "last_reminder_id": 0})[span_120](start_span)[span_120](end_span)[span_121](start_span)[span_121](end_span)
        await q.message.edit_caption(caption=q.message.caption + f"\n\n✅ **Approved by** {q.from_user.mention}", reply_markup=None)[span_122](start_span)[span_122](end_span)
        try: await c.send_message(uid, f"🎉 **Congratulations!**\n\n✅ Your premium of **{days} Days** is Active.\n📅 **Expires:** {get_ist_str(ex)}\n\nEnjoy our service! ❤️")[span_123](start_span)[span_123](end_span)
        except: pass
    else:
        await q.message.edit_caption(caption=q.message.caption + f"\n\n❌ **Rejected by** {q.from_user.mention}", reply_markup=None)[span_124](start_span)[span_124](end_span)
        try: await c.send_message(uid, "❌ **Payment Rejected!**\nContact admin manually.")[span_125](start_span)[span_125](end_span)
        except: pass
        
    if uid in VERIFY_CACHE:
        await safe_del(c, uid, [VERIFY_CACHE.pop(uid)])[span_126](start_span)[span_126](end_span)
