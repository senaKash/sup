import asyncio

import sys
from os import getenv

from aiogram.client.session.aiohttp import AiohttpSession

from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import User, Message, ContentType
from aiogram.utils.markdown import hbold
from aiogram.types import FSInputFile
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InputFile

from excel_manager import ExcelManager
import re

from aiogram.filters import Command
from aiogram.filters import Command, CommandObject, CommandStart
from commands import set_default_commands

from aiogram.filters.callback_data import CallbackData


from datetime import datetime, timedelta

import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from datetime import datetime
from typing import Callable, Any, Optional


from aiogram.handlers import MessageHandler, CallbackQueryHandler

from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback, get_user_locale
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.state import StateFilter
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback, get_user_locale


dp = Dispatcher()
file_name = "DATA_BASE.xlsx"



def get_user_link(user: User) -> str:
    if user.username:
        return f"https://t.me/{user.username}"
    else:
        return f"tg://user?id={user.id}"




#admin_id = [541020016, 1832033163]

admin_id = [541020016, 2081737934]


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:

    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
    )

    await message.answer(f"Здравствуйте, <b>{message.from_user.full_name}</b> для продолжнения отправьте номер телефона", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="html")
    print(f"{message.from_user.full_name} нажал start")

#@dp.message(F.photo)
#async def photo_handler(message: Message) -> None:
#    photo_data = message.photo[-1]
#    await message.answer(f"{photos_data}")


#для коллбека
class OrderSupState(StatesGroup):
    waiting_for_additional_info = State()



@dp.message(lambda message: message.content_type == ContentType.CONTACT)
async def contact_handler(message: Message) -> None:

    contact = message.contact
    user_phone_number = contact.phone_number

    user_link = get_user_link(message.from_user)

    excel_manager = ExcelManager(file_name)
    excel_manager.create_or_update_workbook(message.from_user.id, strip_html_tags(hbold(message.from_user.full_name)), user_link, user_phone_number)

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Согласиться и продолжить",
        callback_data="choose_sup")
    )

    builder_2 = types.ReplyKeyboardRemove()  # Этот метод убирает клавиатуру с экрана
    await message.answer("Спасибо! регистрация завершена", reply_markup=builder_2)

    await message.answer(f"❗️САПЫ ВЫДАЮТСЯ ПО ДОГОВОРУ АРЕНДЫ❗️\nЗалог - 5000р.👌🏼 не зависит от количества взятых сапов в аренду ( либо паспорт РФ)\n🛑ЗА УТЕРЮ КОМПЛЕКТА, ЗАДЕРЖКУ АРЕНДЫ И СДАЧУ САП ДОСОК В НЕПОТРЕБНОМ ВИДЕ ПРЕДУСМОТРЕН ШТРАФ🛑", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.callback_query(F.data == "choose_sup")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    excel_manager = ExcelManager(file_name)
    mark = excel_manager.get_sups()

    #await callback.message.answer(f"{mark}")

    media = [types.InputMediaPhoto(media=item['url']) for item in mark]

    builder = InlineKeyboardBuilder()

    count = 0
    row = []

    for item in mark:
        row.append(types.InlineKeyboardButton(text=item['name'], callback_data=f"sup_{item['id']}"))
        count += 1
        if count == 2:
            builder.row(*row)
            row = []
            count = 0

    if row:
        builder.row(*row)

    await callback.message.answer_media_group(media=media)
    await callback.message.answer("Выберите один из вариантов:", reply_markup=builder.as_markup(resize_keyboard=True))


# Определение состояний
#class OrderSupState(StatesGroup):
#    waiting_for_additional_info = State()
#    waiting_for_confirmation = State()
#    waiting_for_payment_screenshot = State()

class OrderSupState(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_confirmation = State()
    waiting_for_payment_screenshot = State()
    waiting_for_payment_screenshot = State()


# Функция проверки даты и времени
def is_valid_date(date_text):
    try:
        datetime.strptime(date_text, '%H:%M %d.%m')
        return True
    except ValueError:
        return False


def is_valid_day_month(date_text):
    try:
        datetime.strptime(date_text, '%d.%m')
        return True
    except ValueError:
        return False

# Словарь для перевода дней недели
days_of_week = {
    0: 'понедельник',
    1: 'вторник',
    2: 'среду',
    3: 'четверг',
    4: 'пятницу',
    5: 'субботу',
    6: 'воскресенье'
}

# Калькулятор стоимости
def calculate_rent_cost(date_from_str, date_to_str=None):
    cost_per_hour = 300
    cost_per_weekday = 1000
    cost_per_weekend_evening = 1300
    cost_per_weekend = 3000
    cost_per_week = 5900

    current_year = datetime.now().year

    # Обработка начальной даты и времени
    if len(date_from_str) == 5:  # Формат: DD.MM
        date_from = datetime.strptime(date_from_str, '%d.%m')
        date_from = date_from.replace(year=current_year)
    elif len(date_from_str) == 10:  # Формат: DD.MM.YYYY
        date_from = datetime.strptime(date_from_str, '%d.%m.%Y')
    else:  # Форматы с временем: HH:MM DD.MM или HH:MM DD.MM.YYYY
        try:
            date_from = datetime.strptime(date_from_str, '%H:%M %d.%m.%Y')
        except ValueError:
            date_from = datetime.strptime(date_from_str, '%H:%M %d.%m')
            date_from = date_from.replace(year=current_year)

    # Обработка конечной даты и времени
    if date_to_str:
        if len(date_to_str) == 5:  # Формат: DD.MM
            date_to = datetime.strptime(date_to_str, '%d.%m')
            date_to = date_to.replace(year=current_year)
        elif len(date_to_str) == 10:  # Формат: DD.MM.YYYY
            date_to = datetime.strptime(date_to_str, '%d.%m.%Y')
        else:  # Форматы с временем: HH:MM DD.MM или HH:MM DD.MM.YYYY
            try:
                date_to = datetime.strptime(date_to_str, '%H:%M %d.%m.%Y')
            except ValueError:
                date_to = datetime.strptime(date_to_str, '%H:%M %d.%m')
                date_to = date_to.replace(year=current_year)
    else:
        date_to = date_from

    if date_from > date_to:
        return 0, []

    if date_from == date_to:
        if date_from.weekday() < 5:  # Будний день
            return cost_per_weekday, [f"Добавлено {cost_per_weekday} руб. за будний день {days_of_week[date_from.weekday()]} {date_from.date()}"]
        else:  # Суббота или воскресенье
            return cost_per_weekend, [f"Добавлено {cost_per_weekend} руб. за выходной день {days_of_week[date_from.weekday()]} {date_from.date()}"]

    if (date_to - date_from).days == 6:
        return cost_per_week, [f"Добавлено {cost_per_week} руб. за недельную аренду с {date_from.date()} по {date_to.date()}"]

    if date_from.weekday() == 5 and date_to.weekday() == 6 and (date_to - date_from).days == 1:
        return cost_per_weekend, [f"Добавлено {cost_per_weekend} руб. за аренду с субботы по воскресенье {date_from.date()} - {date_to.date()}"]

    total_cost = 0
    cost_details = []
    current_date = date_from

    while current_date <= date_to:
        if (date_to - date_from).total_seconds() / 3600 <= 12:
            hours_diff = (date_to - date_from).total_seconds() / 3600
            total_cost += cost_per_hour * hours_diff
            cost_details.append(f"Добавлено {cost_per_hour * hours_diff:.2f} руб. за почасовую аренду с {date_from} по {date_to}")
            break

        day_name = days_of_week[current_date.weekday()]

        if current_date.weekday() < 5:
            total_cost += cost_per_weekday
            cost_details.append(f"Добавлено {cost_per_weekday} руб. за будний день {day_name} {current_date.date()}")
        else:
            total_cost += cost_per_weekend_evening
            cost_details.append(f"Добавлено {cost_per_weekend_evening} руб. за выходной день {day_name} {current_date.date()}")

        current_date += timedelta(days=1)

    return total_cost, cost_details

########################### ДАТА ГРАББЕР №№№№№№№№№№№№№№№№



# Обработчик коллбэка для выбора начальной даты
@dp.callback_query(SimpleCalendarCallback.filter(), StateFilter(OrderSupState.waiting_for_start_date))
async def process_start_date(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):

    # Проверка нажатия на кнопку Cancel
    if callback_data.act == "CANCEL":
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="Домой",
            callback_data="choose_sup")
        )
        await callback_query.message.answer("Вы отменили выбор даты.", reply_markup=builder.as_markup(resize_keyboard=True))
        return  # Завершаем обработчик

    # Проверка нажатия на кнопку TODAY
    if callback_data.act == "TODAY":
        today_date = datetime.now()
        start_date_str = today_date.strftime('%d.%m.%Y')
        await state.update_data(start_date=start_date_str)  # Сохраняем начальную дату в состояние
        await callback_query.message.answer(
            f"Дата начала: {start_date_str}\nТеперь выберите дату окончания: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора конечной даты
        )
        await state.set_state(OrderSupState.waiting_for_end_date)  # Переключаем состояние на ожидание конечной даты
        return  # Завершаем обработчик

    # Обработка выбора даты
    selected, date = await SimpleCalendar(locale='ru_RU').process_selection(callback_query, callback_data)

    if selected:
        start_date_str = date.strftime('%d.%m.%Y')
        await state.update_data(start_date=start_date_str)  # Сохраняем начальную дату в состояние
        await callback_query.message.answer(
            f"Дата начала: {start_date_str}\nТеперь выберите дату окончания: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar() # Показываем календарь для выбора конечной даты
        )
        await state.set_state(OrderSupState.waiting_for_end_date)  # Переключаем состояние на ожидание конечной даты


# Обработчик коллбэка для выбора конечной даты
@dp.callback_query(SimpleCalendarCallback.filter(), StateFilter(OrderSupState.waiting_for_end_date))
async def process_end_date(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):

    # Проверка нажатия на кнопку Cancel
    if callback_data.act == "CANCEL":
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="Домой",
            callback_data="choose_sup")
        )
        await callback_query.message.answer("Вы отменили выбор даты.", reply_markup=builder.as_markup(resize_keyboard=True))
        return  # Завершаем обработчик

    # Проверка нажатия на кнопку TODAY
    if callback_data.act == "TODAY":
        today_date = datetime.now().date()
        end_date_str = today_date.strftime('%d.%m.%Y')
        user_data = await state.get_data()
        start_date_str = user_data.get('start_date')
        start_date = datetime.strptime(start_date_str, '%d.%m.%Y').date()

        # Проверка корректности промежутка дат
        if start_date > today_date:
            await callback_query.message.answer(f"Ошибка: Дата окончания ({end_date_str}) не может быть раньше даты начала ({start_date_str}).")
            await confirm_no(callback_query, state)
            return

        await state.update_data(end_date=end_date_str)  # Сохраняем конечную дату в состояние

        # Рассчитываем стоимость аренды
        cost, details = calculate_rent_cost(start_date_str, end_date_str)
        await state.update_data(rent_cost=cost, cost_details=details)

        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Да", callback_data="confirm_yes"))
        builder.add(types.InlineKeyboardButton(text="Нет", callback_data="confirm_no"))

        # Показываем пользователю информацию о выбранных датах и стоимости аренды, запрашиваем подтверждение
        await callback_query.message.answer(
            f"<b>Вы уверены, что хотите использовать эту дату: {start_date_str} - {end_date_str}?</b>\n\n"
            f"<b>Стоимость аренды: {cost}₽</b>\nДетали:\n"
            + '\n'.join(details),
            reply_markup=builder.as_markup(),
            parse_mode="html"
        )
        await state.set_state(OrderSupState.waiting_for_confirmation)  # Переключаем состояние на ожидание подтверждения
        return  # Завершаем обработчик

    # Обработка выбора даты
    selected, date = await SimpleCalendar(locale='ru_RU').process_selection(callback_query, callback_data)

    if selected:
        today_date = datetime.now().date()
        end_date = date.date()
        end_date_str = end_date.strftime('%d.%m.%Y')
        user_data = await state.get_data()
        start_date_str = user_data.get('start_date')
        start_date = datetime.strptime(start_date_str, '%d.%m.%Y').date()

        # Проверка корректности промежутка дат
        if start_date > end_date:
            await callback_query.message.answer(f"Ошибка: Дата окончания ({end_date_str}) не может быть раньше даты начала ({start_date_str}).")
            await confirm_no(callback_query, state)
            return

        if end_date < today_date:
            await callback_query.message.answer(f"Ошибка: Дата окончания ({end_date_str}) не может быть раньше сегодняшнего дня ({today_date.strftime('%d.%m.%Y')}).")
            await confirm_no(callback_query, state)
            return

        await state.update_data(end_date=end_date_str)  # Сохраняем конечную дату в состояние

        # Рассчитываем стоимость аренды
        cost, details = calculate_rent_cost(start_date_str, end_date_str)
        await state.update_data(rent_cost=cost, cost_details=details)

        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Да", callback_data="confirm_yes"))
        builder.add(types.InlineKeyboardButton(text="Нет", callback_data="confirm_no"))

        # Показываем пользователю информацию о выбранных датах и стоимости аренды, запрашиваем подтверждение
        await callback_query.message.answer(
            f"<b>Вы уверены, что хотите использовать эту дату: {start_date_str} - {end_date_str}?</b>\n\n"
            f"<b>Стоимость аренды: {cost}₽</b>\nДетали:\n"
            + '\n'.join(details),
            reply_markup=builder.as_markup(),
            parse_mode="html"
        )
        await state.set_state(OrderSupState.waiting_for_confirmation)  # Переключаем состояние на ожидание подтверждения

# Обработчик коллбэка для отказа от подтверждения дат
@dp.callback_query(lambda c: c.data == "confirm_no", StateFilter(OrderSupState.waiting_for_confirmation))
async def confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Пожалуйста, выберите дату начала аренды: ",
        reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Снова показываем календарь для выбора начальной даты
    )
    await state.set_state(OrderSupState.waiting_for_start_date)  # Возвращаем состояние к ожиданию начальной даты


@dp.callback_query(F.data =="confirm_yes", StateFilter(OrderSupState.waiting_for_confirmation))
async def confirm_yes(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    start_date = user_data.get('start_date')
    end_date = user_data.get('end_date')
    rent_cost = user_data.get('rent_cost')

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Отмена",
        callback_data="payment_cancel")
    )

    await callback.message.answer(
        f"Дата {start_date} - {end_date} подтверждена.\n"
        f"Стоимость аренды: {rent_cost}₽\n\n"
        "Оплатите на номер +7 981 743 6822 Сбербанк или Альфа банк и пришлите скриншот или нажмите Отмена.",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(OrderSupState.waiting_for_payment_screenshot)


@dp.message(OrderSupState.waiting_for_payment_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    text = user_data.get('text', '')
    additional_info = user_data.get('additional_info')
    rent_cost = user_data.get('rent_cost')
    cost_details = user_data.get('cost_details', [])
    text += (
    f"\n<b>Дата: {additional_info}</b>\n"
    f"<b>Стоимость аренды: {rent_cost}₽</b>\n\n"
    "Детали:\n" + '\n'.join(cost_details))


    photo = message.photo[-1]
    photo_file_id = photo.file_id



    media = [types.InputMediaPhoto(media=photo_file_id)]


    for id_ad in admin_id:
        await message.bot.send_message(id_ad, text)
        await message.bot.send_media_group(id_ad, media=media)
        #await callback.message.answer_media_group(media=media)

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Домой",
        callback_data="choose_sup")
    )
    await message.answer("Спасибо! Ваш заказ был отправлен.", reply_markup=builder.as_markup(resize_keyboard=True))


    #await state.finish()

@dp.callback_query(F.data == "payment_cancel")
async def payment_cancel(callback: types.CallbackQuery, state: FSMContext):

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Домой",
        callback_data="choose_sup")
    )

    await callback.message.answer("Оплата отменена", reply_markup=builder.as_markup(resize_keyboard=True))



###########################ОТПРАВИТЬ АДМИНАМ№№№№№№№№№№№№№№№№

##########################################SUP BLOCK########################################################################

@dp.callback_query(F.data == "sup_1")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    # Получаем данные
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_sups()

    # Ищем элемент с id=1
    selected_sup = next((sup for sup in sups if sup['id'] == 1), None)

    #await callback.message.answer(f"{selected_sup}")

    if selected_sup:



        price = selected_sup['price']
        price = list(map(int, price.split(", ")))
        price_text = f"💸СТОИМОСТЬ АРЕНДЫ В СУТКИ:💸:\n- {price[0]}руб час\n- {price[1]}руб (будни пн -чт)\n- {price[2]}руб (выxoдныe чт 16:00 - вс)\n- {price[3]}руб (на выходные с вечера ПТ по ВС)\n- {price[4]}руб (аренда на неделю)🚀"

        availability = selected_sup['availability']

        media = [types.InputMediaPhoto(media=selected_sup['url'])]
        await callback.message.answer_media_group(media=media)
        #await callback.message.answer_media_group(media=media)
        # Создаем сообщение



        if availability == 1:

            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>В наличии</b>\n\n" + price_text

            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Выбрать цвет",
                callback_data="choose_color_sup_1")
            )
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        else:

            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )


        await callback.message.answer(f"{sup_text}", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="html")

    else:
        sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        await callback.message.answer(sup_text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "choose_color_sup_1")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    text = f"Выберите цвет:"
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
                text="Синий 🟦",
                callback_data="send_admin_sup_1")
    )
    builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
    )
    await callback.message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


#########################################################МРАЗЬ КОТОРАЯ ОТВЕЧАЕТ ЗА ФОРМИРОВАНИЕ ЗАКАЗА###########################################

# Изначальный обработчик для начала процесса выбора дат
@dp.callback_query(F.data == "send_admin_sup_1")
async def send_admin_sup(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)  # Удаляем клавиатуру после нажатия
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")



@dp.callback_query(F.data == "sup_2")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    # Получаем данные
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_sups()

    # Ищем элемент с id=1
    selected_sup = next((sup for sup in sups if sup['id'] == 2), None)

    #await callback.message.answer(f"{selected_sup}")

    if selected_sup:
        price = selected_sup['price']
        price = list(map(int, price.split(", ")))
        price_text = f"💸СТОИМОСТЬ АРЕНДЫ В СУТКИ:💸:\n- {price[0]}руб час\n- {price[1]}руб (будни пн -чт)\n- {price[2]}руб (выxoдныe чт 16:00 - вс)\n- {price[3]}руб (на выходные с вечера ПТ по ВС)\n- {price[4]}руб (аренда на неделю)🚀"
        availability = selected_sup['availability']

        media = [types.InputMediaPhoto(media=selected_sup['url'])]
        await callback.message.answer_media_group(media=media)
        #await callback.message.answer_media_group(media=media)
        # Создаем сообщение
        if availability == 1:
            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>В наличии</b>\n\n" + price_text

            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Выбрать цвет",
                callback_data="choose_color_sup_2")
            )
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        else:

            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )

        await callback.message.answer(f"{sup_text}", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="html")

    else:
        sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        await callback.message.answer(sup_text, reply_markup=builder.as_markup(resize_keyboard=True))



@dp.callback_query(F.data == "choose_color_sup_2")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    text = f"Выберите цвет:"
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
                text="Красный 🟥",
                callback_data="send_admin_sup_2")
    )
    builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
    )
    await callback.message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "send_admin_sup_2")
async def send_admin_sup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")


@dp.callback_query(F.data == "sup_3")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    # Получаем данные
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_sups()

    # Ищем элемент с id=1
    selected_sup = next((sup for sup in sups if sup['id'] == 3), None)

    #await callback.message.answer(f"{selected_sup}")

    if selected_sup:
        price = selected_sup['price']
        price = list(map(int, price.split(", ")))
        price_text = f"💸СТОИМОСТЬ АРЕНДЫ В СУТКИ:💸:\n- {price[0]}руб час\n- {price[1]}руб (будни пн -чт)\n- {price[2]}руб (выxoдныe чт 16:00 - вс)\n- {price[3]}руб (на выходные с вечера ПТ по ВС)\n- {price[4]}руб (аренда на неделю)🚀"
        availability = selected_sup['availability']

        media = [types.InputMediaPhoto(media=selected_sup['url'])]
        await callback.message.answer_media_group(media=media)
        #await callback.message.answer_media_group(media=media)
        # Создаем сообщение



        if availability == 1:
            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>В наличии</b>\n\n" + price_text

            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Выбрать цвет",
                callback_data="choose_color_sup_3")
            )
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        else:

            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )


        await callback.message.answer(f"{sup_text}", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="html")

    else:
        sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        await callback.message.answer(sup_text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "choose_color_sup_3")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    text = f"Выберите цвет:"
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
                text="Синий 🟦",
                callback_data="send_admin_sup_3_1")
    )
    builder.add(types.InlineKeyboardButton(
                text="Голубой ⏹️",
                callback_data="send_admin_sup_3_2")
    )
    builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
    )
    await callback.message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "send_admin_sup_3_1")
async def send_admin_sup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")



@dp.callback_query(F.data == "send_admin_sup_3_2")
async def send_admin_sup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")


@dp.callback_query(F.data == "sup_4")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    # Получаем данные
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_sups()

    # Ищем элемент с id=1
    selected_sup = next((sup for sup in sups if sup['id'] == 4), None)

    #await callback.message.answer(f"{selected_sup}")

    if selected_sup:
        price = selected_sup['price']
        price = list(map(int, price.split(", ")))
        price_text = f"💸СТОИМОСТЬ АРЕНДЫ В СУТКИ:💸:\n- {price[0]}руб час\n- {price[1]}руб (будни пн -чт)\n- {price[2]}руб (выxoдныe чт 16:00 - вс)\n- {price[3]}руб (на выходные с вечера ПТ по ВС)\n- {price[4]}руб (аренда на неделю)🚀"
        availability = selected_sup['availability']

        media = [types.InputMediaPhoto(media=selected_sup['url'])]
        await callback.message.answer_media_group(media=media)
        # Создаем сообщение
        if availability == 1:
            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>В наличии</b>\n\n" + price_text

            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Выбрать цвет",
                callback_data="choose_color_sup_4")
            )
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        else:

            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )


        await callback.message.answer(f"{sup_text}", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="html")

    else:
        sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        await callback.message.answer(sup_text, reply_markup=builder.as_markup(resize_keyboard=True))

@dp.callback_query(F.data == "choose_color_sup_4")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    text = f"Выберите цвет:"
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
                text="Зелёный 🟩",
                callback_data="send_admin_sup_4")
    )

    builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
    )
    await callback.message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "send_admin_sup_4")
async def send_admin_sup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")



@dp.callback_query(F.data == "sup_5")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    # Получаем данные
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_sups()

    # Ищем элемент с id=1
    selected_sup = next((sup for sup in sups if sup['id'] == 5), None)

    #await callback.message.answer(f"{selected_sup}")

    if selected_sup:
        price = selected_sup['price']
        price = list(map(int, price.split(", ")))
        price_text = f"💸СТОИМОСТЬ АРЕНДЫ В СУТКИ:💸:\n- {price[0]}руб час\n- {price[1]}руб (будни пн -чт)\n- {price[2]}руб (выxoдныe чт 16:00 - вс)\n- {price[3]}руб (на выходные с вечера ПТ по ВС)\n- {price[4]}руб (аренда на неделю)🚀"
        availability = selected_sup['availability']

        media = [types.InputMediaPhoto(media=selected_sup['url'])]
        await callback.message.answer_media_group(media=media)
        # Создаем сообщение
        if availability == 1:
            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>В наличии</b>\n\n" + price_text

            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Выбрать цвет",
                callback_data="choose_color_sup_5")
            )
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        else:

            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )


        await callback.message.answer(f"{sup_text}", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="html")

    else:
        sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        await callback.message.answer(sup_text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "choose_color_sup_5")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    text = f"Выберите цвет:"
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
                text="Синий 🟦",
                callback_data="send_admin_sup_5_1")
    )
    builder.add(types.InlineKeyboardButton(
                text="Голубой ⏹️",
                callback_data="send_admin_sup_5_2")
    )
    builder.add(types.InlineKeyboardButton(
                text="Красный 🟥",
                callback_data="send_admin_sup_5_3")
    )

    builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
    )
    await callback.message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "send_admin_sup_5_1")
async def send_admin_sup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")

@dp.callback_query(F.data == "send_admin_sup_5_2")
async def send_admin_sup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")



@dp.callback_query(F.data == "send_admin_sup_5_3")
async def send_admin_sup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")




@dp.callback_query(F.data == "sup_6")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    # Получаем данные
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_sups()

    # Ищем элемент с id=1
    selected_sup = next((sup for sup in sups if sup['id'] == 6), None)

    #await callback.message.answer(f"{selected_sup}")

    if selected_sup:
        price = selected_sup['price']
        price = list(map(int, price.split(", ")))
        price_text = f"💸СТОИМОСТЬ АРЕНДЫ В СУТКИ:💸:\n- {price[0]}руб час\n- {price[1]}руб (будни пн -чт)\n- {price[2]}руб (выxoдныe чт 16:00 - вс)\n- {price[3]}руб (на выходные с вечера ПТ по ВС)\n- {price[4]}руб (аренда на неделю)🚀"
        availability = selected_sup['availability']

        media = [types.InputMediaPhoto(media=selected_sup['url'])]
        await callback.message.answer_media_group(media=media)
        # Создаем сообщение
        if availability == 1:
            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>В наличии</b>\n\n" + price_text

            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Выбрать цвет",
                callback_data="choose_color_sup_6")
            )
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        else:

            sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )


        await callback.message.answer(f"{sup_text}", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="html")

    else:
        sup_text = f"<b>{selected_sup['name']}</b>\n\nРазмер - {selected_sup['size']}\n<b>Нет в наличии</b>\n\n" + price_text
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
            )
        await callback.message.answer(sup_text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "choose_color_sup_6")
async def choose_sup(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    text = f"Выберите цвет:"
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
                text="Ораньжевый 🟧",
                callback_data="send_admin_sup_6")
    )

    builder.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="choose_sup")
    )
    await callback.message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "send_admin_sup_6")
async def send_admin_sup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        text = (
            f"НОВЫЙ ЗАКАЗ\nID - {selected_sup['id']}\nИмя - {selected_sup['name']}\n"
            f"Ссылка тг - {selected_sup['link']}\nНомер - {selected_sup['number']}\n\nCOOLSURF Синий"
        )

        await state.update_data(text=text)  # Сохраняем информацию о заказе в состоянии
        await state.set_state(OrderSupState.waiting_for_start_date)  # Устанавливаем состояние ожидания начальной даты
        await callback.message.answer(
            "Пожалуйста, выберите дату начала аренды: ",
            reply_markup=await SimpleCalendar(locale='ru_RU').start_calendar()  # Показываем календарь для выбора начальной даты
        )
    else:
        await callback.message.answer("Ошибка: Не удалось найти информацию о пользователе.")

##########################################END SUP BLOCK########################################################################
'''
class SUPCallbackData(CallbackData, prefix="sup_"):
    id: int

@dp.callback_query(SUPCallbackData.filter())
async def send_homework(callback: types.CallbackQuery, callback_data: SUPCallbackData):
    await callback.message.edit_reply_markup(reply_markup=None)

    sup_id = callback_data.id

    excel_manager = ExcelManager("your_file_name.xlsx")
    mark = excel_manager.get_sups()

    selected_sup = next((item for item in mark if item['id'] == sup_id), None)

    if selected_sup:
        await callback.message.answer(f"Вы выбрали SUP: {selected_sup['name']}")
    else:
        await callback.message.answer("Выбранный SUP не найден")
'''





@dp.callback_query(F.data == "zapisi_lekcii")
async def send_random_value(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    excel_manager = ExcelManager(file_name)
    urls = excel_manager.lektsionnie_url()
    msg = "Лекции\n"
    print(f"{callback.from_user.full_name} посмотрел список лекций")
    #ids = excel_manager.get_all_ids()
    #print(ids)
    #for user_id in ids:
    #    await callback.bot.send_message(user_id, "Лекция загружена(Дз кста тоже посмотрите)")
    #await callback.bot.send_message(541020016, "Хуй")
    await callback.message.answer(f"{msg}{urls}", reply_markup=build_keyboard().as_markup(resize_keyboard=True))


@dp.callback_query(F.data == "homework")
async def send_homework(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    msg = "Дз\n"

    print(f"{callback.from_user.full_name} посмотрел дз")
    await callback.message.answer(f"{msg}Повторить то, что я написал на практике(p.s. кому сильно лень - кину в начале след пары, но это -rep)", reply_markup=build_keyboard().as_markup(resize_keyboard=True))

@dp.callback_query(F.data == "timetable")
async def send_homework(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    dates = ["07.04;18:00", "14.04;18:00"]
    formatted_message = format_schedule(dates)

    print(f"{callback.from_user.full_name} посмотрел расписание")
    msg = "Расписание\n"
    await callback.message.answer(f"{msg}{formatted_message}", reply_markup=build_keyboard().as_markup(resize_keyboard=True))

@dp.callback_query(F.data == "files")
async def send_materials(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    print(f"{callback.from_user.full_name} посмотрел материалы")
    msg = "Материалы\n"
    await callback.message.answer(f"{msg}Сюда залью презентации, книжки и т.д.", reply_markup=build_keyboard().as_markup(resize_keyboard=True))

@dp.callback_query(F.data == "mark")
async def update_poseshuaemost(callback: types.CallbackQuery):  #время устанавливается вручную
    excel_manager = ExcelManager(file_name)
    mark = excel_manager.check_and_update_attendance(callback.from_user.id)
    print("mark = ", mark)
    if mark == 2:
        await callback.answer(
        text="Уже отметился",
        show_alert=True
        )
    elif mark == 1:
        await callback.answer(
        text="Отметился",
        show_alert=True
        )
    elif mark == 0:
        await callback.answer(
        text="ошибка id или exel",
        show_alert=True
        )
    elif mark == 3:
        await callback.answer(
        text="Отмечатся можно только во время пары",
        show_alert=True
        )


@dp.message(Command('home'))#commands=['addLectureUrl'])
async def add_lecture_url(message: types.Message, command: CommandObject) -> None:

    user_id = message.from_user.id
    excel_manager = ExcelManager(file_name)
    sups = excel_manager.get_user_info()
    selected_sup = next((sup for sup in sups if sup['id'] == user_id), None)

    if selected_sup:
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="Выбрать SUP",
            callback_data="choose_sup")
        )

        await message.answer(f"Домой", reply_markup=builder.as_markup(resize_keyboard=True))

    else:
        await command_start_handler(message)


@dp.message(Command('start'))#commands=['addLectureUrl'])
async def add_lecture_url(message: types.Message, command: CommandObject) -> None:
    await command_start_handler(message)


@dp.message(Command('spam'))#commands=['addLectureUrl'])
async def add_lecture_url(message: types.Message, command: CommandObject) -> None:
    if message.from_user.id in admin_id:
        command_text = command.args
        if not command_text:
            await message.answer("Добавьте текст сообщения")
            return
        msg = command_text.strip()
        excel_manager = ExcelManager(file_name)
        #msg = "Лекции\n"
        ids = excel_manager.get_all_ids()
        print(ids, msg)

        #user_id = 541020016
        #await message.bot.send_message(user_id, msg)
        for user_id in ids:
            try:
                await message.bot.send_message(user_id, msg)
            except:
                for admin in admin_id:
                    try:
                        await message.bot.send_message(admin, f"Не удалось отправить сообщение {user_id}\n tg://user?id={user_id}")
                    except Exception as e:
                        print(f"Не удалось отправить сообщение администратору {admin}: {e}")
                #await message.bot.send_message(541020016, f"не удалось отрпавить сообщение {user_id}")
        #link = command_text.strip()  # Удаляем лишние пробелы по краям
        #excel_manager = ExcelManager(file_name)
        #excel_manager.lektsionnie_url(link)
        #await message.answer(f"Вы добавили ссылку: {link}")
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")



@dp.message()
async def handle_message(message: types.Message) -> None:
    if message.text == '1':
        photo_path = "12.jpg"
        await message.answer_photo(FSInputFile(photo_path))



async def main() -> None:
    session = AiohttpSession(proxy='http://proxy.server:3128')
    bot = Bot(token='6606236242:AAFj4FaySsTXxbHXgqHmQD6iSrFfNORdhkE', session=session)
    #bot = Bot('6606236242:AAEv2NK18R07gUnqk1O_hOJubvP-25YMSmI', default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await set_default_commands(bot)
    await dp.start_polling(bot)
    #register_handlers(dp)
#async def main() -> None:
#    bot = Bot('6606236242:AAFlHP2zlHhs956QKruEWHvouVO5aGSngdc', default=DefaultBotProperties(parse_mode=ParseMode.HTML))
#    await set_default_commands(bot)
#    await dp.start_polling(bot)
#    register_handlers(dp)


def strip_html_tags(text):
    """Функция для удаления HTML тегов из строки."""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def format_schedule(dates):
    # Находим максимальную длину даты и времени
    max_date_length = max(len(date_time.split(";")[0]) for date_time in dates)
    max_time_length = max(len(date_time.split(";")[1]) for date_time in dates)

    # Заголовок таблицы
    header = "Дата".ljust(max_date_length + 4)
    time_row = "Время".ljust(max_time_length + 2)
    for date_time in dates:
        date, time = date_time.split(";")
        header += date.ljust(max_date_length + 2)
        time_row += time.ljust(max_time_length + 2)

    # Разделитель
    separator = "-" * (len(header) + 10)
    # Формируем сообщение
    message = header + "\n" + separator + "\n"+ time_row
    return message



def build_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="Лекции", callback_data="zapisi_lekcii"),
        types.InlineKeyboardButton(text="Дз", callback_data="homework")
    )
    builder.row(
        types.InlineKeyboardButton(text="Расписание", callback_data="timetable"),

    )
    builder.row(
        types.InlineKeyboardButton(text="Всякое полезное", callback_data="files"),
        types.InlineKeyboardButton(text="Я на паре", callback_data="mark")
    )
    #builder.as_markup(resize_keyboard=True)
    return builder



if __name__ == "__main__":
    #logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())