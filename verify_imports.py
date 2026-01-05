import sys
import asyncio
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

async def verify_imports():
    print("Verifying imports...")
    try:
        from src.config import DISCORD_TOKEN
        from src.database.models import Base
        from src.cogs.setup import Setup
        from src.cogs.moderation import Moderation
        from src.cogs.tickets import Tickets
        from src.cogs.roles import Roles
        from src.cogs.tracking import Tracking
        from src.cogs.system import System
        print("Imports successful.")
    except ImportError as e:
        print(f"Import failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during import verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify_imports())
