#!/usr/bin/env python3
"""计算脂肪供能比并判定清淡档位。

纯本地确定性计算：不联网、不调用 MCP、不写除 --output 指定路径以外的文件。
仅使用 Python 标准库，要求 Python 3.10 及以上。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

KJ_PER_KCAL = 4.184
FAT_KCAL_PER_GRAM = 9
LIGHT_MAX = 0.35
MODERATE_MAX = 0.50

TIERS = (
    ("light", "不油腻"),
    ("moderate", "尚可"),
    ("greasy", "偏油腻"),
)


def to_number(value: Any) -> float | None:
    if value in (None, "", "null", "None"):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def energy_kcal(entry: dict[str, Any]) -> float | None:
    kcal = to_number(entry.get("energyKcal"))
    if kcal is not None:
        return kcal
    kj = to_number(entry.get("energyKj"))
    if kj is not None:
        return round(kj / KJ_PER_KCAL, 4)
    return None


def accumulate(entry: dict[str, Any]) -> dict[str, float | None]:
    quantity = to_number(entry.get("quantity"))
    factor = 1.0 if quantity is None else quantity

    totals: dict[str, float] = {"energyKcal": 0.0, "fat": 0.0, "protein": 0.0, "sodium": 0.0}
    present = {"energyKcal": False, "fat": False, "protein": False, "sodium": False}

    kcal = energy_kcal(entry)
    if kcal is not None:
        totals["energyKcal"] += kcal * factor
        present["energyKcal"] = True
    for field in ("fat", "protein", "sodium"):
        value = to_number(entry.get(field))
        if value is not None:
            totals[field] += value * factor
            present[field] = True

    return {
        "energyKcal": totals["energyKcal"] if present["energyKcal"] else None,
        "fat": totals["fat"] if present["fat"] else None,
        "protein": totals["protein"] if present["protein"] else None,
        "sodium": totals["sodium"] if present["sodium"] else None,
    }


def combine(items: list[dict[str, Any]]) -> dict[str, float | None]:
    sums: dict[str, float] = {"energyKcal": 0.0, "fat": 0.0, "protein": 0.0, "sodium": 0.0}
    present = {"energyKcal": False, "fat": False, "protein": False, "sodium": False}
    for item in items:
        part = accumulate(item)
        for field, value in part.items():
            if value is not None:
                sums[field] += value
                present[field] = True
    return {
        field: sums[field] if present[field] else None
        for field in ("energyKcal", "fat", "protein", "sodium")
    }


def classify(totals: dict[str, float | None]) -> tuple[str, str, str, float | None]:
    kcal = totals.get("energyKcal")
    fat = totals.get("fat")

    if kcal is None or fat is None:
        return "unknown", "数据不足", "缺少热量或脂肪数值，无法判定", None
    if kcal <= 0:
        return "zero_energy", "无法判定", "热量为 0，脂肪供能比没有定义", None

    ratio = round(fat * FAT_KCAL_PER_GRAM / kcal, 4)
    if ratio <= LIGHT_MAX:
        code, label = TIERS[0]
    elif ratio <= MODERATE_MAX:
        code, label = TIERS[1]
    else:
        code, label = TIERS[2]
    return code, label, f"脂肪供能比 {ratio * 100:.1f}%", ratio


def evaluate(entry: dict[str, Any]) -> dict[str, Any]:
    name = str(entry.get("name", entry.get("餐品", "")))
    items = entry.get("items")
    if isinstance(items, list) and items:
        totals = combine([item for item in items if isinstance(item, dict)])
        components = [str(item.get("name", "")) for item in items if isinstance(item, dict)]
        items_value: Any = components
    else:
        totals = accumulate(entry)
        items_value = None

    code, label, detail, ratio = classify(totals)
    result: dict[str, Any] = {
        "name": name,
        "energyKcal": None if totals["energyKcal"] is None else round(totals["energyKcal"], 2),
        "fat": None if totals["fat"] is None else round(totals["fat"], 2),
        "protein": None if totals["protein"] is None else round(totals["protein"], 2),
        "sodium": None if totals["sodium"] is None else round(totals["sodium"], 2),
        "fatEnergyRatio": ratio,
        "fatEnergyPercent": None if ratio is None else f"{ratio * 100:.1f}%",
        "tierCode": code,
        "tier": label,
        "detail": detail,
    }
    if items_value is not None:
        result["components"] = items_value
    return result


def load_entries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        for key in ("dishes", "items", "data", "results"):
            if key in value:
                return load_entries(value[key])
        return [value]
    if isinstance(value, list):
        if not value:
            raise ValueError("输入为空")
        if not all(isinstance(item, dict) for item in value):
            raise ValueError("数组元素必须是对象")
        return value
    raise ValueError("输入格式无法识别")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="计算脂肪供能比并判定清淡档位")
    parser.add_argument("--input", type=Path, required=True, help="餐品或方案 JSON")
    parser.add_argument("--output", type=Path, help="可选，结果输出路径")
    args = parser.parse_args(argv)

    try:
        entries = load_entries(json.loads(args.input.read_text(encoding="utf-8-sig")))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": f"输入无法解析：{exc}"}, ensure_ascii=False, indent=2))
        return 1

    results = [evaluate(entry) for entry in entries]
    report = {
        "thresholds": {
            "light": f"脂肪供能比 <= {LIGHT_MAX:.2f}",
            "moderate": f"{LIGHT_MAX:.2f} < 脂肪供能比 <= {MODERATE_MAX:.2f}",
            "greasy": f"脂肪供能比 > {MODERATE_MAX:.2f}",
        },
        "results": results,
        "notes": [
            "档位只由脂肪供能比自算得出，不得凭餐品名或直觉判定。",
            "「尚可」不得表述为「不油腻」，「偏油腻」不得表述为「尚可」。",
            "纯乳制品脂肪供能比天然偏高，输出时保留实算档位并加注说明，不额外升级为警告。",
            "组合方案按组成品求和后重新计算，不使用单品档位代替。",
        ],
    }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(json.dumps({"status": "error", "error": f"写入失败：{exc}"}, ensure_ascii=False, indent=2))
            return 1
        summary = [
            {"name": item["name"], "tier": item["tier"], "fatEnergyPercent": item["fatEnergyPercent"]}
            for item in results
        ]
        print(json.dumps({"status": "ok", "output": str(args.output), "results": summary}, ensure_ascii=False, indent=2))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
