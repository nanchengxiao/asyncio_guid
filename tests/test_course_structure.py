import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSONS = sorted((ROOT / "lessons").glob("[0-9][0-9]_*"))
LEGACY = ROOT / "legacy" / "cloudfit_translation"
CJK = re.compile(r"[\u4e00-\u9fff]")


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


def test_every_theory_readme_uses_course_template():
    headings = [
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
    for lesson in LESSONS:
        text = (lesson / "README.md").read_text(encoding="utf-8")
        for heading in headings:
            assert heading in text, (lesson.name, heading)


def test_lessons_after_foundation_declare_prerequisites():
    for lesson in LESSONS[1:]:
        text = (lesson / "README.md").read_text(encoding="utf-8")
        assert "## 进入本课前" in text, lesson.name

    foundation = (LESSONS[0] / "README.md").read_text(encoding="utf-8")
    assert "不要求你预先理解" in foundation
    assert "本课会从普通 `for` 循环开始" in foundation


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
