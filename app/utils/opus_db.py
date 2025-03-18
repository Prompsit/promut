import psycopg2
from datetime import datetime
import re
def _connect_to_db():
    # Connect to the database
    connection = psycopg2.connect(
        host="opus_db",
        port=5432,
        database="postgres",
        user="postgres",
        password="pass123"
    )
    return connection


def get_opus_model_link(lang1, lang2):
    model_substr = f"{lang1}-{lang2}"
    try:
        connection = _connect_to_db()
        cursor = connection.cursor()

        cursor.execute(f"SELECT download_link FROM models where model LIKE '%{model_substr}%' AND catalog='OPUS';")
        rows = cursor.fetchall()
        models_by_date = []
        for row in rows:
            date = re.split('[- _]', row[0])[-3:]
            date = '-'.join(date)
            cleaned_date = date.replace(".zip", "")
            models_by_date.append((row[0], datetime.fromisoformat(cleaned_date)))
        sorted_models = sorted(models_by_date,key=lambda x: x[1], reverse=True)
        return sorted_models[0][0]
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Connection closed.")
