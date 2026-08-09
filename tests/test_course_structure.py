import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSONS = sorted((ROOT / "lessons").glob("[0-9][0-9]_*"))
LEGACY = ROOT / "legacy" / "cloudfit_translation"
CJK = re.compile(r"[\u4e00-\u9fff]")

LESSON_HEADINGS = [
    "## 进入本课前",
    "## 本课新增术语",
    "## 本节目标",
    "## 为什么需要学习它",
    "## 核心理论",
    "## 脑内执行模型",
    "## 常见误解",
    "## 本节规则总结",
    "## 关键问题",
    "## 场景命题",
    "## 验收",
]

ROOT_README_HEADINGS = [
    "## 课程定位",
    "## 前置要求",
    "## 学习路线",
    "## 运行方式",
    "## 仓库导航",
]

NAVIGATION_ONLY_TERMS = [
    "coroutine",
    "Awaitable",
    "`await`",
    "Event Loop",
    "TaskGroup",
    "structured concurrency",
    "cancellation",
    "CancelledError",
    "ExceptionGroup",
    "Semaphore",
    "backpressure",
    "aiohttp",
    "ClientSession",
    "connection pool",
    "to_thread",
    "DAG",
    "idempotency",
    "rate limit",
    "retry storm",
    "metrics",
    "QPS",
    "SDK",
    "HTTP",
    "JSON",
]


def _visible_markdown_text(text: str) -> str:
    """移除链接目标和代码块，近似得到学习者在渲染页面中看到的正文。"""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    return text


def test_has_twelve_lessons_covering_00_to_11():
    assert [p.name[:2] for p in LESSONS] == [f"{i:02d}" for i in range(12)]


def test_every_lesson_has_closed_learning_loop():
    for lesson in LESSONS:
        required = [
            lesson / "README.md",
            lesson / "practice" / "README.md",
            lesson / "practice" / "starter.py",
            lesson / "solution" / "reference.py",
            lesson / "tests" / "test_acceptance.py",
        ]
        assert all(path.exists() for path in required), lesson.name


def test_every_theory_readme_defines_terms_before_objectives():
    for lesson in LESSONS:
        text = (lesson / "README.md").read_text(encoding="utf-8")
        positions = []
        for heading in LESSON_HEADINGS:
            assert heading in text, (lesson.name, heading)
            positions.append(text.index(heading))
        assert positions == sorted(positions), lesson.name


def test_prerequisites_only_point_backward_in_course():
    """结构层面保证每课先声明前置，再声明本课新术语。"""
    for lesson in LESSONS:
        text = (lesson / "README.md").read_text(encoding="utf-8")
        prereq = text.index("## 进入本课前")
        terms = text.index("## 本课新增术语")
        objectives = text.index("## 本节目标")
        assert prereq < terms < objectives, lesson.name


def test_root_readme_is_only_project_entrypoint():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## .+$", text, flags=re.MULTILINE)
    assert headings == ROOT_README_HEADINGS

    forbidden_sections = [
        "教学约定",
        "教学规范",
        "每节课怎么学",
        "两套验收",
        "优化说明",
        "最终能力",
        "本轮",
        "重构过程",
    ]
    assert all(section not in text for section in forbidden_sections)


def test_navigation_docs_do_not_preteach_course_terms():
    for path in [ROOT / "README.md", ROOT / "COURSE_MAP.md"]:
        visible = _visible_markdown_text(path.read_text(encoding="utf-8"))
        for term in NAVIGATION_ONLY_TERMS:
            assert term not in visible, (path.name, term)


def test_authoring_contract_records_first_use_rule():
    text = (ROOT / "AUTHORING.md").read_text(encoding="utf-8")
    assert "普通 Python 基础" in text
    assert "第一次进入主线" in text
    assert "必须先用一句白话" in text
    assert "本课新增术语" in text
    assert "根 README" in text
    assert "不记录教学规范" in text


def test_course_code_comments_use_chinese():
    """课程中的教学注释使用中文；静态检查工具指令不受此限制。"""
    tool_directives = ("# noqa", "# type:", "# fmt:", "# pragma:")

    for path in (ROOT / "lessons").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            comment = token.string.strip()
            if comment.startswith(tool_directives):
                continue
            assert CJK.search(comment), (
                path.relative_to(ROOT),
                token.start[0],
                comment,
            )


def test_design_before_code_exists_for_integrated_stages():
    for name in ["10_business_modeling", "11_production_asyncio"]:
        assert (ROOT / "lessons" / name / "practice" / "DESIGN.md").exists()


def test_legacy_repository_materials_are_grouped_together():
    required = [
        "README.md",
        "01_基础概念与模式.md",
        "02_可等待对象_任务与Future.md",
        "03_异步上下文管理器与异步迭代器.md",
        "04_库支持.md",
        "05_混合同步与异步代码.md",
        "asyncio_guide_zh.md",
        "asyncio_guide_zh.html",
        "assets/SubVsCoRoutines.png",
        "examples/01_interleave.py",
        "examples/06_async_tests.py",
        "NOTICE.md",
        "SOURCES.md",
        "MANIFEST.json",
        "style.css",
        "pyproject.toml",
        "uv.lock",
    ]
    assert all((LEGACY / path).exists() for path in required)

    old_root_paths = [
        "01_基础概念与模式.md",
        "02_可等待对象_任务与Future.md",
        "03_异步上下文管理器与异步迭代器.md",
        "04_库支持.md",
        "05_混合同步与异步代码.md",
        "asyncio_guide_zh.md",
        "asyncio_guide_zh.html",
        "assets",
        "examples",
        "NOTICE.md",
        "SOURCES.md",
        "MANIFEST.json",
        "style.css",
    ]
    assert all(not (ROOT / path).exists() for path in old_root_paths)
