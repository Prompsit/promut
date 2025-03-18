# Instalación

## Entorno de python

```
$ python3 -mvenv venv
$ source venv/bin/activate
(venv) $ pip3 install -r requirements.txt
```

## Configurar acceso a DB

Editar fichero process.sh y poner valores a las variables DB

## Crear base de datos



```
$ docker run -d --name postgres -p 15432:5432 -e POSTGRES_PASSWORD=pass123 postgres
$ docker exec -it -u postgres postgres /bin/bash
# psql
psql> create database scores;
psql> \c scores
psql> GRANT ALL PRIVILEGES ON DATABASE scores TO postgres;
```

(abandonar con control + D )

## Ejecutar

El siguiente comando se lo baja todo y monta la base de datos

```
$ ./process.sh
```
