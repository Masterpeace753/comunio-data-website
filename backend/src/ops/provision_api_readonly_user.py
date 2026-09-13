from __future__ import annotations

import os
import secrets
import string
from urllib.parse import quote

import boto3
import psycopg2
from psycopg2 import sql


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    region = os.getenv("AWS_REGION", "eu-central-1")
    master_secret_arn = required("MASTER_DATABASE_URL_SECRET_ARN")
    api_secret_arn = required("API_DATABASE_URL_SECRET_ARN")
    role_name = os.getenv("API_DATABASE_ROLE", "comunio_api_readonly")

    secrets_client = boto3.client("secretsmanager", region_name=region)
    master_dsn = secrets_client.get_secret_value(SecretId=master_secret_arn)["SecretString"]
    password_alphabet = string.ascii_letters + string.digits + "_-=%+"
    password = "".join(secrets.choice(password_alphabet) for _ in range(32))

    with psycopg2.connect(master_dsn) as connection:
        database_name = connection.info.dbname
        with connection.cursor() as cursor:
            role_identifier = sql.Identifier(role_name)
            role_literal = sql.Literal(password)
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
            if cursor.fetchone() is not None:
                cursor.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(role_identifier, role_literal))
            else:
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(role_identifier, role_literal))
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database_name), role_identifier))
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role_identifier))
            cursor.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(role_identifier))
            cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}").format(role_identifier))

        api_dsn = (
            f"postgresql://{quote(role_name, safe='')}:{quote(password, safe='')}"
            f"@{connection.info.host}:{connection.info.port}/{quote(database_name, safe='')}?sslmode=require"
        )

    secrets_client.put_secret_value(SecretId=api_secret_arn, SecretString=api_dsn)
    print(f"Provisioned read-only database role {role_name}.")


if __name__ == "__main__":
    main()