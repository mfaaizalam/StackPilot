import json
from pathlib import Path

FIXTURES = Path(__file__).parents[1] / "app" / "data" / "demo_fixtures.json"


def test_all_three_demo_fixtures_are_complete_and_static():
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert set(fixtures) == {"hospital", "ecommerce", "university"}
    for name, item in fixtures.items():
        assert item["name"] == name
        assert item["requirements"]["functional_requirements"]
        assert item["requirements"]["non_functional_requirements"]
        assert item["markdown"].startswith("# ")
        assert item["diagrams"]
        assert item["board"]["columns"] == ["Backlog", "Ready", "In Progress", "Testing", "Done"]
        assert item["board"]["tasks"]
        assert item["cost"]["currency"] == "PKR"
        assert "illustrative" in item["cost"]["disclaimer"].lower()


def test_demo_fixture_requirement_and_task_ids_are_traceable():
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for item in fixtures.values():
        fr_ids = {fr["id"] for fr in item["requirements"]["functional_requirements"]}
        task_ids = {task["requirement_id"] for task in item["board"]["tasks"]}
        assert fr_ids == task_ids
