import asyncio

WORKERS = 3
QUEUE_MAXSIZE = 4                 # bounded Queue：backlog 上界
API_CONCURRENCY = 3               # 同一时刻最多多少个 API attempt 正在进行
QPS = 20                          # 每秒最多启动多少个新 attempt
ATTEMPT_TIMEOUT = 0.2             # 每个 attempt 自己的 time budget
MAX_RETRIES = 2                   # retry 次数上限
WRITER_CONCURRENCY = 2            # writer 也是有限 resource

api_gate = asyncio.Semaphore(API_CONCURRENCY)
writer_gate = asyncio.Semaphore(WRITER_CONCURRENCY)
metrics = {"received": 0, "succeeded": 0, "failed": 0, "retried": 0}
processed_ids = set()             # 已真正产生 side effect 的业务，用于幂等检查

def log(event, **fields):
    """structured logging：事件名 + 明确字段，而不是一段自由文本。"""
    parts = [f"event={event}"] + [f"{k}={v}" for k, v in fields.items()]
    print(" ".join(parts))

class RateLimiter:
    """rate limit：控制新 attempt 的启动速度，与并发上限是两个维度。"""

    def __init__(self, qps):
        self.interval = 1 / qps
        self.next_start = 0.0
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = asyncio.get_running_loop().time()
            wait = self.next_start - now
            self.next_start = max(now, self.next_start) + self.interval
        if wait > 0:
            await asyncio.sleep(wait)

rate_limiter = RateLimiter(QPS)

async def external_api(job, attempt):
    # side effect 前先做幂等检查：重复执行不能产生重复副作用
    if job["id"] in processed_ids:
        log("job_duplicate", job_id=job["id"])
        return {"id": job["id"], "duplicate": True}
    if job["id"] % 7 == 0:
        raise ValueError("参数错误")              # permanent failure：不 retry
    if job["id"] % 5 == 0 and attempt == 1:
        raise ConnectionError("网络抖动")          # transient failure：可 retry
    if job["id"] % 4 == 0:
        if attempt == 1:
            processed_ids.add(job["id"])
            await asyncio.sleep(1.0)               # side effect 已发生，但 response 永远等不到
        return {"id": job["id"]}
    processed_ids.add(job["id"])
    await asyncio.sleep(0.05)
    return {"id": job["id"]}

async def call_with_retry(job):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await rate_limiter.acquire()           # 先拿到启动许可……
            async with api_gate:                   # 再受 concurrency limit 约束
                async with asyncio.timeout(ATTEMPT_TIMEOUT):
                    return await external_api(job, attempt)
        except TimeoutError:
            reason = "timeout"
        except ConnectionError:
            reason = "transient"
        if attempt < MAX_RETRIES:
            metrics["retried"] += 1
            log("job_retry", job_id=job["id"], attempt=attempt, reason=reason)
    raise RuntimeError(f"job {job['id']} 重试次数用尽")

async def save(result):
    async with writer_gate:                        # writer 有自己的容量边界
        await asyncio.sleep(0.02)

async def worker(queue, name):
    while True:
        job = await queue.get()
        try:
            if job is None:                        # sentinel：没有新工作了
                break
            result = await call_with_retry(job)
            await save(result)
            metrics["succeeded"] += 1
        except ValueError:
            metrics["failed"] += 1                 # permanent failure：记录后继续
        except RuntimeError:
            metrics["failed"] += 1
        finally:
            queue.task_done()

async def main():
    queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
    async with asyncio.TaskGroup() as tg:
        for n in range(WORKERS):
            tg.create_task(worker(queue, f"worker-{n}"))
        jobs = [{"id": i} for i in range(1, 11)]
        for job in jobs:                            # 停止接收新输入之前只到这里
            metrics["received"] += 1
            await queue.put(job)                    # Queue 满 → 生产侧自动放慢
        for _ in range(WORKERS):
            await queue.put(None)
        await queue.join()                          # graceful shutdown：drain 已接收工作
    print("最终 metrics:", metrics)

asyncio.run(main())
