import psycopg2
import json
import sys

db_params = {
    "host": sys.argv[1],
    "port": sys.argv[2],
    "dbname": sys.argv[3],
    "user": sys.argv[4],
    "password": sys.argv[5]
}


def execute_query(conn, sql_cmd, sql_params):
    try:
        cur = conn.cursor()
        cur.execute(sql_cmd, sql_params)
     
    except Exception as e:
        print(f'Error: {e}')
        raise
    finally:
        cur.close()

create_table = """
    CREATE TABLE IF NOT EXISTS scores (
        id    serial primary key,
        model VARCHAR(1023),
        langpair VARCHAR(50),
        testset VARCHAR(255),
        score DECIMAL,
        catalog VARCHAR(255),
        score_type VARCHAR(50),
        date DATE
    );
"""
create_table2 = """
  CREATE TABLE scores2 (LIKE scores);
"""

sql_alter = """
BEGIN;
ALTER TABLE scores RENAME TO scores3;
ALTER TABLE scores2 RENAME TO scores;
DROP TABLE scores3; 
COMMIT;
"""

sql_insert = """
INSERT INTO scores2 (model, langpair, testset, score, catalog, score_type, date)
VALUES (%s, %s, %s, %s, %s, %s, %s);
"""

conn = psycopg2.connect(**db_params)

execute_query(conn, create_table, ())
execute_query(conn, create_table2, ())
conn.commit()

execute_query(conn, "DROP INDEX IF EXISTS testset_idx;", ())
execute_query(conn, "DROP INDEX IF EXISTS model_idx;", ())
execute_query(conn, "DROP INDEX IF EXISTS langpair_idx;", ())
execute_query(conn, "DROP INDEX IF EXISTS catalog_idx;", ()) 

execute_query(conn, "TRUNCATE TABLE scores2;", ())
conn.commit()

for line in sys.stdin:
    json_line = json.loads(line.strip())
    
    model = json_line.get('model')
    langpair = json_line.get('langpair')
    testset = json_line.get('testset')
    if json_line.get('score') == '':
        score = None
    else:     
        score = json_line.get('score')
    catalog = json_line.get('catalog')
    score_type = json_line.get('score_type')
    date = json_line.get('date')
        
    t = (model, langpair, testset, score, catalog, score_type, date)
        
    execute_query(conn, sql_insert, t)
execute_query(conn, "CREATE INDEX IF NOT EXISTS testset_idx ON scores2 (testset);", ())
execute_query(conn, "CREATE INDEX IF NOT EXISTS model_idx ON scores2 (model);", ())
execute_query(conn, "CREATE INDEX IF NOT EXISTS langpair_idx ON scores2 (langpair);", ())
execute_query(conn, "CREATE INDEX IF NOT EXISTS catalog_idx ON scores2 (catalog);", ())
execute_query(conn, sql_alter, ())
conn.commit()
conn.close()
