"""
src/p4_0_output_train_result.py

# =============================================================================
# 公開API（外部から呼び出す想定の関数）と入出力仕様
# =============================================================================
# 本モジュールは「学習結果・メトリクス・学習コスト・学習曲線・モデル・中間生成物」
# を一括で成果物ディレクトリに保存するためのユーティリティです。
#
# 依存:
# - 必須: Python 3.9+, numpy
# - 任意: matplotlib (図のPNG出力), torch (state_dict保存/環境情報の付与)
#
# すべての出力は out_dir/<timestamp>/ 以下に保存されます（timestampは本モジュール側で採番）。
#
# ----------------------------------------------------------------------------- 
# 1) output_single_run(...)
# ----------------------------------------------------------------------------- 
# 単一分割（train/val/test）の結果を保存します。
#
# シグネチャ:
#   output_single_run(
#       *,
#       out_dir: Path,
#       splits: Dict[str, Dict[str, Any]],
#       training_cost: Optional[Dict[str, str]] = None,
#       figures: bool = True,
#       config_content: Optional[dict | str] = None,
#       history: Optional[dict] = None,
#       model: Optional[Any] = None,
#       model_extra: Optional[Dict[str, Any]] = None,
#       model_info: Optional[Dict[str, Any]] = None,
#       # ★ 追加: 中間生成物の保存
#       artifacts: Optional[Dict[str, Any]] = None,
#       promote_artifacts_to_models: Optional[List[str]] = None,
#   ) -> None
#
# 引数:
# - out_dir:
#     出力ベースディレクトリ（存在しない場合は作成）。
# - splits:
#     各splitごとの予測とメタ:
#       {
#         "train": {"y_true": np.ndarray[int], "y_pred": np.ndarray[int], "id2label": Dict[int, str]},
#         "val"  : { ... 同上 ... },
#         "test" : { ... 同上 ... }
#       }
#     ※ y_true/y_pred は長さNの1次元配列（クラスID）。id2label は省略可（なければ 0..K-1 を使用）。
# - training_cost:
#     学習コストの生データ（文字列化済み）:
#       {
#         "json_str": "<JSON文字列>",       # 後で costs/train_cost.json に保存
#         "csv_header": "col1,col2,...",    # 任意
#         "csv_line":   "v1,v2,...",        # 必須
#       }
#     JSONに (gpu.devices[].torch_max_allocated_mb, gpu.available, gpu.torch_timeseries_total 等)
#     が含まれていれば、サマリやGPUメモリ時系列CSV/PNGの生成に使用します。
# - figures:
#     True の場合、混同行列や学習曲線のPNGを生成（matplotlibが無い環境では自動スキップ）。
# - config_content:
#     使用した設定のスナップショット（dict または str）。config/used_config.json として保存。
# - history:
#     学習履歴。CSV/JSON/PNGを learning_curves/ 以下に保存。
#       期待キー: {"epoch": [...], "train_loss": [...], "val_loss": [...],
#                  "train_acc": [...], "val_acc": [...]}
# - model:
#     学習済みモデル（torch.nn.Module 互換を想定）。**models/model.<ext>** に保存。
#     （ext は model_info["save_ext"] または "pt"。互換のため model_state_dict.pt も複製出力）
# - model_extra:
#     追加で torch.save したいオブジェクトの辞書（例: {"optimizer_state_dict": opt.state_dict()}）。
# - model_info:
#     任意のメタ情報（dict）。model_meta.json に同梱（例: {"save_ext": "pt"}）。
# - artifacts:
#     中間生成物の辞書（名前→内容）を <run_dir>/artifacts/ に保存。
#     値は Path/str（コピー）、dict/list（JSON化）、bytes（バイナリ）を受け付けます。
#     例: {"vocab.json": Path(".../vocab.json"), "label2id.json": {"neg":0,"pos":1}}
# - promote_artifacts_to_models:
#     ここで指定したファイル名は <run_dir>/models/ にも複製（推論時に参照しやすくするため）。
#     例: ["vocab.json", "label2id.json"]
#
# 返り値: なし（副作用で出力を保存）
#
# 出力（例）:
#   <out_dir>/<ts>/
#     config/used_config.json
#     metrics/{train,val,test}_per_class.csv
#     metrics/{train,val,test}_summary.json
#     metrics/{train,val,test}_confusion.npy
#     metrics/{train,val,test}_confusion_{none,true,pred,all}.npy
#     figures/{train,val,test}_confusion_{none,true,pred,all}.png  (figures=True かつ matplotlib あり)
#     learning_curves/learning_history.{csv,json}                   (history を渡したとき)
#     learning_curves/learning_curves_{loss,acc}.png                (matplotlib あり)
#     costs/train_cost.{json,csv,_summary.json,_readable.txt}       (training_cost を渡したとき)
#     costs/gpu/torch_mem_timeseries.{csv,png}                      (コストJSONに時系列がある場合)
#     models/model.<ext>    ※固定名（extは model_info["save_ext"] or "pt"）
#     models/model_state_dict.pt（互換用の複製）
#     models/model_meta.json
#     models/<key>.pt（追加アーティファクト）
#     artifacts/*（vocab.json などの中間生成物）
#     ※ promote_artifacts_to_models に指定したファイルは models/ にも複製
#
# ----------------------------------------------------------------------------- 
# 2) output_cv_fold(...)
# ----------------------------------------------------------------------------- 
# CVの各fold単位で「val（必須）・test（任意）」の結果と学習情報を保存します。
#
# シグネチャ:
#   output_cv_fold(
#       *,
#       fold_name: str,
#       out_dir: Path,
#       val: Dict[str, Any],
#       test: Optional[Dict[str, Any]] = None,
#       training_cost: Optional[Dict[str, str]] = None,
#       figures: bool = True,
#       config_content: Optional[dict | str] = None,
#       history: Optional[dict] = None,
#       model: Optional[Any] = None,
#       model_extra: Optional[Dict[str, Any]] = None,
#       model_info: Optional[Dict[str, Any]] = None,
#       # ★ 追加: 中間生成物
#       artifacts: Optional[Dict[str, Any]] = None,
#       promote_artifacts_to_models: Optional[List[str]] = None,
#   ) -> None
#
# 引数/返り値:
#   output_single_run と同様。ただし splits の代わりに val/test を個別に渡す。
#   保存先は out_dir/<timestamp>/ 以下（fold名はディレクトリ名には含めない）。
#
# 出力:
#   metrics/{val,test}_*.{csv,json,npy}, figures/{val,test}_*.png, learning_curves/*,
#   costs/train_cost.*, models/*, artifacts/* など（与えた引数に応じて）。
#
# ----------------------------------------------------------------------------- 
# 3) output_cv_summary(...)
# ----------------------------------------------------------------------------- 
# 全foldのスコアを集計して保存します（平均・標準偏差を含む）。
#
# シグネチャ:
#   output_cv_summary(
#       *,
#       out_dir: Path,
#       fold_summaries: list
#   ) -> None
#
# 引数:
# - fold_summaries:
#     各foldの集計行（呼び出し側で用意）:
#       例: [{"fold": "fold_1", "val_acc": 0.812, "test_acc": 0.805}, ...]
#     ※ "val_acc" および "test_acc" は None 可（その場合は平均/分散の計算から除外）。
#
# 返り値: なし（副作用で out_dir/<timestamp>/cv/ に保存）
#
# 出力:
#   <out_dir>/<ts>/cv/cv_summary.json
#   <out_dir>/<ts>/cv/cv_summary.csv
#
# ----------------------------------------------------------------------------- 
# 参考: 入力辞書の詳細
# ----------------------------------------------------------------------------- 
# [splits の各要素 / val / test の共通フォーマット]
#   y_true: 1次元 np.ndarray[int]  例: array([0,2,1,...])
#   y_pred: 1次元 np.ndarray[int]  同じ長さ
#   id2label: Dict[int, str]        ラベル名（省略可）
#
# [training_cost の JSON 中で認識する主なキー（任意）]
#   "phase", "start_time"/"started_at", "end_time"/"ended_at", "wall_time_sec"/"duration_sec",
#   "pid", "gpu": {
#       "available": bool,
#       "devices": [{"name": "...", "torch_max_allocated_mb": <float>}, ...],
#       "torch_timeseries_total": [
#           {"t": "<ISO8601>", "alloc_mb": <float>, "reserved_mb": <float>}, ...
#       ]
#   }
#
# エラーハンドリング:
# - 必須項目が欠けている場合は WARN を出しつつ可能な処理のみ実行します。
# - matplotlib / torch が無い環境でも障害にならないようにスキップ動作を実装しています。
#
# 使い方（最小例）:
#   from pathlib import Path
#   import numpy as np
#   splits = {
#     "train": {"y_true": np.array([0,1]), "y_pred": np.array([0,1]), "id2label": {0:"neg",1:"pos"}},
#     "val":   {"y_true": np.array([0,1]), "y_pred": np.array([1,1]), "id2label": {0:"neg",1:"pos"}},
#     "test":  {"y_true": np.array([0,1]), "y_pred": np.array([0,0]), "id2label": {0:"neg",1:"pos"}},
#   }
#   output_single_run(
#       out_dir=Path("./result"),
#       splits=splits,
#       figures=True,
#       artifacts={"vocab.json": Path("./work/vocab.json")},
#       promote_artifacts_to_models=["vocab.json"]
#   )
# =============================================================================

"""

from __future__ import annotations
import os, json, csv, sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

import numpy as np

# matplotlib は無くても致命的ではない（PNGだけスキップ）
try:
    import matplotlib.pyplot as plt
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


# =========================
# ANSI color helpers
# =========================

_RED = "\033[31m"
_RESET = "\033[0m"

def _warn(msg: str):
    print(f"{_RED}[WARN]{_RESET} {msg}", file=sys.stderr)


# =========================
# config helpers
# =========================

def _save_config_snapshot(base_dir: Path, config_content: Optional[dict | str]) -> None:
    """
    渡された設定内容のスナップショットを config/used_config.json に保存。
    - dict: pretty JSON
    - str : JSONとしてparseできれば整形、できなければ生文字列
    """
    if config_content is None:
        _warn("config_content が指定されていません（スナップショットをスキップ）。")
        return

    cfg_dir = base_dir / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg_dir / "used_config.json"

    try:
        if isinstance(config_content, dict):
            out_path.write_text(json.dumps(config_content, ensure_ascii=False, indent=2), encoding="utf-8")
        elif isinstance(config_content, str):
            try:
                parsed = json.loads(config_content)
                out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                out_path.write_text(config_content, encoding="utf-8")
        else:
            _warn(f"config_content の型が想定外です: {type(config_content)}（保存をスキップ）")
            return
        print(f"[INFO] Config snapshot saved to {out_path}")
    except Exception as e:
        _warn(f"Config スナップショットの保存に失敗: {e}")

# =========================
# intermediate artifacts helpers
# =========================
def _save_intermediate_artifacts(
    run_dir: Path,
    artifacts: Optional[Dict[str, Any]],
) -> None:
    """
    中間生成物（vocab.json, label2id.json, idf.npy など）を **models/** に保存する。

    受け付ける値の型:
      - Path / str: そのパスのファイルをコピー
      - dict / list: JSON(UTF-8, indent=2) として保存
      - bytes / bytearray: バイナリとして保存
      - それ以外: JSON化を試み、不可なら str() をテキスト保存

    旧仕様の promote_to_models / subdir は後方互換のため受け付けるが、
    本実装では常に models/ 配下に書き出すため実質無視される。
    """
    if not artifacts:
        return

    import shutil

    models_dir = run_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    for fname, obj in artifacts.items():
        try:
            dst = models_dir / fname
            dst.parent.mkdir(parents=True, exist_ok=True)

            # 1) コピー元がパス（Path/str）ならファイルとして複製
            if isinstance(obj, (str, Path)):
                src = Path(obj)
                if not src.exists():
                    _warn(f"artifact '{fname}': ソースファイルが見つかりません: {src}")
                    continue
                shutil.copy2(src, dst)

            # 2) dict/list は JSON として書き出し
            elif isinstance(obj, (dict, list)):
                dst.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

            # 3) bytes/bytearray はバイナリとして書き出し
            elif isinstance(obj, (bytes, bytearray)):
                with open(dst, "wb") as f:
                    f.write(obj)

            # 4) それ以外は JSON 直列化を試行、不可なら str() で保存
            else:
                try:
                    s = json.dumps(obj, ensure_ascii=False, indent=2)
                    dst.write_text(s, encoding="utf-8")
                except Exception:
                    dst.write_text(str(obj), encoding="utf-8")

            print(f"[INFO] Artifact saved under models/: {dst}")

        except Exception as e:
            _warn(f"artifact '{fname}' の保存に失敗: {e}")




# =========================
# model artifact helpers
# =========================
def _save_model_artifacts(run_dir: Path,
                          *,
                          model: Any,
                          model_extra: Optional[Dict[str, Any]] = None,
                          model_info: Optional[Dict[str, Any]] = None) -> None:
    """
    学習済みモデルを run_dir/models に保存する。

    仕様:
      - 主モデル: models/model.<ext> に固定名で保存（既定 ext="pt"）
      - メタ情報: models/model_meta.json
      - 追加:     models/<key>.pt （従来どおり）
      - 互換:     models/model_state_dict.pt を model.<ext> の内容で複製（今後廃止予定）

    ext の決定:
      - model_info に "save_ext" があればそれを採用（例: {"save_ext": "pt"})
      - なければ "pt"
    """
    models_dir = run_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # --- パラメータ数の取得（任意） ---
    def _count_params(m) -> Tuple[Optional[int], Optional[int]]:
        try:
            total, trainable = 0, 0
            for p in m.parameters():
                n = int(p.numel())
                total += n
                if getattr(p, "requires_grad", False):
                    trainable += n
            return total, trainable
        except Exception:
            return None, None

    from datetime import datetime as _dt
    meta: Dict[str, Any] = {
        "saved_at": _dt.now().astimezone().isoformat(),
        "model_name": "model",
    }
    save_ext = "pt"
    if isinstance(model_info, dict) and isinstance(model_info.get("save_ext"), str):
        save_ext = model_info["save_ext"].lstrip(".") or "pt"

    # 環境情報
    try:
        import torch  # lazy import
        meta["env"] = {
            "torch": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
        }
    except Exception:
        meta["env"] = {"torch": None, "cuda_available": None}

    total, trainable = _count_params(model)
    meta["num_parameters"] = total
    meta["num_trainable_parameters"] = trainable
    if model_info:
        meta["info"] = model_info

    # --- 主モデルの保存（固定名 model.<ext>） ---
    main_model_path = models_dir / f"model.{save_ext}"
    try:
        import torch  # lazy import
        # 可能なら state_dict を保存（最も互換性が高い）
        sd = None
        try:
            sd = getattr(model, "state_dict")()
        except Exception:
            sd = None

        if sd is not None:
            torch.save(sd, main_model_path)
        else:
            # state_dict が取れない（TorchScript等）の場合も torch.save で丸ごと保存を試みる
            torch.save(model, main_model_path)
        print(f"[INFO] Model saved to {main_model_path}")
    except Exception as e:
        _warn(f"model の保存に失敗: {e}")

    # --- 後方互換: model_state_dict.pt を複製 ---
    try:
        compat_path = models_dir / "model_state_dict.pt"
        if main_model_path.exists() and str(main_model_path) != str(compat_path):
            # 同じファイル名でなければ複製
            import shutil as _sh
            _sh.copy2(main_model_path, compat_path)
            print(f"[INFO] (compat) Duplicated to {compat_path}")
    except Exception as e:
        _warn(f"互換ファイル model_state_dict.pt の作成に失敗: {e}")

    # --- 追加アーティファクト（従来どおり） ---
    if isinstance(model_extra, dict):
        for k, v in model_extra.items():
            try:
                import torch  # lazy import
                extra_path = models_dir / f"{k}.pt"
                torch.save(v, extra_path)
                print(f"[INFO] Extra artifact saved to {extra_path}")
            except Exception as e:
                _warn(f"追加アーティファクト {k} の保存に失敗: {e}")

    # --- メタ情報保存 ---
    try:
        (models_dir / "model_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        _warn(f"model meta の保存に失敗: {e}")



# =========================
# learning curves helpers
# =========================

def _save_learning_curves(out_dir: Path, history: dict):
    """
    学習履歴を保存（CSV, JSON, Loss/AccuracyグラフPNG）。
    history = {"epoch": [...], "train_loss": [...], "val_loss": [...], "train_acc": [...], "val_acc": [...]}
    """
    hist_dir = out_dir / "learning_curves"
    hist_dir.mkdir(parents=True, exist_ok=True)

    # CSV / JSON
    try:
        with open(hist_dir / "learning_history.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["epoch", "train_loss", "val_loss", "train_acc", "val_acc"])
            for i in range(len(history.get("epoch", []))):
                w.writerow([
                    history["epoch"][i],
                    history["train_loss"][i],
                    history["val_loss"][i],
                    history["train_acc"][i],
                    history["val_acc"][i]
                ])
        (hist_dir / "learning_history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        _warn(f"学習履歴の保存に失敗: {e}")

    # Loss / Acc PNG
    if _HAS_PLT:
        try:
            plt.figure()
            plt.plot(history["epoch"], history["train_loss"], label="train_loss")
            plt.plot(history["epoch"], history["val_loss"], label="val_loss")
            plt.xlabel("epoch"); plt.ylabel("loss"); plt.title("Learning Curve (Loss)")
            plt.legend(); plt.tight_layout()
            plt.savefig(hist_dir / "learning_curves_loss.png", dpi=150)
            plt.close()

            plt.figure()
            plt.plot(history["epoch"], history["train_acc"], label="train_acc")
            plt.plot(history["epoch"], history["val_acc"], label="val_acc")
            plt.xlabel("epoch"); plt.ylabel("accuracy"); plt.title("Learning Curve (Accuracy)")
            plt.legend(); plt.tight_layout()
            plt.savefig(hist_dir / "learning_curves_acc.png", dpi=150)
            plt.close()
        except Exception as e:
            _warn(f"学習曲線PNGの保存に失敗: {e}")
    else:
        _warn("matplotlib が無いため学習曲線PNGをスキップします。")


# =========================
# metrics helpers
# =========================

def _annotate_matrix(ax, cm_counts: np.ndarray, cm_ratios: np.ndarray):
    """1セルに「件数 / 比率%」を描く。"""
    im = None
    for im_ in ax.get_images():
        im = im_
    def _text_color(i, j):
        if im is None:
            return "black"
        try:
            rgba = im.cmap(im.norm(cm_ratios[i, j]))
            Y = 0.2126*rgba[0] + 0.7152*rgba[1] + 0.0722*rgba[2]  # BT.709
            return "black" if Y > 0.5 else "white"
        except Exception:
            return "black"

    H, W = cm_counts.shape
    for i in range(H):
        for j in range(W):
            s = f"{int(cm_counts[i, j])}\n{cm_ratios[i, j]*100.0:.1f}%"
            ax.text(j, i, s, ha="center", va="center", fontsize=8, color=_text_color(i, j))

def _normalize_confusion(cm: np.ndarray, mode: str) -> np.ndarray:
    """
    mode in {"none","true","pred","all"}:
      - none: そのまま
      - true: 行正規化（各行で割る）→ リコール視点
      - pred: 列正規化（各列で割る）→ 精度視点
      - all : 総和で割る（全体比）
    """
    mode = (mode or "none").lower()
    cm = cm.astype(float)
    if mode == "none":
        return cm
    if mode == "true":
        denom = cm.sum(axis=1, keepdims=True); denom[denom == 0] = 1.0
        return cm / denom
    if mode == "pred":
        denom = cm.sum(axis=0, keepdims=True); denom[denom == 0] = 1.0
        return cm / denom
    if mode == "all":
        s = cm.sum(); return cm / s if s > 0 else cm
    _warn(f"未知の normalize_mode={mode} のため 'none' を適用します。")
    return cm

def _compute_confusion(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1
    return cm

def _metrics_from_confusion(cm: np.ndarray):
    K = cm.shape[0]
    per_class = []
    for k in range(K):
        tp = int(cm[k, k]); fp = int(cm[:, k].sum() - tp); fn = int(cm[k, :].sum() - tp)
        support = int(cm[k, :].sum())
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = (2*prec*rec)/(prec+rec) if (prec+rec) > 0 else 0.0
        per_class.append(dict(precision=prec, recall=rec, f1=f1, support=support))
    supports = np.array([pc["support"] for pc in per_class], dtype=np.int64)
    weights  = supports / max(int(supports.sum()), 1)
    macro = dict(
        precision=float(np.mean([pc["precision"] for pc in per_class])) if K>0 else 0.0,
        recall=float(np.mean([pc["recall"] for pc in per_class])) if K>0 else 0.0,
        f1=float(np.mean([pc["f1"] for pc in per_class])) if K>0 else 0.0,
        support=int(supports.sum())
    )
    weighted = dict(
        precision=float(np.sum([pc["precision"]*w for pc, w in zip(per_class, weights)])) if K>0 else 0.0,
        recall=float(np.sum([pc["recall"]*w for pc, w in zip(per_class, weights)])) if K>0 else 0.0,
        f1=float(np.sum([pc["f1"]*w for pc, w in zip(per_class, weights)])) if K>0 else 0.0,
        support=int(supports.sum())
    )
    tp_sum = int(np.trace(cm)); total = int(cm.sum())
    micro_prec = tp_sum / total if total > 0 else 0.0
    micro = dict(precision=float(micro_prec), recall=float(micro_prec), f1=float(micro_prec), support=int(supports.sum()))
    accuracy = float(tp_sum / max(total, 1))
    return per_class, macro, micro, weighted, accuracy


# =========================
# GPU timeseries helpers (PyTorch only)
# =========================

def _extract_torch_timeseries(raw_cost: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    p4_0_compute_cost の新形式のみ対応。
    参照キー: gpu.torch_timeseries_total
      - 各要素は {"t": ISO時刻, "alloc_mb": float, "reserved_mb": float}
      - CSV/PNG では allocated_mb/reserved_mb のみを使用し、他は None 扱い
    返り値:
      {
        "rows": [
          { "t": <iso>, "used_mb": None, "allocated_mb": <float|None>,
            "reserved_mb": <float|None>, "free_mb": None, "total_mb": None }
        ],
        "pid": <int|None>,
        "phase": <str|None>
      } もしくは None
    """
    gpu = (raw_cost or {}).get("gpu") or {}
    pid = raw_cost.get("pid")
    phase = raw_cost.get("phase")

    series_total = gpu.get("torch_timeseries_total")
    if not (isinstance(series_total, list) and series_total):
        return None

    rows: List[Dict[str, Any]] = []
    for it in series_total:
        if not isinstance(it, dict):
            continue
        rows.append({
            "t": it.get("t"),
            "used_mb": None,
            "allocated_mb": it.get("alloc_mb"),
            "reserved_mb": it.get("reserved_mb"),
            "free_mb": None,
            "total_mb": None,
        })

    return {"rows": rows, "pid": pid, "phase": phase} if rows else None



def _save_torch_timeseries(out_dir: Path, raw_cost: Dict[str, Any]) -> None:
    """
    PyTorch 時系列があれば CSV/PNG を保存。
    CSV: costs/gpu/torch_mem_timeseries.csv
    PNG: costs/gpu/torch_mem_timeseries.png
    """
    pack = _extract_torch_timeseries(raw_cost)
    if not pack:
        _warn("PyTorch GPU メモリ時系列が提供されていないため、GPU時系列CSV/PNGをスキップします。")
        return

    gpu_dir = out_dir / "costs" / "gpu"
    gpu_dir.mkdir(parents=True, exist_ok=True)
    csv_path = gpu_dir / "torch_mem_timeseries.csv"

    cols = ["time_iso", "used_mb", "allocated_mb", "reserved_mb", "free_mb", "total_mb"]
    meta_cols = ["pid", "phase"]
    rows: List[Dict[str, Any]] = pack["rows"]
    pid = pack.get("pid")
    phase = pack.get("phase")

    try:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(meta_cols + cols)
            for it in rows:
                w.writerow([
                    pid, phase,
                    it.get("t"),
                    _fmt_num(it.get("used_mb")),
                    _fmt_num(it.get("allocated_mb")),
                    _fmt_num(it.get("reserved_mb")),
                    _fmt_num(it.get("free_mb")),
                    _fmt_num(it.get("total_mb")),
                ])
    except Exception as e:
        _warn(f"GPU時系列CSVの保存に失敗: {e}")

    # PNG (任意)
    if _HAS_PLT:
        try:
            xs = list(range(len(rows)))
            series_map = {
                "used_mb": [],
                "allocated_mb": [],
                "reserved_mb": [],
                "free_mb": [],
                "total_mb": [],
            }
            for it in rows:
                for k in series_map.keys():
                    v = it.get(k)
                    series_map[k].append(None if v is None else float(v))

            plt.figure()
            plotted = False
            for k, ys in series_map.items():
                if any(y is not None for y in ys):
                    plt.plot(xs, [np.nan if y is None else y for y in ys], label=k)
                    plotted = True
            if plotted:
                plt.xlabel("sample index")
                plt.ylabel("MiB")
                plt.title("PyTorch GPU memory timeseries")
                plt.legend()
                plt.tight_layout()
                plt.savefig(gpu_dir / "torch_mem_timeseries.png", dpi=150)
            plt.close()
        except Exception as e:
            _warn(f"GPU時系列PNGの保存に失敗: {e}")


def _fmt_num(x):
    if x is None:
        return ""
    try:
        return f"{float(x)}"
    except Exception:
        return ""


# =========================
# training cost helpers
# =========================

def _save_and_print_training_cost(out_dir: Path, training_cost: Dict[str, str], *, context: str = "train") -> None:
    """
    training_cost: {"json_str":..., "csv_header":..., "csv_line":...}
    保存場所:
      - costs/{context}_cost.json
      - costs/{context}_cost.csv
      - costs/{context}_cost_summary.json
      - costs/{context}_cost_readable.txt
      - costs/gpu/torch_mem_timeseries.csv（あれば）
    """
    cost_dir = out_dir / "costs"
    cost_dir.mkdir(parents=True, exist_ok=True)

    # 1) JSON / CSV 保存
    try:
        (cost_dir / f"{context}_cost.json").write_text(training_cost["json_str"], encoding="utf-8")
    except Exception as e:
        _warn(f"{context}_cost.json の保存に失敗: {e}")

    try:
        with open(cost_dir / f"{context}_cost.csv", "w", encoding="utf-8") as f:
            if training_cost.get("csv_header"):
                f.write(training_cost["csv_header"] + "\n")
            f.write(training_cost["csv_line"] + "\n")
    except Exception as e:
        _warn(f"{context}_cost.csv の保存に失敗: {e}")

    # 2) JSON→dict
    raw = {}
    try:
        raw = json.loads(training_cost.get("json_str", "{}"))
    except Exception as e:
        _warn(f"{context}: training_cost.json_str が不正JSONです: {e}")

    # 3) サマリ抽出
    def _get(d, *keys, default=None):
        for k in keys:
            if isinstance(d, dict) and k in d:
                return d[k]
        return default

    started_at = _get(raw, "start_time", "started_at")
    ended_at   = _get(raw, "end_time", "ended_at")
    duration_s = _get(raw, "wall_time_sec", "duration_sec")
    if duration_s is None and started_at and ended_at:
        try:
            from datetime import datetime as _dt
            duration_s = (_dt.fromisoformat(ended_at) - _dt.fromisoformat(started_at)).total_seconds()
        except Exception:
            pass

    gpu = raw.get("gpu") or {}
    devices = gpu.get("devices") or []
    gpu_name = devices[0].get("name") if devices else None
    # vram peak は torch の最大確保量を採用（nvidia-smi は不使用）
    vram_peak = None
    if devices:
        vram_peak = max([d.get("torch_max_allocated_mb") or 0 for d in devices], default=None)

    summary = {
        "phase": raw.get("phase", context),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_sec": duration_s,
        "cuda_available": gpu.get("available"),
        "gpu_name": gpu_name,
        "gpu_mem_peak_mib": vram_peak,
        "pid": raw.get("pid"),
    }

    # 4) 標準出力
    print(f"[{context.upper()} COST SUMMARY]")
    for k, v in summary.items():
        if v is None:
            _warn(f"{context}: {k} が取得できませんでした。")
        else:
            print(f"  - {k}: {v}")

    # 5) サマリ保存
    try:
        (cost_dir / f"{context}_cost_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        lines = [f"[{context.upper()} COST SUMMARY]"] + [f"{k}: {v}" for k, v in summary.items()]
        (cost_dir / f"{context}_cost_readable.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        _warn(f"{context}_cost_summary の保存に失敗: {e}")

    # 6) PyTorch GPU時系列の保存 + 簡易PNG（nvidia-smi は完全非対応）
    try:
        _save_torch_timeseries(out_dir, raw)
    except Exception as e:
        _warn(f"GPU時系列の保存に失敗: {e}")


# =========================
# per-split writers
# =========================

def _write_split_reports(split_name: str,
                         pack: Dict[str, Any],
                         out_dir: Path,
                         figures: bool = True):
    """
    pack = { "y_true": np.ndarray, "y_pred": np.ndarray, "id2label": Dict[int,str] }
    出力分類:
      - metrics/ : confusion.npy, per_class.csv, summary.json (+ 正規化4種 .npy)
      - figures/ : confusion PNG（正規化4種）
    """
    try:
        y_true = np.asarray(pack.get("y_true"))
        y_pred = np.asarray(pack.get("y_pred"))
        id2label = pack.get("id2label", {})
        if y_true.ndim != 1 or y_pred.ndim != 1 or y_true.shape[0] != y_pred.shape[0]:
            _warn(f"{split_name}: y_true/y_pred の形状が不正のためスキップします。")
            return None

        # ディレクトリ
        metrics_dir = out_dir / "metrics"
        figures_dir = out_dir / "figures"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        if figures:
            figures_dir.mkdir(parents=True, exist_ok=True)

        num_classes = len(id2label) if id2label else int(max(int(y_true.max(initial=0)), int(y_pred.max(initial=0))) + 1)
        cm = _compute_confusion(y_true, y_pred, num_classes)
        per_class, macro, micro, weighted, acc = _metrics_from_confusion(cm)

        # metrics 出力
        with open(metrics_dir / f"{split_name}_per_class.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["label", "precision", "recall", "f1", "support"])
            for i, pc in enumerate(per_class):
                w.writerow([id2label.get(i, str(i)), pc["precision"], pc["recall"], pc["f1"], pc["support"]])

        summary = dict(accuracy=acc, micro=micro, macro=macro, weighted=weighted)
        (metrics_dir / f"{split_name}_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        np.save(metrics_dir / f"{split_name}_confusion.npy", cm)

        # figures / 正規化4種
        modes = ["none", "true", "pred", "all"]
        for mode in modes:
            cm_norm = _normalize_confusion(cm, mode)
            np.save(metrics_dir / f"{split_name}_confusion_{mode}.npy", cm_norm)

            if figures and _HAS_PLT:
                try:
                    perc_mat = _normalize_confusion(cm, "all") if mode == "none" else cm_norm
                    fig, ax = plt.subplots()
                    im = ax.imshow(cm_norm, interpolation="nearest")
                    ax.set_title(f"Confusion Matrix ({split_name}) [{mode}]")
                    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
                    fig.colorbar(im, ax=ax)
                    _annotate_matrix(ax, cm, perc_mat)
                    fig.tight_layout()
                    fig.savefig(figures_dir / f"{split_name}_confusion_{mode}.png", dpi=150)
                    plt.close(fig)
                except Exception as e:
                    _warn(f"{split_name}: 混同行列PNG({mode})の保存に失敗: {e}")
            elif figures and not _HAS_PLT:
                _warn(f"{split_name}: matplotlib が無いため混同行列PNG({mode})をスキップします。")

        print(f"[{split_name}] accuracy={acc:.4f}  macro_f1={macro['f1']:.4f}  micro_f1={micro['f1']:.4f}")
        return summary

    except Exception as e:
        _warn(f"{split_name}: 例外によりスキップします: {e}")
        return None


# =========================
# public APIs
# =========================

def _make_run_dir(out_dir: Path) -> Path:
    """ out_dir/<timestamp>/ を作成して返す。 """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = out_dir / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir

def output_single_run(*,
                      out_dir: Path,
                      splits: Dict[str, Dict[str, Any]],
                      training_cost: Optional[Dict[str, str]] = None,
                      figures: bool = True,
                      config_content: Optional[dict | str] = None,
                      history: Optional[dict] = None,
                      model: Optional[Any] = None,
                      model_extra: Optional[Dict[str, Any]] = None,
                      model_info: Optional[Dict[str, Any]] = None,
                      artifacts: Optional[Dict[str, Any]] = None
                      ) -> None:
    """
    単一分割(train/val/test)の結果を out_dir/<timestamp>/ に保存。
    """
    run_dir = _make_run_dir(out_dir)

    # config 保存
    _save_config_snapshot(run_dir, config_content)

    # 各 split
    for split_name in ["train", "val", "test"]:
        if split_name in splits:
            _write_split_reports(split_name, splits[split_name], run_dir, figures=figures)
        else:
            _warn(f"{split_name}: 入力が無いためスキップします。")

    # 学習コスト
    if training_cost:
        _save_and_print_training_cost(run_dir, training_cost, context="train")
    else:
        _warn("training_cost が提供されていないため、学習コスト保存をスキップします。")

    # 学習履歴
    if history:
        _save_learning_curves(run_dir, history)
    else:
        _warn("history が提供されていないため、学習曲線の保存をスキップします。")
        
    # 学習済みモデル
    if model is not None:
        _save_model_artifacts(run_dir,
                              model=model,
                              model_extra=model_extra,
                              model_info=model_info)
    else:
        _warn("model が提供されていないため、学習済みモデルの保存をスキップします。")

    # ★ 中間生成物（vocab.json 等）
    if artifacts:
        _save_intermediate_artifacts(
            run_dir,
            artifacts
        )

def output_cv_fold(*,
                   fold_name: str,
                   out_dir: Path,
                   val: Dict[str, Any],
                   test: Optional[Dict[str, Any]] = None,
                   training_cost: Optional[Dict[str, str]] = None,
                   figures: bool = True,
                   config_content: Optional[dict | str] = None,
                   history: Optional[dict] = None,
                   model: Optional[Any] = None,
                   model_extra: Optional[Dict[str, Any]] = None,
                   model_info: Optional[Dict[str, Any]] = None,
                   artifacts: Optional[Dict[str, Any]] = None,
                   ) -> None:
    """
    各foldの出力を out_dir/<timestamp>/ に保存。
    """
    run_dir = _make_run_dir(out_dir)

    # config 保存（fold単位のスナップショット）
    _save_config_snapshot(run_dir, config_content)

    _write_split_reports("val", val, run_dir, figures=figures)
    if test is not None:
        _write_split_reports("test", test, run_dir, figures=figures)
    else:
        _warn(f"{fold_name}: test が無いためスキップします。")

    if training_cost:
        _save_and_print_training_cost(run_dir, training_cost, context="train")
    else:
        _warn("training_cost が提供されていないため、学習コスト保存をスキップします。")

    if history:
        _save_learning_curves(run_dir, history)
    else:
        _warn("history が提供されていないため、学習曲線の保存をスキップします。")
        
    if model is not None:
        _save_model_artifacts(run_dir,
                              model=model,
                              model_extra=model_extra,
                              model_info=model_info)
    else:
        _warn("model が提供されていないため、学習済みモデルの保存をスキップします。")

    # ★ 中間生成物（vocab.json 等）
    if artifacts:
        _save_intermediate_artifacts(
            run_dir,
            artifacts
        )



def output_cv_summary(*,
                      out_dir: Path,
                      fold_summaries: list) -> None:
    """
    CV全体の集計結果を out_dir/<timestamp>/cv/ に保存。
    """
    ts_dir = _make_run_dir(out_dir)  # CVも新しい run_dir を切る
    cv_dir = ts_dir / "cv"
    cv_dir.mkdir(parents=True, exist_ok=True)

    try:
        summary = {
            "folds": fold_summaries,
            "val_acc_mean": _safe_mean([x.get("val_acc") for x in fold_summaries]),
            "val_acc_std":  _safe_std([x.get("val_acc") for x in fold_summaries]),
            "test_acc_mean": _safe_mean([x.get("test_acc") for x in fold_summaries]),
            "test_acc_std":  _safe_std([x.get("test_acc") for x in fold_summaries]),
        }
        (cv_dir / "cv_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[CV SUMMARY]", json.dumps(summary, ensure_ascii=False, indent=2))
    except Exception as e:
        _warn(f"cv_summary.json の保存に失敗: {e}")

    try:
        with open(cv_dir / "cv_summary.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["fold", "val_acc", "test_acc"])
            for r in fold_summaries:
                w.writerow([r.get("fold", ""), _fmt(r.get("val_acc")), _fmt(r.get("test_acc"))])
            w.writerow([])
            w.writerow(["metric", "mean", "std"])
            vvals = [x.get("val_acc") for x in fold_summaries]
            tvals = [x.get("test_acc") for x in fold_summaries]
            w.writerow(["val_acc", _safe_mean(vvals), _safe_std(vvals)])
            w.writerow(["test_acc", _safe_mean(tvals), _safe_std(tvals)])
    except Exception as e:
        _warn(f"cv_summary.csv の保存に失敗: {e}")


# =========================
# stats helpers
# =========================

def _clean(vals):
    return [float(v) for v in vals if v is not None]

def _safe_mean(vals):
    xs = _clean(vals)
    if not xs: return None
    return float(np.mean(xs))

def _safe_std(vals):
    xs = _clean(vals)
    if not xs: return None
    return float(np.std(xs))

def _fmt(x):
    return "" if x is None else x
