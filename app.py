import asyncio
from itertools import zip_longest

from redis.asyncio import Redis

from datetime import datetime, timedelta, timezone
import hashlib
import os
from functools import wraps

import jwt
from html2markdown import convert

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hlink
from aiogram.fsm.storage.redis import RedisStorage

import graph
import keyboards
import lists
from repository import Repo

from dotenv import load_dotenv
load_dotenv()

import logging
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))

redis_client = Redis(host="localhost", port=6379, db=0, decode_responses=True)
storage = RedisStorage(redis=redis_client)
dp = Dispatcher(storage=storage)

class AuthStates(StatesGroup):
    """States for authentication and output"""
    waiting_for_login = State()
    waiting_for_password = State()

class SelectInfo(StatesGroup):
    """FSM StatesGroup for managing user states when interacting with a bot."""
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
    """User name"""
    name = None

class Info:
    """Login Attempt Counter"""
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
        logger.error("[ERROR]Token has expired.")
        return None
    except jwt.InvalidTokenError:
        logger.error("[ERROR]Invalid token.")
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
        Registred.name = result.name
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
    status = Repo.select_type_accident()
    info = msg.text.split('|')
    if len(info) != 3:
        await msg.answer(f"Что-то не так с данными :(")
        await state.clear()
        return
    if info[1] not in status:
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
                await Repo.insert_into_visited_date(Registred.name, f"Посмотрел данные по БС {row.number}")
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
        await msg.answer(f"Некорректные данные :(")
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
async def view_man(message: types.Message, state: FSMContext):
    manuals = await Repo.select_type_manual()
    await state.update_data(manuals=manuals)
    builder = InlineKeyboardBuilder()
    for left, right in zip_longest(manuals[::2], manuals[1::2]):
        buttons = []
        if left:
            buttons.append(types.InlineKeyboardButton(text=left, callback_data=f"manual:{left}"))
        if right:
            buttons.append(types.InlineKeyboardButton(text=right, callback_data=f"manual:{right}"))
        builder.row(*buttons)

    await message.answer("Что надо?", reply_markup=builder.as_markup())


@dp.callback_query(lambda c: c.data.startswith("manual:"), token_required)
async def send_manual_value(callback: types.CallbackQuery, state: FSMContext):
    manual_name = callback.data[len("manual:"):]
    data = await state.get_data()
    manuals = data.get("manuals")
    if not manuals:
        await callback.message.answer("Не удалось загрузить список мануалов.")
        return
    try:
        manual_index = manuals.index(manual_name)
    except ValueError:
        await callback.message.answer("Выбранное руководство не найдено.")
        return
    answer = await Repo.select_manual(manual_index + 1)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел man по {manual_name}")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n{description}")


@dp.message(Command("view_accident"))
@token_required
async def view_accident(message: types.Message, state: FSMContext):
    """Search accident by status."""
    type_of_accident = await Repo.select_type_accident()
    builder = InlineKeyboardBuilder()

    for left, right in zip_longest(type_of_accident[::2], type_of_accident[1::2]):
        buttons = []
        if left:
            buttons.append(types.InlineKeyboardButton(text=f"Инцидент: {left}", callback_data=f"accident:{left}"))
        if right:
            buttons.append(types.InlineKeyboardButton(text=f"Инцидент: {right}", callback_data=f"accident:{right}"))
        builder.row(*buttons)

    await message.answer(
        "варианты запроса",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith("accident:"))
@token_required
async def view_status_accident(callback: types.CallbackQuery, state: FSMContext):
    """View accident by status."""
    type_of_accident = callback.data.split(":")[1]

    answer = await Repo.select_accident(type_of_accident)
    await Repo.insert_into_visited_date(Registred.name, f"Посмотрел заявки в статусе {type_of_accident}")

    for row in answer:
        await callback.message.answer(
            f"Номер:  {row.number} \nКатегория:  {row.category} "
            f"\nСрок ликвидации:  {row.sla}, \nВремя открытия:  {row.datetime_open},"
            f"\nОписание проблемы:  {row.problem},"
            f"\nГород:  {row.city}, \nАдрес:  {row.address},"
            f"\nФИО:  {row.name},  \nТелефон: +{row.phone},"
            f"\nАбонентский номер:  {row.subscriber}, \nКомментарий:  {row.comment},"
            f"\nРешение:  {row.decide}, \nСтатус заявки:  {row.status} "
        )


@dp.message(Command("view_stat"))
@token_required
async def view_stat(message: types.Message, state: FSMContext):
    """View action statistics."""
    answer = await Repo.select_stat()
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел последние 10 заявок по инцидентам")
    for row in answer:
        await message.answer(f"Номер:  {row.id} \nКто заходил:  {row.login} "
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


@dp.message(Command("charts"))
@token_required
async def charts(message: types.Message, state: FSMContext):
    """Request to create a graph."""
    types_of_graph = ["bar", "pie", "gorizontal", "ring"]
    builder = InlineKeyboardBuilder()
    for left, right in zip_longest(types_of_graph[::2], types_of_graph[1::2]):
        buttons = []
        if left:
            buttons.append(types.InlineKeyboardButton(text=f"График: {left}", callback_data=left))
        if right:
            buttons.append(types.InlineKeyboardButton(text=f"График: {right}", callback_data=right))
        builder.row(*buttons)

    await message.answer(
        "Что смотрим?",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(lambda c: c.data in ["bar", "pie", "gorizontal", "ring"])
@token_required
async def send_chart(callback: types.CallbackQuery, state: FSMContext):
    """Send selected chart image."""
    chart_type = callback.data
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел график {chart_type}")
    chart_path = await graph.create_chart(chart_type)
    try:
        with open(chart_path, 'rb') as file:
            photo = BufferedInputFile(file.read(), f'{chart_type}.png')
            await callback.message.answer_photo(photo)
    finally:
        os.remove(chart_path)

# недокументированный запрос(скрыт в lists)
@dp.message(Command("view_tracks"))
@token_required
async def view_routes(message: types.Message, state: FSMContext):
    """View routes."""
    builder = InlineKeyboardBuilder()

    for i in range(1, 6):
        builder.row(types.InlineKeyboardButton(
            text=os.getenv(f"PATH_TO_CLUSTER_{i}"),
            callback_data=f"fttx_{i}")
        )

    await message.answer(
        "Что надо?",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(lambda c: c.data and c.data.startswith("fttx_"))
@token_required
async def view_tracks(callback: types.CallbackQuery, state: FSMContext):
    cluster_number = callback.data.split("_")[1]
    image_path = f'{os.getcwd()}/image/fttx_{cluster_number}.png'
    try:
        with open(image_path, 'rb') as file:
            photo = BufferedInputFile(file.read(), 'any_filename.png')
        await callback.message.answer_photo(photo)
    except FileNotFoundError:
        await callback.message.answer(f"Изображение fttx_{cluster_number} не найдено.")
# end недокументированный запрос


@dp.message(Command("exit"))
@token_required
async def cmd_logout(message: types.Message, state: FSMContext):
    """exit"""
    await state.clear()
    tg_id = message.from_user.id
    await Repo.exit_user_bot(tg_id)
    Registred.name = None
    await message.answer("Вы вышли из системы. Чтобы снова войти, используйте /start.")


async def main():
    """Start"""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
