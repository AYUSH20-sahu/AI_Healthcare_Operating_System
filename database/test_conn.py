"""PostgreSQL connection diagnostic script.

Checks network accessibility and credentials against PostgreSQL.
Supports asyncpg if installed, with socket-level fallback diagnostics.
"""

import asyncio
import os
import socket
import sys

import importlib

asyncpg = None
try:
    asyncpg = importlib.import_module("asyncpg")  # type: ignore
except ImportError:
    pass

host = os.getenv("POSTGRES_HOST", "localhost")
port = int(os.getenv("POSTGRES_PORT", "5432"))
user = os.getenv("POSTGRES_USER", "postgres")
database = os.getenv("POSTGRES_DB", "ai_hos")
default_pw = os.getenv("POSTGRES_PASSWORD", "postgres")

passwords_to_test = [
    default_pw,
]


def test_socket_reachability(host_name: str, port_num: int) -> bool:
    """Test raw TCP connection to database port."""
    print(f"Testing TCP reachability to {host_name}:{port_num}...")
    try:
        sock = socket.create_connection((host_name, port_num), timeout=5)
        sock.close()
        print(f"  -> Port {port_num} on {host_name} is reachable.")
        return True
    except Exception as e:
        print(f"  -> TCP connection to {host_name}:{port_num} failed: {e}")
        return False


async def test_pass(pw: str) -> bool:
    """Test database authentication using asyncpg."""
    if asyncpg is None:
        print("  -> Notice: 'asyncpg' is not installed in the current Python environment.")
        print("     To run async database queries, install it with: pip install asyncpg")
        return False

    print(f"Testing authentication for user '{user}' against '{database}'...")
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=pw,
            database=database,
            timeout=10,
        )
        print(f"  -> SUCCESS: Connected to {database} on {host}:{port}!")
        await conn.close()
        return True
    except Exception as e:
        print(f"  -> FAILED: {type(e).__name__}: {e}")
        return False


async def main():
    print(f"=== AI-HOS Database Connection Diagnostic ===")
    print(f"Host: {host} | Port: {port} | Database: {database} | User: {user}\n")

    # 1. Socket reachability check
    is_reachable = test_socket_reachability(host, port)
    if not is_reachable:
        print("\nNote: Make sure PostgreSQL container is running: docker-compose up -d postgres")
        return

    # 2. Authentication test
    if asyncpg is not None:
        for pw in passwords_to_test:
            if await test_pass(pw):
                break
    else:
        print("\nTCP port is reachable. To perform SQL authentication tests, install asyncpg:")
        print(f"  {sys.executable} -m pip install asyncpg")


if __name__ == "__main__":
    asyncio.run(main())
