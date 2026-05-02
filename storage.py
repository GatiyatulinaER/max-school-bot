import json
import os
from datetime import datetime

# Файлы для хранения данных
REQUESTS_FILE = "requests.json"
FEEDBACK_FILE = "feedback.json"

# Загрузка данных
def load_requests():
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_requests_to_file(requests):
    with open(REQUESTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(requests, f, ensure_ascii=False, indent=2)

def load_feedback_from_file():
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_feedback_to_file(feedback):
    with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
        json.dump(feedback, f, ensure_ascii=False, indent=2)

# Инициализация
requests_storage = load_requests()
feedback_storage = load_feedback_from_file()

def save_all_data():
    """Сохраняет все данные в файлы"""
    save_requests_to_file(requests_storage)
    save_feedback_to_file(feedback_storage)

# ========== ФУНКЦИИ ДЛЯ ЗАЯВОК ==========
def save_request(data: dict) -> int:
    """Сохраняет новую заявку"""
    request_id = len(requests_storage) + 1
    requests_storage[request_id] = {
        "id": request_id,
        "user_id": data["user_id"],
        "building": data["building"],
        "fullname": data["fullname"],
        "class": data["class"],
        "birth_date": data["birth_date"],
        "reason": data["reason"],
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "assigned_to": None,
        "reject_reason": None
    }
    save_all_data()
    return request_id

def get_all_requests():
    """Возвращает все заявки"""
    return list(requests_storage.values())

def get_request_by_id(request_id: int):
    """Возвращает заявку по ID"""
    return requests_storage.get(request_id)

def update_request_status(request_id: int, status: str, admin_name: str = None, reject_reason: str = None):
    """Обновляет статус заявки"""
    if request_id in requests_storage:
        requests_storage[request_id]["status"] = status
        requests_storage[request_id]["updated_at"] = datetime.now().isoformat()
        if admin_name:
            requests_storage[request_id]["assigned_to"] = admin_name
        if reject_reason:
            requests_storage[request_id]["reject_reason"] = reject_reason
        save_all_data()

def get_user_requests(user_id: int):
    """Возвращает заявки пользователя"""
    return [r for r in requests_storage.values() if r["user_id"] == user_id]

# ========== ФУНКЦИИ ДЛЯ ОБРАЩЕНИЙ ==========
def save_feedback(data: dict) -> int:
    """Сохраняет обращение"""
    feedback_id = len(feedback_storage) + 1
    feedback_storage[feedback_id] = {
        "id": feedback_id,
        "user_id": data["user_id"],
        "user_name": data.get("user_name", ""),
        "fullname": data["fullname"],
        "phone": data.get("phone", ""),
        "phone_raw": data.get("phone_raw", ""),
        "message": data["message"],
        "type": data["type"],
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "assigned_to": None
    }
    save_all_data()
    return feedback_id

def get_user_feedback(user_id: int):
    """Возвращает обращения пользователя"""
    return [f for f in feedback_storage.values() if f["user_id"] == user_id]

def get_feedback_by_id(feedback_id: int):
    """Возвращает обращение по ID"""
    return feedback_storage.get(feedback_id)

def update_feedback_status(feedback_id: int, status: str, admin_name: str = None):
    """Обновляет статус обращения"""
    if feedback_id in feedback_storage:
        feedback_storage[feedback_id]["status"] = status
        feedback_storage[feedback_id]["updated_at"] = datetime.now().isoformat()
        if admin_name:
            feedback_storage[feedback_id]["assigned_to"] = admin_name
        save_all_data()

def get_unanswered_feedback():
    """Возвращает неотвеченные обращения"""
    return [f for f in feedback_storage.values() if f["status"] in ["pending", "in_progress"]]

def get_all_feedback():
    """Возвращает все обращения"""
    return list(feedback_storage.values())

print("✅ storage.py загружен")