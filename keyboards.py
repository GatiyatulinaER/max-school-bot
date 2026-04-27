from maxapi.types import CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent


def main_menu():
    """Главное меню пользователя"""
    btn1 = CallbackButton(text="📄 Заказать справку", payload="new_request", intent=Intent.POSITIVE)
    btn2 = CallbackButton(text="💬 Обращение", payload="new_feedback", intent=Intent.DEFAULT)
    btn3 = CallbackButton(text="📋 Мои заявки", payload="my_requests", intent=Intent.DEFAULT)
    btn4 = CallbackButton(text="✉️ Мои обращения", payload="my_feedback", intent=Intent.DEFAULT)

    payload = ButtonsPayload(buttons=[[btn1], [btn2], [btn3, btn4]])
    return Attachment(type="inline_keyboard", payload=payload)


def building_menu():
    """Меню выбора здания для справки"""
    building1 = CallbackButton(text="🏫 Здание на ул. Марченко", payload="building1_request", intent=Intent.POSITIVE)
    building2 = CallbackButton(text="🏫 Здание на ул. Танкистов", payload="building2_request", intent=Intent.POSITIVE)
    cancel = CallbackButton(text="❌ Отмена", payload="cancel", intent=Intent.NEGATIVE)

    payload = ButtonsPayload(buttons=[[building1], [building2], [cancel]])
    return Attachment(type="inline_keyboard", payload=payload)


def feedback_type_menu():
    """Меню выбора типа обращения"""
    complaint = CallbackButton(text="⚠️ Обращение / Жалоба", payload="complaint", intent=Intent.DEFAULT)
    suggestion = CallbackButton(text="💡 Предложение", payload="suggestion", intent=Intent.DEFAULT)
    cancel = CallbackButton(text="❌ Отмена", payload="cancel", intent=Intent.NEGATIVE)

    payload = ButtonsPayload(buttons=[[complaint], [suggestion], [cancel]])
    return Attachment(type="inline_keyboard", payload=payload)


def get_confirm_buttons():
    """Кнопки подтверждения заявки"""
    yes = CallbackButton(text="✅ ДА, ОТПРАВИТЬ", payload="confirm_yes", intent=Intent.POSITIVE)
    no = CallbackButton(text="❌ НЕТ, ОТМЕНИТЬ", payload="confirm_no", intent=Intent.NEGATIVE)
    payload = ButtonsPayload(buttons=[[yes], [no]])
    return Attachment(type="inline_keyboard", payload=payload)


def get_reject_reasons_buttons(request_id: int):
    """Кнопки для выбора причины отклонения"""
    buttons = [
        [CallbackButton(text="📝 Данные некорректно введены", payload=f"reject_{request_id}_wrong_data",
                        intent=Intent.NEGATIVE)],
        [CallbackButton(text="❌ Нет оснований для выдачи", payload=f"reject_{request_id}_no_basis",
                        intent=Intent.NEGATIVE)],
        [CallbackButton(text="◀️ Назад", payload="back_to_request", intent=Intent.DEFAULT)]
    ]
    payload = ButtonsPayload(buttons=buttons)
    return Attachment(type="inline_keyboard", payload=payload)


def get_status_buttons(request_id: int, current_status: str):
    """Кнопки управления статусом заявки"""
    buttons = []

    if current_status == "pending":
        buttons.append([
            CallbackButton(text="🔵 Взять в работу", payload=f"status_in_progress_{request_id}", intent=Intent.POSITIVE),
            CallbackButton(text="❌ Отклонить", payload=f"reject_request_{request_id}", intent=Intent.NEGATIVE)
        ])
    elif current_status == "in_progress":
        buttons.append([
            CallbackButton(text="✅ ГОТОВО (можно забрать)", payload=f"status_completed_{request_id}",
                           intent=Intent.POSITIVE)
        ])

    buttons.append([
        CallbackButton(text="📋 Все заявки", payload="all_requests", intent=Intent.DEFAULT)
    ])

    payload = ButtonsPayload(buttons=buttons)
    return Attachment(type="inline_keyboard", payload=payload)


def get_feedback_status_buttons(feedback_id: int, current_status: str):
    """Кнопки для обращений"""
    buttons = []

    if current_status == "pending":
        buttons.append([
            CallbackButton(text="🔵 Взять в работу", payload=f"take_fb_{feedback_id}", intent=Intent.POSITIVE)
        ])
    elif current_status == "in_progress":
        buttons.append([
            CallbackButton(text="✅ Отметить как отвеченное", payload=f"done_fb_{feedback_id}", intent=Intent.POSITIVE)
        ])

    if buttons:
        payload = ButtonsPayload(buttons=buttons)
        return Attachment(type="inline_keyboard", payload=payload)
    return None


def get_feedback_list_buttons():
    """Кнопки для списка обращений"""
    buttons = [
        [CallbackButton(text="🆕 Активные обращения", payload="admin_active_feedback", intent=Intent.DEFAULT)],
        [CallbackButton(text="📋 История обращений", payload="admin_all_feedback", intent=Intent.DEFAULT)]
    ]
    payload = ButtonsPayload(buttons=buttons)
    return Attachment(type="inline_keyboard", payload=payload)


# ========== СЛОВАРИ ==========

BUILDING_NAMES = {
    "building1": "🏫 Здание на ул. Марченко",
    "building2": "🏫 Здание на ул. Танкистов"
}

# ========== АДРЕСА И ТЕЛЕФОНЫ ДЛЯ КАЖДОГО ЗДАНИЯ ==========
BUILDING_INFO = {
    "building1": {
        "name": "Здание на ул. Марченко",
        "address": "г. Челябинск, ул. Марченко, д. 23г",
        "phone": "+7 (351) 773-69-27",
        "cabinet": "приемная",
        "floor": "2-й этаж",
        "email": "mousosh39@mail.ru",
        "work_hours": "Понедельник - пятница: 9:00 - 16:00",
        "lunch": "12:00 - 13:00"
    },
    "building2": {
        "name": "Здание на ул. Танкистов",
        "address": "г. Челябинск, ул. Танкистов, д. 144б",
        "phone": "+7 (351) 772-47-47",
        "cabinet": "приемная",
        "floor": "1-й этаж",
        "email": "mousosh39@mail.ru",
        "work_hours": "Понедельник - пятница: 9:00 - 16:00",
        "lunch": "12:00 - 13:00"
    }
}

STATUS_TEXT = {
    "pending": "⏳ Ожидает рассмотрения",
    "in_progress": "📝 В обработке",
    "completed": "✅ ГОТОВО (можно забрать)",
    "cancelled": "❌ Отклонена"
}

STATUS_EMOJI = {
    "pending": "🟡",
    "in_progress": "🔵",
    "completed": "✅",
    "cancelled": "❌"
}

FEEDBACK_STATUS_TEXT = {
    "pending": "🟡 Ожидает ответа",
    "in_progress": "🔵 В работе",
    "completed": "✅ Отвечено"
}

print("✅ keyboards.py загружен")