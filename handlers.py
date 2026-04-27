import re
from datetime import datetime
from maxapi import Bot, Dispatcher, F
from maxapi.types import MessageCreated, BotStarted, MessageCallback, Command
from maxapi.types import CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent

from config import (
    BOT_TOKEN, BUILDING_1_CHAT_ID, BUILDING_2_CHAT_ID,
    COMPLAINTS_CHAT_ID, SUGGESTIONS_CHAT_ID, ADMIN_ID
)
from keyboards import (
    main_menu, building_menu, feedback_type_menu, get_status_buttons,
    get_reject_reasons_buttons, get_confirm_buttons, get_feedback_status_buttons,
    get_feedback_list_buttons, STATUS_TEXT, STATUS_EMOJI, FEEDBACK_STATUS_TEXT,
    BUILDING_NAMES, BUILDING_INFO
)
from storage import (
    save_request, get_all_requests, get_request_by_id, update_request_status, get_user_requests,
    save_feedback, get_user_feedback, get_feedback_by_id, update_feedback_status,
    get_unanswered_feedback, get_all_feedback
)

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_states = {}
user_step = {}


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def validate_birth_date(date_str: str) -> bool:
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    if not re.match(pattern, date_str):
        return False
    try:
        day, month, year = map(int, date_str.split('.'))
        birth_date = datetime(year, month, day)
        return birth_date <= datetime.now()
    except ValueError:
        return False


def get_request_chat_id(building_type: str):
    if building_type == "building1":
        return BUILDING_1_CHAT_ID
    elif building_type == "building2":
        return BUILDING_2_CHAT_ID
    return ADMIN_ID


def get_feedback_chat_id(feedback_type: str):
    if feedback_type == "complaint":
        return COMPLAINTS_CHAT_ID
    elif feedback_type == "suggestion":
        return SUGGESTIONS_CHAT_ID
    return ADMIN_ID


# ========== ОБРАБОТЧИКИ ЗАПУСКА ==========
@dp.bot_started()
async def on_start(event: BotStarted):
    await bot.send_message(
        chat_id=event.chat_id,
        text="👋 Привет! Я школьный помощник.\n\nВыберите действие:",
        attachments=[main_menu()]
    )


@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    await event.message.answer(
        "👋 Привет!\n\nВыберите действие:",
        attachments=[main_menu()]
    )


# ========== ЗАЯВКИ НА СПРАВКИ ==========
@dp.message_callback(F.callback.payload == "new_request")
async def new_request(event: MessageCallback):
    user_states[event.callback.user.user_id] = {"step": "select_building"}
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="📄 **Выберите здание:**",
        attachments=[building_menu()]
    )
    await event.answer()


@dp.message_callback(F.callback.payload == "building1_request")
async def building1_request(event: MessageCallback):
    user_id = event.callback.user.user_id
    user_states[user_id] = {"step": "fullname", "building": "building1"}
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="📝 Введите ФИО ученика:")
    await event.answer()


@dp.message_callback(F.callback.payload == "building2_request")
async def building2_request(event: MessageCallback):
    user_id = event.callback.user.user_id
    user_states[user_id] = {"step": "fullname", "building": "building2"}
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="📝 Введите ФИО ученика:")
    await event.answer()


@dp.message_callback(F.callback.payload == "my_requests")
async def my_requests(event: MessageCallback):
    user_id = event.callback.user.user_id
    requests = get_user_requests(user_id)

    # Фильтруем заявки за последние 5 дней
    five_days_ago = datetime.now().timestamp() - (5 * 24 * 60 * 60)
    recent_requests = []

    for r in requests:
        try:
            created_date = datetime.fromisoformat(r["created_at"]).timestamp()
            if created_date >= five_days_ago:
                recent_requests.append(r)
        except:
            recent_requests.append(r)

    recent_requests = recent_requests[-10:]

    if not recent_requests:
        text = "📭 У вас пока нет заявок за последние 5 дней"
    else:
        text = "📋 ═══════════════ ВАШИ ЗАЯВКИ (за последние 5 дней) ═══════════════\n\n"

        for r in reversed(recent_requests):
            building_name = BUILDING_NAMES.get(r.get("building", "building1"), "Справка")
            building_info = BUILDING_INFO.get(r.get("building", "building1"), BUILDING_INFO["building1"])
            status = r["status"]

            if status == "pending":
                status_emoji = "🟡"
                status_text = "⏳ Ожидает рассмотрения"
            elif status == "in_progress":
                status_emoji = "🔵"
                status_text = "📝 В обработке"
            elif status == "completed":
                status_emoji = "✅"
                status_text = "✅ ГОТОВО (можно забрать)"
            elif status == "cancelled":
                status_emoji = "❌"
                status_text = "❌ Отклонена"
            else:
                status_emoji = "⚪"
                status_text = status

            text += "╔" + "═" * 58 + "╗\n"
            text += f"║ {status_emoji} {building_name} (№{r['id']}) {status_emoji}\n"
            text += "╠" + "═" * 58 + "╣\n"
            text += f"║ 👤 ФИО ученика:   {r['fullname']}\n"
            text += f"║ 📚 Класс:         {r['class']}\n"
            text += f"║ 🎂 Дата рождения: {r.get('birth_date', 'не указана')}\n"
            text += f"║ 📌 Причина:       {r['reason']}\n"
            text += f"║ 📊 Статус:        {status_emoji} {status_text}\n"
            text += f"║ 🕒 Создана:       {r['created_at'][:16]}\n"

            if status == "completed":
                text += "║\n"
                text += "║ 📍 ИНФОРМАЦИЯ О ПОЛУЧЕНИИ:\n"
                text += f"║    Адрес:   {building_info['address']}\n"
                text += f"║    Кабинет: {building_info['cabinet']}, {building_info['floor']}\n"
                text += f"║    Часы:    {building_info['work_hours']}\n"
                text += f"║    Обед:    {building_info['lunch']}\n"
                text += f"║    Телефон: {building_info['phone']}\n"
                text += f"║    Email:   {building_info['email']}\n"
                text += "║\n"
                text += "║ 📄 При себе иметь:\n"
                text += "║    - Паспорт родителя/законного представителя\n"
                text += "║    - Свидетельство о рождении ученика\n"

            elif status == "cancelled":
                reason = r.get("reject_reason", "Не указана")
                text += "║\n"
                text += "║ ❌ ПРИЧИНА ОТКАЗА:\n"
                text += f"║    {reason}\n"
                text += "║\n"
                text += "║ 📞 КУДА ОБРАТИТЬСЯ:\n"
                text += f"║    Адрес:   {building_info['address']}\n"
                text += f"║    Телефон: {building_info['phone']}\n"
                text += f"║    Email:   {building_info['email']}\n"

            elif status == "in_progress":
                text += "║\n"
                text += "║ 🔄 Заявка в обработке. О готовности вы получите уведомление.\n"

            elif status == "pending":
                text += "║\n"
                text += "║ ⏳ Заявка ожидает рассмотрения администратором.\n"

            text += "╚" + "═" * 58 + "╝\n\n"

    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text, attachments=[main_menu()])
    await event.answer()


@dp.message_callback(F.callback.payload == "confirm_yes")
async def confirm_yes(event: MessageCallback):
    user_id = event.callback.user.user_id
    state = user_states.get(user_id, {})

    if state.get("step") != "waiting_confirm":
        await event.answer(notification="❌ Нет активной заявки")
        return

    request_id = save_request({
        "user_id": user_id,
        "building": state.get("building", "building1"),
        "fullname": state.get("fullname"),
        "class": state.get("class"),
        "birth_date": state.get("birth_date"),
        "reason": state.get("reason")
    })

    building_name = BUILDING_NAMES.get(state.get("building", "building1"), "Справка")

    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text=f"✅ **{building_name} #{request_id} принята!**\n\n"
             f"📊 **Текущий статус:** ⏳ {STATUS_TEXT['pending']}\n\n"
             f"📌 **Отслеживать статус заявки вы можете в разделе:**\n"
             f"   «📋 Мои заявки» в главном меню\n\n"
             f"🔄 Статус обновляется автоматически при его изменении администратором.\n\n"
             f"🙏 Спасибо за обращение! Ждем Вас в нашем канале https://max.ru/id7452019867_gos",
        attachments=[main_menu()]
    )

    chat_id = get_request_chat_id(state.get("building", "building1"))
    group_text = f"🆕 **НОВАЯ ЗАЯВКА**\n\n"
    group_text += f"🏫 {building_name}\n"
    group_text += f"📋 **№{request_id}**\n"
    group_text += f"👤 {state.get('fullname')}\n📚 {state.get('class')}\n"
    group_text += f"🎂 {state.get('birth_date')}\n📌 {state.get('reason')}\n"
    group_text += f"👨‍💻 Отправил: {event.callback.user.first_name}\n"
    group_text += f"🆔 ID пользователя: `{user_id}`\n"
    group_text += f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
    group_text += f"📌 **Порядок действий:**\n"
    group_text += f"1️⃣ Нажмите «Взять в работу»\n"
    group_text += f"2️⃣ Подготовьте справку\n"
    group_text += f"3️⃣ Нажмите «ГОТОВО»\n"
    group_text += f"4️⃣ Пользователь получит уведомление с адресом получения"

    try:
        await bot.send_message(chat_id=chat_id, text=group_text,
                               attachments=[get_status_buttons(request_id, "pending")])
        print(f"✅ Заявка #{request_id} отправлена")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

    user_states.pop(user_id, None)
    await event.answer(notification="✅ Заявка отправлена!")


@dp.message_callback(F.callback.payload == "confirm_no")
async def confirm_no(event: MessageCallback):
    user_id = event.callback.user.user_id
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="❌ Заявка отменена.",
                           attachments=[main_menu()])
    user_states.pop(user_id, None)
    await event.answer()


@dp.message_callback(F.callback.payload == "cancel")
async def cancel_handler(event: MessageCallback):
    user_id = event.callback.user.user_id
    user_states.pop(user_id, None)
    user_step.pop(user_id, None)
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="❌ Отменено", attachments=[main_menu()])
    await event.answer()


# ========== ОБРАЩЕНИЯ И ПРЕДЛОЖЕНИЯ ==========
@dp.message_callback(F.callback.payload == "new_feedback")
async def new_feedback(event: MessageCallback):
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="📝 **Выберите тип обращения:**",
        attachments=[feedback_type_menu()]
    )
    await event.answer()


@dp.message_callback(F.callback.payload == "complaint")
async def new_complaint(event: MessageCallback):
    user_step[event.callback.user.user_id] = "complaint"
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="⚠️ Напишите ваше обращение или жалобу:")
    await event.answer()


@dp.message_callback(F.callback.payload == "suggestion")
async def new_suggestion(event: MessageCallback):
    user_step[event.callback.user.user_id] = "suggestion"
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="💡 Напишите ваше предложение:")
    await event.answer()


@dp.message_callback(F.callback.payload == "my_feedback")
async def my_feedback(event: MessageCallback):
    user_id = event.callback.user.user_id
    feedbacks = get_user_feedback(user_id)

    if not feedbacks:
        text = "📭 У вас пока нет обращений"
    else:
        text = "✉️ ═══════════════ ВАШИ ОБРАЩЕНИЯ ═══════════════\n\n"

        for f in reversed(feedbacks[-5:]):
            type_name = "Обращение" if f["type"] == "complaint" else "Предложение"
            type_emoji = "⚠️" if f["type"] == "complaint" else "💡"
            status = FEEDBACK_STATUS_TEXT.get(f["status"], "🟡 Ожидает")

            if f["status"] == "pending":
                status_emoji = "🟡"
            elif f["status"] == "in_progress":
                status_emoji = "🔵"
            elif f["status"] == "completed":
                status_emoji = "✅"
            else:
                status_emoji = "⚪"

            text += "╔" + "═" * 58 + "╗\n"
            text += f"║ {type_emoji} {type_name} #{f['id']} {status_emoji}\n"
            text += "╠" + "═" * 58 + "╣\n"

            # Разбиваем длинный текст на строки
            message_text = f['message']
            text += "║ 📝 Текст обращения:\n"
            for i in range(0, len(message_text), 52):
                line = message_text[i:i + 52]
                text += f"║    {line}\n"

            text += f"║\n"
            text += f"║ 📊 Статус: {status_emoji} {status}\n"
            text += f"║ 🕒 Создано: {f['created_at'][:16]}\n"

            if f["status"] == "completed":
                text += "║\n"
                text += "║ ✅ Администратор ответил на ваше обращение.\n"
                text += "║    Ответ отправлен в личные сообщения.\n"
            elif f["status"] == "in_progress":
                text += "║\n"
                text += "║ 🔄 Ваше обращение взято в работу.\n"
                text += "║    Администратор готовит ответ.\n"
            elif f["status"] == "pending":
                text += "║\n"
                text += "║ ⏳ Обращение ожидает рассмотрения.\n"

            text += "╚" + "═" * 58 + "╝\n\n"

    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text, attachments=[main_menu()])
    await event.answer()


# ========== ОСНОВНОЙ ОБРАБОТЧИК ТЕКСТА ==========
@dp.message_created()
async def handle_text(event: MessageCreated):
    user_id = event.message.sender.user_id
    text = event.message.body.text if event.message.body else None

    if not text or text.startswith('/'):
        return

    state = user_states.get(user_id, {})
    step = state.get("step")

    if step == "fullname":
        user_states[user_id] = {"step": "class", "fullname": text, "building": state.get("building")}
        await event.message.answer("📚 Введите класс (например, 9.5):")
        return
    elif step == "class":
        user_states[user_id] = {"step": "birth_date", "fullname": state["fullname"], "class": text,
                                "building": state.get("building")}
        await event.message.answer("🎂 Введите дату рождения (ДД.ММ.ГГГГ):")
        return
    elif step == "birth_date":
        if not validate_birth_date(text):
            await event.message.answer("❌ Неверный формат! Используйте ДД.ММ.ГГГГ")
            return
        user_states[user_id] = {"step": "reason", "fullname": state["fullname"], "class": state["class"],
                                "birth_date": text, "building": state.get("building")}
        await event.message.answer("📌 Укажите причину получения справки:")
        return
    elif step == "reason":
        user_states[user_id] = {
            "step": "waiting_confirm",
            "building": state.get("building"),
            "fullname": state["fullname"],
            "class": state["class"],
            "birth_date": state["birth_date"],
            "reason": text
        }
        building_name = BUILDING_NAMES.get(state.get("building"), "Справка")
        msg = f"📝 **ПРОВЕРЬТЕ ДАННЫЕ:**\n\n🏫 {building_name}\n👤 {state['fullname']}\n📚 {state['class']}\n🎂 {state['birth_date']}\n📌 {text}\n\n✅ Всё правильно?"
        await event.message.answer(msg, attachments=[get_confirm_buttons()])
        return
    elif step == "waiting_confirm":
        await event.message.answer("⏳ Подтвердите или отмените заявку кнопками.")
        return

    # Проверяем обращения
    if user_id in user_step:
        fb_type = user_step[user_id]
        type_name = "Обращение" if fb_type == "complaint" else "Предложение"
        type_emoji = "⚠️" if fb_type == "complaint" else "💡"
        fullname = event.message.sender.first_name or str(user_id)

        feedback_id = save_feedback({
            "user_id": user_id, "fullname": fullname, "message": text, "type": fb_type
        })

        chat_id = get_feedback_chat_id(fb_type)
        admin_text = f"{type_emoji} **НОВОЕ {type_name.upper()}**\n\n"
        admin_text += f"📋 **№{feedback_id}**\n"
        admin_text += f"👤 {fullname}\n"
        admin_text += f"🆔 ID пользователя: `{user_id}`\n"
        admin_text += f"📝 {text}\n"
        admin_text += f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        admin_text += f"📌 **Порядок действий:**\n"
        admin_text += f"1️⃣ Нажмите «Взять в работу»\n"
        admin_text += f"2️⃣ Ответьте пользователю в ЛС (используя его ID)\n"
        admin_text += f"3️⃣ Нажмите «Отметить как отвеченное»"

        try:
            btn_take = CallbackButton(text="🔵 Взять в работу", payload=f"take_fb_{feedback_id}", intent=Intent.POSITIVE)
            await bot.send_message(chat_id=chat_id, text=admin_text, attachments=[
                Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=[[btn_take]]))])
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")

        await event.message.answer(
            f"✅ **{type_name} #{feedback_id} отправлено!**\n\n"
            f"Администратор рассмотрит ваше обращение и ответит вам в личные сообщения.\n\n"
             f"📌 **Отслеживать статус обращения вы можете в разделе:**\n"
             f"   «📋 Мои обращения» в главном меню\n\n"
             f"🔄 Статус обновляется автоматически при его изменении администратором.\n\n"
            f"🙏 Спасибо за обращение! Ждем Вас в нашем канале https://max.ru/id7452019867_gos"
        )
        user_step.pop(user_id, None)
        return

    await cmd_start(event)


# ========== ОБРАБОТЧИКИ ДЛЯ ЗАЯВОК (ГРУППЫ) ==========
@dp.message_callback(F.callback.payload.startswith("status_"))
async def change_status(event: MessageCallback):
    try:
        payload = event.callback.payload
        parts = payload.split("_")

        if len(parts) >= 4 and parts[1] == "in" and parts[2] == "progress":
            new_status = "in_progress"
            request_id = int(parts[3])
        elif len(parts) >= 3 and parts[1] == "completed":
            new_status = "completed"
            request_id = int(parts[2])
        else:
            return

        request = get_request_by_id(request_id)
        if not request:
            await event.answer(notification="❌ Заявка не найдена", show_alert=True)
            return

        update_request_status(request_id, new_status, event.callback.user.first_name)
        status_emoji = STATUS_EMOJI.get(new_status, "⚪")
        status_text = STATUS_TEXT.get(new_status, new_status)
        building_name = BUILDING_NAMES.get(request.get("building", "building1"), "Справка")
        building_info = BUILDING_INFO.get(request.get("building", "building1"), BUILDING_INFO["building1"])

        text = f"📋 **Заявка #{request_id}**\n\n"
        text += f"🏫 {building_name}\n"
        text += f"👤 {request['fullname']}\n📚 {request['class']}\n"
        text += f"📌 {request['reason']}\n\n"
        text += f"📊 **Статус:** {status_emoji} {status_text}"

        if new_status == "in_progress":
            text += "\n\n👇 Действия:"
            await bot.send_message(chat_id=event.message.recipient.chat_id, text=text,
                                   attachments=[get_status_buttons(request_id, "in_progress")])

            try:
                user_text = f"🔵 **Ваша заявка #{request_id} взята в работу!**\n\n"
                user_text += f"🏫 {building_name}\n👤 {request['fullname']}\n"
                user_text += f"👨‍💻 Администратор: {event.callback.user.first_name}\n\n"
                user_text += f"📊 Статус: 📝 В обработке\n\n📌 Вы можете отслеживать статус в разделе «📋 Мои заявки»"
                await bot.send_message(chat_id=request["user_id"], text=user_text)
            except Exception as e:
                print(f"⚠️ Не удалось отправить уведомление: {e}")

        elif new_status == "completed":
            await bot.send_message(chat_id=event.message.recipient.chat_id, text=text)

            try:
                user_text = f"✅ **Ваша заявка #{request_id} готова!**\n\n"
                user_text += f"🏫 {building_name}\n👤 {request['fullname']}\n📚 {request['class']}\n\n"
                user_text += f"📍 **Где забрать справку:**\n"
                user_text += f"   • {building_info['address']}\n"
                user_text += f"   • {building_info['cabinet']}, {building_info['floor']}\n\n"
                user_text += f"🕒 Часы: {building_info['work_hours']}\n"
                user_text += f"📞 Телефон: {building_info['phone']}\n"
                user_text += f"✉️ Email: {building_info['email']}\n\n"
                user_text += f"📄 При себе иметь: паспорт родителя и свидетельство о рождении"
                await bot.send_message(chat_id=request["user_id"], text=user_text)
            except Exception as e:
                print(f"⚠️ Не удалось отправить уведомление: {e}")

        await event.answer(notification=f"✅ Статус изменён: {status_text}")

    except Exception as e:
        print(f"❌ Ошибка в change_status: {e}")


@dp.message_callback(F.callback.payload.startswith("reject_request_"))
async def reject_request(event: MessageCallback):
    try:
        request_id = int(event.callback.payload.split("_")[2])
        user_states[event.callback.user.user_id] = {"reject_request_id": request_id}
        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=f"❌ **Отклонение заявки #{request_id}**\n\nВыберите причину:",
            attachments=[get_reject_reasons_buttons(request_id)]
        )
        await event.answer()
    except Exception as e:
        print(f"❌ Ошибка: {e}")


@dp.message_callback(F.callback.payload.startswith("reject_"))
async def execute_reject(event: MessageCallback):
    try:
        parts = event.callback.payload.split("_")
        request_id = int(parts[1])
        reason_code = parts[2]

        reasons = {"wrong_data": "Данные некорректно введены", "no_basis": "Нет оснований"}
        reason_text = reasons.get(reason_code, "Не указана")
        request = get_request_by_id(request_id)

        if request:
            building_name = BUILDING_NAMES.get(request.get("building", "building1"), "Справка")
            building_info = BUILDING_INFO.get(request.get("building", "building1"), BUILDING_INFO["building1"])

            update_request_status(request_id, "cancelled", event.callback.user.first_name, reason_text)

            text = f"❌ **Заявка #{request_id} отклонена**\n\n🏫 {building_name}\n👤 {request['fullname']}\n📌 Причина: {reason_text}"
            await bot.send_message(chat_id=event.message.recipient.chat_id, text=text)

            try:
                user_text = f"❌ **Ваша заявка #{request_id} отклонена!**\n\n"
                user_text += f"🏫 {building_name}\n👤 {request['fullname']}\n\n"
                user_text += f"📌 Причина: {reason_text}\n\n"
                user_text += f"📞 Для уточнения: {building_info['address']}, тел. {building_info['phone']}"
                await bot.send_message(chat_id=request["user_id"], text=user_text)
            except Exception as e:
                print(f"⚠️ Не удалось отправить уведомление: {e}")

            await event.answer(notification=f"❌ Заявка #{request_id} отклонена")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


@dp.message_callback(F.callback.payload == "back_to_request")
async def back_to_request(event: MessageCallback):
    try:
        user_state = user_states.get(event.callback.user.user_id, {})
        request_id = user_state.get("reject_request_id")
        if request_id:
            request = get_request_by_id(request_id)
            if request:
                building_name = BUILDING_NAMES.get(request.get("building", "building1"), "Справка")
                await bot.send_message(
                    chat_id=event.message.recipient.chat_id,
                    text=f"📋 **Заявка #{request_id}**\n🏫 {building_name}",
                    attachments=[get_status_buttons(request_id, request["status"])]
                )
        await event.answer()
    except Exception as e:
        print(f"❌ Ошибка: {e}")


@dp.message_callback(F.callback.payload == "all_requests")
async def show_all_requests(event: MessageCallback):
    requests = get_all_requests()
    active = [r for r in requests if r.get("status") in ["pending", "in_progress"]]

    if not active:
        await bot.send_message(chat_id=event.message.recipient.chat_id, text="📭 Нет активных заявок")
        await event.answer()
        return

    text = "📋 **Активные заявки:**\n\n"
    for req in reversed(active[-10:]):
        building_name = BUILDING_NAMES.get(req.get("building", "building1"), "Справка")
        status_emoji = STATUS_EMOJI.get(req["status"], "⚪")
        text += f"{status_emoji} **{building_name} #{req['id']}** | {req['fullname']}\n"
        text += f"   📚 {req['class']} | 📊 {STATUS_TEXT.get(req['status'], req['status'])}\n\n"

    refresh = CallbackButton(text="🔄 Обновить", payload="all_requests", intent=Intent.DEFAULT)
    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text, attachments=[
        Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=[[refresh]]))])
    await event.answer()


# ========== ОБРАБОТЧИКИ ДЛЯ ОБРАЩЕНИЙ (ГРУППЫ) ==========
@dp.message_callback(F.callback.payload.startswith("take_fb_"))
async def take_feedback(event: MessageCallback):
    try:
        feedback_id = int(event.callback.payload.split("_")[2])
        feedback = get_feedback_by_id(feedback_id)
        if not feedback:
            await event.answer(notification="❌ Обращение не найдено", show_alert=True)
            return

        update_feedback_status(feedback_id, "in_progress", event.callback.user.first_name)

        btn_done = CallbackButton(text="✅ Отметить как отвеченное", payload=f"done_fb_{feedback_id}",
                                  intent=Intent.POSITIVE)

        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=f"🔵 **Обращение #{feedback_id} (В РАБОТЕ)**\n\n"
                 f"👤 {feedback['fullname']}\n🆔 ID: `{feedback['user_id']}`\n"
                 f"📝 {feedback['message']}\n\n👨‍💻 Взял: {event.callback.user.first_name}\n\n"
                 f"📌 **После ответа пользователю в ЛС, нажмите кнопку:**",
            attachments=[Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=[[btn_done]]))]
        )
        await event.answer(notification="✅ Обращение взято в работу")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


@dp.message_callback(F.callback.payload.startswith("done_fb_"))
async def done_feedback(event: MessageCallback):
    try:
        feedback_id = int(event.callback.payload.split("_")[2])
        feedback = get_feedback_by_id(feedback_id)
        if not feedback:
            await event.answer(notification="❌ Обращение не найдено", show_alert=True)
            return

        update_feedback_status(feedback_id, "completed", event.callback.user.first_name)

        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=f"✅ **Обращение #{feedback_id} (ОТВЕЧЕНО)**\n\n"
                 f"👤 {feedback['fullname']}\n✅ Отвечено: {event.callback.user.first_name}"
        )
        await event.answer(notification="✅ Обращение отмечено как отвеченное")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


@dp.message_callback(F.callback.payload == "admin_active_feedback")
async def admin_active_feedback(event: MessageCallback):
    feedbacks = get_unanswered_feedback()

    if not feedbacks:
        await bot.send_message(chat_id=event.message.recipient.chat_id, text="📭 Нет активных обращений")
        await event.answer()
        return

    text = "🆕 **Активные обращения:**\n\n"
    for fb in reversed(feedbacks):
        type_name = "Обращение" if fb["type"] == "complaint" else "Предложение"
        type_emoji = "⚠️" if fb["type"] == "complaint" else "💡"
        status = FEEDBACK_STATUS_TEXT.get(fb["status"], "🟡 Ожидает")
        text += f"{type_emoji} **{type_name} #{fb['id']}**\n👤 {fb['fullname']}\n🆔 `{fb['user_id']}`\n📊 {status}\n\n"

    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text,
                           attachments=[get_feedback_list_buttons()])
    await event.answer()


@dp.message_callback(F.callback.payload == "admin_all_feedback")
async def admin_all_feedback(event: MessageCallback):
    feedbacks = get_all_feedback()

    if not feedbacks:
        await bot.send_message(chat_id=event.message.recipient.chat_id, text="📭 Нет обращений")
        await event.answer()
        return

    text = "📋 **История обращений:**\n\n"
    for fb in reversed(feedbacks[-20:]):
        type_name = "Обращение" if fb["type"] == "complaint" else "Предложение"
        type_emoji = "⚠️" if fb["type"] == "complaint" else "💡"
        status = FEEDBACK_STATUS_TEXT.get(fb["status"], "🟡 Ожидает")
        text += f"{type_emoji} **{type_name} #{fb['id']}**\n👤 {fb['fullname']}\n🆔 `{fb['user_id']}`\n"
        text += f"📊 {status}\n🕒 {fb['created_at'][:16]}\n\n"

    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text)
    await event.answer()


print("✅ handlers.py загружен")