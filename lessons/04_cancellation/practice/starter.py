async def upload_chunks(chunks, send_chunk, cleanup):
    # TODO：依次发送所有 chunk；无论成功、失败还是调用方取消，都必须执行 cleanup。
    # 不要把 cancellation 转换成“成功返回值”。
    raise NotImplementedError
