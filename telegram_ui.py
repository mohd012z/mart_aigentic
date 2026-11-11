"""MART Telegram command registry and research-only menu presentation."""
COMMANDS = [
    {"command": "start", "description": "Open MART main menu"},
    {"command": "menu", "description": "Show interactive tools"},
    {"command": "campaign", "description": "Prepare a campaign for review"},
    {"command": "campaignstatus", "description": "Check campaign progress"},
    {"command": "research", "description": "Research a product or market"},
    {"command": "recommend", "description": "Get business recommendations"},
    {"command": "marketing", "description": "Generate a marketing plan"},
    {"command": "ads", "description": "Draft advertisement copy"},
    {"command": "social", "description": "Draft social media content"},
    {"command": "video", "description": "Draft short-video script"},
    {"command": "affiliate", "description": "Research affiliate products"},
    {"command": "status", "description": "Check service configuration"},
    {"command": "help", "description": "Show command instructions"},
]
ACTIONS = {
    "campaign": ("🚀 Campaign", "Campaign review"),
    "research": ("🔎 Research", "Research"),
    "recommend": ("📊 Recommendations", "Recommendations"),
    "marketing": ("📣 Marketing", "Marketing plan"),
    "ads": ("🎯 Ads Creator", "Advertising draft"),
    "social": ("📱 Social Posts", "Social content"),
    "video": ("🎬 Video Script", "Short-video script"),
    "affiliate": ("🛍 Affiliate", "Affiliate research"),
}
def keyboard():
    pairs = list(ACTIONS.items())
    rows = [
        [{"text": label, "callback_data": "action:" + key}
         for key, (label, _) in pairs[i:i + 2]]
        for i in range(0, len(pairs), 2)
    ]
    rows.append([
        {"text": "⚙️ Status", "callback_data": "status"},
        {"text": "❓ Help", "callback_data": "help"},
    ])
    rows.append([{"text": "🏠 Main Menu", "callback_data": "menu"}])
    return {"inline_keyboard": rows}

def menu_text():
    return (
        "🚀 MART | AI Research & Marketing Studio\n\n"
        "Choose a tool below or type a command.\n\n"
        "🔎 Research & recommendations\n"
        "📣 Marketing, ads, social and video drafts\n"
        "🛍 Affiliate research (verified catalog + evidence)\n"
        "🚀 Campaign preparation and review\n"
        "📈 /metrics — usage & cost ledger\n\n"
        "🔒 Research mode: no automatic publishing or live campaign delivery.\n"
        "Use /help for examples."
    )
