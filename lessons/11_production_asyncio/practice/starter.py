from dataclasses import dataclass


class TransientJobError(Exception):
    pass


@dataclass(frozen=True)
class Job:
    job_id: str
    payload: object


async def process_jobs(jobs, call_api, save_result, *, queue_size=10, workers=3,
                       api_concurrency=2, write_concurrency=1,
                       rate_per_second=1000.0, request_timeout=1.0, retries=1,
                       logger=None):
    # TODO：按照 README 和 DESIGN.md 中的约束实现完整的生产级处理流水线。
    raise NotImplementedError
