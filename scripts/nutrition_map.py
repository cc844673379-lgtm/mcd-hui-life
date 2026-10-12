#!/usr/bin/env python3
"""把门店菜单餐品映射到麦当劳营养数据，并输出缺口清单。

纯本地确定性计算：不联网、不调用 MCP、不写除 --output 指定路径以外的文件。
仅使用 Python 标准库，要求 Python 3.10 及以上。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

BRAND_PREFIXES = ("麦咖啡", "麦当劳")
SYMBOLS_TO_DROP = ("™", "®", "©", "\u3000")
WRAPPER_KEYWORDS = ("盒装", "瓶装", "罐装")
# 饮品在菜单与营养表中的差异几乎只来自形态标记：杯型与冷热。剥离后才可能对齐。
SIZE_TOKENS = ("特大杯", "中杯", "大杯", "小杯")
TEMPERATURE_TOKENS = ("冰", "热")
VARIANT_SUFFIXES = ("(冰/热)", "(冷/热)", "(冰/热)")
# 组合餐的名称里常含单品名（如「吉士汉堡包套餐」含「吉士汉堡包」），
# 绝不允许把单品营养数据套用到组合餐上，必须按 roundList 拆解后分别取值再求和。
COMBO_MARKERS = (
    "套餐", "件套", "随心配", "随心选", "随心拼", "任选", "分享餐",
    "双人", "三人", "四人", "多人", "亲子餐", "乐园餐", "拼盘",
    "四宫格", "组合餐", "百宝袋", "全家桶",
)

NUTRIENT_KEYS = (
    "energyKj",
    "energyKcal",
    "protein",
    "fat",
    "carbohydrate",
    "sodium",
    "calcium",
)


def normalize(name: str) -> str:
    """归一化餐品名称，用于跨体系比对。"""
    text = str(name or "")
    for symbol in SYMBOLS_TO_DROP:
        text = text.replace(symbol, "")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(" ", "").replace("\t", "")
    for prefix in BRAND_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.strip().lower()


def strip_wrapper(name: str) -> str:
    """去掉末尾的包装说明括号组，例如 (盒装)。"""
    text = name
    while text.endswith(")") or text.endswith("）"):
        open_index = max(text.rfind("("), text.rfind("（"))
        if open_index <= 0:
            break
        inner = text[open_index + 1: -1]
        if not any(keyword in inner for keyword in WRAPPER_KEYWORDS):
            break
        text = text[:open_index]
    return text


def core_key(name: str) -> str:
    """剥离形态标记后的核心名，用于对齐「同一杯饮品的不同杯型与冷热」。

    只剥离杯型与冷热这两类标记，不做子串包含判断，避免把「奶铁雪冰」错配到「奶铁」。
    """
    text = normalize(name)
    changed = True
    while changed:
        changed = False
        for suffix in VARIANT_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)]
                changed = True
        for token in SIZE_TOKENS:
            if text.endswith(token) and len(text) > len(token):
                text = text[: -len(token)]
                changed = True
            elif text.startswith(token) and len(text) > len(token):
                text = text[len(token):]
                changed = True
        for token in TEMPERATURE_TOKENS:
            if text.startswith(token) and len(text) > len(token):
                text = text[len(token):]
                changed = True
    return text


def parse_nutrition_table(raw: str) -> list[dict[str, Any]]:
    """解析 list-nutrition-foods 的表格字符串。"""
    head = re.search(r"\[(\d+)\]\{([^}]*)\}\s*:", raw)
    if not head:
        raise ValueError("营养数据表头无法识别")
    columns = [item.strip() for item in head.group(2).split(",") if item.strip()]
    if "productName" not in columns:
        raise ValueError("营养数据缺少 productName 列")

    body = raw[head.end():]
    rows: list[dict[str, Any]] = []
    for line in body.splitlines():
        text = line.strip()
        if not text:
            continue
        parts = [item.strip() for item in text.split(",")]
        if len(parts) < len(columns):
            continue
        if len(parts) > len(columns):
            head_extra = len(parts) - len(columns) + 1
            parts = [",".join(parts[:head_extra])] + parts[head_extra:]
        rows.append(dict(zip(columns, parts)))
    if not rows:
        raise ValueError("营养数据没有可用行")
    return rows


def load_nutrition(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        for key in ("data", "nutritionFoods", "list"):
            if key in value:
                return load_nutrition(value[key])
        raise ValueError("营养数据对象中找不到 data 字段")
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("[") and "{" in text and "productName" in text:
            return parse_nutrition_table(text)
        parsed = json.loads(text)
        return load_nutrition(parsed)
    if isinstance(value, list):
        if not value:
            raise ValueError("营养数据为空")
        if all(isinstance(item, dict) for item in value):
            return value
        raise ValueError("营养数据数组元素必须是对象")
    raise ValueError("营养数据格式无法识别")


def load_menu(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        if "data" in value:
            return load_menu(value["data"])
        if "meals" in value and isinstance(value["meals"], dict):
            return load_menu(value["meals"])
        entries: list[dict[str, Any]] = []
        for code, detail in value.items():
            if isinstance(detail, dict):
                entries.append({"code": str(code), "name": detail.get("name", "")})
            elif isinstance(detail, str):
                entries.append({"code": str(code), "name": detail})
        if not entries:
            raise ValueError("菜单对象为空")
        return entries
    if isinstance(value, list):
        entries = []
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("菜单数组元素必须是对象")
            code = item.get("code", item.get("productCode", ""))
            entries.append({"code": str(code), "name": str(item.get("name", item.get("productName", "")))})
        if not entries:
            raise ValueError("菜单为空")
        return entries
    raise ValueError("菜单格式无法识别")


def to_number(value: Any) -> float | None:
    if value in (None, "", "null", "None"):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def dedupe(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """按归一化名分组；完全重复的行合并，值不同的保留为歧义。"""
    grouped: dict[str, list[dict[str, Any]]] = {}
    duplicate_names: list[str] = []
    for row in rows:
        key = normalize(row.get("productName", ""))
        if not key:
            continue
        grouped.setdefault(key, []).append(row)

    unique: list[dict[str, Any]] = []
    for key, items in grouped.items():
        signatures = {
            tuple(str(item.get(column, "")) for column in NUTRIENT_KEYS) for item in items
        }
        if len(signatures) > 1:
            duplicate_names.append(key)
        unique.append(items[0])
    return unique, duplicate_names


def build_index(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = normalize(row.get("productName", ""))
        if key:
            index.setdefault(key, []).append(row)
    return index


def pick_nutrients(row: dict[str, Any]) -> dict[str, float | None]:
    return {key: to_number(row.get(key)) for key in NUTRIENT_KEYS}


def map_menu(menu: list[dict[str, Any]], nutrition: list[dict[str, Any]]) -> dict[str, Any]:
    exact_index = build_index(nutrition)

    unwrapped_index: dict[str, list[dict[str, Any]]] = {}
    for row in nutrition:
        key = strip_wrapper(normalize(row.get("productName", "")))
        if key:
            unwrapped_index.setdefault(key, []).append(row)

    core_index: dict[str, list[dict[str, Any]]] = {}
    for row in nutrition:
        key = core_key(row.get("productName", ""))
        if key:
            core_index.setdefault(key, []).append(row)

    matched: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for item in menu:
        code = item["code"]
        name = item.get("name", "")
        key = normalize(name)

        if not name:
            missing.append({"code": code, "menu_name": name, "reason": "菜单缺少名称"})
            continue

        hits = exact_index.get(key, [])
        if hits and len({normalize(hit.get("productName", "")) for hit in hits}) == 1:
            first = hits[0]
            matched.append(
                {
                    "code": code,
                    "menu_name": name,
                    "nutrition_name": first.get("productName", ""),
                    "match_type": "exact",
                    "nutrients": pick_nutrients(first),
                }
            )
            continue

        loose_key = strip_wrapper(key)
        loose_hits: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        for hit in unwrapped_index.get(loose_key, []):
            hit_name = normalize(hit.get("productName", ""))
            if hit_name not in seen_names:
                seen_names.add(hit_name)
                loose_hits.append(hit)
        if len(loose_hits) == 1:
            first = loose_hits[0]
            matched.append(
                {
                    "code": code,
                    "menu_name": name,
                    "nutrition_name": first.get("productName", ""),
                    "match_type": "normalized",
                    "nutrients": pick_nutrients(first),
                }
            )
            continue

        if any(marker in name for marker in COMBO_MARKERS):
            missing.append(
                {
                    "code": code,
                    "menu_name": name,
                    "reason": "组合餐不适用单品营养数据，需按 roundList 拆解为子项后分别取值再求和",
                }
            )
            continue

        candidates: list[str] = []
        for row in nutrition:
            row_key = normalize(row.get("productName", ""))
            if not row_key or row_key == key:
                continue
            if row_key.startswith(key) or key.startswith(row_key):
                row_name = row.get("productName", "")
                if row_name not in candidates:
                    candidates.append(row_name)

        if len(candidates) == 1:
            target_key = normalize(candidates[0])
            row = exact_index[target_key][0]
            matched.append(
                {
                    "code": code,
                    "menu_name": name,
                    "nutrition_name": row.get("productName", ""),
                    "match_type": "containment",
                    "nutrients": pick_nutrients(row),
                }
            )
        elif len(candidates) > 1:
            ambiguous.append(
                {
                    "code": code,
                    "menu_name": name,
                    "reason": "名称可对应多个规格或口味，需用 query-meal-detail 取默认项或请用户指定",
                    "candidates": candidates,
                }
            )
        else:
            core_hits: list[dict[str, Any]] = []
            core_seen: set[str] = set()
            for hit in core_index.get(core_key(name), []):
                hit_name = hit.get("productName", "")
                if hit_name not in core_seen:
                    core_seen.add(hit_name)
                    core_hits.append(hit)
            if len(core_hits) == 1:
                first = core_hits[0]
                matched.append(
                    {
                        "code": code,
                        "menu_name": name,
                        "nutrition_name": first.get("productName", ""),
                        "match_type": "core",
                        "nutrients": pick_nutrients(first),
                    }
                )
            elif len(core_hits) > 1:
                ambiguous.append(
                    {
                        "code": code,
                        "menu_name": name,
                        "reason": "同一饮品存在多个杯型或冷热规格，需确定杯型与冷热后取值",
                        "candidates": [hit.get("productName", "") for hit in core_hits],
                    }
                )
            else:
                suffix_candidates: list[str] = []
                if key:
                    for row in nutrition:
                        row_key = normalize(row.get("productName", ""))
                        row_name = row.get("productName", "")
                        if row_key.endswith(key) and row_name not in suffix_candidates:
                            suffix_candidates.append(row_name)
                if len(suffix_candidates) == 1:
                    target_key = normalize(suffix_candidates[0])
                    row = exact_index[target_key][0]
                    matched.append(
                        {
                            "code": code,
                            "menu_name": name,
                            "nutrition_name": row.get("productName", ""),
                            "match_type": "category",
                            "nutrients": pick_nutrients(row),
                        }
                    )
                elif len(suffix_candidates) > 1:
                    ambiguous.append(
                        {
                            "code": code,
                            "menu_name": name,
                            "reason": "名称是品类名，对应多个口味或规格，需请用户指定后再取值",
                            "candidates": suffix_candidates,
                        }
                    )
                else:
                    missing.append(
                        {
                            "code": code,
                            "menu_name": name,
                            "reason": "营养数据中无对应条目",
                        }
                    )

    return {
        "summary": {
            "nutrition_count": len(nutrition),
            "menu_count": len(menu),
            "matched": len(matched),
            "ambiguous": len(ambiguous),
            "missing": len(missing),
        },
        "matched": matched,
        "ambiguous": ambiguous,
        "missing": missing,
        "notes": [
            "ambiguous 项必须先经 query-meal-detail 取默认规格消歧，或请用户指定口味后再使用。",
            "missing 项一律标记为「暂无营养数据」，不得估算或用同类餐品替代。",
            "匹配结果只解决名称对应关系，不代表可售；可售性以 calculate-price 为准。",
        ],
    }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把门店菜单餐品映射到营养数据并输出缺口清单")
    parser.add_argument("--nutrition", type=Path, required=True, help="营养数据文件，支持原始表格字符串或 JSON")
    parser.add_argument("--menu", type=Path, required=True, help="菜单文件，支持 query-meals 的 data.meals 或 {code,name} 数组")
    parser.add_argument("--output", type=Path, help="可选，映射结果输出路径")
    args = parser.parse_args(argv)

    try:
        nutrition_rows = load_nutrition(read_json(args.nutrition))
        menu_rows = load_menu(read_json(args.menu))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": f"输入无法解析：{exc}"}, ensure_ascii=False, indent=2))
        return 1

    unique_rows, duplicate_names = dedupe(nutrition_rows)
    report = map_menu(menu_rows, unique_rows)
    if duplicate_names:
        report["duplicate_nutrition_entries"] = sorted(duplicate_names)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(json.dumps({"status": "error", "error": f"写入失败：{exc}"}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({"status": "ok", "output": str(args.output), "summary": report["summary"]}, ensure_ascii=False, indent=2))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
