#!/usr/bin/env python3
"""Check if all required services are running"""
import subprocess
import asyncpg
import redis
import httpx
import asyncio


async def check_services():
    print("🔍 Checking required services...\n")
    
    # Check Redis
    try:
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print("✅ Redis: Running")
    except Exception as e:
        print(f"❌ Redis: Not running - {e}")
        print("   Run: brew services start redis")
    
    # Check PostgreSQL
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',  # or your username
            database='mechanical_integrity'
        )
        await conn.close()
        print("✅ PostgreSQL: Running and database exists")
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
        print("   Run: createdb mechanical_integrity")
    
    # Check Ollama
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags")
            models = response.json()
            if models.get('models'):
                print(f"✅ Ollama: Running with {len(models['models'])} models")
                for model in models['models']:
                    print(f"   - {model['name']}")
            else:
                print("⚠️  Ollama: Running but no models installed")
                print("   Run: ollama pull phi3:mini")
    except Exception as e:
        print(f"❌ Ollama: Not running - {e}")
        print("   Run: ollama serve (in separate terminal)")


if __name__ == "__main__":
    asyncio.run(check_services())
