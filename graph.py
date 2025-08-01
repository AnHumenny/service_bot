import os
import random
from collections import OrderedDict
from datetime import datetime
import matplotlib.pyplot as plt
import psycopg2
import pytz


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
