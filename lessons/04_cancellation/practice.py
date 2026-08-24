import asyncio

async def send_chunk(chunk) -> None:
    print(f"发送分片 {chunk} 中...")
    asyncio.sleep(0.05)
    print(f"分片{chunk} 已发送")

async def uplord() -> None:
    print(f"open: 打开上传链接")
    try:
        for chunk in range(1,101):
            await send_chunk()
        print("上传完成")  # 本例中不会执行到这里
    finally:
        # 无论正常结束还是异常报错还是cancellation，都会收尾资源
        print('cleanup：关闭上传链接')
        
async def uplord_with_log() -> None:
    try:
        await uplord()
    except asyncio.CancelledError:
        print("中间层记录 cancellation，然后继续传播")
        raise  # 重新抛出当前捕获的 CancelledError，让取消继续向上传播

async def main() -> None:
    task = asyncio.create_task(uplord_with_log())
    await asyncio.sleep(0.12)  #上传进行中
    task.cancel()
    try:
        await task  # 在这里抓到 CancelledError，然后进行最后处理，处理就是：print('调用者看到CancelledError，而不是伪装的成功')
    except asyncio.CancelledError:
        # 最外层调用者明确识别 cancellation，不把它当成正常结果
        print('调用者看到CancelledError，而不是伪装的成功')

asyncio.run(main())
        
