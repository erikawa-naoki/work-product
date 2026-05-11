#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
p4_0_output_infer_result.py
- <timestamp> 直下に inference_<時刻>/ を作り、推論時の計算コストを保存
- 見た目は学習時の出力と揃える（costs/infer_cost.* と GPU時系列）
- 実装は p4_0_output_train_result.py の保存ロジックを内部利用して統一感を確保
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json
import sys

# 同ディレクトリ or PYTHONPATH 前提
import src.p4_0_output_train_result as train_out  # _save_and_print_training_cost を流用

_RED = "\033[31m"; _RESET = "\033[0m"
def _warn(msg: str): print(f"{_RED}[WARN]{_RESET} {msg}", file=sys.stderr)

def _make_infer_dir(ts_dir: Path) -> Path:
    """<ts>/inference_<YYYY-mm-dd_HH-MM-SS>/ を作成"""
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = ts_dir / f"inference_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    return out

def output_infer_run(*,
                     ts_dir: Path,
                     infer_cost: Dict[str, str],
                     extra_meta: Optional[Dict[str, Any]] = None) -> None:
    """
    推論一回分のコストを <ts>/inference_*/ 以下に保存。

    Parameters
    ----------
    ts_dir : Path
        学習成果物のタイムスタンプディレクトリ（例: result/2025-10-29_21-00-00）
    infer_cost : Dict[str, str]
        {"json_str": "...", "csv_header": "...", "csv_line": "..."} を期待
    extra_meta : Optional[Dict[str, Any]]
        実行環境・引数などを補足保存（inference_meta.json）
    """
    run_dir = _make_infer_dir(ts_dir)

    # infer_cost を costs/infer_cost.* として保存（学習時の見た目と揃える）
    # 内部実装をそのまま再利用し、context="infer" として出力
    train_out._save_and_print_training_cost(run_dir, infer_cost, context="infer")

    # 追加メタ（任意）
    if extra_meta:
        try:
            (run_dir / "inference_meta.json").write_text(
                json.dumps(extra_meta, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            _warn(f"inference_meta.json の保存に失敗: {e}")

    # 画面通知
    print(f"[INFER OUTPUT] saved under: {run_dir}")
