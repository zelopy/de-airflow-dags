from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
from pandas import Timestamp
import pandas as pd
import logging
import requests, json


def get_Redshift_connection(autocommit=True):
    hook = PostgresHook(postgres_conn_id='redshift_dev_db')
    conn = hook.get_conn()
    conn.autocommit = autocommit
    return conn.cursor()


@task
def get_rest_countries():
    url = 'https://restcountries.com/v3/all'
    records = []

    response = requests.get(url, verify=False)
    countries = response.json()
    
    for country in countries:
        name = country["name"]["official"]
        population = country["population"]
        area = country["area"]
        records.append([name, population, area])

    return records


def _create_table(cur, schema, table, drop_first):
    if drop_first:
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{table};")
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            country VARCHAR(256) primary key,
            population int,
            area float
        );"""
    )


@task
def load(schema, table, records):
    logging.info("load started")
    cur = get_Redshift_connection()
    try:
        cur.execute("BEGIN;")
        # 원본 테이블이 없으면 생성 - 테이블이 처음 한번 만들어질 때 필요한 코드
        _create_table(cur, schema, table, False)
        # 임시 테이블로 원본 테이블을 복사
        cur.execute(f"CREATE TEMP TABLE t AS SELECT * FROM {schema}.{table};")
        for r in records:
            sql = f"INSERT INTO t VALUES ('{r[0]}', {r[1]}, {r[2]});"
            print(sql)
            cur.execute(sql)

        # 원본 테이블 생성
        _create_table(cur, schema, table, True)
        # 임시 테이블 내용을 원본 테이블로 복사
        cur.execute(f"INSERT INTO {schema}.{table} SELECT DISTINCT * FROM t;")
        cur.execute("COMMIT;")   # cur.execute("END;")
    except Exception as error:
        print(error)
        cur.execute("ROLLBACK;") 
        raise
    logging.info("load done")


with DAG(
    dag_id = 'RestCountries',
    start_date = datetime(2024,5,22),
    catchup=False,
    tags=['API'],
    schedule = '30 6 * * 6' # 매주 토요일 오전 6시 30분
) as dag:

    results = get_rest_countries()
    load("zelopy", "country", results)
