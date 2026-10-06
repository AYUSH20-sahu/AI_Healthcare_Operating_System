#!/usr/bin/env python3
"""Convenience runner for seeding AI-HOS database."""
import asyncio
from database.seed import seed_database

if __name__ == "__main__":
    asyncio.run(seed_database())
