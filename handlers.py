import logging
from maxapi import Bot, Dispatcher, F
from maxapi.types import MessageCreated, BotStarted, MessageCallback, Command
from maxapi.types import CallbackButton, ButtonsPayload, Attachment
from maxapi.enums.intent import Intent

from config import BOT_TOKEN, REQUESTS_CHAT_ID, FEEDBACK_CHAT_ID
from keyboards import main_menu, feedback_menu, get_status_buttons, STATUS_TEXT, STATUS_EMOJI
from storage import save_request, get_all_requests, get_request_by_id, update_request_status, save_feedback, \
    get_user_requests, get_user_feedback

logger = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_states = {}


def get_confirm_buttons():
    btn_yes = CallbackButton(text="✅ ДА, ОТПРАВИТЬ", payload="confirm_yes", intent=Intent.POSITIVE)
    btn_no = CallbackButton(text="❌ НЕТ, ОТМЕНИТЬ", payload="confirm_no", intent=Intent.NEGATIVE)
    payload = ButtonsPayload(buttons=[[btn_yes], [btn_no]])
    return Attachment(type="inline_keyboard", payload=payload)


async def update_request_status_in_chat(user_id: int, request_id: int, new_status: str):
    request = get_request_by_id(request_id)
    if not request:
        return

    status_emoji = STATUS_EMOJI.get(new_status, "⚪")
    status_text = STATUS_TEXT.get(new_status, new_status)

    message = (
        f"🔄 **Статус заявки #{request_id} изменён!**\n\n"
        f"📄 Справка для: {request['fullname']}\n"
        f"📚 Класс: {request['class']}\n"
        f"📌 Причина: {request['reason']}\n\n"
        f"**Новый статус:** {status_emoji} {status_text}\n"
    )

    if new_status == "completed":
        message += "\n🎉 **Справка готова!**\nВы можете забрать её в школьной канцелярии.\n📍 Кабинет №12, понедельник-пятница 9:00-16:00"
    elif new_status == "cancelled":
        message += "\n❌ **Заявка отклонена.**\nПо вопросам обращайтесь в канцелярию школы."
    elif new_status == "in_progress":
        message += "\n📝 **Заявка принята в работу.**\nОжидайте уведомления о готовности."

    try:
        await bot.send_message(chat_id=user_id, text=message)
    except Exception as e:
        if "dialog.not.found" not in str(e):
            print(f"⚠️ Не удалось отправить обновление: {e}")


@dp.bot_started()
async def on_start(event: BotStarted):
    await bot.send_message(
        chat_id=event.chat_id,
        text="👋 Привет! Я школьный помощник.\n\n📄 Заказывай справки\n💬 Отправляй обращения\n\nВыберите действие:",
        attachments=[main_menu()]
    )


@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    await event.message.answer(
        "👋 Привет!\n\n📄 Заказывай справки\n💬 Отправляй обращения\n\nВыберите действие:",
        attachments=[main_menu()]
    )


@dp.message_callback(F.callback.payload == "new_request")
async def new_request(event: MessageCallback):
    user_id = event.callback.user.user_id
    user_states[user_id] = {"step": "fullname"}
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="📝 Введите ФИО ученика:")
    await event.answer()


@dp.message_callback(F.callback.payload == "my_requests")
async def my_requests(event: MessageCallback):
    user_id = event.callback.user.user_id
    requests = get_user_requests(user_id)

    if not requests:
        text = "📭 У вас пока нет заявок"
    else:
        text = "📋 **Ваши заявки:**\n\n"
        for r in reversed(requests[-10:]):
            status = r.get("status", "pending")
            status_emoji = STATUS_EMOJI.get(status, "⚪")
            status_text = STATUS_TEXT.get(status, status)

            text += f"{status_emoji} **Заявка #{r['id']}**\n"
            text += f"👤 Ученик: {r['fullname']}\n"
            text += f"📚 Класс: {r['class']}\n"
            text += f"📌 Причина: {r['reason']}\n"
            text += f"📊 **Статус:** {status_text}\n"
            text += f"🕒 Создана: {r['created_at'][:16]}\n"

            if status == "completed":
                text += f"✅ **Справка готова к выдаче!**\n"
            elif status == "cancelled":
                text += f"❌ **Заявка отклонена**\n"

            text += "─" * 30 + "\n\n"

    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text, attachments=[main_menu()])
    await event.answer()


@dp.message_callback(F.callback.payload == "my_feedback")
async def my_feedback(event: MessageCallback):
    user_id = event.callback.user.user_id
    feedbacks = get_user_feedback(user_id)

    if not feedbacks:
        text = "📭 У вас пока нет обращений"
    else:
        text = "✉️ **Ваши обращения:**\n\n"
        for f in reversed(feedbacks[-5:]):
            type_name = "Обращение" if f.get("type") == "complaint" else "Предложение"
            text += f"{'⚠️' if f.get('type') == 'complaint' else '💡'} **{type_name} #{f['id']}**\n"
            text += f"📝 {f['message'][:80]}\n"
            text += f"🕒 {f['created_at'][:16]}\n\n"

    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text, attachments=[main_menu()])
    await event.answer()


@dp.message_callback(F.callback.payload == "new_feedback")
async def new_feedback(event: MessageCallback):
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="📝 **Что вы хотите отправить?**",
        attachments=[feedback_menu()]
    )
    await event.answer()


@dp.message_callback(F.callback.payload == "complaint")
async def complaint(event: MessageCallback):
    user_id = event.callback.user.user_id
    user_states[user_id] = {"step": "feedback", "type": "complaint"}
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="📝 Напишите ваше обращение:")
    await event.answer()


@dp.message_callback(F.callback.payload == "suggestion")
async def suggestion(event: MessageCallback):
    user_id = event.callback.user.user_id
    user_states[user_id] = {"step": "feedback", "type": "suggestion"}
    await bot.send_message(chat_id=event.message.recipient.chat_id, text="💡 Напишите ваше предложение:")
    await event.answer()


@dp.message_callback(F.callback.payload == "cancel")
async def cancel_callback(event: MessageCallback):
    user_id = event.callback.user.user_id
    user_states.pop(user_id, None)
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="❌ Отменено",
        attachments=[main_menu()]
    )
    await event.answer()


@dp.message_callback(F.callback.payload == "confirm_yes")
async def confirm_yes(event: MessageCallback):
    user_id = event.callback.user.user_id
    state = user_states.get(user_id, {})

    if state.get("step") != "waiting_confirm":
        await event.answer(notification="❌ Нет активной заявки", show_alert=True)
        return

    request_id = save_request({
        "user_id": user_id,
        "fullname": state.get("fullname"),
        "class": state.get("class"),
        "reason": state.get("reason")
    })

    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text=f"✅ **Заявка #{request_id} принята!**\n\n📊 Статус: {STATUS_TEXT['pending']}\n\nВы можете отслеживать статус в разделе 📋 Мои заявки"
    )
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="Выберите действие:",
        attachments=[main_menu()]
    )

    if REQUESTS_CHAT_ID:
        group_text = f"🆕 **НОВАЯ ЗАЯВКА НА СПРАВКУ**\n\n"
        group_text += f"📋 **№{request_id}**\n"
        group_text += f"👤 Ученик: {state.get('fullname')}\n"
        group_text += f"📚 Класс: {state.get('class')}\n"
        group_text += f"📌 Причина: {state.get('reason')}\n"
        group_text += f"👨‍💻 Отправил: {event.callback.user.first_name}\n"
        group_text += f"🕒 {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        group_text += f"📊 **Статус:** 🟡 {STATUS_TEXT['pending']}\n\n"
        group_text += f"👇 Нажмите на кнопку для изменения статуса:"

        await bot.send_message(
            chat_id=REQUESTS_CHAT_ID,
            text=group_text,
            attachments=[get_status_buttons(request_id, "pending")]
        )
        print(f"✅ Заявка #{request_id} отправлена в группу")

    user_states.pop(user_id, None)
    await event.answer(notification="✅ Заявка отправлена!")


@dp.message_callback(F.callback.payload == "confirm_no")
async def confirm_no(event: MessageCallback):
    user_id = event.callback.user.user_id

    await bot.send_message(chat_id=event.message.recipient.chat_id, text="❌ Заявка отменена.")
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text="Выберите действие:",
        attachments=[main_menu()]
    )

    user_states.pop(user_id, None)
    await event.answer(notification="❌ Заявка отменена")


@dp.message_created()
async def handle_text(event: MessageCreated):
    user_id = event.message.sender.user_id
    text = event.message.body.text if event.message.body else None

    if not text or text.startswith('/'):
        return

    state = user_states.get(user_id, {})
    step = state.get("step")

    if step == "fullname":
        user_states[user_id] = {"step": "class", "fullname": text}
        await event.message.answer("📚 Введите **класс** (например, 9.5):")

    elif step == "class":
        user_states[user_id] = {"step": "reason", "fullname": state["fullname"], "class": text}
        await event.message.answer("📌 **Укажите причину получения справки:**")

    elif step == "reason":
        user_states[user_id] = {
            "step": "waiting_confirm",
            "fullname": state["fullname"],
            "class": state["class"],
            "reason": text
        }
        msg = f"📝 **ПРОВЕРЬТЕ ДАННЫЕ ЗАЯВКИ:**\n\n"
        msg += f"👤 ФИО ученика: {state['fullname']}\n"
        msg += f"📚 Класс: {state['class']}\n"
        msg += f"📌 Причина: {text}\n\n"
        msg += "✅ **Всё правильно?**"
        await event.message.answer(msg, attachments=[get_confirm_buttons()])

    elif step == "feedback":
        fb_type = state.get("type")
        type_name = "Обращение" if fb_type == "complaint" else "Предложение"

        feedback_id = save_feedback({
            "user_id": user_id,
            "message": text,
            "type": fb_type,
            "fullname": event.message.sender.full_name
        })

        await event.message.answer(f"✅ **{type_name} #{feedback_id} отправлено!**", attachments=[main_menu()])

        if FEEDBACK_CHAT_ID:
            await bot.send_message(
                chat_id=FEEDBACK_CHAT_ID,
                text=f"{'⚠️' if fb_type == 'complaint' else '💡'} **{type_name}**\n👤 {event.message.sender.full_name}\n📝 {text}"
            )

        user_states.pop(user_id, None)

    else:
        await event.message.answer("Выберите действие:", attachments=[main_menu()])


@dp.message_callback(F.callback.payload.startswith("status_"))
async def change_status_in_group(event: MessageCallback):
    print(f"🔍 Нажата кнопка: {event.callback.payload}")

    payload = event.callback.payload
    without_status = payload[7:]
    last_underscore = without_status.rfind("_")
    new_status = without_status[:last_underscore]
    request_id = int(without_status[last_underscore + 1:])

    print(f"📌 Новый статус: {new_status}, ID заявки: {request_id}")

    request = get_request_by_id(request_id)
    if not request:
        await event.answer(notification="❌ Заявка не найдена", show_alert=True)
        return

    update_request_status(request_id, new_status, event.callback.user.first_name)

    status_text = STATUS_TEXT.get(new_status, new_status)
    status_emoji = STATUS_EMOJI.get(new_status, "⚪")

    # Отправляем НОВОЕ сообщение в группу с обновлённым статусом
    new_message_text = f"📋 **Заявка #{request_id}**\n\n"
    new_message_text += f"👤 Ученик: {request['fullname']}\n"
    new_message_text += f"📚 Класс: {request['class']}\n"
    new_message_text += f"📌 Причина: {request['reason']}\n\n"
    new_message_text += f"📊 **Статус:** {status_emoji} {status_text}\n"
    new_message_text += f"🕒 Обновлена: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"

    if new_status in ["pending", "in_progress"]:
        new_message_text += "👇 Действия:"
        new_buttons = get_status_buttons(request_id, new_status)
        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=new_message_text,
            attachments=[new_buttons]
        )
    else:
        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=new_message_text,
            attachments=[]
        )

    # Уведомляем пользователя
    if request["user_id"] != event.callback.user.user_id:
        await update_request_status_in_chat(request["user_id"], request_id, new_status)

    await event.answer(notification=f"✅ Статус изменён: {status_text}")
    print(f"✅ Статус заявки #{request_id} изменён на {new_status}")


@dp.message_callback(F.callback.payload == "all_requests")
async def show_all_requests(event: MessageCallback):
    requests = get_all_requests()

    if not requests:
        await bot.send_message(chat_id=event.message.recipient.chat_id, text="📭 Заявок пока нет")
        await event.answer()
        return

    text = "📋 **Список всех заявок:**\n\n"
    for req in reversed(requests[-10:]):
        status_emoji = STATUS_EMOJI.get(req["status"], "⚪")
        text += f"{status_emoji} **#{req['id']}** | {req['fullname']} ({req['class']})\n"
        text += f"   📊 {STATUS_TEXT.get(req['status'], req['status'])}\n"
        text += f"   🕒 {req['created_at'][:16]}\n\n"

    refresh = CallbackButton(text="🔄 Обновить", payload="all_requests", intent=Intent.DEFAULT)
    payload = ButtonsPayload(buttons=[[refresh]])
    attachment = Attachment(type="inline_keyboard", payload=payload)

    await bot.send_message(chat_id=event.message.recipient.chat_id, text=text, attachments=[attachment])
    await event.answer()


print("✅ handlers.py загружен")