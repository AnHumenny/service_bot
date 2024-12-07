from dotenv import load_dotenv
import os
load_dotenv()

helps = ["/help - мануал по боту\n",
        "/contact - контактная информация\n",
        "/view_azs - посмотреть автозаправки Газпром\n",
        "/view_bs_id - посмотреть БС по номеру\n",
        "/view_bs_address - посмотреть БС по адресу\n",
        "/view_all_info - посмотреть данные fttx\n",
        "/view_man - посмотреть manual\n",
        "/add_new_info - добавить в info\n",
        "/update_accident - обновить инцидент по номеру\n",
        "/charts - графики\n",
        "/view_accident - посмотреть инциденты\n",
        "/view_accident_number - посмотреть инциденты номеру\n",
      #   "/view_tracks - трассы"
        ]
status = ["open", "close", "check"]

block_word = [
    "Гомель", "Минск", "Гродно", "Витебск", "Могилёв", "Брест"
]

contact = os.getenv('contact')

log_admin = os.getenv('log_admin')
id_user = os.getenv('id_user')
access = os.getenv('access')

