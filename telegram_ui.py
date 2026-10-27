"""Telegram keyboard and command registry."""
COMMANDS = [
    {"command":"start","description":"Open MART dashboard"},
    {"command":"research","description":"Research market or product"},
    {"command":"recommend","description":"Business opportunity recommendations"},
    {"command":"marketing","description":"Create a marketing plan"},
    {"command":"ads","description":"Draft an ad campaign"},
    {"command":"social","description":"Create social media posts"},
    {"command":"video","description":"Create short-video script"},
    {"command":"affiliate","description":"Research affiliate opportunities"},
    {"command":"status","description":"Check research service"},
    {"command":"help","description":"Show instructions"},
]
ACTIONS = {
    "research": ("🔎 Research", "Research"),
    "recommend": ("📈 Recommendations", "Recommendations"),
    "marketing": ("📣 Marketing plan", "Marketing plan"),
    "ads": ("🎯 Ads creator", "Advertising campaign"),
    "social": ("📱 Social posts", "Social content"),
    "video": ("🎬 Video script", "Short-video script"),
    "affiliate": ("🛍 Affiliate", "Affiliate research"),
}
def keyboard():
    items=list(ACTIONS.items())
    rows=[]
    for i in range(0,len(items),2):
        rows.append([{"text": label, "callback_data": "action:"+key} for key,(label,_) in items[i:i+2]])
    rows.append([{"text":"⚙️ Status","callback_data":"status"},{"text":"❓ Help","callback_data":"help"}])
    return {"inline_keyboard":rows}
def menu_text():
    return ("🚀 MART Agentic Research & Marketing Studio\n\n"
            "Choose a tool below. Then send your business, product, niche or campaign topic.\n"
            "Research requires a configured search provider. Drafts are suggestions, not published ads.")
