"""Initialize the first administrator after database migrations."""

from app.auth import initialize_bootstrap_admin
from app.config import get_settings
from app.database import SessionLocal


def main() -> None:
    """Initialize the migrated administrator when it is still blocked."""
    with SessionLocal() as db:
        initialize_bootstrap_admin(db, get_settings())


if __name__ == "__main__":
    main()
