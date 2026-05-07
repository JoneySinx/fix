import math
from hydrogram import Client, utils, raw
from hydrogram.types import Message
from hydrogram.session import Session, Auth
from hydrogram.errors import AuthBytesInvalid
from hydrogram.file_id import FileId, FileType, ThumbnailSource
from utils import temp

async def chunk_size(length): return 2 ** max(min(math.ceil(math.log2(length / 1024)), 10), 2) * 1024
async def offset_fix(offset, chunksize): return offset - (offset % chunksize)

class TGCustomYield:
    def __init__(self):
        self.main_bot = temp.BOT

    @staticmethod
    async def generate_file_properties(msg: Message):
        return FileId.decode(getattr(msg, msg.media.value).file_id)

    async def generate_media_session(self, c: Client, msg: Message):
        d = await self.generate_file_properties(msg)
        ms = c.media_sessions.get(d.dc_id)
        
        if not ms:
            test_mode = await c.storage.test_mode()
            if d.dc_id != await c.storage.dc_id():
                ms = Session(c, d.dc_id, await Auth(c, d.dc_id, test_mode).create(), test_mode, is_media=True)
                await ms.start()
                for _ in range(3):
                    ex = await c.invoke(raw.functions.auth.ExportAuthorization(dc_id=d.dc_id))
                    try:
                        await ms.send(raw.functions.auth.ImportAuthorization(id=ex.id, bytes=ex.bytes))
                        break
                    except AuthBytesInvalid: continue
                else:
                    await ms.stop(); raise AuthBytesInvalid
            else:
                ms = Session(c, d.dc_id, await c.storage.auth_key(), test_mode, is_media=True)
                await ms.start()
            c.media_sessions[d.dc_id] = ms
            
        return ms

    @staticmethod
    async def get_location(f: FileId):
        if f.file_type == FileType.CHAT_PHOTO:
            peer = raw.types.InputPeerUser(user_id=f.chat_id, access_hash=f.chat_access_hash) if f.chat_id > 0 else (raw.types.InputPeerChat(chat_id=-f.chat_id) if f.chat_access_hash == 0 else raw.types.InputPeerChannel(channel_id=utils.get_channel_id(f.chat_id), access_hash=f.chat_access_hash))
            return raw.types.InputPeerPhotoFileLocation(peer=peer, volume_id=f.volume_id, local_id=f.local_id, big=f.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG)
        elif f.file_type == FileType.PHOTO:
            return raw.types.InputPhotoFileLocation(id=f.media_id, access_hash=f.access_hash, file_reference=f.file_reference, thumb_size=f.thumbnail_size)
        return raw.types.InputDocumentFileLocation(id=f.media_id, access_hash=f.access_hash, file_reference=f.file_reference, thumb_size=f.thumbnail_size)

    async def yield_file(self, msg: Message, offset: int, first_cut: int, last_cut: int, parts: int, chunk_size: int):
        ms = await self.generate_media_session(self.main_bot, msg)
        loc = await self.get_location(await self.generate_file_properties(msg))
        
        # ✅ FIX: For-loop makes streaming perfectly clean without writing request again & again
        for i in range(1, parts + 1):
            r = await ms.send(raw.functions.upload.GetFile(location=loc, offset=offset, limit=chunk_size))
            if not isinstance(r, raw.types.upload.File) or not r.bytes: break
            
            chunk = r.bytes
            if parts == 1: yield chunk[first_cut:last_cut]
            elif i == 1: yield chunk[first_cut:]
            elif i == parts: yield chunk[:last_cut]
            else: yield chunk
            
            offset += chunk_size

    async def download_as_bytesio(self, msg: Message):
        ms = await self.generate_media_session(self.main_bot, msg)
        loc = await self.get_location(await self.generate_file_properties(msg))
        limit, offset, m_file = 1048576, 0, []
        
        # ✅ FIX: Single request call dynamically handles full buffering
        while True:
            r = await ms.send(raw.functions.upload.GetFile(location=loc, offset=offset, limit=limit))
            if not isinstance(r, raw.types.upload.File) or not r.bytes: break
            m_file.append(r.bytes)
            offset += limit
            
        return m_file
