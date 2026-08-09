from course_testing import load_target

m = load_target(__file__)


def test_stream_is_lazy_and_cleanup_runs_on_early_exit():
    events = []

    def source():
        for item in [1, 2, 3]:
            events.append(f"produce:{item}")
            yield item

    with m.managed_records(source(), lambda: events.append("closed")) as records:
        assert next(records) == 1
        assert events == ["produce:1"]
    assert events == ["produce:1", "closed"]


def test_cleanup_runs_after_normal_consumption():
    events = []
    with m.managed_records([1, 2], lambda: events.append("closed")) as records:
        assert list(records) == [1, 2]
    assert events == ["closed"]
