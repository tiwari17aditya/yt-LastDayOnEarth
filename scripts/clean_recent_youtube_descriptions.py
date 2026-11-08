import re
import sys
from googleapiclient.discovery import build
from src.google_auth import get_google_credentials

# Pattern to match and remove licensing and copyright disclaimers
DISCLAIMER_PATTERN = re.compile(
    r"(?:\n?─{10,}\s*)?"
    r"🎵 MUSIC & (?:AUDIO )?LICENSING ATTRIBUTION:.*?"
    r"⚖️ COPYRIGHT & FAIR USE DISCLAIMER:.*?"
    r"protected under Fair Use \(Section 107 of the US Copyright Act 1976\)\.\s*"
    r"(?:─{10,}\s*)?",
    re.DOTALL,
)


def clean_desc(desc: str) -> str:
    cleaned = DISCLAIMER_PATTERN.sub("\n\n", desc)
    if "MUSIC &" in cleaned and "LICENSING ATTRIBUTION:" in cleaned:
        cleaned = re.sub(
            r"(?:\n?─{10,}\s*)?🎵 MUSIC & [^\n]+.*?https://creativecommons\.org/[^\s]+\s*",
            "\n\n",
            cleaned,
            flags=re.DOTALL,
        )
    if "COPYRIGHT & FAIR USE DISCLAIMER:" in cleaned:
        cleaned = re.sub(
            r"(?:\n?─{10,}\s*)?⚖️ COPYRIGHT & FAIR USE DISCLAIMER:.*?(?:1976\)\.\s*)",
            "\n\n",
            cleaned,
            flags=re.DOTALL,
        )
    # Clean redundant dividers and multiple blank lines
    cleaned = re.sub(r"(─{10,}\s*){2,}", "────────────────────────────────────────\n\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def main():
    creds = get_google_credentials()
    yt = build("youtube", "v3", credentials=creds)

    # Check recent videos
    res = yt.search().list(part="id,snippet", forMine=True, type="video", maxResults=10, order="date").execute()
    for item in res.get("items", []):
        vid = item["id"]["videoId"]
        title = item["snippet"]["title"]

        # Fetch full snippet
        v_res = yt.videos().list(part="snippet", id=vid).execute()
        if not v_res["items"]:
            continue
        v_item = v_res["items"][0]
        snippet = v_item["snippet"]
        old_desc = snippet["description"]

        if "MUSIC &" in old_desc or "COPYRIGHT & FAIR USE" in old_desc:
            print(f"Cleaning video {vid}: {title}")
            new_desc = clean_desc(old_desc)
            snippet["description"] = new_desc
            yt.videos().update(part="snippet", body={"id": vid, "snippet": snippet}).execute()
            print(f"  -> Successfully cleaned description for {vid}!")
        else:
            print(f"Video {vid} is already clean: {title}")


if __name__ == "__main__":
    main()
