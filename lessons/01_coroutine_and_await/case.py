import asyncio


async def fetch_profile():
    print("fetching profile")
    await asyncio.sleep(0.1)
    print("profile ready")
    return {"name": "alice"}


async def main():
    profile = await fetch_profile()
    print(profile)


if __name__ == "__main__":
    asyncio.run(main())
