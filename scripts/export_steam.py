#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
SPACE_RE = re.compile(r"\s+")


@dataclass
class TableRow:
    item: str
    ingredients: str
    yield_text: str


def strip_markdown(text: str) -> str:
    text = LINK_RE.sub(r"\1", text)
    text = text.replace("\\|", "|")
    text = text.replace("`", "")
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = SPACE_RE.sub(" ", text)
    return text.strip()


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(SEPARATOR_RE.fullmatch(cell.replace(" ", "")) for cell in cells)


def row_to_record(cells: list[str], header_index: dict[str, int]) -> TableRow | None:
    try:
        item = strip_markdown(cells[header_index["item"]])
        ingredients = strip_markdown(cells[header_index["ingredients"]])
        yield_text = strip_markdown(cells[header_index["yield"]])
    except (IndexError, KeyError):
        return None

    if not item:
        return None

    return TableRow(item=item, ingredients=ingredients, yield_text=yield_text)


def header_mapping(headers: list[str]) -> dict[str, int] | None:
    normalized = [strip_markdown(header) for header in headers]

    aliases = {
        "item": ("物品", "Item"),
        "ingredients": ("材料", "Ingredients", "Crafting Materials"),
        "yield": ("解构产物", "Deconstruction Yield"),
    }

    mapping: dict[str, int] = {}
    for key, names in aliases.items():
        for idx, header in enumerate(normalized):
            if header in names:
                mapping[key] = idx
                break

    if len(mapping) != 3:
        return None
    return mapping


def render_table(block: list[str]) -> list[str]:
    if len(block) < 2:
        return [strip_markdown(line) for line in block]

    headers = split_markdown_row(block[0])
    separator = split_markdown_row(block[1])
    mapping = header_mapping(headers)

    if mapping is None or not is_separator_row(separator):
        return [strip_markdown(line) for line in block]

    grouped: OrderedDict[tuple[str, str], list[str]] = OrderedDict()
    for raw_row in block[2:]:
        cells = split_markdown_row(raw_row)
        record = row_to_record(cells, mapping)
        if record is None:
            continue

        key = (record.ingredients, record.yield_text)
        names = grouped.setdefault(key, [])
        if record.item not in names:
            names.append(record.item)

    rendered = ["[table]", "[tr][th]物品[/th][th]材料[/th][th]解构产物[/th][/tr]"]
    for (ingredients, yield_text), names in grouped.items():
        item_text = "、".join(names)
        rendered.append(
            f"[tr][td]{item_text}[/td][td]{ingredients}[/td][td]{yield_text}[/td][/tr]"
        )
    rendered.append("[/table]")
    return rendered


def convert_markdown_to_steam(source: str) -> str:
    lines = source.splitlines()
    output: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()

        if line.strip().startswith("|"):
            table_block: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_block.append(lines[index].rstrip())
                index += 1
            output.extend(render_table(table_block))
            continue

        stripped = line.strip()
        if not stripped:
            if output and output[-1] != "":
                output.append("")
            index += 1
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            level = 1 if len(heading.group(1)) == 1 else 2
            title = strip_markdown(heading.group(2))
            output.append(f"[h{level}]{title}[/h{level}]")
            index += 1
            continue

        output.append(strip_markdown(stripped))
        index += 1

    while output and output[-1] == "":
        output.pop()

    return "\n".join(output) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export Barotrauma crafting markdown to Steam BBCode tables."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="crafting-tables.md",
        help="Source markdown file.",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="crafting-tables-steam.txt",
        help="Target Steam-compatible text file.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    steam_text = convert_markdown_to_steam(input_path.read_text(encoding="utf-8"))
    output_path.write_text(steam_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())