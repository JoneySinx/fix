import logging
import asyncio
import motor.motor_asyncio
from info import (
    BOT_ID,
    DATABASE_URL,
    DATABASE_NAME,
    FILE_CAPTION,
    WELCOME,
    WELCOME_TEXT,
    SPELL_CHECK,
    PROTECT_CONTENT,
    AUTO_DELETE
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🔌 ASYNC DATABASE CONNECTION (Optimized)
# ─────────────────────────────────────────────
class Database:
    
    def __init__(self):
        # Motor Client (Non-Blocking)
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            DATABASE_URL,
            minPoolSize=10,
            maxPoolSize=50,       
            maxIdleTimeMS=45000,
            serverSelectionTimeoutMS=5000 
        )
        self.db = self.client[DATABASE_NAME]
        
        self.users = self.db.Users
        self.groups = self.db.Groups
        self.premium = self.db.Premiums
        self.connections = self.db.Connections
        self.settings = self.db.Settings
        self.warns = self.db.Warns  

    async def _ensure_indexes(self):
        """Creates indexes on 'id' for ultra-fast database querying."""
        try:
            await self.users.create_index("id", unique=True)
            await self.groups.create_index("id", unique=True)
            await self.premium.create_index("id", unique=True)
            await self.settings.create_index("id", unique=True)
            logger.info("✅ Database Indexes created successfully!")
        except Exception as e:
            logger.warning(f"Index warning: {e}")

    # Default settings
    default_setgs = {
        "file_secure": PROTECT_CONTENT,
        "spell_check": SPELL_CHECK,
        "auto_delete": AUTO_DELETE,
        "welcome": WELCOME,
        "welcome_text": WELCOME_TEXT,
        "caption": FILE_CAPTION,
        "search_enabled": True,
        "blacklist": [],
        "dlink": {},
        "notes": {}
    }

    default_prm = {
        "expire": "", "trial": False, "plan": "", "premium": False,
        "reminded_24h": False, "reminded_6h": False, "reminded_1h": False
    }

    # ───────────────── USERS ─────────────────
    
    async def add_user(self, user_id, name):
        try:
            await self.users.update_one(
                {"id": int(user_id)},
                {
                    "$set": {"name": name},
                    "$setOnInsert": {"ban_status": {"is_banned": False, "ban_reason": ""}}
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error adding user: {e}")

    async def is_user_exist(self, user_id):
        user = await self.users.find_one({"id": int(user_id)})
        return bool(user)

    async def total_users_count(self):
        return await self.users.count_documents({})

    async def get_all_users(self):
        return self.users.find({})

    async def delete_user(self, user_id):
        await self.users.delete_many({"id": int(user_id)})

    async def ban_user(self, user_id, reason="No Reason"):
        await self.users.update_one(
            {"id": int(user_id)},
            {"$set": {"ban_status": {"is_banned": True, "ban_reason": reason}}},
            upsert=True 
        )

    async def unban_user(self, user_id):
        await self.users.update_one(
            {"id": int(user_id)},
            {"$set": {"ban_status": {"is_banned": False, "ban_reason": ""}}}
        )

    async def get_ban_status(self, user_id):
        user = await self.users.find_one({"id": int(user_id)})
        return user.get("ban_status", {"is_banned": False, "ban_reason": ""}) if user else {"is_banned": False, "ban_reason": ""}

    # ───────────────── GROUPS ─────────────────

    async def add_chat(self, group_id, title):
        try:
            await self.groups.update_one(
                {"id": int(group_id)},
                {
                    "$set": {"title": title},
                    "$setOnInsert": {
                        "settings": self.default_setgs, 
                        "chat_status": {"is_disabled": False, "reason": ""}
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error adding chat: {e}")

    async def get_chat(self, group_id):
        grp = await self.groups.find_one({"id": int(group_id)})
        if grp:
            return grp.get("chat_status", {"is_disabled": False, "reason": ""})
        return {"is_disabled": False, "reason": ""}

    async def total_chat_count(self):
        return await self.groups.count_documents({})

    async def get_all_chats(self):
        return self.groups.find({})

    # ───────────────── SETTINGS & MANAGEMENT ─────────────────
    
    async def update_settings(self, group_id, settings):
        await self.groups.update_one(
            {"id": int(group_id)},
            {"$set": {"settings": settings}},
            upsert=True
        )

    async def get_settings(self, group_id):
        grp = await self.groups.find_one({"id": int(group_id)})
        if grp:
            settings = grp.get("settings", self.default_setgs)
            settings.setdefault("search_enabled", True)
            settings.setdefault("blacklist", [])
            settings.setdefault("dlink", {})
            return settings
        return self.default_setgs

    # ⚠️ WARN SYSTEM 
    async def get_warn(self, user_id, chat_id):
        doc = await self.warns.find_one({"user_id": user_id, "chat_id": chat_id})
        return doc if doc else {"count": 0}

    async def set_warn(self, user_id, chat_id, data):
        await self.warns.update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$set": data},
            upsert=True
        )

    async def clear_warn(self, user_id, chat_id):
        await self.warns.delete_one({"user_id": user_id, "chat_id": chat_id})

    # ⚠️ NOTES SYSTEM
    async def get_all_notes(self, chat_id):
        grp = await self.groups.find_one({"id": int(chat_id)})
        if grp and "settings" in grp:
            return grp["settings"].get("notes", {})
        return {}

    async def save_note(self, chat_id, name, note_data):
        await self.groups.update_one(
            {"id": int(chat_id)},
            {"$set": {f"settings.notes.{name}": note_data}},
            upsert=True
        )

    async def delete_note(self, chat_id, name):
        await self.groups.update_one(
            {"id": int(chat_id)},
            {"$unset": {f"settings.notes.{name}": ""}}
        )

    # ───────────────── PREMIUM ─────────────────
    
    async def get_plan(self, user_id):
        st = await self.premium.find_one({"id": int(user_id)})
        if st:
            status = st.get("status", {})
            status.setdefault("reminded_24h", False)
            status.setdefault("reminded_6h", False)
            status.setdefault("reminded_1h", False)
            return status
        return self.default_prm.copy()

    async def update_plan(self, user_id, data):
        await self.premium.update_one(
            {"id": int(user_id)},
            {"$set": {"status": data}},
            upsert=True
        )

    async def get_premium_users(self):
        return self.premium.find({})

    async def reset_reminder_flags(self, user_id):
        await self.premium.update_one(
            {"id": int(user_id)},
            {"$set": {
                "status.reminded_24h": False,
                "status.reminded_6h": False,
                "status.reminded_1h": False
            }}
        )

    # ───────────────── CONNECTIONS ─────────────────
    
    async def add_connect(self, group_id, user_id):
        await self.connections.update_one(
            {"_id": int(user_id)},
            {"$addToSet": {"group_ids": group_id}},
            upsert=True
        )

    async def get_connections(self, user_id):
        user = await self.connections.find_one({"_id": int(user_id)})
        return user.get("group_ids", []) if user else []

    async def delete_connection(self, user_id, group_id):
        await self.connections.update_one(
            {"_id": int(user_id)},
            {"$pull": {"group_ids": group_id}}
        )

    # ───────────────── BOT & STATS ─────────────────
    
    async def update_bot_sttgs(self, var, val):
        await self.settings.update_one(
            {"id": BOT_ID},
            {"$set": {var: val}},
            upsert=True
        )

    async def get_bot_sttgs(self):
        return await self.settings.find_one({"id": BOT_ID}) or {}

    async def get_data_db_size(self):
        stats = await self.db.command("dbstats")
        return stats["dataSize"]
        
    async def get_banned(self):
        banned_users = []
        banned_chats = []
        
        async for u in self.users.find({"ban_status.is_banned": True}):
            banned_users.append(u["id"])
            
        async for g in self.groups.find({"chat_status.is_disabled": True}):
            banned_chats.append(g["id"])
            
        return banned_users, banned_chats

# ─────────────────────────────────────────────
# 🔚 INSTANCE
# ─────────────────────────────────────────────
db = Database()
