import json
import os
from datetime import datetime

DATA_DIR = "data"
REQUESTS_FILE = os.path.join(DATA_DIR, "requests.json")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.json")


def init_storage():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def save_request(data):
    with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
        requests = json.load(f)

    request_id = len(requests) + 1
    data.update({
        "id": request_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    requests.append(data)

    with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(requests, f, ensure_ascii=False, indent=2)

    return request_id


def get_all_requests():
    with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_request_by_id(request_id):
    with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
        requests = json.load(f)
    for req in requests:
        if req["id"] == request_id:
            return req
    return None


def get_user_requests(user_id):
    with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
        requests = json.load(f)
    return [r for r in requests if r["user_id"] == user_id]


def update_request_status(request_id, new_status, updated_by="admin"):
    with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
        requests = json.load(f)

    for req in requests:
        if req["id"] == request_id:
            req["status"] = new_status
            req["updated_at"] = datetime.now().isoformat()
            break

    with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(requests, f, ensure_ascii=False, indent=2)


def save_feedback(data):
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        feedbacks = json.load(f)

    feedback_id = len(feedbacks) + 1
    data.update({
        "id": feedback_id,
        "created_at": datetime.now().isoformat()
    })
    feedbacks.append(data)

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=2)

    return feedback_id


def get_user_feedback(user_id):
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        feedbacks = json.load(f)
    return [f for f in feedbacks if f["user_id"] == user_id]


init_storage()
print("✅ storage.py загружен")