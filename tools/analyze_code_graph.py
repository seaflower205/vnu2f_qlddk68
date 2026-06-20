# -*- coding: utf-8 -*-
"""Build and validate the plugin's source-derived dependency graph.

The graph is deliberately regenerated from Python ASTs.  Generated reports are
diagnostics in ``scratch/code_graph``; policy lives in ``code_graph_rules.json``.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = Path(__file__).with_name("code_graph_rules.json")
REPORT_DIR = ROOT / "scratch" / "code_graph"
EDGE_KINDS = {"static_import", "lazy_import"}


def load_rules(path: Path = RULES_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def discover_sources(root: Path, rules: dict[str, Any]) -> dict[str, Path]:
    paths: list[Path] = []
    tool_modules: dict[Path, str] = {}
    for source in rules["source_roots"]:
        candidate = root / source
        if candidate.is_file():
            paths.append(candidate)
        elif candidate.is_dir():
            paths.extend(candidate.rglob("*.py"))
    for prefix in rules.get("allowed_tools_prefixes", []):
        candidate = root / prefix
        if candidate.is_dir():
            for path in candidate.rglob("*.py"):
                paths.append(path)
                rel = path.relative_to(candidate).with_suffix("")
                parts = [candidate.name, *rel.parts]
                if parts[-1] == "__init__":
                    parts.pop()
                tool_modules[path] = ".".join(parts)

    excluded = set(rules.get("excluded_path_parts", []))
    sources: dict[str, Path] = {}
    for path in sorted(set(paths)):
        rel_parts = path.relative_to(root).parts
        if excluded.intersection(rel_parts) or any(
            part.startswith("backup_modules_") for part in rel_parts
        ):
            continue
        sources[tool_modules.get(path, _module_name(path, root))] = path
    return sources


def _resolve_relative(current: str, imported: str | None, level: int) -> str:
    package = current.removesuffix(".__init__") if current.endswith(".__init__") else current.rpartition(".")[0]
    parts = package.split(".") if package else []
    keep = max(0, len(parts) - level + 1)
    prefix = parts[:keep]
    if imported:
        prefix.extend(imported.split("."))
    return ".".join(prefix)


def _known_module(name: str, known: set[str]) -> str | None:
    probe = name
    while probe:
        if probe in known:
            return probe
        probe = probe.rpartition(".")[0]
    return None


def _expr_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expr_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def _top_level_symbols(tree: ast.Module) -> list[str]:
    """Names available from a module, including compatibility re-exports."""
    symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for item in node.names:
                if item.name != "*":
                    symbols.add(item.asname or item.name.split(".")[0])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            symbols.update(target.id for target in targets if isinstance(target, ast.Name))
    return sorted(symbols)


@dataclass
class ModuleVisitor(ast.NodeVisitor):
    module: str
    known: set[str]
    edges: list[dict[str, Any]]
    references: list[dict[str, Any]]
    aliases: dict[str, str] = field(default_factory=dict)
    function_depth: int = 0
    is_package: bool = False

    def _import_reference(self, target: str, kind: str, node: ast.AST) -> None:
        self.references.append({
            "module": self.module, "kind": kind, "target": target,
            "line": getattr(node, "lineno", 0), "confidence": "high",
        })

    def _edge(self, target_name: str, kind: str, node: ast.AST, confidence: str = "high") -> None:
        target = _known_module(target_name, self.known)
        if target and target != self.module:
            self.edges.append({
                "source": self.module, "target": target, "kind": kind,
                "line": getattr(node, "lineno", 0), "confidence": confidence,
            })

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        kind = "lazy_import" if self.function_depth else "static_import"
        for item in node.names:
            self.aliases[item.asname or item.name.split(".")[0]] = item.name
            self._import_reference(item.name, kind, node)
            self._edge(item.name, kind, node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        current = f"{self.module}.__init__" if self.is_package else self.module
        base = _resolve_relative(current, node.module, node.level) if node.level else (node.module or "")
        kind = "lazy_import" if self.function_depth else "static_import"
        for item in node.names:
            candidate = f"{base}.{item.name}" if base else item.name
            self.aliases[item.asname or item.name] = candidate
            self._import_reference(candidate, kind, node)
            self._edge(candidate, kind, node)
        self._import_reference(base, kind, node)
        self._edge(base, kind, node)

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "connect"
            and isinstance(node.func.value, ast.Attribute)
            and node.args
        ):
            target_expr = _expr_name(node.args[0])
            root_name = target_expr.split(".")[0]
            imported = self.aliases.get(root_name)
            target_module = _known_module(imported or "", self.known)
            ref = {
                "module": self.module, "kind": "signal_slot",
                "signal": _expr_name(node.func.value), "target": target_expr,
                "line": node.lineno, "confidence": "high" if target_module else "medium",
            }
            self.references.append(ref)
            if target_module:
                self._edge(target_module, "signal_slot", node, ref["confidence"])

        if isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2:
            attr = node.args[1]
            if isinstance(attr, ast.Constant) and isinstance(attr.value, str):
                owner = _expr_name(node.args[0])
                root_name = owner.split(".")[0]
                imported = self.aliases.get(root_name, owner)
                target_module = _known_module(imported, self.known)
                self.references.append({
                    "module": self.module, "kind": "dynamic_getattr", "owner": owner,
                    "target": attr.value, "line": node.lineno,
                    "confidence": "high" if target_module else "medium",
                })
                if target_module:
                    self._edge(target_module, "dynamic_getattr", node, "high")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if not isinstance(node.value, str) or "." not in node.value or len(node.value) > 200:
            return
        candidate = node.value.removeprefix("vnu2f_qlddk68.")
        if candidate.startswith("."):
            level = len(candidate) - len(candidate.lstrip("."))
            candidate = _resolve_relative(self.module, candidate[level:], level)
        target = _known_module(candidate, self.known)
        if target:
            self.references.append({
                "module": self.module, "kind": "string_registry", "target": node.value,
                "line": node.lineno, "confidence": "low",
            })
            self._edge(target, "string_registry", node, "low")

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        # Resolve common registries such as f"{top_package}.cadastral_tools.ui.qa_tab".
        suffix = "".join(
            value.value for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        ).lstrip(".")
        target = _known_module(suffix, self.known)
        if target:
            self.references.append({
                "module": self.module, "kind": "string_registry", "target": suffix,
                "line": node.lineno, "confidence": "medium",
            })
            self._edge(target, "string_registry", node, "medium")
        self.generic_visit(node)


def build_graph(root: Path = ROOT, rules: dict[str, Any] | None = None) -> dict[str, Any]:
    rules = rules or load_rules()
    sources = discover_sources(root, rules)
    known = set(sources)
    edges: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    for module, path in sources.items():
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        symbols = _top_level_symbols(tree)
        nodes.append({"id": module, "path": path.relative_to(root).as_posix(), "symbols": symbols})
        ModuleVisitor(
            module, known, edges, references, is_package=path.name == "__init__.py"
        ).visit(tree)

    unique_edges = list({
        (e["source"], e["target"], e["kind"], e["line"]): e for e in edges
    }.values())
    return {
        "schema_version": 1,
        "nodes": sorted(nodes, key=lambda item: item["id"]),
        "edges": sorted(unique_edges, key=lambda e: (e["source"], e["target"], e["kind"], e["line"])),
        "references": sorted(references, key=lambda r: (r["module"], r["line"], r["kind"])),
    }


def _strong_components(nodes: Iterable[str], adjacency: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in adjacency.get(node, set()):
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component: list[str] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node in nodes:
        if node not in indices:
            visit(node)
    return sorted(components)


def validate_graph(graph: dict[str, Any], rules: dict[str, Any] | None = None) -> list[str]:
    rules = rules or load_rules()
    node_map = {node["id"]: node for node in graph["nodes"]}
    errors: list[str] = []
    adjacency: dict[str, set[str]] = {}
    incoming = {name: 0 for name in node_map}
    for edge in graph["edges"]:
        if edge["kind"] in EDGE_KINDS:
            adjacency.setdefault(edge["source"], set()).add(edge["target"])
        incoming[edge["target"]] = incoming.get(edge["target"], 0) + 1
        source_parts, target_parts = edge["source"].split("."), edge["target"].split(".")
        if "core" in source_parts and "ui" in target_parts:
            errors.append(f"Forbidden core -> ui dependency: {edge['source']} -> {edge['target']}")

    allowed_cycles = {tuple(sorted(item)) for item in rules.get("cycle_allowlist", [])}
    for component in _strong_components(node_map, adjacency):
        if tuple(component) not in allowed_cycles:
            errors.append("New dependency cycle: " + " <-> ".join(component))

    allowed_orphans = set(rules.get("orphan_allowlist", []))
    entry_modules = set(rules.get("entry_modules", []))
    for module, count in sorted(incoming.items()):
        is_package = node_map[module]["path"].endswith("/__init__.py")
        if count == 0 and not is_package and module not in entry_modules and module not in allowed_orphans:
            errors.append(f"Orphan runtime module: {module}")

    for module, symbols in rules.get("required_public_api", {}).items():
        node = node_map.get(module)
        if not node:
            errors.append(f"Required public module is missing: {module}")
            continue
        missing = sorted(set(symbols) - set(node["symbols"]))
        if missing:
            errors.append(f"Required public symbols missing from {module}: {', '.join(missing)}")

    forbidden_roots = tuple(rules.get("forbidden_import_roots", []))
    allowed_tools = tuple(rules.get("allowed_tools_modules", []))
    for reference in graph["references"]:
        if reference["kind"] not in EDGE_KINDS:
            continue
        target = reference["target"]
        forbidden = any(
            target == root or target.startswith(f"{root}.") or (root.endswith("_") and target.startswith(root))
            for root in forbidden_roots
        )
        allowed = any(target == root or target.startswith(f"{root}.") for root in allowed_tools)
        if forbidden and not allowed:
            errors.append(f"Forbidden runtime import: {reference['module']} -> {target}")
    return sorted(set(errors))


def write_reports(graph: dict[str, Any], output_dir: Path = REPORT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "code_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# Runtime code graph", "", "```mermaid", "flowchart LR"]
    for node in graph["nodes"]:
        safe = node["id"].replace(".", "_").replace("-", "_")
        lines.append(f'    {safe}["{node["id"]}"]')
    style = {"static_import": "-->", "lazy_import": "-.->", "signal_slot": "==>"}
    for edge in graph["edges"]:
        source = edge["source"].replace(".", "_").replace("-", "_")
        target = edge["target"].replace(".", "_").replace("-", "_")
        arrow = style.get(edge["kind"], "-.->")
        lines.append(f'    {source} {arrow}|"{edge["kind"]}"| {target}')
    lines.extend(["```", "", "Solid: static import; dashed: lazy/dynamic; thick: signal-slot.", ""])
    (output_dir / "code_graph.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate graph against committed rules")
    parser.add_argument("--no-write", action="store_true", help="Do not write scratch reports")
    args = parser.parse_args()
    rules = load_rules()
    graph = build_graph(rules=rules)
    if not args.no_write:
        write_reports(graph)
        print(f"Code graph: {len(graph['nodes'])} modules, {len(graph['edges'])} edges")
        print(f"Reports: {REPORT_DIR}")
    errors = validate_graph(graph, rules) if args.check else []
    for error in errors:
        print(f"FAIL {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
