import logging
from motor.motor_asyncio import AsyncIOMotorClient
from info import (BOT_ID, DATABASE_URL, DATABASE_NAME, FILE_CAPTION, WELCOME, 
                  WELCOME_TEXT, SPELL_CHECK, PROTECT_CONTENT, AUTO_DELETE)

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(DATABASE_URL, minPoolSize=10, maxPoolSize=50, maxIdleTimeMS=45000, serverSelectionTimeoutMS=5000)
        self.db = self.client[DATABASE_NAME]
        
        # 🎯 Collections
        self.users, self.groups, self.premium = self.db.Users, self.db.Groups, self.db.Premiums
        self.connections, self.settings, self.warns = self.db.Connections, self.db.Settings, self.db.Warns

    async def _ensure_indexes(self):
        for col in [self.users, self.groups, self.premium, self.settings]:
            try: await col.create_index("id", unique=True)
            except Exception as e: logger.warning(f"Index warn: {e}")

    # ⚙️ Default Values (Memory Efficient)
    df_set = {"file_secure": PROTECT_CONTENT, "spell_check": SPELL_CHECK, "auto_delete": AUTO_DELETE, "welcome": WELCOME, "welcome_text": WELCOME_TEXT, "caption": FILE_CAPTION, "search_enabled": True, "blacklist": [], "dlink": {}, "notes": {}}
    df_prm = {"expire": "", "trial": False, "plan": "", "premium": False, "reminded_24h": False, "reminded_6h": False, "reminded_1h": False}
    df_ban = {"is_banned": False, "ban_reason": ""}
    df_chat = {"is_disabled": False, "reason": ""}

    # ───────────────── USERS ─────────────────
    async def add_user(self, uid, name): await self.users.update_one({"id": int(uid)}, {"$set": {"name": name}, "$setOnInsert": {"ban_status": self.df_ban}}, upsert=True)
    async def is_user_exist(self, uid): return bool(await self.users.find_one({"id": int(uid)}))
    async def total_users_count(self): return await self.users.count_documents({})
    async def get_all_users(self): return self.users.find({})
    async def delete_user(self, uid): await self.users.delete_many({"id": int(uid)})
    
    async def ban_user(self, uid, rsn="No Reason"): await self.users.update_one({"id": int(uid)}, {"$set": {"ban_status": {"is_banned": True, "ban_reason": rsn}}}, upsert=True)
    async def unban_user(self, uid): await self.users.update_one({"id": int(uid)}, {"$set": {"ban_status": self.df_ban}})
    async def get_ban_status(self, uid): return (await self.users.find_one({"id": int(uid)}) or {}).get("ban_status", self.df_ban)

    # ───────────────── GROUPS ─────────────────
    async def add_chat(self, gid, title): await self.groups.update_one({"id": int(gid)}, {"$set": {"title": title}, "$setOnInsert": {"settings": self.df_set, "chat_status": self.df_chat}}, upsert=True)
    async def get_chat(self, gid): return (await self.groups.find_one({"id": int(gid)}) or {}).get("chat_status", None) # ✅ Missing Group Bug Fixed
    async def total_chat_count(self): return await self.groups.count_documents({})
    async def get_all_chats(self): return self.groups.find({})
    
    # ✅ Missing Admin Commands Fixed
    async def disable_chat(self, gid, rsn="No Reason"): await self.groups.update_one({"id": int(gid)}, {"$set": {"chat_status": {"is_disabled": True, "reason": rsn}}})
    async def re_enable_chat(self, gid): await self.groups.update_one({"id": int(gid)}, {"$set": {"chat_status": self.df_chat}})

    # ───────────────── SETTINGS & MGMT ─────────────────
    async def update_settings(self, gid, st): await self.groups.update_one({"id": int(gid)}, {"$set": {"settings": st}}, upsert=True)
    
    # ✅ Smart Dictionary Merging (`**`)
    async def get_settings(self, gid): return {**self.df_set, **((await self.groups.find_one({"id": int(gid)})) or {}).get("settings", {})}
    
    async def get_warn(self, uid, cid): return await self.warns.find_one({"user_id": uid, "chat_id": cid}) or {"count": 0}
    async def set_warn(self, uid, cid, data): await self.warns.update_one({"user_id": uid, "chat_id": cid}, {"$set": data}, upsert=True)
    async def clear_warn(self, uid, cid): await self.warns.delete_one({"user_id": uid, "chat_id": cid})

    async def get_all_notes(self, cid): return ((await self.groups.find_one({"id": int(cid)})) or {}).get("settings", {}).get("notes", {})
    async def save_note(self, cid, name, data): await self.groups.update_one({"id": int(cid)}, {"$set": {f"settings.notes.{name}": data}}, upsert=True)
    async def delete_note(self, cid, name): await self.groups.update_one({"id": int(cid)}, {"$unset": {f"settings.notes.{name}": ""}})

    # ───────────────── PREMIUM ─────────────────
    async def get_plan(self, uid): return {**self.df_prm, **((await self.premium.find_one({"id": int(uid)})) or {}).get("status", {})}
    async def update_plan(self, uid, data): await self.premium.update_one({"id": int(uid)}, {"$set": {"status": data}}, upsert=True)
    async def get_premium_users(self): return self.premium.find({})
    async def reset_reminder_flags(self, uid): await self.premium.update_one({"id": int(uid)}, {"$set": {"status.reminded_24h": False, "status.reminded_6h": False, "status.reminded_1h": False}})

    # ───────────────── CONNECTIONS & STATS ─────────────────
    async def add_connect(self, gid, uid): await self.connections.update_one({"_id": int(uid)}, {"$addToSet": {"group_ids": gid}}, upsert=True)
    async def get_connections(self, uid): return (await self.connections.find_one({"_id": int(uid)}) or {}).get("group_ids", [])
    async def delete_connection(self, uid, gid): await self.connections.update_one({"_id": int(uid)}, {"$pull": {"group_ids": gid}})

    async def update_bot_sttgs(self, var, val): await self.settings.update_one({"id": BOT_ID}, {"$set": {var: val}}, upsert=True)
    async def get_bot_sttgs(self): return await self.settings.find_one({"id": BOT_ID}) or {}
    async def get_data_db_size(self): return (await self.db.command("dbstats")).get("dataSize", 0)
    
    # ✅ Fast List Comprehension Loop
    async def get_banned(self):
        return ([u["id"] async for u in self.users.find({"ban_status.is_banned": True})], 
                [g["id"] async for g in self.groups.find({"chat_status.is_disabled": True})])

db = Database()
