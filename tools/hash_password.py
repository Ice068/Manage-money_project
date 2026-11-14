from getpass import getpass

from app.routers.auth import hash_password


def main() -> None:
    password = getpass("New app password: ")
    confirmation = getpass("Confirm app password: ")
    if len(password) < 12:
        raise SystemExit("Use a password with at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    print(hash_password(password))


if __name__ == "__main__":
    main()
