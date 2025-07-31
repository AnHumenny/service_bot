# Aiogram3 Bot Application

Приложение предназначено для обработки рабочей информации, хранящейся в базе данных основного проекта, а также для обновления и добавления новых заявок и отображения информации в виде графиков. Используетс Redis. В качестве базы данных используется **PostgreSQL**.

## Требования

Перед началом работы убедитесь, что у вас установлены следующие компоненты:

- **Python** (версия 3.12 или выше)
- **PostgreSQL** (версия 14 или выше)
- **pip**
- **virtualenv** (опционально, для создания виртуального окружения)

## Установка

1. **Создайте виртуальное окружение** (рекомендуется):

    ```bash
    python -m venv venv


2. **Активируйте виртуальное окружение**:

    ```bash
    Для macOS/Linux:
    bashsource venv/bin/activate

    Для Windows:
    bashvenv\Scripts\activate

3. **Установите зависимости**:
    ```bash
    pip install -r requirements.txt

### Настройка базы данных

1. **Создайте базу данных в PostgreSQL**.

#### Настройте параметры подключения в файле .env вашего проекта. Пример содержимого файла .env
- **TELEGRAM_BOT_TOKEN='YOUR_TELEGRAM_BOT_TOKEN'**
- **SECRET_KEY='YOUR_SECRET_KEY'**
- **host='YOUR_DB_HOST'**
- **port='YOUR_DB_PORT'**
- **user='YOUR_DB_USER'**
- **password='YOUR_DB_PASSWORD'**
- **database='YOUR_DB_NAME'**
- **DATABASE_URL='postgresql://user:password@host:port/database'**
- **CONTACT='Список контактов'**
- **PATH_TO_CLUSTER_1="Трассы кластер 1"**
- **PATH_TO_CLUSTER_2="Трассы кластер 2"**
- **PATH_TO_CLUSTER_3="Трассы кластер 3"**
- **PATH_TO_CLUSTER_4="Трассы кластер 4"**
- **PATH_TO_CLUSTER_5="Трассы кластер 5"**
- 
1. **Замените значения на соответствующие для вашего окружения**.


### Запуск приложения
#### Для запуска приложения выполните следующую команду:
    python3 app.py