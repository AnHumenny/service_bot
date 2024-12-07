import random
from collections import OrderedDict
import psycopg2
from aiogram import types, F, Router, Bot
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import as_list
from aiogram.utils.keyboard import InlineKeyboardBuilder
import base64
from aiogram.utils.markdown import hlink
import lists
from aiogram.fsm.state import StatesGroup, State
from html2markdown import convert
import keyboards
from repository import Repo
from time import sleep
import os
import matplotlib.pyplot as plt
from datetime import datetime
import pytz
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
host = os.getenv('host')
port = os.getenv('port')
user = os.getenv('user')
password = os.getenv('password')
database = os.getenv('database')

router = Router()

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
    admin_OK = False
    user_OK = False
    login = None
    name = None
    count = 0


@router.message(StateFilter(None), Command("start"))
async def start_handler(msg: Message, state=FSMContext):
    await msg.answer("Привет! \n")
    await msg.answer(
        text="Знаешь как зайти? :)",
        reply_markup=keyboards.make_row_keyboard(['xxxxx'])
    )
    await state.set_state(SelectInfo.register_user)


# ввод и проверка пароля
@router.message(SelectInfo.register_user)
async def cmd_auth(msg: Message, state: FSMContext):
    if Registred.count > 3:
        Registred.count = 0
    bots = Bot(token=API_TOKEN)
    autent = msg.text.split('|')
    if len(autent) != 2:
        Registred.count += 1
        await msg.answer(
            text=f"Что то за не то с паролем :("
        )
        print("count", Registred.count)
        if Registred.count == 3:
            await msg.answer(
                text="Теперь ждём минуту :("
            )
            await Repo.insert_into_visited_date(msg.from_user.id, f"{msg.from_user.id} три некорректные авторизации :)")
            sleep(60)
            print("count", Registred.count)
            sleep(60)
        return
    else:
        Registred.count += 1
        auth = msg.text.split("|")
        login = auth[0]
        pswrd = auth[1]
        pass_wrd = pswrd.encode('utf-8')
        pswrd = base64.b64encode(pass_wrd)
        if len(login) == 0 or len(pswrd) < 7:
            await msg.answer(
                text=f"Что то не получилось с паролем :("
            )
            print("count", Registred.count)
            if Registred.count == 3:
                await msg.answer(
                    text="Теперь ждём минуту :("
                )
                await Repo.insert_into_visited_date(msg.from_user.id, f"{msg.from_user.id} три неверных пароля :)")
                sleep(60)
            await state.clear()
            return
        else:
            result = await Repo.select_pass(login, pswrd, msg.from_user.id)
            if result is None:
                await msg.answer(
                    text=f"Не зашло с паролем :("
                )
                Registred.count += 1
                if Registred.count == 3:
                    await msg.answer(
                        text="Теперь ждём минуту :("
                    )
                    await Repo.insert_into_visited_date(msg.from_user.id, f"{msg.from_user.id} три хаотичных пароля :)")
                    sleep(60)
                    await state.clear()
                    return
            else:
                if result.tg_id not in lists.access:
                    await msg.answer(
                        text=f"Упс. Что то не так с данными :("
                    )
                    return
                if result.status == "admin":
                    Registred.admin_OK = True
                if result.tg_id in lists.access:
                    Registred.user_OK = True
                    Registred.login = result.login
                    Registred.name = result.name
                    await Repo.insert_into_visited_date(Registred.name, f"зашёл в чат ")
                await msg.answer(
                    text=f"Набери\n/help, {result.name}"
                )
                await bots.send_message(os.getenv("id_admin"), 'В бот зашёл ' + result.name)  # ошибка незакрытой сессии
                await state.clear()
                return


# мануал
@router.message(F.text, Command("help"))
async def cmd_help(msg: Message):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await msg.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        content = as_list(*lists.helps)
        await msg.answer(**content.as_kwargs())
        # if Registred.admin_OK is True:            #пока лочим, неактуально
        #     content = as_list(*lists.adm_help)
        #     await msg.answer(**content.as_kwargs())


# список контактов по МТС
@router.message(F.text, Command('contact'))
async def message_handler(msg: Message):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await msg.answer(
            text=f"недостаточно прав доступа :("
        )
        return
    else:
        content = as_list(*lists.contact)
        await msg.answer(**content.as_kwargs())


# поиск АЗС по номеру
@router.message(StateFilter(None), Command("view_azs"))
async def view_number_azs(msg: Message, state: FSMContext):
    if Registred.login in lists.id_user and Registred.user_OK is True:  # проверка статуса
        await msg.answer(
            text=f"номер АЗС",
            reply_markup=keyboards.make_row_keyboard(["АЗС-52"])
        )
        await state.set_state(SelectInfo.view_azs)
    else:
        await msg.answer(
            text=f"недостаточно прав доступа :(",
        )
        return
    await state.set_state(SelectInfo.view_azs)


@router.message(SelectInfo.view_azs)
async def select_azs(msg: Message, state: FSMContext):
    if msg.text is None:
        await msg.answer(f"Фигня  с данными :(")
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


# поиск инфы по fttx
@router.message(StateFilter(None), Command("view_all_info"))
async def view_all_info(msg: Message, state: FSMContext):
    if Registred.login in lists.id_user and Registred.user_OK is True:  # проверка статуса
        await msg.answer(
            text=f"адрес через запятую с пробелом ",
            reply_markup=keyboards.make_row_keyboard(["Гомель, Мазурова, 77"])
        )
        await state.set_state(SelectInfo.view_all_fttx)
    else:
        await msg.answer(
            text=f"недостаточно прав доступа :(",
        )
        return
    await state.set_state(SelectInfo.view_all_fttx)


@router.message(SelectInfo.view_all_fttx)
async def select_azs(msg: Message, state: FSMContext):
    if msg.text is None:
        await msg.answer(f"Фигня  с данными :(")
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


# поиск BS по number
@router.message(StateFilter(None), Command("view_bs_id"))
async def view_namber_bs(msg: Message, state: FSMContext):
    if Registred.login in lists.id_user and Registred.user_OK is True:  # проверка статуса
        await msg.answer(
            text=f"номер БС",
            reply_markup=keyboards.make_row_keyboard(["474"])
        )
        await state.set_state(SelectInfo.view_bs_number)
    else:
        await msg.answer(
            text=f"недостаточно прав доступа :(",
        )
        return
    await state.set_state(SelectInfo.view_bs_number)


@router.message(SelectInfo.view_bs_number)
async def select_bs_id(msg: Message, state: FSMContext):
    if msg.text is None:
        await msg.answer(f"Фигня  с данными :(")
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


# добавить запись в info
@router.message(StateFilter(None), Command("add_new_info"))
async def add_new_info(msg: Message, state: FSMContext):
    if Registred.login in lists.id_user and Registred.user_OK is True:  # проверка статуса
        await msg.answer(
            text=f"добавить запись в info в формате \n"
                 "Номер реестра|Город|Улица|Дом|Квартира|ФИО|К1|К2|К3|коннектор"
        )
        await state.set_state(SelectInfo.add_new_info)
    else:
        await msg.answer(
            text=f"недостаточно прав доступа :(",
        )
        return
    await state.set_state(SelectInfo.add_new_info)


@router.message(SelectInfo.add_new_info)
async def insert_new_info(msg: Message, state: FSMContext):
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


# закрыть инцидент по номеру
@router.message(StateFilter(None), Command("update_accident"))
async def update_accident(msg: Message, state: FSMContext):
    if Registred.login in lists.id_user and Registred.user_OK is True:  # проверка статуса
        await msg.answer(
            text=f"Инцидент по номеру\n"
                 f"Номер|Статус(open, close, check)|Решение "
        )
        await state.set_state(SelectInfo.update_accident)
    else:
        await msg.answer(
            text=f"недостаточно прав доступа :(",
        )
        return
    await state.set_state(SelectInfo.update_accident)


@router.message(SelectInfo.update_accident)
async def view_accident(msg: Message, state: FSMContext):
    info = msg.text.split('|')
    if len(info) != 3:  # или быстрый выход
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


# поиск BS по street
@router.message(StateFilter(None), Command("view_bs_address"))
async def view_address_bs(msg: Message, state: FSMContext):
    if Registred.login in lists.id_user and Registred.user_OK is True:  # проверка статуса
        await msg.answer(
            text=f"адреc БС(улица)",
            reply_markup=keyboards.make_row_keyboard(["Телегина"])
        )
        await state.set_state(SelectInfo.view_bs_address)
    else:
        await msg.answer(
            text=f"недостаточно прав доступа :(",
        )
        return
    await state.set_state(SelectInfo.view_bs_address)


@router.message(SelectInfo.view_bs_address)
async def select_bs_ad(msg: Message, state: FSMContext):
    if msg.text is None:
        await msg.answer(f"Фигня  с данными :(")
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


# выборка действий пользователя
@router.message(StateFilter(None), Command("view_action"))
async def view_action_select(msg: Message, state: FSMContext):
    print('help', Registred.login, Registred.user_OK)
    if Registred.login in lists.log_admin and Registred.admin_OK is True:  # проверка статуса
        await msg.answer(
            text=f"Пользовательские запросы(количество): ",
            reply_markup=keyboards.make_row_keyboard(["15"])
        )
        await state.set_state(SelectInfo.select_action)
    else:
        await msg.answer(
            text=f"недостаточно прав доступа :(",
        )
        return
    await state.set_state(SelectInfo.select_action)


@router.message(SelectInfo.select_action)
async def select_action_user(msg: Message, state: FSMContext):
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


@router.message(Command("view_man"))
async def cmd_random(message: types.Message):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await message.answer(
            text=f"недостаточно прав доступа :("
        )
        return
    else:
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


@router.callback_query(F.data == "1")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(int(1))
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел man по Huawei-5100")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@router.callback_query(F.data == "2")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(2)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по Ubiquti")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@router.callback_query(F.data == "3")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(3)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по D-Link DGS-3000/3120")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@router.callback_query(F.data == "4")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(4)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по Cisco точки доступа")
    model = convert(answer.model)
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@router.callback_query(F.data == "5")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(5)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по Mikrotik 3G стартовая конфигурация")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@router.callback_query(F.data == "6")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(6)
    await Repo.insert_into_visited_date(Registred.name, f"MikroTik 3G/4G сеть")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@router.callback_query(F.data == "7")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(7)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел данные по MikroTik FTTХ")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@router.callback_query(F.data == "8")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(8)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел Основные команды d-link")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


@router.callback_query(F.data == "9")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_manual(9)
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел Huawei вход через boot-menu")
    model = answer.model
    description = convert(answer.description)
    await callback.message.answer(f"{model} \n {description}")


# выборка открытых инцидентов
@router.message(Command("view_accident"))
async def cmd_random(message: types.Message):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await message.answer(
            text=f"недостаточно прав доступа :("
        )
        return
    else:
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


@router.callback_query(F.data == "open")
async def send_random_value(callback: types.CallbackQuery):
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


@router.callback_query(F.data == "check")
async def send_random_value(callback: types.CallbackQuery):
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


@router.callback_query(F.data == "close")
async def send_random_value(callback: types.CallbackQuery):
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


@router.callback_query(F.data == "stat")
async def send_random_value(callback: types.CallbackQuery):
    answer = await Repo.select_stat()
    await Repo.insert_into_visited_date(Registred.name, f"посмотрел последние 10 заявок по инцидентам")
    for row in answer:
        await callback.message.answer(f"Номер:  {row.id} \nКто заходил:  {row.login} "
                                      f"\nДата:  {row.date_created}, \nДействие:  {row.action}"
                                      )


# поиск инцидента по номеру
@router.message(StateFilter(None), Command("view_accident_number"))
async def view_accident_number(msg: Message, state: FSMContext):
    if Registred.login in lists.id_user and Registred.user_OK is True:  # проверка статуса
        await msg.answer(
            text=f"номер инцидента",
            reply_markup=keyboards.make_row_keyboard(["148650"])
        )
        await state.set_state(SelectInfo.view_accident)
    else:
        await msg.answer(
            text=f"недостаточно прав доступа :(",
        )
        return
    await state.set_state(SelectInfo.view_accident)


@router.message(SelectInfo.view_accident)
async def insert_accident_number(msg: Message, state: FSMContext):
    if msg.text is None:
        await msg.answer(f"Фигня  с данными :(")
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


# создание графика
def create_chart(temp):
    result_query = dict()
    list_query = []
    set_street = set()
    timezone = pytz.timezone('Europe/Moscow')
    end_date = datetime.now(timezone)
    start_date = datetime(end_date.year, 1, 1)
    conn = psycopg2.connect(host=host, port=port, user=user,
                            password=password, database=database)
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
                result_query[rows] = result_query.get(rows, 0) + 1  # в словарь result_query
            list_query = [[key, value] for key, value in result_query.items()]
        plt.minorticks_on()
        plt.grid(which='major')  # включаем основную сетк
        plt.grid(which='minor', linestyle='-.')  # включаем дополнительную сетку
        plt.tight_layout()
        plt.xlabel('Ось X', labelpad=80)  # Увеличиваем отступ для метки оси X
        plt.ylabel('Ось Y', labelpad=80)  # Увеличиваем отступ для метки оси Y
        plt.title(str(end_date), pad=20)  # Увеличиваем отступ для заголовка
        plt.tight_layout()  # Оптимизируем расположение элементов графика
        if temp == 'bar':
            d = OrderedDict(sorted(list_query, key=lambda x: x[0]))  # вертикальная диаграмма
            values = list(d.values())  # столбчатая диаграмма
            plt.bar(range(len(d)), values, color='purple',
                    tick_label=sorted_street)
            axes = plt.subplot(1, 1, 1)
            axes.tick_params(axis='x', labelrotation=55)
        if temp == 'gorizontal':
            d = OrderedDict(sorted(list_query, key=lambda x: x[0]))  # столбчатая диаграмма
            values = list(d.values())  # столбчатая диаграмма
            plt.barh(range(len(d)), values, tick_label=sorted_street)  # горизонтальная диаграмма
        if temp == 'ring':
            list_explode = []
            d = OrderedDict(sorted(list_query, key=lambda x: x[0]))  # круговая диаграмма
            values = list(d.values())
            for row in range(len(list_query)):
                list_explode.append(round(random.random() / 3, 4))  # случайное расстояние между долями
            plt.pie(values, labels=sorted_street, autopct='%1.1f%%',
                    explode=list_explode, rotatelabels=False)
        if temp == 'pie':
            list_explode = []
            d = OrderedDict(sorted(list_query, key=lambda x: x[0]))  # кольцевая диаграмма
            values = list(d.values())
            for row in range(len(list_query)):
                list_explode.append(round(random.random() / 3, 4))  # случайное расстояние между долями
            plt.pie(values, labels=sorted_street, autopct='%1.1f%%',
                    explode=list_explode, rotatelabels=False, shadow=False, wedgeprops=dict(width=0.5))
    chart_path = 'chart.png'
    plt.savefig(chart_path)
    plt.close()
    cursor.close()
    return chart_path


@router.message(Command("charts"))
async def cmd_random(message: types.Message):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await message.answer(
            text=f"недостаточно прав доступа :("
        )
        return
    else:
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


@router.callback_query(F.data == "pie")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        await Repo.insert_into_visited_date(Registred.name, f"посмотрел график PIE")
        temp = "pie"
        chart_path = create_chart(temp)
        with open(chart_path, 'rb') as file:
            photo = BufferedInputFile(file.read(), 'круговая диаграмма')
            await callback.message.answer_photo(photo)
        os.remove(chart_path)


@router.callback_query(F.data == "gorizontal")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        await Repo.insert_into_visited_date(Registred.name, f"посмотрел график Gorizontal")
        temp = "gorizontal"
        chart_path = create_chart(temp)
        with open(chart_path, 'rb') as file:
            photo = BufferedInputFile(file.read(), 'круговая диаграмма')
            await callback.message.answer_photo(photo)
        os.remove(chart_path)


@router.callback_query(F.data == "ring")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        await Repo.insert_into_visited_date(Registred.name, f"посмотрел график RING")
        temp = "ring"
        chart_path = create_chart(temp)
        with open(chart_path, 'rb') as file:
            photo = BufferedInputFile(file.read(), 'круговая диаграмма')
            await callback.message.answer_photo(photo)
        os.remove(chart_path)


@router.callback_query(F.data == "bar")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        await Repo.insert_into_visited_date(Registred.name, f"посмотрел график BAR")
        temp = "bar"
        chart_path = create_chart(temp)
        with open(chart_path, 'rb') as file:
            photo = BufferedInputFile(file.read(), 'круговая диаграмма')
            await callback.message.answer_photo(photo)
        os.remove(chart_path)


# недокументированный запрос(отсутствует в lists)
@router.message(Command("view_tracks"))
async def cmd_random(message: types.Message):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await message.answer(
            text=f"недостаточно прав доступа :("
        )
        return
    else:
        builder = InlineKeyboardBuilder()

        builder.row(types.InlineKeyboardButton(
            text="Кожара 65 > Мазурова > Головацкого > Кожара 59/2",
            callback_data="fttx_1")
        )
        builder.row(types.InlineKeyboardButton(
            text="Кожара 61 > Головацкого > Мазурова 40",
            callback_data="fttx_2")
        )
        builder.row(types.InlineKeyboardButton(
            text="Мазурова 117/А > Головацкого > Мазурова 59/3",
            callback_data="fttx_3")
        )
        builder.row(types.InlineKeyboardButton(
            text="Мазурова 111 > Бородина > Мазурова 73",
            callback_data="fttx_4")
        )

        builder.row(types.InlineKeyboardButton(
            text="Мазурова 14 > Головацкого > Хатаевича > Мазурова 16 ",
            callback_data="fttx_5")
        )

        await message.answer(
            "Что надо?",
            reply_markup=builder.as_markup()
        )


@router.callback_query(F.data == "fttx_1")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        print("путь к директории: ", os.getcwd())
        with open(f'{os.getcwd()}/image/fttx_1.png', 'rb') as file:
            photo = BufferedInputFile(file.read(), 'any_filename')
        await callback.message.answer_photo(photo)


@router.callback_query(F.data == "fttx_2")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        with open(f'{os.getcwd()}/image/fttx_2.png', 'rb') as file:
            photo = BufferedInputFile(file.read(), 'any_filename')
        await callback.message.answer_photo(photo)


@router.callback_query(F.data == "fttx_3")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        with open(f'{os.getcwd()}/image/fttx_3.png', 'rb') as file:
            photo = BufferedInputFile(file.read(), 'any_filename')
        await callback.message.answer_photo(photo)


@router.callback_query(F.data == "fttx_4")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        with open(f'{os.getcwd()}/image/fttx_4.png', 'rb') as file:
            photo = BufferedInputFile(file.read(), 'any_filename')
        await callback.message.answer_photo(photo)


@router.callback_query(F.data == "fttx_5")
async def send_current_graf(callback: types.CallbackQuery):
    if Registred.login not in lists.id_user and Registred.user_OK is False:  # проверка статуса
        await callback.message.answer(
            text=f"Увы. Нет доступа к внутренней информации :("
        )
        return
    else:
        with open(f'{os.getcwd()}/image/fttx_5.png', 'rb') as file:
            photo = BufferedInputFile(file.read(), 'any_filename')
        await callback.message.answer_photo(photo)
# end недокументированный запрос
