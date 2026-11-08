"""Telegram keyboard and command registry."""
COMMANDS = [
    {"command":"menu","description":"Open the MART tools"},
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
            "Choose a tool below or use a slash shortcut such as /research or /campaign.\n"
            "Research requires a configured search provider. Drafts are suggestions, not published ads.")


if __name__ == "__main__":
    # Paste this list into BotFather's Edit Commands screen for the staging bot.
    for command in COMMANDS:
        print(f"{command['command']} - {command['description']}")
