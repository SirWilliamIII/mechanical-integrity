#!/usr/bin/env python3
"""Check if all required services are running for mechanical integrity system"""
import asyncpg
import redis
import httpx
import asyncio
import sys


async def check_services():
    print("🔍 Checking required services for Mechanical Integrity System")
    print("=" * 60)
    
    all_good = True
    
    # Check Redis
    try:
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        info = r.info()
        print(f"✅ Redis: Running (version {info['redis_version']})")
    except Exception as e:
        print(f"❌ Redis: Not running - {e}")
        print("   Run: brew services start redis")
        all_good = False
    
    # Check PostgreSQL
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='will',
            database='risk-assessment'
        )
        version = await conn.fetchval('SELECT version()')
        await conn.close()
        print("✅ PostgreSQL: Running and database 'risk-assessment' exists")
        print(f"   {version.split(',')[0]}")
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
        if "database" in str(e).lower():
            print("   Run: createdb mechanical_integrity")
        else:
            print("   Run: brew services start postgresql@14")
        all_good = False
    
    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            models = response.json()
            if models.get('models'):
                print(f"✅ Ollama: Running with {len(models['models'])} models")
                model_names = [model['name'] for model in models['models']]
                for name in model_names[:3]:  # Show first 3 models
                    print(f"   - {name}")
                if len(model_names) > 3:
                    print(f"   ... and {len(model_names) - 3} more")
                    
                # Check for recommended model
                if 'llama3.2:latest' not in model_names:
                    print("   💡 Recommended: ollama pull llama3.2:latest")
            else:
                print("⚠️  Ollama: Running but no models installed")
                print("   Run: ollama pull llama3.2:latest")
    except Exception as e:
        print(f"❌ Ollama: Not running - {e}")
        print("   Run: ollama serve (in separate terminal)")
        all_good = False
    
    print("\n" + "=" * 60)
    
    if all_good:
        print("🎯 All services are running! System ready for testing.")
        print("\nNext steps:")
        print("1. cd backend")  
        print("2. uv run uvicorn app.main:app --reload")
        print("3. uv run python test_api579_integration.py")
        return 0
    else:
        print("❌ Some services need to be started. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(check_services())
    sys.exit(exit_code)
