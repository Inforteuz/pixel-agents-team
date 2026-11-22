"""Launch the independent Pixel Team server on loopback."""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv
from backend.security import hash_password

ROOT = Path(__file__).resolve().parent


def main():
    env = ROOT / ".env"
    if not env.exists():
        password = secrets.token_urlsafe(18)
        fd = os.open(env, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(
                f"PIXEL_ADMIN_PASSWORD_HASH='{hash_password(password)}'\nAPP_PUBLIC_URL=http://127.0.0.1:8090\nAPP_ENV=development\n"
            )
        data = ROOT / "data"
        data.mkdir(exist_ok=True, mode=0o700)
        fd = os.open(
            data / "local-password.txt", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
        )
        with os.fdopen(fd, "w") as stream:
            stream.write(password + "\n")
        print(
            "Local owner configured. Password is in data/local-password.txt (private)."
        )
    load_dotenv(env, override=False)
    import uvicorn
    from backend.app import create_app

    uvicorn.run(
        create_app(),
        host="127.0.0.1",
        port=int(os.getenv("PIXEL_PORT", "8090")),
        forwarded_allow_ips="127.0.0.1,::1",
    )


if __name__ == "__main__":
    main()
