import os
import hashlib
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('database'),
    'user': os.getenv('user'),
    'password': os.getenv('password'),
    'host': os.getenv('host'),
    'port': os.getenv('port')
}

def hashing_password(password: str) -> str:
    """hashing password."""
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(login, name, status, password, phone, email, tg_id):
    pswrd = hashing_password(password)
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        insert_query = '''
        INSERT INTO _userbot(login, name, status, password, phone, email, tg_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(insert_query, (login, name, status, pswrd, phone, email, tg_id))
        conn.commit()
        print("Пользователь добавлен успешно!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    add_user(
        login="User",
        name = "Имя пользователя",
        status = "статус",
        password = "пароль",
        phone = "номер телефона",
        email = "email",
        tg_id = "идентификатор tg"
    )
