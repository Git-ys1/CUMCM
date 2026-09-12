"""生成供 LaTeX 附录引用的无注释代码副本。"""
from __future__ import annotations

import ast
import io
import shutil
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "paper" / "code"

FILES = [
    ("solve/params.py", "params.py"),
    ("solve/io_data.py", "io_data.py"),
    ("solve/lp_core.py", "lp_core.py"),
    ("solve/forecast.py", "forecast.py"),
    ("solve/load_forecast.py", "load_forecast.py"),
    ("solve/price_forecast.py", "price_forecast.py"),
    ("solve/settle.py", "settle.py"),
    ("solve/q1.py", "q1.py"),
    ("solve/q2.py", "q2.py"),
    ("solve/q3.py", "q3.py"),
    ("solve/q4.py", "q4.py"),
    ("solve/export.py", "export.py"),
    ("solve/ablation.py", "ablation.py"),
    ("solve/official_forecast.py", "official_forecast.py"),
    ("solve/paper_tables.py", "paper_tables.py"),
    ("solve/validate_q2.py", "validate_q2.py"),
    ("solve/validate_all.py", "validate_all.py"),
    ("solve/build_manifest.py", "build_manifest.py"),
    ("solve/plot_style.py", "plot_style.py"),
    ("solve/fig_data.py", "fig_data.py"),
    ("solve/fig_q1.py", "fig_q1.py"),
    ("solve/fig_results.py", "fig_results.py"),
    ("solve/fig_route.py", "fig_route.py"),
    ("solve/plot_results.py", "plot_results.py"),
    ("tests/mutate.py", "mutate.py"),
    ("tests/test_causality.py", "test_causality.py"),
    ("tests/test_q2_q3.py", "test_q2_q3.py"),
    ("tests/test_paper_consistency.py", "test_paper_consistency.py"),
    ("tests/test_settlement.py", "test_settlement.py"),
    ("tests/test_regression.py", "test_regression.py"),
]


_DOCSTRING_PARENTS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _is_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _docstring_spans(tree: ast.AST) -> list[tuple[int, int, bool]]:
    spans: list[tuple[int, int, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_PARENTS) or not node.body:
            continue
        first = node.body[0]
        if _is_docstring(first):
            spans.append((first.lineno, first.end_lineno or first.lineno, len(node.body) == 1))
    return spans


class _RemoveDocstrings(ast.NodeTransformer):
    def _visit_body(self, node: ast.AST) -> ast.AST:
        self.generic_visit(node)
        body = node.body
        if body and _is_docstring(body[0]):
            node.body = body[1:] or [ast.Pass()]
        return node

    visit_Module = _visit_body
    visit_ClassDef = _visit_body
    visit_FunctionDef = _visit_body
    visit_AsyncFunctionDef = _visit_body


def _normalized_ast(source: str) -> str:
    tree = _RemoveDocstrings().visit(ast.parse(source))
    return ast.dump(tree, include_attributes=False)


def _strip_for_appendix(source: str, source_name: str) -> str:
    original_tree = ast.parse(source, filename=source_name)
    lines = source.splitlines(keepends=True)
    for start, end, needs_pass in sorted(_docstring_spans(original_tree), reverse=True):
        indent = lines[start - 1][: len(lines[start - 1]) - len(lines[start - 1].lstrip())]
        lines[start - 1] = f"{indent}pass\n" if needs_pass else "\n"
        for index in range(start, end):
            lines[index] = "\n"

    tokens: list[tokenize.TokenInfo] = []
    for token in tokenize.generate_tokens(io.StringIO("".join(lines)).readline):
        if token.type == tokenize.COMMENT:
            token = tokenize.TokenInfo(token.type, "", token.start, token.end, token.line)
        tokens.append(token)
    without_comments = tokenize.untokenize(tokens)

    protected_lines: set[int] = set()
    for token in tokenize.generate_tokens(io.StringIO(without_comments).readline):
        if token.type == tokenize.STRING and token.start[0] != token.end[0]:
            protected_lines.update(range(token.start[0], token.end[0] + 1))
    compact = [
        line.rstrip()
        for number, line in enumerate(without_comments.splitlines(), start=1)
        if line.strip() or number in protected_lines
    ]
    output = "\n".join(compact) + "\n"

    compile(output, source_name, "exec")
    if _normalized_ast(source) != _normalized_ast(output):
        raise ValueError(f"去注释后 AST 不一致：{source_name}")
    if any(
        token.type == tokenize.COMMENT
        for token in tokenize.generate_tokens(io.StringIO(output).readline)
    ):
        raise ValueError(f"代码副本仍含注释：{source_name}")
    if _docstring_spans(ast.parse(output, filename=source_name)):
        raise ValueError(f"代码副本仍含文档字符串：{source_name}")
    return output


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    expected = {name for _, name in FILES}
    for stale in TARGET.glob("*.py"):
        if stale.name not in expected:
            stale.unlink()
    missing = []
    for source, name in FILES:
        path = ROOT / source
        if not path.exists():
            missing.append(source)
            continue
        raw = path.read_text(encoding="utf-8-sig")
        cleaned = _strip_for_appendix(raw, source)
        target = TARGET / name
        target.write_text(cleaned, encoding="utf-8", newline="\n")
        shutil.copystat(path, target)
        removed = raw.count("\n") - cleaned.count("\n")
        print(f"[sync] {source} -> paper/code/{name} (精简 {removed} 行)")
    if missing:
        print("[sync][missing]", missing)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
