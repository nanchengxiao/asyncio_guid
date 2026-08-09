async def upload_chunks(chunks, send_chunk, cleanup):
    # TODO：发送所有分片；无论成功、普通失败还是调用者取消，cleanup 都必须执行。
    # 收到取消时不能把它转换成一个“成功”的返回值。
    raise NotImplementedError
