"""Telegram voice intake: bounded downloads, explicit transcription provider, no publishing."""
import os
import re
import httpx
MAX_BYTES=8*1024*1024
MAX_DURATION=120
class VoiceError(Exception):pass

def parse_command(transcript):
    if not isinstance(transcript,str):raise VoiceError("Invalid transcript")
    t=" ".join(transcript.strip().split())
    if len(t)>500:raise VoiceError("Voice instruction too long")
    m=re.match(r"^(?:research|search|find|cari|selidik)\s+(.+)$",t,re.I)
    if m:return ("research",m.group(1))
    m=re.match(r"^(?:create campaign|run campaign|campaign|buat kempen|cipta kempen)\s+(.+)$",t,re.I)
    if m:return ("campaign",m.group(1))
    return ("confirm",t)

async def transcribe_telegram_voice(file_id,duration=None,client=None):
    if not isinstance(file_id,str) or not 1<=len(file_id)<=256:raise VoiceError("Invalid file ID")
    if duration is not None and (not isinstance(duration,int) or duration<0 or duration>MAX_DURATION):
        raise VoiceError("Voice message exceeds duration limit")
    bot=os.getenv("TELEGRAM_BOT_TOKEN")
    key=os.getenv("MART_TRANSCRIBE_API_KEY")
    if not bot or not key:raise VoiceError("Voice transcription not configured")
    owned=client is None
    if owned:client=httpx.AsyncClient(timeout=25,follow_redirects=False)
    try:
        resp=await client.get("https://api.telegram.org/bot"+bot+"/getFile",params={"file_id":file_id})
        resp.raise_for_status()
        payload=resp.json()
        if not payload.get("ok"):raise VoiceError("Telegram file lookup failed")
        info=payload["result"]
        if int(info.get("file_size",0))>MAX_BYTES:raise VoiceError("Voice message too large")
        path=info.get("file_path","")
        if not path.startswith("voice/") or ".." in path or not path.endswith((".oga",".ogg")):
            raise VoiceError("Unexpected voice file path")
        audio=await client.get("https://api.telegram.org/file/bot"+bot+"/"+path)
        audio.raise_for_status()
        if len(audio.content)>MAX_BYTES:raise VoiceError("Voice message too large")
        result=await client.post("https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization":"Bearer "+key},
            data={"model":os.getenv("MART_TRANSCRIBE_MODEL","whisper-1")},
            files={"file":("voice.ogg",audio.content,"audio/ogg")})
        result.raise_for_status()
        transcript=result.json().get("text")
        if not isinstance(transcript,str) or not transcript.strip():raise VoiceError("Empty transcription")
        return transcript[:1000]
    except (httpx.HTTPError,KeyError,TypeError,ValueError) as exc:
        raise VoiceError("Voice service unavailable") from exc
    finally:
        if owned:await client.aclose()
