import asyncio
import asyncpg
import urllib.parse

passwords_to_test = [
    "uzipXYN9RhSe@7i",
    "uzipXYN9RhSe%407i",
    "uzipXYN9RhSe",
]

host = "icfbnbiumbflxblqcwdl.db.ap-south-1.nhost.run"
port = 5432
user = "postgres"
database = "icfbnbiumbflxblqcwdl"

async def test_pass(pw):
    print(f"Testing password: {pw!r}")
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=pw,
            database=database,
            ssl="require",
            timeout=10
        )
        print(f"  -> SUCCESS with password: {pw!r}")
        await conn.close()
        return True
    except Exception as e:
        print(f"  -> FAILED: {type(e).__name__}: {e}")
        return False

async def main():
    for pw in passwords_to_test:
        if await test_pass(pw):
            break

if __name__ == "__main__":
    asyncio.run(main())
