import asyncio

async def send_chunk(chunk):
    print(f"发送分片 {chunk} 中……")
    await asyncio.sleep(0.05)        # 这里会暂停，Task 可在等待附近响应 cancellation
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

async def upload_with_log():
    try:
        await upload()
    except asyncio.CancelledError:
        print("中间层记录 cancellation，然后继续传播")
        raise                              # 重新抛出同一个 cancellation

async def main():
    task = asyncio.create_task(upload_with_log())
    await asyncio.sleep(0.12)        # 上传进行中……
    task.cancel()                    # 只是发出停止请求，不是立即杀死
    try:
        await task                   # Task 在可响应位置看到 CancelledError
    except asyncio.CancelledError:
        # 最外层调用者明确识别 cancellation，不把它当成正常结果
        print("调用者看到 CancelledError，而不是伪装的成功")

asyncio.run(main())
