# MART V8 Telegram Voice Intake

V8 supports **Telegram voice notes**, not always-on microphone listening. The bot fetches voice notes from the official Telegram Bot API and sends them to an authorized transcription endpoint.

Required: `TELEGRAM_BOT_TOKEN`, `MART_TRANSCRIBE_API_KEY`. Optional: `MART_TRANSCRIBE_MODEL` (default `whisper-1`).

Privacy: voice recordings are sent to the configured transcription service; do not claim on-device processing. Keep tokens out of logs and URLs in user-facing errors. Telegram voice files are limited to 8 MiB and 120 seconds by the application. Unrecognized voice instructions are not executed; the bot requests a text command instead.

Commands: "research <topic>", "cari <topic>", "campaign <topic>", "buat kempen <topic>". Campaigns produce review drafts only, with no automatic publishing or spending.

V8 is stacked on V7, which is stacked on V5. CI, privacy review and live bot verification are required before merging.
