from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "pdf"
OUTPUT = ROOT / "src" / "data" / "wordBank.json"


def has_chinese(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def parse_list(block: str, list_number: int) -> list[dict[str, object]]:
    lines = block.splitlines()
    word_line = re.compile(r"^\s*([A-Za-z][A-Za-z-']*)\b(.*)$")
    candidates: list[tuple[int, str, str]] = []

    for index, line in enumerate(lines):
        normalized_line = re.sub(r"^\s*【拓展】\s*", "", line)
        match = word_line.match(normalized_line)
        if not match:
            continue

        word, rest = match.groups()
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        # A dictionary entry is followed by its pronunciation, either on the
        # same line or on the next line. This filters out example sentences.
        if "/" not in rest and not next_line.lstrip().startswith("/"):
            continue
        if len(word) < 2 or word.lower() in {
            "list", "the", "pride", "bullying", "ad", "adv", "n", "v", "vi", "vt", "http", "https"
        }:
            continue
        candidates.append((index, word.lower(), rest.strip()))

    entries: list[dict[str, object]] = []
    seen: set[str] = set()
    for item_index, (line_index, word, rest) in enumerate(candidates):
        end = candidates[item_index + 1][0] if item_index + 1 < len(candidates) else len(lines)
        definition_parts: list[str] = []
        inline = re.sub(r"/[^/]+/", " ", rest)
        if has_chinese(inline):
            definition_parts.append(inline)

        for line in lines[line_index + 1 : end]:
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("【"):
                continue
            if clean_line.startswith("/"):
                pronunciation_tail = re.sub(r"^/[^/]+/\s*", "", clean_line)
                if has_chinese(pronunciation_tail):
                    definition_parts.append(pronunciation_tail)
                    break
                continue
            if has_chinese(clean_line):
                definition_parts.append(clean_line)
            if definition_parts:
                break

        # A page break can place a short definition immediately before the
        # word. Use it only when the normal forward lookup found nothing.
        if not definition_parts:
            previous_start = candidates[item_index - 1][0] + 1 if item_index else 0
            for line in reversed(lines[previous_start:line_index]):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("【") or clean_line.startswith("/"):
                    continue
                if has_chinese(clean_line):
                    definition_parts.append(clean_line)
                    break

        meaning = re.sub(r"\s+", " ", " ".join(definition_parts)).strip(" ：:，,。.")
        meaning = re.sub(r"^(?:a|ad|adv|n|v|vi|vt|prep|conj|pron|num|aux)\.?\s*", "", meaning)
        if word in seen:
            continue
        seen.add(word)
        entries.append({
            "id": f"list-{list_number}-{len(entries) + 1}",
            "list": list_number,
            "word": word,
            "meaning": meaning or "请结合词书原文复习该词义",
        })
    return entries


def main() -> None:
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit("No PDF found in pdf/")
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        raise SystemExit("pdftotext is required to extract the wordbook")

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp:
        text_path = Path(temp.name)
    try:
        subprocess.run(
            [pdftotext, "-layout", str(pdfs[0]), str(text_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        text = text_path.read_text(encoding="utf-8")
    finally:
        text_path.unlink(missing_ok=True)

    headers = list(re.finditer(r"\f[^\n]*List\s+(\d+)", text))
    if len(headers) < 20:
        raise SystemExit(f"Expected 20 Lists, found {len(headers)}")

    words: list[dict[str, object]] = []
    for index, header in enumerate(headers[:20]):
        list_number = int(header.group(1))
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        words.extend(parse_list(text[header.end() : end], list_number))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(words, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {number: sum(1 for item in words if item["list"] == number) for number in range(1, 21)}
    print(json.dumps({"total": len(words), "lists": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
