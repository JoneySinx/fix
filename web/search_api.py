from aiohttp import web
import time
from database.ia_filterdb import get_web_search_results
from utils import temp, get_size

search_routes = web.RouteTableDef()

# ─────────────────────────────────────────────
# 🔒 SECURITY CHECK HELPER
# ─────────────────────────────────────────────
def is_admin_logged_in(request):
    session_id = request.cookies.get('admin_session')
    if not hasattr(temp, 'ADMIN_SESSIONS'):
        return False
    if not session_id or session_id not in temp.ADMIN_SESSIONS:
        return False
    if time.time() > temp.ADMIN_SESSIONS[session_id]:
        del temp.ADMIN_SESSIONS[session_id]
        return False
    return True

# ─────────────────────────────────────────────
# 📡 BACKEND API (JSON RESPONSE)
# ─────────────────────────────────────────────
@search_routes.get('/api/search')
async def api_search_handler(request):
    # सुरक्षा जांच
    if not is_admin_logged_in(request):
        return web.json_response({"error": "Unauthorized Access"}, status=403)

    query = request.query.get('q', '').strip()
    if not query:
        return web.json_response([])

    # डेटाबेस से लाइव रिज़ल्ट लाएं
    docs = await get_web_search_results(query, limit=30)
    
    results = []
    for doc in docs:
        # file_ref असली Telegram ID है जिससे वेब सर्वर सीधे स्ट्रीम कर सकता है
        target_id = doc.get("file_ref", doc.get("file_id"))
        
        results.append({
            "name": doc.get("file_name", "Unknown File"),
            "size": get_size(doc.get("file_size", 0)),
            "type": doc.get("file_type", "document").upper(),
            "watch": f"/watch/{target_id}",
            "download": f"/download/{target_id}"
        })
        
    return web.json_response(results)

# ─────────────────────────────────────────────
# 🎬 FRONTEND UI (WEB PLAYER & SEARCH)
# ─────────────────────────────────────────────
@search_routes.get('/player')
async def web_player_ui(request):
    # सुरक्षा जांच
    if not is_admin_logged_in(request):
        return web.Response(text="❌ Unauthorized Access! Please login via Telegram link first.", status=403)

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Web Player | Admin Panel</title>
        <style>
            body {
                background-color: #0f0f1a;
                color: #e0e0e0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0; padding: 20px;
            }
            .header { text-align: center; margin-bottom: 30px; }
            h1 { color: #00d2ff; margin: 0; font-size: 28px; }
            
            .search-container {
                max-width: 600px; margin: 0 auto; display: flex; gap: 10px;
            }
            input[type="text"] {
                flex: 1; padding: 15px 20px; border-radius: 30px; border: none;
                background-color: #1a1a2e; color: white; font-size: 16px;
                outline: none; box-shadow: inset 0 2px 5px rgba(0,0,0,0.5);
            }
            input[type="text"]:focus { box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), 0 0 10px rgba(0, 210, 255, 0.3); }
            
            button {
                padding: 15px 25px; border-radius: 30px; border: none;
                background: linear-gradient(90deg, #3a7bd5, #00d2ff);
                color: white; font-size: 16px; font-weight: bold; cursor: pointer;
            }
            button:hover { opacity: 0.9; }
            
            #results {
                display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px; max-width: 1000px; margin: 40px auto;
            }
            .card {
                background: #16213e; padding: 20px; border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3); transition: transform 0.2s;
            }
            .card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,210,255,0.2); }
            .card-title { font-size: 16px; font-weight: bold; margin-bottom: 10px; word-wrap: break-word; }
            .card-info { color: #a0a0b0; font-size: 13px; margin-bottom: 15px; }
            .btn-group { display: flex; gap: 10px; }
            
            .btn-play { background: #28a745; color: white; flex: 1; text-align: center; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; }
            .btn-dl { background: #ffc107; color: black; flex: 1; text-align: center; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; }
            .btn-play:hover { background: #218838; }
            .btn-dl:hover { background: #e0a800; }
            
            .loader { text-align: center; color: #00d2ff; display: none; margin-top: 20px; }
            .nav-link { color: #a0a0b0; text-decoration: none; display: block; text-align: center; margin-bottom: 20px; }
            .nav-link:hover { color: white; }
        </style>
    </head>
    <body>
        <a href="/dashboard" class="nav-link">⬅️ Back to Dashboard</a>
        
        <div class="header">
            <h1>🍿 Live OTT Search & Play</h1>
            <p>Directly stream movies from your bot's database.</p>
        </div>

        <div class="search-container">
            <input type="text" id="searchInput" placeholder="Search movies, series, or files...">
            <button onclick="performSearch()">Search</button>
        </div>
        
        <div id="loader" class="loader"><h2>Searching... ⏳</h2></div>
        
        <div id="results"></div>

        <script>
            async function performSearch() {
                const query = document.getElementById('searchInput').value;
                const resultsDiv = document.getElementById('results');
                const loader = document.getElementById('loader');
                
                if (!query) return;
                
                resultsDiv.innerHTML = "";
                loader.style.display = "block";
                
                try {
                    const response = await fetch('/api/search?q=' + encodeURIComponent(query));
                    const data = await response.json();
                    
                    loader.style.display = "none";
                    
                    if (data.error) {
                        resultsDiv.innerHTML = `<h3 style="color:red; text-align:center; width:100%;">Error: ${data.error}</h3>`;
                        return;
                    }
                    
                    if (data.length === 0) {
                        resultsDiv.innerHTML = '<h3 style="text-align:center; width:100%;">❌ No results found!</h3>';
                        return;
                    }
                    
                    data.forEach(file => {
                        const card = `
                            <div class="card">
                                <div class="card-title">${file.name}</div>
                                <div class="card-info">💾 Size: ${file.size} | 📁 Type: ${file.type}</div>
                                <div class="btn-group">
                                    <a href="${file.watch}" target="_blank" class="btn-play">▶️ Play</a>
                                    <a href="${file.download}" class="btn-dl">⬇️ Download</a>
                                </div>
                            </div>
                        `;
                        resultsDiv.innerHTML += card;
                    });
                } catch (err) {
                    loader.style.display = "none";
                    resultsDiv.innerHTML = '<h3 style="color:red; text-align:center; width:100%;">Connection Error!</h3>';
                }
            }

            // Enter button support
            document.getElementById("searchInput").addEventListener("keypress", function(event) {
                if (event.key === "Enter") performSearch();
            });
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')
