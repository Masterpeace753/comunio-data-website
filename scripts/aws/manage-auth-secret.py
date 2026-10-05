from __future__ import annotations

import argparse
import getpass
import json
import secrets

import bcrypt
import boto3


SECRET_NAME = "comunio/auth"


def read_new_password() -> str:
    password = getpass.getpass("New login password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password:
        raise ValueError("Password must not be empty.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be no more than 72 UTF-8 bytes for bcrypt.")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return password


def load_secret(client, secret_id: str) -> dict[str, str]:
    response = client.get_secret_value(SecretId=secret_id)
    value = json.loads(response["SecretString"])
    required = {"username", "passwordHash", "jwtSecret"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise ValueError("The existing auth secret does not have the expected fields.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or rotate the Comunio API login secret.")
    parser.add_argument(
        "action",
        choices=("create", "rotate-password", "rotate-jwt"),
        help="create the secret, replace its password hash, or revoke all sessions by rotating the JWT key",
    )
    parser.add_argument("--secret-name", default=SECRET_NAME)
    args = parser.parse_args()

    client = boto3.client("secretsmanager")
    if args.action == "create":
        username = input("Login username: ").strip()
        if not username:
            raise ValueError("Username must not be empty.")
        password_hash = bcrypt.hashpw(read_new_password().encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")
        response = client.create_secret(
            Name=args.secret_name,
            Description="Single-user API authentication configuration",
            SecretString=json.dumps(
                {
                    "username": username,
                    "passwordHash": password_hash,
                    "jwtSecret": secrets.token_urlsafe(48),
                }
            ),
        )
    else:
        value = load_secret(client, args.secret_name)
        if args.action == "rotate-password":
            value["passwordHash"] = bcrypt.hashpw(
                read_new_password().encode("utf-8"),
                bcrypt.gensalt(rounds=12),
            ).decode("ascii")
        else:
            value["jwtSecret"] = secrets.token_urlsafe(48)
        response = client.put_secret_value(
            SecretId=args.secret_name,
            SecretString=json.dumps(value),
        )

    print(f"Authentication secret updated: {response['ARN']}")
    print("Roll out/restart every API task to load the new secret version.")
    if args.action == "rotate-jwt":
        print("Existing login sessions will be invalid after all API tasks use the new JWT key.")


if __name__ == "__main__":
    main()
