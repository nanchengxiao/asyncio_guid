import asyncio

async def send_chunk(chunk):
    print(f"发送分片 {chunk} 中……")
    await asyncio.sleep(0.05)        # await 是 Task 能响应 cancellation 的位置
    print(f"分片 {chunk} 已发送")

async def upload():
    print("open：打开上传连接")
    try:
        for chunk in range(1, 100):
            await send_chunk(chunk)
        print("上传完成")             # 本例中不会执行到这里
    finally:
        # 无论正常结束、普通异常还是 cancellation，都负责收尾
        print("cleanup：关闭上传连接")

async def main():
    task = asyncio.create_task(upload())
    await asyncio.sleep(0.12)        # 上传进行中……
    task.cancel()                    # 只是发出停止请求，不是立即杀死
    try:
        await task                   # Task 在可响应位置看到 CancelledError
    except asyncio.CancelledError:
        # 不把 cancellation 伪装成成功，让它继续向调用者传播
        print("调用者看到 CancelledError，而不是伪装的成功")

asyncio.run(main())
