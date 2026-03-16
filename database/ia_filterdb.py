import logging
import re
import base64
import asyncio
from struct import pack
import motor.motor_asyncio
from hydrogram.file_id import FileId
from info import DATABASE_URL, DATABASE_NAME, MAX_BTN, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# ⚙️ MOTOR CONNECTION — Koyeb Free Tier Optimized
# ─────────────────────────────────────────────────────────
client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL,
    maxPoolSize=5,
    minPoolSize=1,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,
    retryWrites=True,
    retryReads=True,
)
db = client[DATABASE_NAME]

primary = db["Primary"]
cloud   = db["Cloud"]
archive = db["Archive"]

COLLECTIONS = {
    "primary": primary,
    "cloud":   cloud,
    "archive": archive,
}

# ─────────────────────────────────────────────────────────
# ⚡ INDEXES — Text index (sorting के लिए)
# ─────────────────────────────────────────────────────────
async def ensure_indexes():
    for name, col in COLLECTIONS.items():
        try:
            await col.create_index(
                [("file_name", "text"), ("caption", "text")],
                name=f"{name}_text"
            )
            logger.info(f"✅ Index OK: {name}")
        except Exception as e:
            if "already exists" in str(e) or "IndexKeySpecsConflict" in str(e) or "86" in str(e):
                pass
            else:
                logger.warning(f"Index warning [{name}]: {e}")

# ─────────────────────────────────────────────────────────
# 📊 DB STATS
# ─────────────────────────────────────────────────────────
async def db_count_documents():
    try:
        p, c, a = await asyncio.gather(
            primary.estimated_document_count(),
            cloud.estimated_document_count(),
            archive.estimated_document_count(),
        )
        return {"primary": p, "cloud": c, "archive": a, "total": p + c + a}
    except Exception as e:
        logger.error(f"Count error: {e}")
        return {"primary": 0, "cloud": 0, "archive": 0, "total": 0}

# ─────────────────────────────────────────────────────────
# 💾 SAVE FILE
#
# ✅ _id = unpack_new_file_id() से बना encoded ID
#    यह ID खुद एक valid Telegram file_id है।
#    access_hash pack होने की वजह से channel छोड़ने के बाद भी काम करती है।
#    इसीलिए plugin doc["_id"] को ही file_id की तरह use करता है — सही है।
#
# ✅ file_type अलग से store करो ताकि plugin जाने:
#    send_document / send_video / send_audio में से क्या call करना है
# ─────────────────────────────────────────────────────────
async def save_file(media, collection_type="primary"):
    try:
        file_id = unpack_new_file_id(media.file_id)
        if not file_id:
            logger.warning(f"Could not unpack file_id: {media.file_name}")
            return "err"

        f_name  = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name or "")).strip()
        caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption  or "")).strip()

        doc = {
            "_id":       file_id,           # ✅ Valid Telegram file_id (encoded with access_hash)
            "file_name": f_name,
            "file_size": media.file_size,
            "caption":   caption,
            "file_type": media.file_type,   # ✅ document / video / audio
        }

        col    = COLLECTIONS.get(collection_type, primary)
        result = await col.replace_one({"_id": file_id}, doc, upsert=True)

        if result.matched_count > 0:
            logger.warning(f"Already Saved - {f_name}")
            return "dup"
        else:
            logger.info(f"Saved - {f_name}")
            return "suc"

    except Exception as e:
        logger.error(f"save_file error: {e}")
        return "err"

# ─────────────────────────────────────────────────────────
# 🔍 REGEX BUILDER
#
# ✅ पुराने working bot से लिया गया — Regex search, Text search से
#    ज्यादा accurate है file names के लिए।
#
#    "Pushpa 2"    → r'pushpa.*[\s\.\+\-_]2'
#    "pushpa"      → r'(\b|[\.\+\-_])pushpa(\b|[\.\+\-_])'
#    ""            → r'.'  (सब कुछ)
# ─────────────────────────────────────────────────────────
def _build_regex(query: str):
    query = query.strip()
    if not query:
        raw = r'.'
    elif ' ' not in query:
        raw = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else:
        raw = re.escape(query).replace(r'\ ', r'.*[\s\.\+\-_]')

    try:
        return re.compile(raw, flags=re.IGNORECASE)
    except Exception:
        return re.compile(re.escape(query), flags=re.IGNORECASE)

# ─────────────────────────────────────────────────────────
# 🔍 SINGLE COLLECTION SEARCH (INTERNAL)
#
# ✅ Regex filter use करो (पुराने bot की तरह — accurate)
# ✅ find + count parallel (नए bot की तरह — fast)
# ✅ doc["file_id"] = doc["_id"]  ← _id IS a valid Telegram file_id
# ─────────────────────────────────────────────────────────
async def _search(col, regex, offset: int, limit: int):
    if USE_CAPTION_FILTER:
        flt = {"$or": [{"file_name": regex}, {"caption": regex}]}
    else:
        flt = {"file_name": regex}

    try:
        async def _fetch():
            cursor = col.find(flt)
            cursor.skip(offset).limit(limit)
            docs = await cursor.to_list(length=limit)
            for doc in docs:
                doc["file_id"] = doc["_id"]  # ✅ _id is valid Telegram file_id
            return docs

        async def _count():
            return await col.count_documents(flt)

        docs, count = await asyncio.gather(_fetch(), _count())
        return docs, count

    except Exception as e:
        logger.error(f"_search error: {e}")
        return [], 0

# ─────────────────────────────────────────────────────────
# 🚀 PUBLIC SEARCH API — TRUE CASCADE
#
#  Primary → (मिला? return) → Cloud → (मिला? return) → Archive
#  कहीं न मिले → Empty return
# ─────────────────────────────────────────────────────────
async def get_search_results(
    query,
    max_results=MAX_BTN,
    offset=0,
    lang=None,
    collection_type="primary"
):
    if not query:
        return [], "", 0, collection_type

    regex      = _build_regex(str(query))
    results    = []
    total      = 0
    actual_src = collection_type

    # ── CASCADE: Primary → Cloud → Archive ──
    if collection_type == "all":
        cascade = [("primary", primary), ("cloud", cloud), ("archive", archive)]
        for src, col in cascade:
            docs, cnt = await _search(col, regex, offset, max_results)
            if docs:
                results    = docs
                total      = cnt
                actual_src = src
                break  # ✅ मिल गया → रुको, बाकी collections छोड़ो

    # ── Single collection ──
    elif collection_type in COLLECTIONS:
        col       = COLLECTIONS[collection_type]
        docs, cnt = await _search(col, regex, offset, max_results)
        results   = docs
        total     = cnt

    # ── Unknown → Primary default ──
    else:
        docs, cnt = await _search(primary, regex, offset, max_results)
        results   = docs
        total     = cnt

    # ── Language filter ──
    if lang and results:
        lang    = lang.lower()
        results = [f for f in results if lang in f.get("file_name", "").lower()]
        total   = len(results)

    next_offset = offset + max_results
    next_offset = "" if next_offset >= total else next_offset

    return results, next_offset, total, actual_src

# ─────────────────────────────────────────────────────────
# 🗑 DELETE FILES
# ─────────────────────────────────────────────────────────
async def delete_files(query, collection_type="all"):
    deleted = 0
    try:
        if query == "*":
            cols    = [col for name, col in COLLECTIONS.items()
                       if collection_type == "all" or name == collection_type]
            results = await asyncio.gather(*[col.delete_many({}) for col in cols])
            return sum(r.deleted_count for r in results)

        regex = _build_regex(str(query))
        flt   = {"file_name": regex}
        cols  = [(name, col) for name, col in COLLECTIONS.items()
                 if collection_type == "all" or name == collection_type]

        results = await asyncio.gather(*[col.delete_many(flt) for _, col in cols])
        for (name, _), res in zip(cols, results):
            deleted += res.deleted_count
            if res.deleted_count:
                logger.info(f"🗑 Deleted {res.deleted_count} from {name}")

        return deleted

    except Exception as e:
        logger.error(f"delete_files error: {e}")
        return deleted

# ─────────────────────────────────────────────────────────
# 📂 GET FILE DETAILS
#
# ✅ _id से file ढूंढो — यही _id plugin को मिलता है
#    doc["file_id"] = doc["_id"] set करो ताकि plugin सीधे use कर सके
# ─────────────────────────────────────────────────────────
async def get_file_details(file_id):
    try:
        # Cascade: Primary → Cloud → Archive (sequential — पहले मिले वो return)
        for col in [primary, cloud, archive]:
            doc = await col.find_one({"_id": file_id})
            if doc:
                doc["file_id"] = doc["_id"]  # ✅ Plugin compatibility
                return doc
        return None
    except Exception as e:
        logger.error(f"get_file_details error: {e}")
        return None

# ─────────────────────────────────────────────────────────
# 🔑 FILE ID ENCODING UTILS
#
# unpack_new_file_id() से जो ID बनती है वो:
#   1. Unique key है (duplicate detection के लिए)
#   2. Valid Telegram file_id है (file भेजने के लिए)
#   3. access_hash include है (channel छोड़ने के बाद भी काम करे)
# ─────────────────────────────────────────────────────────
def encode_file_id(s: bytes) -> str:
    r, n = b"", 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n  = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id: str):
    try:
        decoded = FileId.decode(new_file_id)
        return encode_file_id(
            pack(
                "<iiqq",
                int(decoded.file_type),
                decoded.dc_id,
                decoded.media_id,
                decoded.access_hash,
            )
        )
    except Exception as e:
        logger.error(f"unpack_new_file_id error: {e}")
        return None
