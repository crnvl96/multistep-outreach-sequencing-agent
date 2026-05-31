from pathlib import Path

PACKAGE_ROOT = Path("src/outreach_agent")
EXPECTED_TOP_LEVEL_MODULES = {
    "app.py",
    "enrichment.py",
    "llm.py",
    "models.py",
    "prompts.py",
    "workflow.py",
}
REMOVED_LAYER_DIRS = {"domain", "integrations", "protocols"}


def test_flat_package_layout_stays_simple() -> None:
    top_level_files = {path.name for path in PACKAGE_ROOT.glob("*.py")}
    assert EXPECTED_TOP_LEVEL_MODULES.issubset(top_level_files)

    top_level_dirs = {path.name for path in PACKAGE_ROOT.iterdir() if path.is_dir()}
    assert not (top_level_dirs & REMOVED_LAYER_DIRS)
