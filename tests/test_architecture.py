import ast
from pathlib import Path


def test_routes_do_not_import_sqlalchemy_or_infrastructure_models() -> None:
    route_files = Path("app/modules").glob("*/api/*.py")
    forbidden = ("sqlalchemy", ".infrastructure.models")

    for route_file in route_files:
        tree = ast.parse(route_file.read_text(), filename=str(route_file))
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)
        assert not any(
            marker in imported for imported in imported_modules for marker in forbidden
        ), f"{route_file} bypasses the application layer"
