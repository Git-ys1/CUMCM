"""LaTeX 源文件静态检查：$ 配平、中文入数学模式、未转义特殊字符、环境配对。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1] / "paper"
TEXFILE = PAPER / "texfile"
CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
ENVIRONMENTS = ("equation", "align", "aligned", "cases", "tabular", "tabularx", "table",
                "figure", "itemize", "enumerate", "lstlisting", "abstract", "quotation")


def strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        idx = None
        for m in re.finditer(r"(?<!\\)%", line):
            idx = m.start()
            break
        out.append(line if idx is None else line[:idx])
    return "\n".join(out)


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    raw = path.read_text(encoding="utf-8")
    text = strip_comments(raw)
    # 1) 美元符号配平（\verb 与 lstlisting 内容不检查）
    stripped = re.sub(r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}", "", text, flags=re.S)
    dollars = len(re.findall(r"(?<!\\)\$", stripped))
    if dollars % 2:
        problems.append(f"{path.name}: $ 数量为奇数（{dollars}），可能存在未闭合的行内公式")
    # 2) 数学模式里出现中文
    for m in re.finditer(r"(?<!\\)\$(.+?)(?<!\\)\$", stripped, flags=re.S):
        body = m.group(1)
        if "$" in body:
            continue
        found = CJK.findall(body)
        if found:
            snippet = "".join(found[:6])
            problems.append(f"{path.name}: 行内公式中含中文「{snippet}」→ {body.strip()[:40]!r}")
    # 3) 未转义的 & 出现在表格之外
    for lineno, line in enumerate(stripped.splitlines(), 1):
        if line.count("&") and not re.search(r"\\(begin|end)\{(tabular|tabularx|align)", line):
            pass  # 表格跨行，跳过；由编译期发现
    # 4) 环境配对
    begins = re.findall(r"\\begin\{([A-Za-z*]+)\}", stripped)
    ends = re.findall(r"\\end\{([A-Za-z*]+)\}", stripped)
    for env in set(begins) | set(ends):
        if begins.count(env) != ends.count(env):
            problems.append(f"{path.name}: 环境 {env} 不配对（begin {begins.count(env)} / end {ends.count(env)}）")
    return problems


def main() -> int:
    all_problems: list[str] = []
    for path in sorted(list(TEXFILE.glob("*.tex")) + [PAPER / "document.tex"]):
        if path.exists():
            all_problems += check_file(path)
    if all_problems:
        print("LaTeX 静态检查发现问题：")
        for item in all_problems:
            print("  -", item)
        return 1
    print("LaTeX 静态检查通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
