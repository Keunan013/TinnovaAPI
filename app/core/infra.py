import httpx
import redis.asyncio as redis

from fastapi import Request


def get_redis(request: Request) -> redis.Redis:
    return request.app.state.redis

def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http
