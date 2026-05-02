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
temp_feedback = {}


# ========== ФУНКЦИИ ПРОВЕРКИ ДЛЯ ЗАЯВОК ==========
def validate_fullname(fullname: str) -> tuple:
    """Проверяет ФИО пользователя для заявки на справку"""
    fullname = ' '.join(fullname.split())
    if not fullname:
        return False, "❌ ФИО не может быть пустым", None
    parts = fullname.split()
    if len(parts) < 2:
        return False, "❌ Введите **Фамилию и Имя** (минимум 2 слова)\n\nПример: Иванов Иван Иванович", None
    if len(parts) > 4:
        return False, "❌ Слишком много слов. Введите: Фамилия Имя Отчество (не более 4 слов)", None
    for i, part in enumerate(parts):
        if part and not part[0].isupper():
            parts[i] = part.capitalize()
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-]+$', fullname):
        return False, "❌ ФИО должно содержать только буквы, пробелы и дефис\n\nПример: Иванов Иван Иванович", None
    for part in parts:
        if len(part) < 2:
            return False, f"❌ Слово '{part}' слишком короткое. Проверьте правильность ввода", None
        if len(part) > 30:
            return False, f"❌ Слово '{part[:15]}...' слишком длинное", None
    formatted = ' '.join(parts)
    return True, None, formatted


def validate_class_number(class_str: str) -> tuple:
    """Проверяет класс (только цифровой, с точкой)"""
    class_str = class_str.strip()
    pattern = r'^\d{1,2}\.\d{1}$'
    if not re.match(pattern, class_str):
        return False, "❌ Неверный формат класса\n\nИспользуйте формат: **номер.подгруппа**\nПримеры: 9.1, 10.2, 11.5", None
    try:
        main_class = int(class_str.split('.')[0])
        subgroup = int(class_str.split('.')[1])
        if main_class < 1 or main_class > 11:
            return False, f"❌ Номер класса должен быть от 1 до 11 (вы ввели {main_class})", None
        if subgroup < 1 or subgroup > 5:
            return False, f"❌ Номер подгруппы должен быть от 1 до 5 (вы ввели {subgroup})", None
        return True, None, class_str
    except (ValueError, IndexError):
        return False, "❌ Неверный формат класса\n\nИспользуйте формат: **9.1** или **10.2**", None


def validate_birth_date(date_str: str) -> bool:
    """Проверяет дату рождения"""
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    if not re.match(pattern, date_str):
        return False
    try:
        day, month, year = map(int, date_str.split('.'))
        birth_date = datetime(year, month, day)
        return birth_date <= datetime.now()
    except ValueError:
        return False


def validate_phone(phone: str) -> bool:
    """Простая валидация номера телефона"""
    digits = re.sub(r'\D', '', phone)
    return len(digits) in [10, 11]


def format_phone(phone: str) -> str:
    """Форматирует номер телефона для красивого вывода"""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11:
        return f"+{digits[0]} {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"
    elif len(digits) == 10:
        return f"+7 {digits[0:3]} {digits[3:6]} {digits[6:8]} {digits[8:10]}"
    return phone


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
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="📝 Введите **Фамилию, Имя и Отчество** ученика\n\nПример: Иванов Иван Иванович"
    )
    await event.answer()


@dp.message_callback(F.callback.payload == "building2_request")
async def building2_request(event: MessageCallback):
    user_id = event.callback.user.user_id
    user_states[user_id] = {"step": "fullname", "building": "building2"}
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="📝 Введите **Фамилию, Имя и Отчество** ученика\n\nПример: Иванов Иван Иванович"
    )
    await event.answer()


@dp.message_callback(F.callback.payload == "my_requests")
async def my_requests(event: MessageCallback):
    user_id = event.callback.user.user_id
    requests = get_user_requests(user_id)
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
             f"🙏 Спасибо за обращение!",
        attachments=[main_menu()]
    )
    chat_id = get_request_chat_id(state.get("building", "building1"))
    group_text = f"🆕 **НОВАЯ ЗАЯВКА**\n\n"
    group_text += f"🏫 {building_name}\n"
    group_text += f"📋 **№{request_id}**\n"
    group_text += f"👤 {state.get('fullname')}\n📚 {state.get('class')}\n"
    group_text += f"🎂 {state.get('birth_date')}\n📌 {state.get('reason')}\n"
    group_text += f"👨‍💻 Отправил: {event.callback.user.first_name}\n"
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
    if user_id in temp_feedback:
        del temp_feedback[user_id]
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
    user_id = event.callback.user.user_id
    temp_feedback[user_id] = {"type": "complaint", "step": "fullname"}
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="👤 **Представьтесь, пожалуйста:**\n\n"
             "Введите ваши ФИО полностью.\n"
             "Например: `Иванов Иван Иванович`\n\n"
             "📌 Это нужно, чтобы администратор знал, к кому обращаться."
    )
    await event.answer()


@dp.message_callback(F.callback.payload == "suggestion")
async def new_suggestion(event: MessageCallback):
    user_id = event.callback.user.user_id
    temp_feedback[user_id] = {"type": "suggestion", "step": "fullname"}
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="👤 **Представьтесь, пожалуйста:**\n\n"
             "Введите ваши ФИО полностью.\n"
             "Например: `Иванов Иван Иванович`\n\n"
             "📌 Это нужно, чтобы администратор знал, к кому обращаться."
    )
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
            text += f"║ 👤 Отправитель: {f['fullname']}\n"
            text += f"║ 📞 Телефон: {f.get('phone', 'не указан')}\n"
            text += "║\n"
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

    # ========== ОБРАБОТКА ОБРАЩЕНИЙ ==========
    if user_id in temp_feedback:
        step = temp_feedback[user_id].get("step")

        if step == "fullname":
            fullname = text.strip()
            if len(fullname.split()) < 2:
                await event.message.answer(
                    "❌ **Пожалуйста, введите полные ФИО!**\n\n"
                    "Введите ваши Фамилию, Имя и Отчество полностью.\n"
                    "Например: `Иванов Иван Иванович`"
                )
                return
            temp_feedback[user_id]["fullname"] = fullname
            temp_feedback[user_id]["step"] = "phone"
            first_name = fullname.split()[1] if len(fullname.split()) > 1 else fullname.split()[0]
            await event.message.answer(
                f"✅ **Спасибо, {first_name}!**\n\n"
                f"📞 Теперь укажите ваш номер телефона для связи:\n\n"
                f"Введите номер в любом формате:\n"
                f"• `+7 999 123 45 67`\n"
                f"• `89991234567`\n"
                f"• `9991234567`"
            )
            return

        elif step == "phone":
            phone_raw = text.strip()
            if not validate_phone(phone_raw):
                await event.message.answer(
                    "❌ **Неверный формат номера телефона!**\n\n"
                    "Пожалуйста, введите номер в одном из форматов:\n"
                    "• `+7 999 123 45 67`\n"
                    "• `89991234567`\n"
                    "• `9991234567`\n\n"
                    "Попробуйте ещё раз:"
                )
                return
            formatted_phone = format_phone(phone_raw)
            temp_feedback[user_id]["phone"] = formatted_phone
            temp_feedback[user_id]["phone_raw"] = re.sub(r'\D', '', phone_raw)
            temp_feedback[user_id]["step"] = "message"
            await event.message.answer(
                f"✅ **Номер телефона сохранён:** `{formatted_phone}`\n\n"
                f"📝 **Теперь напишите текст вашего обращения:**\n\n"
                f"✏️ Опишите вашу проблему или предложение как можно подробнее."
            )
            return

        elif step == "message":
            fb_type = temp_feedback[user_id]["type"]
            user_fullname = temp_feedback[user_id]["fullname"]
            phone = temp_feedback[user_id]["phone"]
            phone_raw = temp_feedback[user_id].get("phone_raw", "")

            # ПОЛУЧАЕМ ИМЯ ПОЛЬЗОВАТЕЛЯ ИЗ MAX
            user_name = event.message.sender.first_name
            if not user_name:
                user_name = event.message.sender.username or f"Пользователь"

            feedback_id = save_feedback({
                "user_id": user_id,
                "user_name": user_name,  # СОХРАНЯЕМ ИМЯ
                "fullname": user_fullname,
                "phone": phone,
                "phone_raw": phone_raw,
                "message": text,
                "type": fb_type
            })

            chat_id = get_feedback_chat_id(fb_type)
            type_name = "ОБРАЩЕНИЕ" if fb_type == "complaint" else "ПРЕДЛОЖЕНИЕ"
            type_emoji = "⚠️" if fb_type == "complaint" else "💡"

            # НОВЫЙ ТЕКСТ БЕЗ ID, С ИМЕНЕМ ПОЛЬЗОВАТЕЛЯ
            admin_text = f"{type_emoji}  **НОВОЕ {type_name}**\n\n"
            admin_text += f"📋 **№{feedback_id}**\n"
            admin_text += f"👤  **Имя в MAX:** {user_name}\n"
            admin_text += f"👤  **Отправитель:** {user_fullname}\n"
            admin_text += f"📞  **Телефон:** `{phone}`\n"
            admin_text += f"📝  **Текст:**\n{text}\n"
            admin_text += f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            admin_text += f"📌  **Порядок действий:**\n"
            admin_text += f"1️⃣  Нажмите «Взять в работу»"

            try:
                btn_take = CallbackButton(text="🔵 Взять в работу", payload=f"take_fb_{feedback_id}",
                                          intent=Intent.POSITIVE)
                await bot.send_message(
                    chat_id=chat_id,
                    text=admin_text,
                    attachments=[Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=[[btn_take]]))]
                )
                print(f"✅ Обращение #{feedback_id} отправлено в чат {chat_id}")
            except Exception as e:
                print(f"❌ Ошибка отправки: {e}")

            first_name = user_fullname.split()[1] if len(user_fullname.split()) > 1 else user_fullname.split()[0]
            await event.message.answer(
                f"✅ **{type_name} #{feedback_id} отправлено!**\n\n"
                f"👤 **{first_name}**, ваше обращение принято.\n"
                f"📞 Администратор свяжется с вами в MAX.\n\n"
                f"📌 **Что дальше?**\n"
                f"   • Вы можете отслеживать статус в разделе «✉️ Мои обращения»\n\n"
                f"🙏 Спасибо за обращение!"
            )
            del temp_feedback[user_id]
            return

    # ========== ЗАЯВКИ НА СПРАВКИ ==========
    state = user_states.get(user_id, {})
    step = state.get("step")

    if step == "fullname":
        is_valid, error, formatted = validate_fullname(text)
        if not is_valid:
            await event.message.answer(
                f"{error}\n\n"
                f"📝 **Пожалуйста, введите ФИО правильно:**\n"
                f"• Формат: Фамилия Имя Отчество\n"
                f"• Пример: Иванов Иван Иванович\n\n"
                f"Попробуйте ещё раз:"
            )
            return
        user_states[user_id] = {
            "step": "class",
            "fullname": formatted,
            "building": state.get("building")
        }
        await event.message.answer(
            f"✅ **ФИО принято:** `{formatted}`\n\n"
            f"📚 Введите **класс** в формате **9.1** (номер.подгруппа):\n\n"
            f"Примеры: 9.1, 10.2, 11.5"
        )
        return

    elif step == "class":
        is_valid, error, formatted = validate_class_number(text)
        if not is_valid:
            await event.message.answer(
                f"{error}\n\n"
                f"📚 **Пожалуйста, введите класс в правильном формате:**\n"
                f"• Формат: **номер.подгруппа**\n"
                f"• Примеры: 9.1, 10.2, 11.5\n\n"
                f"Попробуйте ещё раз:"
            )
            return
        user_states[user_id] = {
            "step": "birth_date",
            "fullname": state["fullname"],
            "class": formatted,
            "building": state.get("building")
        }
        await event.message.answer(
            f"✅ **Класс принят:** `{formatted}`\n\n"
            f"🎂 Введите **дату рождения** в формате ДД.ММ.ГГГГ\n\n"
            f"Пример: 15.05.2010"
        )
        return

    elif step == "birth_date":
        if not validate_birth_date(text):
            await event.message.answer(
                "❌ **Неверный формат даты!**\n\n"
                "Используйте формат: ДД.ММ.ГГГГ\n"
                "Пример: 15.05.2010"
            )
            return
        user_states[user_id] = {
            "step": "reason",
            "fullname": state["fullname"],
            "class": state["class"],
            "birth_date": text,
            "building": state.get("building")
        }
        await event.message.answer(
            f"✅ **Дата рождения принята:** `{text}`\n\n"
            f"📌 **Укажите причину получения справки:**\n\n"
        )
        return

    elif step == "reason":
        if len(text.strip()) < 5:
            await event.message.answer(
                "❌ **Причина слишком короткая!**\n\n"
                "Пожалуйста, опишите причину подробнее (минимум 5 символов)."
            )
            return
        user_states[user_id] = {
            "step": "waiting_confirm",
            "building": state.get("building"),
            "fullname": state["fullname"],
            "class": state["class"],
            "birth_date": state["birth_date"],
            "reason": text.strip()
        }
        building_name = BUILDING_NAMES.get(state.get("building"), "Справка")
        msg = f"📝 **ПРОВЕРЬТЕ ДАННЫЕ ЗАЯВКИ:**\n\n"
        msg += f"🏫 **Здание:** {building_name}\n"
        msg += f"👤 **ФИО:** {state['fullname']}\n"
        msg += f"📚 **Класс:** {state['class']}\n"
        msg += f"🎂 **Дата рождения:** {state['birth_date']}\n"
        msg += f"📌 **Причина:**\n{text.strip()}\n\n"
        msg += f"✅ **Всё правильно?**"
        await event.message.answer(msg, attachments=[get_confirm_buttons()])
        return

    elif step == "waiting_confirm":
        await event.message.answer("⏳ Подтвердите или отмените заявку кнопками.")
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
        parts = event.callback.payload.split("_")
        feedback_id = int(parts[2])
        print(f"🔍 Обработка take_feedback для обращения #{feedback_id}")
        feedback = get_feedback_by_id(feedback_id)
        if not feedback:
            await event.answer(notification="❌ Обращение не найдено", show_alert=True)
            return
        print(f"✅ Обращение найдено: {feedback['fullname']}, user_id={feedback['user_id']}")
        update_feedback_status(feedback_id, "in_progress", event.callback.user.first_name)
        user_notified = False
        try:
            btn_ready = CallbackButton(
                text="📨 Получить ответ администратора",
                payload=f"user_ready_for_answer_{feedback_id}",
                intent=Intent.POSITIVE
            )
            user_payload = ButtonsPayload(buttons=[[btn_ready]])
            user_attachment = Attachment(type="inline_keyboard", payload=user_payload)
            first_name = feedback['fullname'].split()[1] if len(feedback['fullname'].split()) > 1 else \
            feedback['fullname'].split()[0]
            await bot.send_message(
                chat_id=feedback["user_id"],
                text=f"🔵 **{first_name}, ваше обращение #{feedback_id} взято в работу!**\n\n"
                     f"👨‍💻 Администратор: {event.callback.user.first_name}\n\n"
                     f"📌 **Когда будете готовы получить ответ, нажмите кнопку ниже:**",
                attachments=[user_attachment]
            )
            user_notified = True
            print(f"✅ Уведомление с кнопкой отправлено пользователю {feedback['user_id']}")
        except Exception as e:
            error_msg = str(e)
            if "chat.not.found" in error_msg:
                print(f"⚠️ Пользователь {feedback['user_id']} еще не писал боту")
            else:
                print(f"❌ Ошибка: {e}")
        btn_copy_phone = CallbackButton(
            text=f"📋 Скопировать телефон: {feedback.get('phone', 'не указан')}",
            payload=f"copy_phone_{feedback_id}",
            intent=Intent.DEFAULT
        )
        btn_done = CallbackButton(
            text="✅ Отметить как отвеченное",
            payload=f"done_fb_{feedback_id}",
            intent=Intent.POSITIVE
        )
        admin_text = f"🔵 **Обращение #{feedback_id} (В РАБОТЕ)**\n\n"
        admin_text += f"👤 {feedback['fullname']}\n"
        admin_text += f"📞 Телефон: `{feedback.get('phone', 'не указан')}`\n"
        admin_text += f"📝 {feedback['message']}\n\n"
        admin_text += f"👨‍💻 Взял: {event.callback.user.first_name}\n\n"
        if user_notified:
            admin_text += f"✅ Пользователю отправлена кнопка «Получить ответ»\n"
        else:
            admin_text += f"⚠️ **Пользователь ещё не писал боту!**\n\n"
            admin_text += f"📌 **Что делать:**\n"
            admin_text += f"   1️⃣ Нажмите кнопку ниже, чтобы скопировать телефон пользователя\n"
            admin_text += f"   2️⃣ Свяжитесь с пользователем по телефону\n\n"
        admin_text += f"✅ **После ответа пользователю нажмите кнопку:**"
        admin_buttons = [[btn_copy_phone], [btn_done]]
        admin_attachment = Attachment(type="inline_keyboard", payload=ButtonsPayload(buttons=admin_buttons))
        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=admin_text,
            attachments=[admin_attachment]
        )
        await event.answer(notification="✅ Обращение взято в работу")
    except Exception as e:
        print(f"❌ Ошибка в take_feedback: {e}")
        await event.answer(notification=f"❌ Ошибка: {e}", show_alert=True)


@dp.message_callback(F.callback.payload.startswith("copy_phone_"))
async def copy_phone_number(event: MessageCallback):
    try:
        feedback_id = int(event.callback.payload.split("_")[2])
        feedback = get_feedback_by_id(feedback_id)
        if not feedback:
            await event.answer(notification="❌ Обращение не найдено", show_alert=True)
            return
        phone = feedback.get('phone', 'не указан')
        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=f"📋 **Телефон пользователя для копирования:**\n\n"
                 f"`{phone}`\n\n"
                 f"👤 {feedback['fullname']}\n"
                 f"📋 Обращение #{feedback_id}\n\n"
                 f"💡 Вы можете связаться с пользователем по этому номеру."
        )
        await event.answer()
    except Exception as e:
        print(f"❌ Ошибка в copy_phone_number: {e}")
        await event.answer(notification=f"❌ Ошибка: {e}", show_alert=True)


@dp.message_callback(F.callback.payload.startswith("user_ready_for_answer_"))
async def user_ready_for_answer(event: MessageCallback):
    try:
        feedback_id = int(event.callback.payload.split("_")[3])
        feedback = get_feedback_by_id(feedback_id)
        if not feedback:
            await event.answer(notification="❌ Обращение не найдено", show_alert=True)
            return
        chat_id = get_feedback_chat_id(feedback["type"])
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ **Пользователь готов получить ответ!**\n\n"
                 f"📋 Обращение #{feedback_id}\n"
                 f"👤 {feedback['fullname']}\n"
                 f"📞 Телефон: `{feedback.get('phone', 'не указан')}`\n\n"
                 f"📌 **Теперь вы можете ответить ему в ЛС** — диалог открыт.\n"
                 f"   Просто напишите сообщение в этот диалог с ботом."
        )
        await event.message.answer(
            text="✅ **Ожидайте ответа администратора!**\n\n"
                 "Администратор скоро ответит вам в этот чат."
        )
        await event.answer()
    except Exception as e:
        print(f"❌ Ошибка в user_ready_for_answer: {e}")


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
                 f"👤 {feedback['fullname']}\n"
                 f"✅ Отвечено: {event.callback.user.first_name}\n"
                 f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        try:
            await bot.send_message(
                chat_id=feedback["user_id"],
                text=f"✅ **Ваше обращение #{feedback_id} отмечено как отвеченное!**\n\n"
                     f"Спасибо, что обратились к нам!"
            )
        except:
            pass
        await event.answer(notification="✅ Обращение отмечено как отвеченное")
    except Exception as e:
        print(f"❌ Ошибка в done_feedback: {e}")


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
        text += f"{type_emoji} **{type_name} #{fb['id']}**\n"
        text += f"👤 {fb['fullname']}\n"
        text += f"📞 {fb.get('phone', 'телефон не указан')}\n"
        text += f"📊 {status}\n\n"
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
        text += f"{type_emoji} **{type_name} #{fb['id']}**\n"
        text += f"👤 {fb['fullname']}\n"
        text += f"📞 {fb.get('phone', 'телефон не указан')}\n"
        text += f"📊 {status}\n🕒 {fb['created_at'][:16]}\n\n"
    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text)
    await event.answer()


print("✅ handlers.py загружен")