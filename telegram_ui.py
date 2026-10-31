"""Telegram keyboard and command registry."""
COMMANDS = [
    {"command":"commerce","description":"AI commerce menu and drafts"},
    {"command":"commercemenu","description":"Open commerce platform buttons"},
    {"command":"shopee","description":"Shopee seller draft shortcut"},
    {"command":"facebook","description":"Facebook content draft shortcut"},
    {"command":"instagram","description":"Instagram content draft shortcut"},
    {"command":"threads","description":"Threads content draft shortcut"},
    {"command":"tiktok","description":"TikTok content draft shortcut"},
    {"command":"tiktokshop","description":"TikTok Shop draft shortcut"},
    {"command":"connections","description":"View account connection status"},
    {"command":"campaign","description":"One-click marketing campaign"},
    {"command":"campaignstatus","description":"Check campaign progress"},
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
    "commerce": ("🛍 Commerce Studio", "Commerce menu"),
    "campaign": ("🚀 Run Campaign", "Marketing campaign"),
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

# Commerce navigation is isolated from existing research menu.
COMMERCE_PAGES = {
    "home": [("🛍 Shopee", "shopee"), ("📘 Facebook", "facebook"),
             ("📸 Instagram", "instagram"), ("🧵 Threads", "threads"),
             ("🎵 TikTok", "tiktok"), ("🛒 TikTok Shop", "tiktok_shop"),
             ("📊 Connections", "connections"), ("❓ Guide", "guide")],
}
def commerce_keyboard(page="home"):
    if page == "home":
        items = COMMERCE_PAGES["home"]
        rows = [[{"text": title, "callback_data": "commerce:" + code}
                 for title, code in items[i:i+2]] for i in range(0, len(items), 2)]
    elif page in ("connections", "guide"):
        rows = []
    else:
        rows = [[{"text": "✍️ Create draft", "callback_data": "commerce:draft:" + page}]]
    rows.append([{"text": "🏠 Commerce home", "callback_data": "commerce:home"}])
    return {"inline_keyboard": rows}
def commerce_page(page):
    from social_agent import PLATFORMS
    if page == "home":
        return "🧠 MART AI Commerce Studio\nSelect a platform below. Drafts only; no publishing."
    if page == "connections":
        return "🔒 Connections: no social or seller API accounts connected. Official OAuth is required."
    if page == "guide":
        return "Select a platform, then Create draft. Send a product name in this private chat. Publishing is disabled."
    if page in PLATFORMS:
        return f"📣 {page.replace('_', ' ').title()}\\nDraft assistant ready. Publishing unavailable."
    raise ValueError("Unknown commerce page")

SHORTCUT_PLATFORMS = {
    "shopee": "shopee", "facebook": "facebook", "instagram": "instagram",
    "threads": "threads", "tiktok": "tiktok", "tiktokshop": "tiktok_shop",
}
def bot_commands():
    """Telegram setMyCommands payload; registering it requires a separate authorized API call."""
    return list(COMMANDS)
