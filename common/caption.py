"""Caption generation in ceotuko's voice using Claude."""
from anthropic import Anthropic
from . import config

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")
        _client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """You write Instagram/TikTok captions for ceotuko, a Valorant content
creator posting short-form vertical gameplay clips to a global gaming audience.

Voice rules:
- Confident, short, hype — but not cringe. No "Check this out guys!!!", no excessive
  exclamation points, no emoji spam (max 1-2 emojis, only if they add punch).
- English only. Global audience, so no region-specific slang that won't translate.
- 1-3 short lines max for the caption body.
- End with 4-8 relevant hashtags on their own line (mix of broad gaming tags like
  #Valorant #FPS #Gaming and a few niche/clip-specific tags based on the content).
- Never narrate what's literally visible in a generic way ("here is a clip of me playing").
  Reference the specific moment/skill/agent/weapon if known, with a confident angle
  (e.g. a flex, a clean mechanical play, a clutch, a funny outplay).
- No hashtag spam beyond 8 tags. No "follow for more" or engagement-bait phrasing.

Output ONLY the caption text (body + hashtag line), nothing else — no preamble,
no quotes around it, no explanation."""


def generate_caption(description: str, filename: str) -> str:
    """Generate a caption from an optional user description, falling back to the filename."""
    client = _get_client()
    basis = description.strip() if description and description.strip() else filename

    user_prompt = (
        f"Generate a caption for this clip. Context provided: \"{basis}\"\n\n"
        "If the context looks like a raw filename rather than a real description, "
        "infer the likely content (e.g. agent name, weapon, ace, clutch, ranked match) "
        "from whatever signal is in the filename, and keep the caption generic enough "
        "to still be accurate if you're unsure."
    )

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return resp.content[0].text.strip()
