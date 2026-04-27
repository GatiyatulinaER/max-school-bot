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


def safe_load_json(file_path, default=[]):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default


def safe_save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ========== ЗАЯВКИ НА СПРАВКИ ==========
def save_request(data):
    requests = safe_load_json(REQUESTS_FILE)
    request_id = len(requests) + 1
    data.update({
        "id": request_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    requests.append(data)
    safe_save_json(REQUESTS_FILE, requests)
    return request_id


def get_all_requests():
    return safe_load_json(REQUESTS_FILE)


def get_request_by_id(request_id):
    requests = safe_load_json(REQUESTS_FILE)
    for req in requests:
        if req["id"] == request_id:
            return req
    return None


def get_user_requests(user_id):
    requests = safe_load_json(REQUESTS_FILE)
    return [r for r in requests if r["user_id"] == user_id]


def update_request_status(request_id, new_status, updated_by="admin", reject_reason=None):
    requests = safe_load_json(REQUESTS_FILE)
    for req in requests:
        if req["id"] == request_id:
            req["status"] = new_status
            req["updated_at"] = datetime.now().isoformat()
            req["updated_by"] = updated_by
            if reject_reason:
                req["reject_reason"] = reject_reason
            break
    safe_save_json(REQUESTS_FILE, requests)
    print(f"✅ Статус заявки #{request_id} обновлён на '{new_status}'")


# ========== ОБРАЩЕНИЯ И ПРЕДЛОЖЕНИЯ ==========
def save_feedback(data):
    feedbacks = safe_load_json(FEEDBACK_FILE)
    feedback_id = len(feedbacks) + 1
    data.update({
        "id": feedback_id,
        "status": "pending",
        "answered": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    feedbacks.append(data)
    safe_save_json(FEEDBACK_FILE, feedbacks)
    return feedback_id


def get_user_feedback(user_id):
    feedbacks = safe_load_json(FEEDBACK_FILE)
    return [f for f in feedbacks if f["user_id"] == user_id]


def get_feedback_by_id(feedback_id):
    feedbacks = safe_load_json(FEEDBACK_FILE)
    for fb in feedbacks:
        if fb["id"] == feedback_id:
            return fb
    return None


def update_feedback_status(feedback_id, new_status, updated_by="admin"):
    feedbacks = safe_load_json(FEEDBACK_FILE)
    for fb in feedbacks:
        if fb["id"] == feedback_id:
            fb["status"] = new_status
            fb["updated_at"] = datetime.now().isoformat()
            fb["updated_by"] = updated_by
            if new_status == "completed":
                fb["answered"] = True
            break
    safe_save_json(FEEDBACK_FILE, feedbacks)
    print(f"✅ Статус обращения #{feedback_id} обновлён на '{new_status}'")


def get_unanswered_feedback():
    feedbacks = safe_load_json(FEEDBACK_FILE)
    return [f for f in feedbacks if f.get("status") in ["pending", "in_progress"]]


def get_all_feedback():
    return safe_load_json(FEEDBACK_FILE)


init_storage()
print("✅ storage.py загружен")