#!/bin/bash
docker exec opus_db psql -d postgres -U postgres -c "CREATE DATABASE scores;"
docker exec  opus_db psql -d postgres -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE scores TO postgres;"
cd scripts/db_scores/ || exit 1
./process.sh