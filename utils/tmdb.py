import aiohttp, re
from info import TMDB_API_KEY

# 🚀 SPEED FIX: एक बार जो पोस्टर आ गया, उसे Cache कर लेंगे ताकि बार-बार इंटरनेट न लगे
_poster_cache = {}

async def get_poster(filename):
    if not TMDB_API_KEY:
        return "https://i.ibb.co/30B3RcS/default-movie.png" # 🚨 Fallback Image (अगर API नहीं है)

    # 🧹 फ़ाइल के नाम को साफ़ करना (1080p, mkv, @channel_name हटाना)
    clean_name = re.sub(r'\[.*?\]|\(.*\)', '', filename)
    clean_name = re.sub(r'(1080p|720p|480p|2160p|4k|HD|WEB-DL|HDRip|BluRay|x264|HEVC)', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\.(mkv|mp4|avi|webm)$', '', clean_name, flags=re.IGNORECASE)
    clean_name = clean_name.replace('.', ' ').replace('_', ' ').strip()
    
    # 📅 साल (Year) निकालना ताकि सर्च एकदम सटीक हो
    year_match = re.search(r'\b(19|20)\d{2}\b', clean_name)
    year = year_match.group(0) if year_match else ""
    if year:
        clean_name = clean_name.replace(year, '').strip()

    search_query = clean_name.split('-')[0].strip()
    if not search_query: return "https://i.ibb.co/30B3RcS/default-movie.png"

    # ⚡ Cache चेक करें
    cache_key = search_query.lower()
    if cache_key in _poster_cache:
        return _poster_cache[cache_key]

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={search_query}"
            if year: url += f"&year={year}"
                
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get('results'):
                    for result in data['results']:
                        if result.get('poster_path'):
                            poster = f"https://image.tmdb.org/t/p/w500{result['poster_path']}"
                            _poster_cache[cache_key] = poster # सेव कर लें
                            return poster
    except Exception as e:
        print(f"TMDb Error: {e}")
        
    # 🚨 Fallback: अगर TMDb पर भारत की कोई छोटी सीरीज़ नहीं मिली, तो यह डिफ़ॉल्ट सुंदर सा पोस्टर दिखेगा
    return "https://i.ibb.co/30B3RcS/default-movie.png" 
