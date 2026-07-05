from __future__ import annotations

import json
import re
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
ROOT_ORG_ID = "https://코칭학원.com/#organization"

LOCAL_PATTERN = re.compile(r'"name":"(와와학습코칭센터 [^"]+)","url":')


def enhance_root(index_file: Path) -> bool:
    text = index_file.read_text(encoding="utf-8")
    if "alternateName" in text:
        return False
    old = (
        '      "name": "와와학습코칭학원",\n'
        '      "url": "https://코칭학원.com/",\n'
        '      "logo":'
    )
    new = (
        '      "name": "와와학습코칭학원",\n'
        '      "alternateName": ["와와학습코칭센터", "와와학원", "코칭학원"],\n'
        '      "url": "https://코칭학원.com/",\n'
        '      "logo":'
    )
    if old not in text:
        print(f"WARN root anchor not found: {index_file}")
        return False
    index_file.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def enhance_local(index_file: Path) -> bool:
    text = index_file.read_text(encoding="utf-8")
    if "alternateName" in text:
        return False

    match = LOCAL_PATTERN.search(text)
    if not match:
        print(f"WARN local anchor not found: {index_file}")
        return False

    name = match.group(1)
    academy_variant = name.replace("코칭센터", "코칭학원")
    alt_names = [academy_variant, "와와학습코칭학원", "와와학습코칭센터", "와와학원"]
    alt_json = json.dumps(alt_names, ensure_ascii=False)
    replacement = (
        f'"name":"{name}","alternateName":{alt_json},'
        f'"branchOf":{{"@id":"{ROOT_ORG_ID}"}},"url":'
    )
    new_text = text[: match.start()] + replacement + text[match.end():]
    index_file.write_text(new_text, encoding="utf-8")
    return True


def validate_jsonld(index_file: Path) -> None:
    text = index_file.read_text(encoding="utf-8")
    m = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', text, re.S
    )
    if not m:
        return
    json.loads(m.group(1))


def main() -> None:
    root_index = SITE / "index.html"
    root_changed = enhance_root(root_index)
    validate_jsonld(root_index)

    changed = 0
    skipped = 0
    warned = 0
    for f in sorted(SITE.glob("전국센터/**/index.html")):
        try:
            ok = enhance_local(f)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {f}: {exc}")
            warned += 1
            continue
        if ok:
            changed += 1
            try:
                validate_jsonld(f)
            except Exception as exc:  # noqa: BLE001
                print(f"JSON-LD BROKEN after edit: {f}: {exc}")
                warned += 1
        else:
            skipped += 1

    print(f"root_changed={root_changed}")
    print(f"local_changed={changed} skipped={skipped} warned={warned}")


if __name__ == "__main__":
    main()
