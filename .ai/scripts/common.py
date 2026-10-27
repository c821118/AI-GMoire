"""AI-GMoire 腳本共用工具：路徑、檔案讀寫、Markdown 章節解析、Token 估算。

只使用標準函式庫。`Hogwarts_TRPG_rules/` 與 `general_TRPG_rules/` 為唯讀來源，
本專案所有腳本都只會讀取、不會寫入這兩個資料夾。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
READ_ONLY_DIRS = ("rules/Hogwarts_TRPG_rules", "rules/general_TRPG_rules")


def setup_console():
    """Windows 主控台預設不是 UTF-8，輸出中文前先切換。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def read_text(path):
    """以 UTF-8 讀取，去除 BOM，統一換行為 LF。"""
    text = Path(path).read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def version():
    return read_text(ROOT / "VERSION").strip()


def assert_in_readonly(path):
    """防呆：禁止寫入唯讀來源資料夾。"""
    rel = Path(path).resolve().relative_to(ROOT)
    if any(rel.as_posix() == d or rel.as_posix().startswith(d + "/") for d in READ_ONLY_DIRS):
        raise PermissionError(f"禁止寫入唯讀來源：{rel}")


# ---------------------------------------------------------------- Markdown

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


class Node:
    """Markdown 章節樹的節點。body 為標題與下一個標題之間的文字。"""

    def __init__(self, level, title):
        self.level = level
        self.title = title
        self.body = ""
        self.children = []

    def find(self, title):
        """深度優先尋找標題完全相符的後代節點，找不到回傳 None。"""
        for child in self.children:
            if child.title == title:
                return child
            found = child.find(title)
            if found is not None:
                return found
        return None

    def get(self, title):
        node = self.find(title)
        if node is None:
            raise KeyError(f"找不到章節：{title}")
        return node

    def render(self, heading=True, children=True):
        """還原為 Markdown。保留原標題層級；區塊之間以空行分隔。"""
        parts = []
        if heading and self.level:
            head = "#" * self.level + " " + self.title
            parts.append(head + ("\n" + self.body if self.body else ""))
        elif self.body:
            parts.append(self.body)
        if children:
            parts.extend(child.render() for child in self.children)
        return "\n\n".join(parts)


def parse_markdown(text):
    """把 Markdown 解析成章節樹。程式碼區塊內的 # 不視為標題，單獨一行的 --- 視為分隔線略過。"""
    root = Node(0, "")
    stack = [root]
    current = root
    buf = []
    in_fence = False

    def flush():
        while buf and not buf[0].strip():
            buf.pop(0)
        while buf and not buf[-1].strip():
            buf.pop()
        current.body = "\n".join(buf)
        buf.clear()

    for line in text.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else _HEADING.match(line)
        if match:
            flush()
            node = Node(len(match.group(1)), match.group(2))
            while stack[-1].level >= node.level:
                stack.pop()
            stack[-1].children.append(node)
            stack.append(node)
            current = node
        elif not in_fence and line.strip() == "---":
            continue
        else:
            buf.append(line)
    flush()
    return root


def body_lines(text):
    """取出文字中有內容且非標題的行（去除首尾空白），供覆蓋率比對。"""
    lines = []
    in_fence = False
    for line in text.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        if not in_fence and _HEADING.match(line):
            continue
        lines.append(stripped)
    return lines


# ---------------------------------------------------------------- Token

_WIDE = re.compile(r"[ -⁯　-鿿＀-￯]")


def estimate_tokens(text):
    """粗估 Token：中日韓全形字約 1 token，其餘字元約 0.7 token。

    以 v1.0.0 的霍格華茲 1991 角色卡校正（估 3773，Chub 顯示 3814），僅供參考。
    """
    wide = len(_WIDE.findall(text))
    return round(wide + (len(text) - wide) * 0.7)
