import os
from dotenv import load_dotenv
load_dotenv()

helps = [
        "/help - мануал по боту\n",
        "/contact - контактная информация\n",
        "/view_azs - посмотреть автозаправки Газпром\n",
        "/view_bs_id - посмотреть БС по номеру\n",
        "/view_bs_address - посмотреть БС по адресу\n",
        "/view_all_info - посмотреть данные fttx\n",
        "/view_man - посмотреть manual\n",
        "/add_new_info - добавить в info\n",
        "/view_accident - посмотреть инциденты по статусу\n",
        "/view_accident_number - посмотреть инциденты номеру\n",
        "/update_accident - обновить инцидент по номеру\n",
        "/charts - графики\n",
        # "/view_tracks - трассы\n",
        "/view_key - ключи\n",
        "/view_stat - посмотреть статистику\n",
        "/view_old - выборка за последние 5 лет\n"
        "/exit - выход",
        ]

block_word = [
    "Гомель", "Минск", "Гродно", "Витебск", "Могилёв", "Брест"
]

contact = os.getenv('CONTACT')
