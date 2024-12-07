import psycopg2
import base64
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('database'),
    'user': os.getenv('user'),
    'password': os.getenv('password'),
    'host': os.getenv('host'),
    'port': os.getenv('port')
}


def add_user(login, name, status, password, phone, email, tg_id):
    # Хешируем пароль в base64
    ## под настроение запилить в bcrypt
    encoded_password = base64.b64encode(password.encode()).decode()
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        insert_query = '''
        INSERT INTO _userbot(login, name, status, password, phone, email, tg_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(insert_query, (login, name, status, encoded_password, phone, email, tg_id))
        conn.commit()
        print("Пользователь добавлен успешно!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":                    #Пользовательские данные для добавления
    add_user(
        login="login",
        name = "name",
        status = "status",
        password = "password",
        phone = "+phone",
        email = "email",
        tg_id = "tg_id"
    )
