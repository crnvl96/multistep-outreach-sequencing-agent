import ast
from pathlib import Path

SRC_ROOT = Path("src")
PACKAGE_ROOT = SRC_ROOT / "outreach_agent"
COMPOSITION_ROOT = "outreach_agent.app"
DOMAIN_MODULE = "outreach_agent.domain"
PROTOCOL_MODULE = "outreach_agent.protocols"
WORKFLOW_MODULE = "outreach_agent.workflow"
INTEGRATIONS_MODULE = "outreach_agent.integrations"


ALLOWED_PROTOCOL_EXTERNAL_PREFIXES = {
    "abc",
    "collections",
    "collections.abc",
    "dataclasses",
    "pydantic",
    "typing",
    "typing_extensions",
}


def production_python_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def module_name_from_path(path: Path) -> str:
    relative = path.relative_to(SRC_ROOT)
    return relative.with_suffix("").as_posix().replace("/", ".")


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                modules.add(node.module)

    return modules


def is_same_or_submodule(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def top_level_module(module: str) -> str:
    return module.split(".", maxsplit=1)[0]


def test_production_import_architecture_rules() -> None:
    violations: list[str] = []

    for path in production_python_files():
        module = module_name_from_path(path)
        imported = imported_modules(path)

        for imported_module in imported:
            if is_same_or_submodule(module, DOMAIN_MODULE):
                if (
                    imported_module.startswith("outreach_agent")
                    and not is_same_or_submodule(imported_module, DOMAIN_MODULE)
                ):
                    violations.append(
                        f"{module} imports {imported_module}, but domain must not "
                        "depend on application/protocol/integration modules"
                    )

            elif is_same_or_submodule(module, PROTOCOL_MODULE):
                if (
                    imported_module.startswith("outreach_agent")
                    and not (
                        is_same_or_submodule(imported_module, DOMAIN_MODULE)
                        or is_same_or_submodule(imported_module, PROTOCOL_MODULE)
                    )
                ):
                    violations.append(
                        f"{module} imports {imported_module}, but protocols may "
                        "only depend on domain and protocol layers"
                    )
                elif (
                    not imported_module.startswith("outreach_agent")
                    and top_level_module(imported_module)
                    not in ALLOWED_PROTOCOL_EXTERNAL_PREFIXES
                ):
                    violations.append(
                        f"{module} imports external dependency {imported_module}, "
                        "but protocols should only depend on standard/library "
                        "typing/contract dependencies"
                    )

            elif is_same_or_submodule(module, WORKFLOW_MODULE):
                if is_same_or_submodule(imported_module, INTEGRATIONS_MODULE):
                    violations.append(
                        f"{module} imports {imported_module}; "
                        "workflow/application orchestration must not "
                        "import concrete integrations"
                    )

            elif (
                module.startswith("outreach_agent")
                and not module.startswith(INTEGRATIONS_MODULE)
                and not module == COMPOSITION_ROOT
            ):
                if is_same_or_submodule(imported_module, INTEGRATIONS_MODULE):
                    violations.append(
                        f"{module} imports {imported_module}; only "
                        f"{COMPOSITION_ROOT} may import concrete integrations"
                    )

    assert not violations, "\n".join(violations)
