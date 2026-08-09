async def upload_chunks(chunks, send_chunk, cleanup):
    try:
        for chunk in chunks:
            await send_chunk(chunk)
    finally:
        await cleanup()
