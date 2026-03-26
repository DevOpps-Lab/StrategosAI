import asyncio
from agents.sandbox import run_sandbox_simulation
import traceback

async def main():
    try:
        await run_sandbox_simulation("c", "c", "s", "q")
    except Exception as e:
        traceback.print_exc()

asyncio.run(main())
