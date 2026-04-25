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


def feedback_menu():
    """Меню выбора типа обращения"""
    complaint = CallbackButton(text="📝 Обращение", payload="complaint", intent=Intent.DEFAULT)
    suggestion = CallbackButton(text="💡 Предложение", payload="suggestion", intent=Intent.DEFAULT)
    cancel = CallbackButton(text="❌ Отмена", payload="cancel", intent=Intent.NEGATIVE)

    payload = ButtonsPayload(buttons=[[complaint, suggestion], [cancel]])
    return Attachment(type="inline_keyboard", payload=payload)


def get_status_buttons(request_id: int, current_status: str):
    """
    Кнопки управления статусом заявки для группового чата
    current_status: pending, in_progress, completed, cancelled
    """
    buttons = []

    # Статус: ОЖИДАЕТ → показываем кнопки "Взять в работу" и "Отклонить"
    if current_status == "pending":
        buttons.append([
            CallbackButton(
                text="🔵 Взять в работу",
                payload=f"status_in_progress_{request_id}",
                intent=Intent.POSITIVE
            ),
            CallbackButton(
                text="❌ Отклонить",
                payload=f"status_cancelled_{request_id}",
                intent=Intent.NEGATIVE
            )
        ])

    # Статус: В РАБОТЕ → показываем кнопку "ГОТОВО"
    elif current_status == "in_progress":
        buttons.append([
            CallbackButton(
                text="✅ ГОТОВО (можно забрать)",
                payload=f"status_completed_{request_id}",
                intent=Intent.POSITIVE
            )
        ])

    # Для статусов "ГОТОВО" и "ОТКЛОНЕНА" — кнопок нет

    # Кнопка "Все заявки" доступна всегда
    buttons.append([
        CallbackButton(
            text="📋 Все заявки",
            payload="all_requests",
            intent=Intent.DEFAULT
        )
    ])

    payload = ButtonsPayload(buttons=buttons)
    return Attachment(type="inline_keyboard", payload=payload)


# ========== СЛОВАРИ СТАТУСОВ ==========

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

print("✅ keyboards.py загружен")