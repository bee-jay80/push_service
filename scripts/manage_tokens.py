#!/usr/bin/env python3
"""
CLI to manage device tokens in Redis for quick local testing.

Usage:
  python scripts/manage_tokens.py list --user-id 123
  python scripts/manage_tokens.py add --user-id 123 --token TEST_TOKEN
  python scripts/manage_tokens.py remove --user-id 123 --token TEST_TOKEN

This script uses the project's `config.get_redis_url()` to connect to Redis and
manipulate token mappings using the same key prefixes as the application.
"""
import argparse
import asyncio
from typing import Optional
from redis.asyncio import Redis
import sys
from pathlib import Path

# ensure project root on path so we can import config
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import config
from config import TOKEN_METADATA_PREFIX


async def get_redis() -> Optional[Redis]:
    url = config.get_redis_url()
    if not url:
        print("Redis URL not configured. Check .env and UPSTASH_REDIS_REST_URL / token.")
        return None
    try:
        r = Redis.from_url(url, decode_responses=True)
        await r.ping()
        return r
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return None


async def list_tokens(user_id: int):
    r = await get_redis()
    if not r:
        return 1
    key = TOKEN_METADATA_PREFIX + f"user:{user_id}"
    data = await r.hgetall(key)
    if not data:
        print(f"No token mapping found for user {user_id} (key: {key})")
        return 0
    print(f"Token mapping for user {user_id} (key: {key}):")
    for k, v in data.items():
        print(f"  {k}: {v}")
    return 0


async def add_token(user_id: int, token: str):
    r = await get_redis()
    if not r:
        return 1
    user_key = TOKEN_METADATA_PREFIX + f"user:{user_id}"
    token_key = TOKEN_METADATA_PREFIX + token

    # store reverse mapping for worker lookup
    await r.hset(user_key, "token", token)
    # store token metadata
    await r.hset(token_key, mapping={"is_valid": "True"})
    print(f"Added token for user {user_id}: {token}")
    return 0


async def remove_token(user_id: int, token: Optional[str]):
    r = await get_redis()
    if not r:
        return 1
    user_key = TOKEN_METADATA_PREFIX + f"user:{user_id}"
    if token:
        # remove only if matches
        current = await r.hget(user_key, "token")
        if current == token:
            await r.hdel(user_key, "token")
            print(f"Removed token mapping for user {user_id}")
        else:
            print(f"Token does not match current mapping for user {user_id}; no action taken.")
    else:
        # remove the token field entirely
        await r.hdel(user_key, "token")
        print(f"Removed token mapping (any token) for user {user_id}")
    return 0


def parse_args():
    ap = argparse.ArgumentParser(description="Manage push device tokens in Redis for testing")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List token mapping for a user")
    p_list.add_argument("--user-id", type=int, required=True)

    p_add = sub.add_parser("add", help="Add/inject a token for a user (overwrites existing mapping)")
    p_add.add_argument("--user-id", type=int, required=True)
    p_add.add_argument("--token", required=True)

    p_remove = sub.add_parser("remove", help="Remove a user's token mapping")
    p_remove.add_argument("--user-id", type=int, required=True)
    p_remove.add_argument("--token", required=False)

    return ap.parse_args()


async def main():
    args = parse_args()
    if args.cmd == "list":
        return await list_tokens(args.user_id)
    if args.cmd == "add":
        return await add_token(args.user_id, args.token)
    if args.cmd == "remove":
        return await remove_token(args.user_id, getattr(args, "token", None))


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(0 if rc is None else rc)
