from maxapi import Bot, F
from maxapi.types import MessageCreated, MessageCallback, Command
from maxapi.enums.intent import Intent

from config import BOT_TOKEN, ADMIN_ID
from keyboards import admin_menu, status_menu
from storage import get_all_requests, get_requests_by_status, get_request_by_id, update_request_status

bot = Bot(token=BOT_TOKEN)

# Статусы и их эмодзи/текст
STATUS_EMOJI = {"pending": "🟡", "in_progress": "🔵", "completed": "✅", "cancelled": "❌"}
STATUS_TEXT = {
    "pending": "⏳ Ожидает рассмотрения",
    "in_progress": "📝 В обработке",
    "completed": "✅ Готово (можно забрать)",
    "cancelled": "❌ Отклонена"
}


async def register_admin_handlers(dp):
    # ========== КОМАНДА /admin ==========
    @dp.message_created(Command('admin'))
    async def admin_panel(event: MessageCreated):
        if event.message.sender.user_id != ADMIN_ID:
            await event.message.answer("⛔ У вас нет доступа к админ-панели")
            return

        requests = get_all_requests()
        stats = {
            "total": len(requests),
            "pending": len([r for r in requests if r["status"] == "pending"]),
            "in_progress": len([r for r in requests if r["status"] == "in_progress"]),
            "completed": len([r for r in requests if r["status"] == "completed"]),
            "cancelled": len([r for r in requests if r["status"] == "cancelled"])
        }

        text = f"🔐 **Админ-панель**\n\n📊 **Статистика:**\n"
        text += f"📋 Всего: {stats['total']}\n"
        text += f"🟡 Ожидают: {stats['pending']}\n"
        text += f"🔵 В работе: {stats['in_progress']}\n"
        text += f"✅ Завершено: {stats['completed']}\n"
        text += f"❌ Отклонено: {stats['cancelled']}\n\n"
        text += f"👇 Выберите категорию:"

        await event.message.answer(text, attachments=[admin_menu()])

    # ========== ОБРАБОТЧИКИ КАТЕГОРИЙ ==========

    @dp.message_callback(F.callback.payload == "admin_all")
    async def admin_all(event: MessageCallback):
        if event.callback.user.user_id != ADMIN_ID:
            await event.answer(notification="⛔ Нет доступа", show_alert=True)
            return
        await show_requests_list(event, get_all_requests(), "📋 Все заявки")

    @dp.message_callback(F.callback.payload == "admin_pending")
    async def admin_pending(event: MessageCallback):
        if event.callback.user.user_id != ADMIN_ID:
            await event.answer(notification="⛔ Нет доступа", show_alert=True)
            return
        await show_requests_list(event, get_requests_by_status("pending"), "🟡 Ожидающие заявки")

    @dp.message_callback(F.callback.payload == "admin_progress")
    async def admin_progress(event: MessageCallback):
        if event.callback.user.user_id != ADMIN_ID:
            await event.answer(notification="⛔ Нет доступа", show_alert=True)
            return
        await show_requests_list(event, get_requests_by_status("in_progress"), "🔵 Заявки в работе")

    @dp.message_callback(F.callback.payload == "admin_completed")
    async def admin_completed(event: MessageCallback):
        if event.callback.user.user_id != ADMIN_ID:
            await event.answer(notification="⛔ Нет доступа", show_alert=True)
            return
        await show_requests_list(event, get_requests_by_status("completed"), "✅ Завершённые заявки")

    @dp.message_callback(F.callback.payload == "admin_cancelled")
    async def admin_cancelled(event: MessageCallback):
        if event.callback.user.user_id != ADMIN_ID:
            await event.answer(notification="⛔ Нет доступа", show_alert=True)
            return
        await show_requests_list(event, get_requests_by_status("cancelled"), "❌ Отклонённые заявки")

    @dp.message_callback(F.callback.payload == "admin_back")
    async def admin_back(event: MessageCallback):
        if event.callback.user.user_id != ADMIN_ID:
            await event.answer(notification="⛔ Нет доступа", show_alert=True)
            return
        await admin_panel(event)

    # ========== ПОКАЗ СПИСКА ЗАЯВОК С КНОПКАМИ ==========

    async def show_requests_list(event: MessageCallback, requests_list: list, title: str):
        if not requests_list:
            await bot.send_message(
                chat_id=event.message.recipient.chat_id,
                text=f"{title}\n\n📭 Заявок не найдено",
                attachments=[admin_menu()]
            )
            await event.answer()
            return

        text = f"{title}\n\n"

        # Показываем до 10 заявок с кнопками "Выбрать"
        from maxapi.types import CallbackButton, ButtonsPayload, Attachment

        buttons = []
        for i, req in enumerate(requests_list[:10], 1):
            status_emoji = STATUS_EMOJI.get(req["status"], "⚪")
            text_line = f"{i}. {status_emoji} #{req['id']} | {req['fullname']} ({req['class']})\n"
            text_line += f"   📌 {req['reason'][:40]}{'...' if len(req['reason']) > 40 else ''}\n"
            text += text_line

            # Кнопка для выбора заявки
            buttons.append([
                CallbackButton(
                    text=f"📄 Заявка #{req['id']}",
                    payload=f"select_request_{req['id']}",
                    intent=Intent.DEFAULT
                )
            ])

        text += f"\n👇 Выберите заявку для управления статусом:"

        # Кнопка "Назад"
        buttons.append([
            CallbackButton(
                text="◀️ Назад в меню",
                payload="admin_back",
                intent=Intent.DEFAULT
            )
        ])

        payload = ButtonsPayload(buttons=buttons)
        attachment = Attachment(type="inline_keyboard", payload=payload)

        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=text,
            attachments=[attachment]
        )
        await event.answer()

    # ========== ВЫБОР ЗАЯВКИ ДЛЯ РЕДАКТИРОВАНИЯ ==========

    @dp.message_callback(F.callback.payload.startswith("select_request_"))
    async def select_request(event: MessageCallback):
        if event.callback.user.user_id != ADMIN_ID:
            await event.answer(notification="⛔ Нет доступа", show_alert=True)
            return

        request_id = int(event.callback.payload.split("_")[2])
        request = get_request_by_id(request_id)

        if not request:
            await event.answer(notification="❌ Заявка не найдена", show_alert=True)
            return

        status_emoji = STATUS_EMOJI.get(request["status"], "⚪")
        status_text = STATUS_TEXT.get(request["status"], request["status"])

        # Показываем подробную информацию о заявке
        text = f"{status_emoji} **Заявка #{request_id}**\n\n"
        text += f"👤 **ФИО ученика:** {request['fullname']}\n"
        text += f"📚 **Класс:** {request['class']}\n"
        text += f"📌 **Причина:** {request['reason']}\n\n"
        text += f"📊 **Текущий статус:** {status_text}\n"
        text += f"🕒 **Создана:** {request['created_at'][:16]}\n"

        if "updated_at" in request:
            text += f"🔄 **Обновлена:** {request['updated_at'][:16]}\n"

        # История статусов
        if "status_history" in request and request["status_history"]:
            text += f"\n📜 **История изменений:**\n"
            for h in request["status_history"][-3:]:  # последние 3 изменения
                h_status = h["status"]
                h_emoji = STATUS_EMOJI.get(h_status, "⚪")
                h_text = STATUS_TEXT.get(h_status, h_status)
                h_time = h["timestamp"][:16]
                text += f"   {h_emoji} {h_text} ({h_time})\n"

        text += f"\n👇 **Выберите новое действие:**"

        await bot.send_message(
            chat_id=event.message.recipient.chat_id,
            text=text,
            attachments=[status_menu(request_id, request["status"])]
        )
        await event.answer()

    # ========== ИЗМЕНЕНИЕ СТАТУСА ==========

    @dp.message_callback(F.callback.payload.startswith("status_"))
    async def change_status(event: MessageCallback):
        if event.callback.user.user_id != ADMIN_ID:
            await event.answer(notification="⛔ Нет доступа", show_alert=True)
            return

        # Парсим: status_НОВЫЙ_СТАТУС_ID
        parts = event.callback.payload.split("_")
        new_status = parts[1]
        request_id = int(parts[2])

        # Получаем заявку
        request = get_request_by_id(request_id)
        if not request:
            await event.answer(notification="❌ Заявка не найдена", show_alert=True)
            return

        old_status = request["status"]

        # Обновляем статус
        update_request_status(request_id, new_status, event.callback.user.first_name)

        # Отправляем уведомление пользователю
        user_notification = (
            f"🔄 **Статус заявки #{request_id} изменён!**\n\n"
            f"📄 Справка для: {request['fullname']}\n"
            f"📚 Класс: {request['class']}\n"
            f"📌 Причина: {request['reason']}\n\n"
            f"**Новый статус:** {STATUS_TEXT.get(new_status, new_status)}\n"
        )

        if new_status == "completed":
            user_notification += f"\n🎉 Справка готова! Вы можете забрать её в школьной канцелярии."
        elif new_status == "cancelled":
            user_notification += f"\n❓ Если у вас есть вопросы, обратитесь в канцелярию школы."

        try:
            await bot.send_message(
                chat_id=request["user_id"],
                text=user_notification
            )
            user_notified = "✅ Пользователь уведомлён"
        except Exception as e:
            user_notified = f"⚠️ Не удалось уведомить пользователя: {e}"

        # Подтверждение администратору
        await event.message.edit_text(
            text=f"✅ **Статус заявки #{request_id} изменён!**\n\n"
                 f"👤 Ученик: {request['fullname']}\n"
                 f"📊 Старый статус: {STATUS_TEXT.get(old_status, old_status)}\n"
                 f"📊 Новый статус: {STATUS_TEXT.get(new_status, new_status)}\n\n"
                 f"{user_notified}\n\n"
                 f"Вернуться в админ-панель: /admin",
            attachments=[admin_menu()]
        )
        await event.answer()

    # ========== КОМАНДА СТАТУС (оставляем для совместимости) ==========

    @dp.message_created(Command('status'))
    async def status_command(event: MessageCreated):
        """Альтернативный способ через команду"""
        if event.message.sender.user_id != ADMIN_ID:
            await event.message.answer("⛔ Нет доступа")
            return

        parts = event.message.body.text.split()
        if len(parts) != 3:
            await event.message.answer(
                "❌ Используйте: /status [номер] [статус]\n\nСтатусы: pending, in_progress, completed, cancelled")
            return

        try:
            request_id = int(parts[1])
            new_status = parts[2]

            if new_status not in ["pending", "in_progress", "completed", "cancelled"]:
                await event.message.answer("❌ Неверный статус")
                return

            request = get_request_by_id(request_id)
            if not request:
                await event.message.answer(f"❌ Заявка #{request_id} не найдена")
                return

            update_request_status(request_id, new_status, event.message.sender.first_name)

            # Уведомляем пользователя
            await bot.send_message(
                chat_id=request["user_id"],
                text=f"🔄 **Статус заявки #{request_id} изменён!**\n\nНовый статус: {STATUS_TEXT.get(new_status, new_status)}"
            )

            await event.message.answer(
                f"✅ Статус заявки #{request_id} изменён на '{new_status}'\nПользователь уведомлён")

        except ValueError:
            await event.message.answer("❌ Номер заявки должен быть числом")


print("✅ admin.py загружен")