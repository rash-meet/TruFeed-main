import os
import datetime
import re
import json
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
import google.generativeai as genai
from dotenv import load_dotenv
from bson import ObjectId

# ---------- Mock datetime for consistent testing ----------
class MockDate(datetime.date):
    @classmethod
    def today(cls):
        return cls(2025, 7, 21)
datetime.date = MockDate

# ---------- Load environment ----------
load_dotenv()

# ---------- Flask & DB Config ----------
app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI"))
db = client["trufeed"]
events = db["event5"]

# ---------- Gemini Config ----------
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# ---------- Helpers ----------
def nearby_places(place: str) -> list[str]:
    prompt = f"""
You are an Indian geography expert.
Return a JSON list (max 10) of city / district / area names that are
very close or commonly considered the same region as "{place}".
The list must include the original name.
Return only valid JSON, nothing else.
Example for "delhi": ["delhi", "new delhi", "ncr", "gurugram", "ghaziabad", "noida"]
    """
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.I).strip()
        places = json.loads(cleaned)
        return [p.strip().lower() for p in places if p.strip()]
    except Exception as e:
        print(f"Error in nearby_places for '{place}': {e}")
        return [place.lower().strip()]

def date_range(days_back=4):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days_back)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

def clean_mongo_docs(docs):
    cleaned = []
    for doc in docs:
        safe = {}
        for k, v in doc.items():
            if k == "_id":
                continue
            if isinstance(v, ObjectId):
                v = str(v)
            safe[k] = v
        cleaned.append(safe)
    return cleaned

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index4.html")

@app.route("/route-map")
def route_map():
    return render_template("route-map.html")

@app.route("/ask", methods=["POST"])
def ask():
    user_query = request.json.get("query", "").strip()
    if not user_query:
        return jsonify({"answer": "Please provide a query.", "events": []}), 400

    client_ip = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)

    extraction_prompt = f"""
You are a travel route and location extractor for India.

Given this user query:
"{user_query}"

Extract:
- intent: "route" or "info"
- from: name of origin place (nullable)
- to: name of destination place (nullable)
- from_latlng: coordinates of the origin (nullable), as [lat, lng]
- to_latlng: coordinates of the destination (nullable), as [lat, lng]

Return a JSON object like:
{{
  "intent": "route",
  "from": "delhi",
  "to": "manali",
  "from_latlng": [28.6139, 77.2090],
  "to_latlng": [32.2432, 77.1892]
}}

If the query doesn't specify a route, set intent to "info" and latlng fields to null.
Return only valid JSON, nothing else.
"""
    try:
        response = model.generate_content(extraction_prompt)
        raw_parsed = response.text.strip()
        cleaned_parsed = re.sub(r"```(?:json)?", "", raw_parsed, flags=re.I).strip()
        parsed = json.loads(cleaned_parsed)

        if parsed.get("from"):
            parsed["from"] = parsed["from"].strip().lower()
        if parsed.get("to"):
            parsed["to"] = parsed["to"].strip().lower()

        if parsed.get("from_latlng") and isinstance(parsed["from_latlng"], list):
            parsed["from_coords"] = {
                "lat": parsed["from_latlng"][0],
                "lng": parsed["from_latlng"][1]
            }
        if parsed.get("to_latlng") and isinstance(parsed["to_latlng"], list):
            parsed["to_coords"] = {
                "lat": parsed["to_latlng"][0],
                "lng": parsed["to_latlng"][1]
            }

    except Exception as e:
        print(f"Error parsing extraction prompt response: {e}. Raw response: {raw_parsed}")
        parsed = {
            "intent": "info", "from": None, "to": None,
            "from_coords": None, "to_coords": None
        }

    start, end = date_range()
    mongo_filter = {"event_date": {"$gte": start, "$lte": end}}
    docs = []

    if parsed["intent"] == "route":
        from_place = parsed.get("from")
        to_place = parsed.get("to")

        if from_place and to_place:
            from_tokens = nearby_places(from_place)
            to_tokens = nearby_places(to_place)
            all_route_tokens = list(set(from_tokens + to_tokens))
            if all_route_tokens:
                regex_pattern = "|".join(re.escape(k) for k in all_route_tokens if k)
                mongo_filter["location"] = {"$regex": regex_pattern, "$options": "i"}

            docs = list(events.find(mongo_filter))

            if not docs:
                kw_prompt = f"""
Given a travel route between {from_place} and {to_place}, what are 3 general keywords for potential road or travel disruptions?
Consider terms like 'roadblock', 'traffic', 'landslide', 'flood', 'accident', 'closure'.
Return comma separated. Example: landslide, traffic, road closure
"""
                try:
                    kw_response = model.generate_content(kw_prompt)
                    kw = [k.strip() for k in kw_response.text.strip().split(",") if k.strip()]
                    if kw:
                        kw_regex = "|".join(re.escape(k) for k in kw)
                        fallback_filter = {
                            "event_summary": {"$regex": kw_regex, "$options": "i"},
                            "event_date": {"$gte": start, "$lte": end}
                        }
                        docs = list(events.find(fallback_filter))
                except Exception as e:
                    print(f"Error generating fallback keywords for route: {e}")

        if not from_place or not to_place:
            docs = [{"info": "Please specify both origin and destination for a route query. Example: 'road from Delhi to Manali'"}]
            parsed["intent"] = "info"
            parsed["from"] = None
            parsed["to"] = None

    else:
        query_target_location = parsed.get("from") or parsed.get("to")
        if query_target_location:
            location_tokens = nearby_places(query_target_location)
            if location_tokens:
                regex_pattern = "|".join(re.escape(k) for k in location_tokens if k)
                mongo_filter["location"] = {"$regex": regex_pattern, "$options": "i"}

            kw_prompt = f"""
Extract up to 3 general keywords from the query: "{user_query}" that describe types of events.
Return comma separated. Example: landslide, flood, fire
"""
            try:
                kw_response = model.generate_content(kw_prompt)
                kw = [k.strip() for k in kw_response.text.strip().split(",") if k.strip()]
                if kw:
                    kw_regex = "|".join(re.escape(k) for k in kw)
                    mongo_filter["$or"] = [
                        {"location": mongo_filter.get("location", {"$exists": True})},
                        {"event_summary": {"$regex": kw_regex, "$options": "i"}}
                    ]
                    if "location" in mongo_filter and "$or" in mongo_filter:
                        del mongo_filter["location"]
            except Exception as e:
                print(f"Error generating info keywords: {e}")
        else:
            kw_prompt = f"""
Extract up to 3 general keywords from the query: "{user_query}" that describe types of events.
Return comma separated. Example: traffic, weather, disaster
"""
            try:
                kw_response = model.generate_content(kw_prompt)
                kw = [k.strip() for k in kw_response.text.strip().split(",") if k.strip()]
                if kw:
                    kw_regex = "|".join(re.escape(k) for k in kw)
                    mongo_filter["event_summary"] = {"$regex": kw_regex, "$options": "i"}
            except Exception as e:
                print(f"Error generating general info keywords: {e}")

        docs = list(events.find(mongo_filter))

    if not docs:
        docs = [{"info": "No significant events matched your criteria in the last 4 days."}]

    summaries = [d.get("event_summary", "") for d in docs if d.get("event_summary")]
    context = "\n".join(summaries) if summaries else "No specific event summaries found."

    answer_prompt_base = f"""
You are a helpful travel assistant and disaster information provider for India.
User query: "{user_query}"
Relevant events from the last 4 days: {context}
"""

    if parsed["intent"] == "route" and parsed.get("from") and parsed.get("to"):
        answer_prompt = f"""{answer_prompt_base}
Based on the user query asking about a route from {parsed['from'].title()} to {parsed['to'].title()} and the relevant events, provide a concise and helpful answer regarding the route.
Clearly state if there are potential impacts on the route (e.g., delays, diversions, closures) due to these events.
Suggest checking local news or authorities for real-time updates if impacts are significant.
If no relevant disruptive events are found, state that the route appears clear based on available information for the last 4 days.
"""
    else:
        answer_prompt = f"""{answer_prompt_base}
Give a concise, helpful answer about the events, focusing on the user's original query.
If no specific events are found for an info query, state that clearly.
"""

    try:
        answer_response = model.generate_content(answer_prompt)
        answer = answer_response.text.strip()
    except Exception as e:
        print(f"Error generating final answer: {e}")
        answer = "I'm unable to provide a clear answer right now. Please try again later."

    db["queries"].insert_one({
        "query": user_query,
        "intent_parsed": parsed,
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "ip": client_ip,
        "mongo_filter_used": mongo_filter,
        "found_events_count": len(docs),
        "generated_answer": answer
    })

    return jsonify({
        "answer": answer,
        "events": clean_mongo_docs(docs),
        "intent": parsed.get("intent", "info"),
        "route": {
            "from": {
                "name": parsed.get("from"),
                **parsed.get("from_coords", {})
            } if parsed.get("from_coords") else None,
            "to": {
                "name": parsed.get("to"),
                **parsed.get("to_coords", {})
            } if parsed.get("to_coords") else None
        }
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
