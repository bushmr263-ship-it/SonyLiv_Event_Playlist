from datetime import datetime, timedelta, timezone
import json
import os
import requests

M3U_SOURCE_URL = "https://raw.githubusercontent.com/sm-monirulislam/SonyLiv_Event_Playlist/refs/heads/main/sonyLiv.m3u"
JSON_SOURCE_URL = "https://raw.githubusercontent.com/sm-monirulislam/SonyLiv_Event_Playlist/refs/heads/main/sonyLiv_data.json"

M3U_OUTPUT_FILE = "SonyLiv.m3u"
JSON_OUTPUT_FILE = "SonyLiv_data.json"

OWNER_NAME = "Shawon"
TELEGRAM_LINK = "https://t.me/+VqDOF_-beaQyMWY1"

# শুধু LIVE ম্যাচ রাখতে True করুন; সব ম্যাচ রাখতে False রাখুন
ONLY_LIVE = False

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cache-Control": "no-cache",
}


def fetch_json_data():
    resp = requests.get(JSON_SOURCE_URL, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return resp.json()


def build_m3u_from_matches(matches, bd_time):
    valid_items = []
    for m in matches:
        stream_link = str(m.get("stream_link") or "").strip()
        if not stream_link:
            continue
        status = str(m.get("status") or "").strip().upper()
        if ONLY_LIVE and status != "LIVE":
            continue

        title = str(m.get("match_name") or m.get("event_name") or "SonyLiv Event").strip()
        lang = str(m.get("audioLanguageName") or "").strip()
        if lang and f"[{lang}]" not in title:
            title = f"{title} [{lang}]"

        tvg_id = str(m.get("contentId") or "").strip()
        logo = str(m.get("src") or "").strip()
        group = str(m.get("event_category") or "Sports").strip()

        extinf = (
            f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{title}" '
            f'tvg-logo="{logo}" group-title="{group}",{title}'
        )
        valid_items.append((extinf, stream_link))

    out_lines = [
        "#EXTM3U",
        "# ==========================================",
        f"# Developed by: {OWNER_NAME}",
        f"# Telegram: {TELEGRAM_LINK}",
        f"# Last Updated: {bd_time} (BD Time)",
        f"# Channels Count: {len(valid_items)}",
        "# ==========================================",
        "",
    ]
    for extinf, url in valid_items:
        out_lines.append(extinf)
        out_lines.append(url)
        out_lines.append("")

    return "\n".join(out_lines).strip() + "\n", len(valid_items)


def build_m3u_fallback(bd_time):
    resp = requests.get(M3U_SOURCE_URL, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    lines = resp.text.splitlines()

    entries = []
    current_extinf = None
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            current_extinf = line
        elif not line.startswith("#") and current_extinf:
            entries.append((current_extinf, line))
            current_extinf = None

    if not entries:
        return None, 0

    out_lines = [
        "#EXTM3U",
        "# ==========================================",
        f"# Developed by: {OWNER_NAME}",
        f"# Telegram: {TELEGRAM_LINK}",
        f"# Last Updated: {bd_time} (BD Time)",
        f"# Channels Count: {len(entries)}",
        "# ==========================================",
        "",
    ]
    for extinf, url in entries:
        out_lines.append(extinf)
        out_lines.append(url)
        out_lines.append("")

    return "\n".join(out_lines).strip() + "\n", len(entries)


def run_sync():
    bd_now = datetime.now(timezone(timedelta(hours=6)))
    bd_time = bd_now.strftime("%Y-%m-%d %H:%M:%S")
    json_time = bd_now.strftime("%I:%M:%S %p %d-%m-%Y")

    data = fetch_json_data()
    raw_matches = data.get("matches", []) if isinstance(data, dict) else []

    if ONLY_LIVE:
        active_matches = [
            m for m in raw_matches if str(m.get("status") or "").strip().upper() == "LIVE"
        ]
    else:
        active_matches = raw_matches

    if isinstance(data, dict):
        data["owner"] = OWNER_NAME
        data["telegram"] = TELEGRAM_LINK
        data["last_update_time"] = json_time
        data["total_matches"] = len(active_matches)
        data["live_match"] = sum(
            1 for m in active_matches if str(m.get("status") or "").strip().upper() == "LIVE"
        )
        data["matches"] = active_matches

        with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    m3u_content, count = build_m3u_from_matches(active_matches, bd_time)
    if count == 0:
        fallback_content, fallback_count = build_m3u_fallback(bd_time)
        if fallback_content and fallback_count > 0:
            m3u_content, count = fallback_content, fallback_count
        elif os.path.exists(M3U_OUTPUT_FILE):
            print(f"No SonyLiv streams found at {bd_time}; keeping existing {M3U_OUTPUT_FILE}.")
            return

    with open(M3U_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(m3u_content)

    print(f"Updated {M3U_OUTPUT_FILE} ({count} active streams) and {JSON_OUTPUT_FILE} at {bd_time}")


if __name__ == "__main__":
    run_sync()
