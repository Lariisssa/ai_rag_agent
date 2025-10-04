"""
Windows-specific startup script to fix asyncio event loop issues.
Uses SelectorEventLoop instead of ProactorEventLoop for psycopg compatibility.
"""
import asyncio
import sys
import selectors

# Force SelectorEventLoop on Windows for psycopg compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
