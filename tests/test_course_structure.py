from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSONS = sorted((ROOT / "lessons").glob("[0-9][0-9]_*"))


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
    headings = ["## 本节目标", "## 为什么需要学习它", "## 核心理论", "## 脑内执行模型",
                "## 常见误解", "## 本节规则总结", "## 关键问题", "## 场景命题", "## 验收"]
    for lesson in LESSONS:
        text = (lesson / "README.md").read_text(encoding="utf-8")
        for heading in headings:
            assert heading in text, (lesson.name, heading)


def test_design_before_code_exists_for_integrated_stages():
    for name in ["10_business_modeling", "11_production_asyncio"]:
        assert (ROOT / "lessons" / name / "practice" / "DESIGN.md").exists()
