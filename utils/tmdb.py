import aiohttp, re
from info import TMDB_API_KEY

_poster_cache = {}

async def get_poster(filename):
    if not TMDB_API_KEY:
        return None # ✅ FIX: डमी की जगह None ताकि असली थंबनेल ट्रिगर हो

    clean_name = re.sub(r'\[.*?\]|\(.*\)', '', filename)
    clean_name = re.sub(r'(1080p|720p|480p|2160p|4k|HD|WEB-DL|HDRip|BluRay|x264|HEVC)', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\.(mkv|mp4|avi|webm)$', '', clean_name, flags=re.IGNORECASE)
    clean_name = clean_name.replace('.', ' ').replace('_', ' ').strip()
    
    year_match = re.search(r'\b(19|20)\d{2}\b', clean_name)
    year = year_match.group(0) if year_match else ""
    if year: clean_name = clean_name.replace(year, '').strip()

    search_query = clean_name.split('-')[0].strip()
    if not search_query: return None

    cache_key = search_query.lower()
    if cache_key in _poster_cache: return _poster_cache[cache_key]

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
                            _poster_cache[cache_key] = poster 
                            return poster
    except Exception as e:
        print(f"TMDb Error: {e}")
        
    return None # ✅ FIX: अगर TMDb पर नहीं मिला, तो असली थंबनेल मंगाएँगे
