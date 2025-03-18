#!/usr/bin/env python3

import sys
import sqlite3
import json
import requests
import tempfile


if __name__ == "__main__":

    
 
        with sqlite3.connect(sys.argv[1]) as conn:

            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [a["name"] for a in c.fetchall()]

            db_content = {}
            for table in tables:
                c.execute("SELECT * FROM {0}".format(table))
                db_content[table] = [dict(a) for a in c.fetchall()]
    

        json.dump(db_content, sys.stdout, indent=4)
        
