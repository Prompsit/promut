import psycopg2
import sys
db_params = {
    "host": sys.argv[1],
    "port": sys.argv[2],
    "database": sys.argv[3],
    "user": sys.argv[4],
    "password": sys.argv[5]
}
def connect_to_db():
    connection = psycopg2.connect(
        host=db_params["host"],
        port=db_params["port"],
        database=db_params["database"],
        user=db_params["user"],
        password=db_params["password"])
    return connection
try:
    connection = connect_to_db()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id SERIAL PRIMARY KEY,
            model VARCHAR(300),
            catalog VARCHAR(100),
            download_link TEXT
        );
    """)
    print("New table for unique models created.")


    cursor.execute("""
        SELECT DISTINCT model, catalog
        FROM scores;
    """)
    rows = cursor.fetchall()

    unique_models = []
    for row in rows:
        model, catalog = row
        if catalog == "External":
            link = model.replace("huggingface", "https://huggingface.co")
        elif catalog == "OPUS":
            link = f"https://object.pouta.csc.fi/{model}.zip"
        else:
            link = None
            continue
        ## TODO: What are Contributed models? are they needed?
        unique_models.append((model, catalog, link))

    cursor.executemany("""
        INSERT INTO models (model, catalog, download_link)
        VALUES (%s, %s, %s);
    """, unique_models)
    print("Unique models with download links inserted into the new table.")

    # Commit changes
    connection.commit()

except psycopg2.Error as e:
    print(f"Database error: {e}")
finally:
    if connection:
        cursor.close()
        connection.close()
        print("Connection closed.")
