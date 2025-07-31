import asyncio
from redis.asyncio import Redis

import random
from collections import OrderedDict

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
from functools import wraps

import jwt
import matplotlib.pyplot as plt
import psycopg2
import pytz
from html2markdown import convert

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hlink
from aiogram.fsm.storage.redis import RedisStorage

import keyboards
import lists
from repository import Repo

from dotenv import load_dotenv
load_dotenv()


class SelectInfo(StatesGroup):
    view_all_fttx = State()
    register_user = State()
    view_azs = State()
    view_man = State()
    view_bs_number = State()
    view_bs_address = State()
    view_action = State()
    select_action = State()
    view_accident = State()
    exit_exit = State()
    add_new_info = State()
    update_accident = State()


class Registred:
    name = None

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))

redis_client = Redis(host="localhost", port=6379, db=0, decode_responses=True)
storage = RedisStorage(redis=redis_client)
dp = Dispatcher(storage=storage)

class AuthStates(StatesGroup):
    """States for authentication and output"""
    waiting_for_login = State()
    waiting_for_password = State()


class Info:
    """Variables for throwing"""
    count = 0


async def create_jwt_token(data):
    """Create token"""
    token = jwt.encode({
        **data,
        'exp': datetime.now(timezone.utc) + timedelta(hours=2)
    }, os.getenv("SECRET_KEY"), algorithm='HS256')
    return token


async def decode_jwt_token(token):
    """Decode token"""
    try:
        decoded_data = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=['HS256'])
        return decoded_data
    except jwt.ExpiredSignatureError:
        print("Token has expired.")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token.")
        return None


def token_required(func):
    """Check token"""
    @wraps(func)
    async def wrapper(message: types.Message, state: FSMContext, *args, **kwargs):
        data = await state.get_data()
        token = data.get("jwt_token")
        if not token:
            await message.answer("Нет сохранённого токена. Пройдите авторизацию через /start.")
            return None
        decoded_data = await decode_jwt_token(token)
        if decoded_data:
            return await func(message, state=state, *args, **kwargs)
        else:
            await message.answer("Токен недействителен или истёк. Авторизуйтесь снова.")
            return None
    return wrapper


@dp.message(StateFilter(None), Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    """Start(enter login)"""
    await message.answer("Введите логин:")
    await state.set_state(AuthStates.waiting_for_login)


@dp.message(AuthStates.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    """Start(enter password)"""
    await state.update_data(username=message.text)
    await message.answer("Теперь введите пароль:")
    await state.set_state(AuthStates.waiting_for_password)


def hash_password(password: str) -> str:
    """Hashing password."""
    return hashlib.sha256(password.encode()).hexdigest()


@dp.message(AuthStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    """Authorization"""
    user_data = await state.get_data()
    username = user_data.get('username')
    password = message.text
    tg_id = message.from_user.id
    encoded_password = hash_password(password)
    result = await Repo.select_pass(username, encoded_password, tg_id)
    if not result:
        Info.count += 1
        if Info.count == 3:
            await message.answer(
                text="Неверный пароль. Ты заблокирован на 60 секунд."
            )
            await asyncio.sleep(60)
            await message.answer(
                text="нажми /start"
            )
            Info.count = 0
            await state.clear()
            return

    if result:
        user_payload = {
            'login': result.login,
            'status': result.status,
        }

        token = await create_jwt_token(user_payload)
        Registred.user = result.name
        await state.update_data(jwt_token=token, chat_id=message.chat.id)

        await state.clear()
        await state.update_data(jwt_token=token)
        await message.answer(
            text=f"Добро пожаловать, {result.login}!\nТеперь можешь написать /help."
        )
        return
    await message.answer(text="Не зашло с паролем :(")
    await state.set_state(AuthStates.waiting_for_login)


@dp.message(Command("help"))
@token_required
async def cmd_start(message: types.Message, state: FSMContext):
    """help"""
    await message.answer("".join(lists.helps))


@dp.message(Command("exit"))
@token_required
async def cmd_logout(message: types.Message, state: FSMContext):
    """exit"""
    await state.clear()
    tg_id = message.from_user.id
    await Repo.exit_user_bot(tg_id)
    await message.answer("Вы вышли из системы. Чтобы снова войти, используйте /start.")


@dp.message(F.text, Command('contact'))
@token_required
async def message_handler(msg: Message, state: FSMContext):
    """Contact"""
    await msg.answer(lists.contact)


@dp.message(StateFilter(None), Command("view_azs"))
@token_required
async def view_number_azs(msg: Message, state: FSMContext):
    """Search for gas station by number."""
    await msg.answer(
        text=f"номер АЗС",
        reply_markup=keyboards.make_row_keyboard(["АЗС-52"])
    )
    await state.set_state(SelectInfo.view_azs)


@dp.message(SelectInfo.view_azs)
@token_required
async def select_azs(msg: Message, state: FSMContext):
    """Result search"""
    if msg.text is None:
        await msg.answer(f"Некорректные данные :(")
        await state.clear()
        return
    else:
        number = msg.text.strip()
        if number != '':
            answer = await Repo.select_azs(number)
            try:
                await msg.answer(f"{answer.ip} \n {answer.address} \n {answer.type} \n "
                                 f"{answer.region} \n {answer.comment}")

                response = hlink('Яндекс-карта', f'https://yandex.by/maps/?ll={answer.geo}&z=16')
                await msg.answer(f"{response}")
                await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по АЗС - {number}")
                await state.clear()
            except AttributeError:
                await msg.answer(text=f"Нет такой АЗС :(")
                return


@dp.message(StateFilter(None), Command("view_all_info"))
@token_required
async def view_all_info(msg: Message, state: FSMContext):
    """Search for info about fttx"""
    await msg.answer(
        text=f"адрес через запятую с пробелом ",
        reply_markup=keyboards.make_row_keyboard(["Гомель, Мазурова, 77"])
    )
    await state.set_state(SelectInfo.view_all_fttx)


@dp.message(SelectInfo.view_all_fttx)
@token_required
async def view_all_fttx(msg: Message, state: FSMContext):
    """Result fttx."""
    if msg.text is None:
        await msg.answer(f"Некорректные данные :(")
        await state.clear()
        return
    else:
        temps = msg.text.strip()
        temp = [[temps[0]], [temps[1]], [temps[2]]]
        if len(temp) != 3:
            await msg.answer(f"Некорректные данные  :(")
            await state.clear()
            return
        else:
            answer = await Repo.select_all_info(temps)
            if answer is not None:
                await msg.answer(f"Город: {answer.city} \n Кластер: {answer.claster} \n {answer.street} "
                                 f"{answer.number} \n "
                                 f"{answer.description} \n АСКУЭ: {answer.askue}")
                await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по {answer.city} "
                                                                    f"{answer.street} {answer.number}")
                await state.clear()
            else:
                print('Пустой запрос')
                await msg.answer(text=f"что то не то с адресом :(")
                return


@dp.message(StateFilter(None), Command("view_bs_id"))
@token_required
async def view_number_bs(msg: Message, state: FSMContext):
    """Search for number BS"""
    await msg.answer(
        text=f"номер БС",
        reply_markup=keyboards.make_row_keyboard(["474"])
    )
    await state.set_state(SelectInfo.view_bs_number)


@dp.message(SelectInfo.view_bs_number)
@token_required
async def select_bs_id(msg: Message, state: FSMContext):
    """Result search BS"""
    if msg.text is None:
        await msg.answer(f"Ошибка вводных данных :(")
        await state.clear()
        return
    else:
        number = msg.text.strip()
        answer = await Repo.select_bs_number(number)
        await msg.answer(f"{answer.number}\n{answer.address}\n{answer.comment}")
        await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по БС - {number}")
        await state.clear()
        if answer is None:
            await msg.answer(text=f"Нет такой БС :(")
            await state.clear()
            return
        return


@dp.message(StateFilter(None), Command("add_new_info"))
@token_required
async def add_new_info(msg: Message, state: FSMContext):
    """Added entry in fttx_fttx"""
    await msg.answer(
        text=f"добавить запись в info в формате \n"
                "Номер реестра|Город|Улица|Дом|Квартира|ФИО|К1|К2|К3|коннектор"
    )
    await state.set_state(SelectInfo.add_new_info)


@dp.message(SelectInfo.add_new_info)
@token_required
async def insert_new_info(msg: Message, state: FSMContext):
    """Insert entry in fttx_fttx"""
    info = msg.text.split('|')
    if len(info) != 10:  # или быстрый выход
        await msg.answer(f"Что-то не так с данными :(")
        await state.clear()
        return
    else:
        query = await Repo.insert_info(info)
        if query is not None:
            await msg.answer(f"добавлено!")
            await Repo.insert_into_visited_date(Registred.name, f"Добавил информацию в info_info ")
        else:
            await msg.answer(f"Что-то не так с данными :(")
        await state.clear()
        return


@dp.message(StateFilter(None), Command("update_accident"))
@token_required
async def update_accident(msg: Message, state: FSMContext):
    """Close incident by number"""
    await msg.answer(
        text=f"Инцидент по номеру\n"
                f"Номер|Статус(open, close, check)|Решение "
    )
    await state.set_state(SelectInfo.update_accident)


@dp.message(SelectInfo.update_accident)
@token_required
async def view_accident(msg: Message, state: FSMContext):
    """Result close incident by number"""
    info = msg.text.split('|')
    if len(info) != 3:
        await msg.answer(f"Что-то не так с данными :(")
        await state.clear()
        return
    if info[1] not in lists.status:
        await msg.answer(f"Введён некорректный статус заявки")
        await state.clear()
        return
    if len(info[2]) < 2:
        await msg.answer(f"Добавьте комментарий")
        await state.clear()
        return
    else:
        await Repo.update_accident(info)
        await Repo.insert_into_visited_date(Registred.name, f"Обновил информацию по инциденту {info[0]}")
        answer = await Repo.select_accident_number(info[0])
        await msg.answer(f"Номер:  {answer.number} \nКатегория:  {answer.category} "
                         f"\nСрок ликвидации:  {answer.sla}, \nВремя открытия:  {answer.datetime_open},"
                         f"\nВремя закрытия:  {answer.datetime_close}, \nОписание проблемы:  {convert(answer.problem)},"
                         f"\nГород:  {answer.city}, \nАдрес:  {answer.address},"
                         f"\nФИО:  {answer.name},  \nТелефон: {answer.phone},"
                         f"\nАбонентский номер:  {answer.subscriber}, \nКомментарий:  {convert(answer.comment)},"
                         f"\nРешение:  {convert(answer.decide)}, \nСтатус заявки:  {answer.status} ")
        await state.clear()


@dp.message(StateFilter(None), Command("view_bs_address"))
@token_required
async def view_address_bs(msg: Message, state: FSMContext):
    """Search for BS by street"""
    await msg.answer(
        text=f"адреc БС(улица)",
        reply_markup=keyboards.make_row_keyboard(["Телегина"])
    )
    await state.set_state(SelectInfo.view_bs_address)


@dp.message(SelectInfo.view_bs_address)
@token_required
async def select_bs_ad(msg: Message, state: FSMContext):
    """Result search for BS by street"""
    if msg.text is None:
        await msg.answer(f"Некорректные данные :(")
        await state.clear()
        return
    else:
        street = msg.text.strip()
        if street in lists.block_word:
            await msg.answer(f" Некорректный запрос ")
            await state.clear()
            return
        answer = await Repo.select_bs_address(street)
        if answer is not None:
            for row in answer:
                await msg.answer(f"\n{row.number} \n{row.address} \n{row.comment}  ")
            await Repo.insert_into_visited_date(Registred.name, f"посмотрел Основные команды d-link")
            await state.clear()
        if answer is None:
            await msg.answer(text=f"Нет такой БС :(")
            await state.clear()
            return
        return


@dp.message(StateFilter(None), Command("view_action"))
@token_required
async def view_action_select(msg: Message, state: FSMContext):
    """Latest user requests"""
    await msg.answer(
        text=f"Пользовательские запросы(количество): ",
        reply_markup=keyboards.make_row_keyboard(["15"])
    )
    await state.set_state(SelectInfo.select_action)


@dp.message(SelectInfo.select_action)
@token_required
async def select_action_user(msg: Message, state: FSMContext):
    """Result latest user requests"""
    if msg.text is None:
        await msg.answer(f"Фигня  с данными :(")
        await state.clear()
        return
    else:
        number = msg.text
        if int(number) > 15:
            await msg.answer(f"{number} > 15, попробуй ещё раз :)")
            await state.clear()
            return
        answer = await Repo.select_action(number)
        l = []
        for row in answer:
            l.append(f"{row.login}, {row.action}, {row.date}")
        for row in l:
            await msg.answer(f"{row}")
        await state.clear()
    return


@dp.message(Command("view_man"))
@token_required
async def cmd_random(message: types.Message, state: FSMContext):
    """View manual"""
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="HUAWEI-5100",
        callback_data="1")
    )
    builder.add(types.InlineKeyboardButton(
        text="Ubiquti",
        callback_data="2")
    )
    builder.row(types.InlineKeyboardButton(
        text="D-Link DGS-3000/3120",
        callback_data="3")
    )
    builder.add(types.InlineKeyboardButton(
        text="Cisco точки доступа ",
        callback_data="4")
    )
    builder.row(types.InlineKeyboardButton(
        text="Mikrotik 3G стартовая конфигурация",
        callback_data="5")
    )
    builder.row(types.InlineKeyboardButton(
        text="MikroTik 3G/4G сеть",
        callback_data="6")
    )
    builder.add(types.InlineKeyboardButton(
        text="MikroTik FTTX",
        callback_data="7")
    )
    builder.row(types.InlineKeyboardButton(
        text="Основные команды d-link",
        callback_data="8")
    )
    builder.row(types.InlineKeyboardButton(
        text="Huawei вход через boot-menu",
        callback_data="9")
    )
    await message.answer(
         "Что надо?",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == "1")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info Huawei."""
    answer = await Repo.select_manual(int(1))
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел man по Huawei-5100")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.callback_query(F.data == "2")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info Ubiquti."""
    answer = await Repo.select_manual(2)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по Ubiquti")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.callback_query(F.data == "3")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info D-Link."""
    answer = await Repo.select_manual(3)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по D-Link DGS-3000/3120")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.callback_query(F.data == "4")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info Cisco."""
    answer = await Repo.select_manual(4)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по Cisco точки доступа")
    model = convert(answer.model)
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.callback_query(F.data == "5")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info Mikrotik 3G."""
    answer = await Repo.select_manual(5)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по Mikrotik 3G стартовая конфигурация")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.callback_query(F.data == "6")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info MikroTik 3G/4G."""
    answer = await Repo.select_manual(6)
    await Repo.insert_into_visited_date(Registred.name, f"MikroTik 3G/4G сеть")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.callback_query(F.data == "7")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info MikroTik FTTХ."""
    answer = await Repo.select_manual(7)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по MikroTik FTTХ")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.callback_query(F.data == "8")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info Basic d-link commands."""
    answer = await Repo.select_manual(8)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел Основные команды d-link")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.callback_query(F.data == "9")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View info Basic d-link commands."""
    answer = await Repo.select_manual(9)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел Huawei login via boot-menu")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@dp.message(Command("view_accident"))
@token_required
async def cmd_random(message: types.Message, state: FSMContext):
    """Search accident by status."""
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Открытые инциденты",
        callback_data="open")
    )
    builder.add(types.InlineKeyboardButton(
        text="В статусе проверки",
        callback_data="check")
    )
    builder.row(types.InlineKeyboardButton(
        text="Закрытые инциденты",
        callback_data="close")
    )
    builder.row(types.InlineKeyboardButton(
        text="Посмотреть статистику изменений",
        callback_data="stat")
    )
    await message.answer(
        "варианты запроса",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == "open")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View accident by status Open."""
    answer = await Repo.select_accident("open")
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел открытые заявки ")
    for row in answer:
        await callback.message.answer(f"Номер:  {row.number} \nКатегория:  {row.category} "
                                      f"\nСрок ликвидации:  {row.sla}, \nВремя открытия:  {row.datetime_open},"
                                      f"\nОписание проблемы:  {row.problem},"
                                      f"\nГород:  {row.city}, \nАдрес:  {row.address},"
                                      f"\nФИО:  {row.name},  \nТелефон: +{row.phone},"
                                      f"\nАбонентский номер:  {row.subscriber}, \nКомментарий:  {row.comment},"
                                      f"\nРешение:  {row.decide}, \nСтатус заявки:  {row.status} ")


@dp.callback_query(F.data == "check")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View accident by status Check."""
    answer = await Repo.select_accident("check")
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел заявки в статусе проверки")
    for row in answer:
        await callback.message.answer(f"Номер:  {row.number} \nКатегория:  {row.category} "
                                      f"\nСрок ликвидации:  {row.sla}, \nВремя открытия:  {row.datetime_open},"
                                      f"\nОписание проблемы:  {row.problem},"
                                      f"\nГород:  {row.city}, \nАдрес:  {row.address},"
                                      f"\nФИО:  {row.name},  \nТелефон: +{row.phone},"
                                      f"\nАбонентский номер:  {row.subscriber}, \nКомментарий:  {row.comment},"
                                      f"\nРешение:  {row.decide}, \nСтатус заявки:  {row.status} ")


@dp.callback_query(F.data == "close")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View accident by status Close."""
    answer = await Repo.select_accident("close")
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел заявки в статусе закрыто")
    for row in answer:
        await callback.message.answer(f"Номер:  {row.number} \nКатегория:  {row.category} "
                                      f"\nСрок ликвидации:  {row.sla}, \nВремя открытия:  {row.datetime_open},"
                                      f"\nВремя закрытия:  {row.datetime_close}, \nОписание проблемы:  {row.problem},"
                                      f"\nГород:  {row.city}, \nАдрес:  {row.address},"
                                      f"\nФИО:  {row.name},  \nТелефон: +{row.phone},"
                                      f"\nАбонентский номер:  {row.subscriber}, \nКомментарий:  {row.comment},"
                                      f"\nРешение:  {row.decide}, \nСтатус заявки:  {row.status} ")


@dp.callback_query(F.data == "stat")
@token_required
async def send_random_value(callback: types.CallbackQuery, state: FSMContext):
    """View last 10 incident requests."""
    answer = await Repo.select_stat()
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел последние 10 заявок по инцидентам")
    for row in answer:
        await callback.message.answer(f"Номер:  {row.id} \nКто заходил:  {row.login} "
                                      f"\nДата:  {row.date_created}, \nДействие:  {row.action}"
                                      )


@dp.message(StateFilter(None), Command("view_accident_number"))
@token_required
async def view_accident_number(msg: Message, state: FSMContext):
    """Search accident by number."""
    await msg.answer(
        text=f"номер инцидента",
        reply_markup=keyboards.make_row_keyboard(["148650"])
    )
    await state.set_state(SelectInfo.view_accident)


@dp.message(SelectInfo.view_accident)
@token_required
async def insert_accident_number(msg: Message, state: FSMContext):
    """Result search accident by number."""
    if msg.text is None:
        await msg.answer(f"Что-то не то с данными :(")
        await state.clear()
        return
    else:
        number = msg.text.strip()
        answer = await Repo.select_accident_number(number)
        if answer is None:
            await msg.answer(text=f"Неверный номер :(")
            await state.clear()
            return
        await msg.answer(f"Номер:  {answer.number}, \nКатегория:  {answer.category}, "
                         f"\nСрок ликвидации:  {answer.sla}, \nВремя открытия:  {answer.datetime_open},"
                         f"\nВремя закрытия:  {answer.datetime_close}, \nОписание проблемы:  {convert(answer.problem)},"
                         f"\nГород:  {answer.city}, \nАдрес:  {answer.address},"
                         f"\nФИО:  {answer.name},  \nТелефон: +{answer.phone},"
                         f"\nАбонентский номер:  {answer.subscriber}, \nКомментарий:  {convert(answer.comment)},"
                         f"\nРешение:  {convert(answer.decide)}, \nСтатус заявки:  {answer.status} ")
        await state.clear()
        await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по инциденту - {number}")
        await state.clear()
        return


async def create_chart(temp):
    """Create graph."""
    result_query = dict()
    list_query = []
    set_street = set()
    tmz = pytz.timezone('Europe/Moscow')
    end_date = datetime.now(tmz)
    start_date = datetime(end_date.year, 1, 1)
    conn = psycopg2.connect(host=os.getenv("host"), port=os.getenv("port"), user=os.getenv("user"),
                            password=os.getenv("password"), database=os.getenv("database"))
    plt.figure(figsize=(25, 18))
    with conn.cursor() as cursor:
        query = "SELECT DISTINCT street FROM info_info WHERE date_created BETWEEN %s AND %s"
        cursor.execute(query, (start_date, end_date))
        result = cursor.fetchall()
        for row in result:
            set_street.add(*row)
        sorted_street = sorted(set_street)
        for query, row in enumerate(sorted_street):
            cursor = conn.cursor()
            query = "SELECT street FROM info_info WHERE date_created BETWEEN %s AND %s AND street = %s "
            cursor.execute(query, (start_date, end_date, row))
            result = cursor.fetchall()
            for rows in result:
                result_query[rows] = result_query.get(rows, 0) + 1
            list_query = [[key, value] for key, value in result_query.items()]
        plt.minorticks_on()
        plt.grid(which='major')
        plt.grid(which='minor', linestyle='-.')
        plt.tight_layout()
        plt.xlabel('Ось X', labelpad=80)
        plt.ylabel('Ось Y', labelpad=80)
        plt.title(str(end_date), pad=20)
        plt.tight_layout()
        if temp == 'bar':
            d = OrderedDict(sorted(list_query, key=lambda x: x[0]))
            values = list(d.values())
            plt.bar(range(len(d)), values, color='purple',
                    tick_label=sorted_street)
            axes = plt.subplot(1, 1, 1)
            axes.tick_params(axis='x', labelrotation=55)
        if temp == 'gorizontal':
            d = OrderedDict(sorted(list_query, key=lambda x: x[0]))
            values = list(d.values())
            plt.barh(range(len(d)), values, tick_label=sorted_street)
        if temp == 'ring':
            list_explode = []
            d = OrderedDict(sorted(list_query, key=lambda x: x[0]))
            values = list(d.values())
            for row in range(len(list_query)):
                list_explode.append(round(random.random() / 3, 4))
            plt.pie(values, labels=sorted_street, autopct='%1.1f%%',
                    explode=list_explode, rotatelabels=False)
        if temp == 'pie':
            list_explode = []
            d = OrderedDict(sorted(list_query, key=lambda x: x[0]))
            values = list(d.values())
            for row in range(len(list_query)):
                list_explode.append(round(random.random() / 3, 4))
            plt.pie(values, labels=sorted_street, autopct='%1.1f%%',
                    explode=list_explode, rotatelabels=False, shadow=False, wedgeprops=dict(width=0.5))
    chart_path = 'chart.png'
    plt.savefig(chart_path)
    plt.close()
    cursor.close()
    return chart_path


@dp.message(Command("charts"))
@token_required
async def cmd_random(message: types.Message, state: FSMContext):
    """Request to create a graph."""
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="chart BAR",
        callback_data="bar")
    )
    builder.row(types.InlineKeyboardButton(
        text="chart Gorizontal",
        callback_data="gorizontal")
    )
    builder.add(types.InlineKeyboardButton(
        text="chart Ring",
        callback_data="ring")
    )
    builder.row(types.InlineKeyboardButton(
        text="chart PIE",
        callback_data="pie")
    )

    await message.answer(
        "Что смотрим?",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == "pie")
@token_required
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Result graph PIE."""
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел график PIE")
    temp = "pie"
    chart_path = await create_chart(temp)
    with open(chart_path, 'rb') as file:
        photo = BufferedInputFile(file.read(), 'круговая диаграмма')
        await callback.message.answer_photo(photo)
    os.remove(chart_path)


@dp.callback_query(F.data == "gorizontal")
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Result graph Gorizontal."""
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел график Gorizontal")
    temp = "gorizontal"
    chart_path = await create_chart(temp)
    with open(chart_path, 'rb') as file:
        photo = BufferedInputFile(file.read(), 'круговая диаграмма')
        await callback.message.answer_photo(photo)
    os.remove(chart_path)


@dp.callback_query(F.data == "ring")
@token_required
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Result graph RING."""
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел график RING")
    temp = "ring"
    chart_path = await create_chart(temp)
    with open(chart_path, 'rb') as file:
        photo = BufferedInputFile(file.read(), 'круговая диаграмма')
        await callback.message.answer_photo(photo)
    os.remove(chart_path)


@dp.callback_query(F.data == "bar")
@token_required
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Result graph BAR."""
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел график BAR")
    temp = "bar"
    chart_path = await create_chart(temp)
    with open(chart_path, 'rb') as file:
        photo = BufferedInputFile(file.read(), 'круговая диаграмма')
        await callback.message.answer_photo(photo)
    os.remove(chart_path)


# недокументированный запрос(скрыт в lists)
@dp.message(Command("view_tracks"))
@token_required
async def cmd_random(message: types.Message, state: FSMContext):
    """View routes."""
    builder = InlineKeyboardBuilder()

    builder.row(types.InlineKeyboardButton(
        text=os.getenv("PATH_TO_CLUSTER_1"),
        callback_data="fttx_1")
    )
    builder.row(types.InlineKeyboardButton(
        text=os.getenv("PATH_TO_CLUSTER_2"),
        callback_data="fttx_2")
    )
    builder.row(types.InlineKeyboardButton(
        text=os.getenv("PATH_TO_CLUSTER_3"),
        callback_data="fttx_3")
    )
    builder.row(types.InlineKeyboardButton(
        text=os.getenv("PATH_TO_CLUSTER_4"),
        callback_data="fttx_4")
    )

    builder.row(types.InlineKeyboardButton(
        text=os.getenv("PATH_TO_CLUSTER_5"),
        callback_data="fttx_5")
    )

    await message.answer(
        "Что надо?",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == "fttx_1")
@token_required
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Route to fttx cluster 1 search result."""
    with open(f'{os.getcwd()}/image/fttx_1.png', 'rb') as file:
        photo = BufferedInputFile(file.read(), 'any_filename')
    await callback.message.answer_photo(photo)


@dp.callback_query(F.data == "fttx_2")
@token_required
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Route to fttx cluster 2 search result."""
    with open(f'{os.getcwd()}/image/fttx_2.png', 'rb') as file:
        photo = BufferedInputFile(file.read(), 'any_filename')
    await callback.message.answer_photo(photo)


@dp.callback_query(F.data == "fttx_3")
@token_required
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Route to fttx cluster 3 search result."""
    with open(f'{os.getcwd()}/image/fttx_3.png', 'rb') as file:
        photo = BufferedInputFile(file.read(), 'any_filename')
    await callback.message.answer_photo(photo)


@dp.callback_query(F.data == "fttx_4")
@token_required
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Route to fttx cluster 4 search result."""
    with open(f'{os.getcwd()}/image/fttx_4.png', 'rb') as file:
        photo = BufferedInputFile(file.read(), 'any_filename')
    await callback.message.answer_photo(photo)


@dp.callback_query(F.data == "fttx_5")
@token_required
async def send_current_graf(callback: types.CallbackQuery, state: FSMContext):
    """Route to fttx cluster 5 search result."""
    with open(f'{os.getcwd()}/image/fttx_5.png', 'rb') as file:
        photo = BufferedInputFile(file.read(), 'any_filename')
    await callback.message.answer_photo(photo)
# end недокументированный запрос


@dp.message(Command("exit"))
async def cmd_logout(message: types.Message, state: FSMContext):
    """Exit"""
    await state.clear()
    tg_id = message.from_user.id
    await Repo.exit_user_bot(tg_id)
    await message.answer("Вы вышли из системы. Чтобы снова войти, используйте /start.")


async def main():
    """Start"""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
