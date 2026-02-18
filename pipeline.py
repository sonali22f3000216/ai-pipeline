import requests
import datetime
import json
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()
client = OpenAI()

DATA_FILE = "stored_results.json"



class PipelineRequest(BaseModel):
    email: str
    source: str



@app.get("/")
def root():
    return {"message": "AI Pipeline is running"}



def analyze_with_ai(text):
    try:
        prompt = f"""
Analyze this comment in 2-3 sentences and classify sentiment as enthusiastic, critical, or objective:

{text}

Respond ONLY in valid JSON format:
{{
  "analysis": "...",
  "sentiment": "enthusiastic/critical/objective"
}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        content = response.choices[0].message.content.strip()
        return json.loads(content)

    except Exception as e:
        return {
            "analysis": "AI processing failed.",
            "sentiment": "objective",
            "error": str(e)
        }



def store_result(item):
    try:
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []

        data.append(item)

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

        return True
    except:
        return False



def send_notification(email):
    print(f"Notification sent to: {email}")
    return True



@app.post("/pipeline")
def run_pipeline(req: PipelineRequest):

    results = []
    errors = []

    
    try:
        response = requests.get(
            "https://jsonplaceholder.typicode.com/comments?postId=1",
            timeout=5
        )
        response.raise_for_status()
        comments = response.json()[:3]

    except Exception as e:
        return {
            "items": [],
            "notificationSent": False,
            "processedAt": datetime.datetime.utcnow().isoformat() + "Z",
            "errors": [f"API fetch failed: {str(e)}"]
        }

    
    for comment in comments:
        try:
            text = comment["body"]

            ai_result = analyze_with_ai(text)

            item = {
                "original": text,
                "analysis": ai_result.get("analysis"),
                "sentiment": ai_result.get("sentiment"),
                "stored": False,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "source": req.source
            }

            stored = store_result(item)
            item["stored"] = stored

            results.append(item)

        except Exception as e:
            errors.append(f"Processing error: {str(e)}")
            continue

    
    notification_status = False
    try:
        notification_status = send_notification(req.email)
    except Exception as e:
        errors.append(f"Notification error: {str(e)}")

    return {
        "items": results,
        "notificationSent": notification_status,
        "processedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "errors": errors
    }
