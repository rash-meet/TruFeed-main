import requests
import json
import os
from datetime import datetime
from typing import Dict, Any

BASE_DIR = os.path.dirname(__file__) or os.getcwd()

# Current response
CURRENT_JSON = os.path.join(BASE_DIR, "instagram_current.json")
CURRENT_TXT  = os.path.join(BASE_DIR, "instagram_current.txt")

# History (append-only)
HISTORY_JSON = os.path.join(BASE_DIR, "instagram_history.json")
HISTORY_TXT  = os.path.join(BASE_DIR, "instagram_history.txt")


def _append_to_history(data: Dict[str, Any]) -> None:
    """Append the response to both history files."""
    entry = {
        "_timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "response":   data
    }
    try:
        if os.path.isfile(HISTORY_JSON):
            with open(HISTORY_JSON, "r+", encoding="utf-8") as f:
                history = json.load(f)
                history.append(entry)
                f.seek(0)
                json.dump(history, f, indent=2, ensure_ascii=False)
                f.truncate()
        else:
            with open(HISTORY_JSON, "w", encoding="utf-8") as f:
                json.dump([entry], f, indent=2, ensure_ascii=False)
    except Exception:   
        with open(HISTORY_JSON, "w", encoding="utf-8") as f:
            json.dump([entry], f, indent=2, ensure_ascii=False)

    # Plain-text history
    with open(HISTORY_TXT, "a", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"Timestamp: {entry['_timestamp']}\n")
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n\n")

# main function is this 
def call_instagram_graph_api(url: str,
                             user_id: str,
                             fields: str,
                             access_token: str) -> Dict[str, Any]:
    """
    Calls the Instagram Graph API and saves the response in four files:
      1. instagram_current.json   – latest response (pretty JSON)
      2. instagram_current.txt    – latest response (plain text)
      3. instagram_history.json   – array of all responses (pretty JSON)
      4. instagram_history.txt    – plain-text append-only log

    Returns the decoded JSON payload.
    """
    endpoint = url.format(user_id=user_id)
    params   = {"user_id": user_id, "fields": fields, "access_token": access_token}

    resp = requests.get(endpoint, params=params)
    resp.raise_for_status()
    data = resp.json()

    # --- Current files (overwrite) ---
    with open(CURRENT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    with open(CURRENT_TXT, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False))

    # --- History files (append) ---
    _append_to_history(data)

    return data


# ------------------------------------------------------------------
# manual test
# ------------------------------------------------------------------
if __name__ == "__main__":
    test_url     = "https://graph.facebook.com/17843724880027643/recent_media?"
    test_uid     = "<user-id>"
    test_fields  = "caption,id,media_type,media_url"
    test_token   = "<access-key>"

    try:
        result = call_instagram_graph_api(
            url=test_url, user_id=test_uid,
            fields=test_fields, access_token=test_token
        )
        print("Success! Latest response:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print("API call failed:", e)
