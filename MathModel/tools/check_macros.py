"""检查 texfile/*.tex 中引用的自定义宏是否都由 numbers.tex 生成。

避免"未定义控制序列"这类编译错误在正式编译时才暴露。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1] / "paper"
TEXFILE = PAPER / "texfile"

# 模板与 amsmath 等宏包已定义的常用宏，不参与检查
BUILTIN = {
    "section", "subsection", "subsubsection", "textbf", "emph", "cite", "ref", "eqref", "label",
    "includegraphics", "caption", "centering", "toprule", "midrule", "bottomrule", "item",
    "keywords", "maketitle", "thispagestyle", "begin", "end", "frac", "sqrt", "sum", "min",
    "max", "mathbb", "mathcal", "left", "right", "quad", "qquad", "text", "Delta", "eta",
    "pi", "pi_t", "times", "cdot", "ge", "le", "star", "varepsilon", "Phi", "Psi", "ell",
    "hat", "perp", "underbrace", "cases", "aligned", "forall", "in", "mid", "approx",
    "newpage", "phantomsection", "addcontentsline", "nocite", "bibliographystyle", "bibliography",
    "appendix", "zihao", "bfseries", "ttfamily", "input", "fbox", "makebox", "lstlisting",
    "lstdefinestyle", "lstset", "hypersetup", "documentclass", "usepackage", "title", "tihao",
    "baominghao", "schoolname", "yearinput", "monthinput", "dayinput", "pagenumbering",
    "renewcommand", "newcommand", "the", "arabic", "sfrac", "SI", "num", "ang", "textwidth",
    "linewidth", "arraystretch", "setlength", "vspace", "hspace", "noindent", "par", "relax",
    "hline", "cline", "multicolumn", "arraybackslash", "raggedright", "centering", "rowcolor",
    "toprule", "cmidrule", "addlinespace", "circ", "le", "lvert", "rvert", "colon", "partial",
    "overline", "underline", "mathrm", "operatorname", "log", "exp", "ln", "arg", "sim",
    "propto", "equiv", "neq", "pm", "mp", "infty", "int", "prod", "binom", "choose",
    "land", "lor", "neg", "Rightarrow", "Longrightarrow", "to", "mapsto", "subseteq", "in",
    "notin", "emptyset", "cup", "cap", "setminus", "subset", "supset", "geq", "leq",
    "mathbb{E}", "boldsymbol", "vec", "tilde", "bar", "dot", "ddot", "prime", "prime",
    "fontsize", "selectfont", "baselineskip", "topsep", "itemsep", "labelindent",
}


def defined_macros() -> set[str]:
    names: set[str] = set()
    path = PAPER / "numbers.tex"
    if path.exists():
        names |= set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", path.read_text(encoding="utf-8")))
    # 模板自带宏（cumcmthesis.cls 与 document.tex 中的定义）
    for extra in (PAPER / "cumcmthesis.cls", PAPER / "document.tex"):
        if extra.exists():
            text = extra.read_text(encoding="utf-8", errors="ignore")
            names |= set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", text))
            names |= set(re.findall(r"\\def\\([A-Za-z]+)", text))
    return names


def main() -> int:
    defined = defined_macros()
    missing: dict[str, list[str]] = {}
    used: set[str] = set()
    for path in sorted(TEXFILE.glob("*.tex")):
        text = path.read_text(encoding="utf-8")
        for name in re.findall(r"\\([A-Za-z]{2,})", text):
            if name in BUILTIN or name in defined:
                continue
            # 只在"看起来像自定义数值宏"时报告：首字母大写或含数字，或以 Q/Sens 开头
            if re.match(r"^(Q[A-Za-z]*|Sens|Delta|EOne|ETwo)", name) or re.match(r"^[A-Z][a-z]+[A-Z]", name):
                used.add(name)
                missing.setdefault(name, []).append(path.name)
    if missing:
        print("以下宏未在 numbers.tex 或模板中定义：")
        for name, files in sorted(missing.items()):
            print(f"  \\{name}  ← {', '.join(sorted(set(files)))}")
        return 1
    print("宏检查通过：论文引用的全部自定义宏均已在 numbers.tex 或模板中定义。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
