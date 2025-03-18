#!/bin/bash

DATABASE_URL=postgresql://postgres:pass123@localhost:15432/postgres

PG_HOST=$(echo $DATABASE_URL | sed  -nr 's%postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/([^?]+)(\?.+)?$%\3%p')
PG_PORT=$(echo $DATABASE_URL | sed  -nr 's%postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/([^?]+)(\?.+)?$%\4%p')
PG_DB=$(echo $DATABASE_URL   | sed  -nr 's%postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/([^?]+)(\?.+)?$%\5%p')
PG_USER=$(echo $DATABASE_URL | sed  -nr 's%postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/([^?]+)(\?.+)?$%\1%p')
PG_PASS=$(echo $DATABASE_URL | sed  -nr 's%postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/([^?]+)(\?.+)?$%\2%p')


URL_PREFIX="https://raw.githubusercontent.com/Helsinki-NLP/"
URL_INFIX="-MT-leaderboard/master/scores/"
URL_SUFFIX="_scores"

CATALOG="External OPUS Contributed"
SCORES="chrf chrf++ spbleu bleu comet"

for i in $CATALOG;
do for j in $SCORES;
   do MYURL_DB="${URL_PREFIX}${i}${URL_INFIX}${j}${URL_SUFFIX}.db";
      MYURL_DATE="${URL_PREFIX}${i}${URL_INFIX}${j}${URL_SUFFIX}.date";
      MYDATE=$(curl -s "${MYURL_DATE}")
      
      
      if ! curl --head --silent --fail $MYURL_DB &> /dev/null;
      then echo "${MYURL_DB} not found -- skipping" >&2
           continue
      else echo "Processing ${MYURL_DB}" >&2
           python3 sqlitetojson.py "$MYURL_DB" | \
           jq -c '.[] | [.[] | .["catalog"] = "'${i}'" | .["score_type"] = "'${j}'" | .["date"] = "'${MYDATE}'"] | .[]'
      fi
   done
done | python3 db_add.py ${PG_HOST} ${PG_PORT} ${PG_DB} ${PG_USER} ${PG_PASS}

python3 create_table.py ${PG_HOST} ${PG_PORT} ${PG_DB} ${PG_USER} ${PG_PASS}