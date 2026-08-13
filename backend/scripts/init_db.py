import asyncio

from app.db.session import create_all, dispose_engine


async def main() -> None:
    await create_all()
    await dispose_engine()
    print("Tables created.")


if __name__ == "__main__":
    asyncio.run(main())