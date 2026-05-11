"""
src/4_0_compute_cost.py

# =============================================================================
# 公開API（外部から呼び出す想定の関数）と入出力仕様
# =============================================================================
# 本モジュールは、学習/推論の実行区間における「経過時間・CPUメモリ・PyTorch GPU
# メモリ（割当/予約）のピークと時系列」を収集し、JSON/CSV 文字列として返す
# 軽量ロガーです（ここでは保存は行いません）。
#
# 依存:
# - 必須: Python 3.9+, 標準ライブラリのみで動作
# - 任意: psutil（CPU RSS取得に使用 / 無くても可）
# - 任意: torch（GPU統計・時系列に使用 / 無くても可）
#
# Colab 判定: _is_probably_colab() は内部利用。挙動に影響なし。
#
# 重要な挙動:
# - cost_start()/cost_end() のペアで使用します。
# - torch.cuda.is_available() が True の場合、バックグラウンドで 1秒間隔の VRAM
#   サンプラ（このプロセスに紐づく）を起動し、cost_end() 時に停止・回収します。
# - 保存は一切行いません（保存は上位層で to_json_str(), to_csv_str(),
#   to_torch_timeseries_csv_*() の返り値を使って行ってください）。
#
# -----------------------------------------------------------------------------
# 1) cost_start(...)
# -----------------------------------------------------------------------------
# シグネチャ:
#   cost_start(model: Optional[Any] = None,
#              phase: str = "train",
#              note: Optional[str] = None) -> CostToken
#
# 概要:
# - 計測開始直前に呼び出します。内部時計や各種統計を初期化し、必要なら
#   PyTorch VRAM サンプラ（1秒間隔）を起動します。
#
# 引数:
# - model:  任意。PyTorch 互換モデル（parameters() を持つ）を与えると
#           パラメータ数と学習可能パラメータ数を計測して保持します。
# - phase:  "train" / "inference" など、任意のフェーズ名。
# - note:   任意の文字列メモ。
#
# 返り値:
# - CostToken（このトークンを cost_end() に渡します）
#
# 失敗時:
# - 例外は原則飲み込み、CostToken.warnings に理由を追加して継続します。
#
# -----------------------------------------------------------------------------
# 2) cost_end(...)
# -----------------------------------------------------------------------------
# シグネチャ:
#   cost_end(token: CostToken) -> Dict[str, Any]
#
# 概要:
# - 計測区間の終了時に呼び出します。必要なら torch.cuda.synchronize() の後、
#   経過時間、CPU RSS 開始/終了/差分、GPU ピーク、VRAM 時系列（サンプラ由来）を
#   取りまとめて辞書（metrics）を返します。
#
# 引数:
# - token:  cost_start() が返した CostToken
#
# 返り値（metrics の主なキー）:
#   {
#     "phase": str,
#     "pid": int,
#     "host": {"platform": str, "python": str},
#     "start_time": ISO8601 str,
#     "end_time":   ISO8601 str,
#     "wall_time_sec": float,
#     "cpu": {
#       "rss_mb_start": float|None,
#       "rss_mb_end":   float|None,
#       "rss_mb_delta": float|None
#     },
#     "gpu": {
#       "available": bool,
#       "devices": [
#         {
#           "index": int,
#           "name": str|None,
#           "total_mb": float|None,
#           "torch_max_allocated_mb": float|None,
#           "torch_max_reserved_mb":  float|None
#         }, ...
#       ],
#       # ↓ サンプラ由来（プロセス確定）
#       "torch_timeseries_per_device":  # List[List[{t,alloc_mb,reserved_mb}]]|None
#       "torch_timeseries_total":       # List[{t,alloc_mb,reserved_mb}]|None
#       "torch_peak_total_alloc_mb": float|None,
#       "torch_peak_total_reserved_mb": float|None
#     },
#     "model": {
#       "num_parameters": int|None,
#       "num_trainable_parameters": int|None
#     },
#     "note": str|None,
#     "warnings": List[str]
#   }
#
# 備考:
# - torch 不在 or CUDA 不可: gpu.available=False、時系列は None、ピークはデバイス情報由来のみ。
#
# -----------------------------------------------------------------------------
# 3) infer_cost_start(...), infer_cost_end(...)
# -----------------------------------------------------------------------------
# シグネチャ:
#   infer_cost_start(model: Optional[Any] = None, note: Optional[str] = None) -> CostToken
#   infer_cost_end(token: CostToken) -> Dict[str, Any]
#
# 概要:
# - 推論用のエイリアス。phase="inference" を固定した cost_start/cost_end と同等です。
#
# -----------------------------------------------------------------------------
# 4) to_json_str(...)
# -----------------------------------------------------------------------------
# シグネチャ:
#   to_json_str(metrics: Dict[str, Any]) -> str
#
# 概要:
# - cost_end() の返す metrics 辞書を、保存用の整形JSON文字列に変換します。
# - 保存は行いません（呼び出し側でファイルに書き込んでください）。
#
# 返り値:
# - インデント付き JSON 文字列（ensure_ascii=False）
#
# -----------------------------------------------------------------------------
# 5) to_csv_str(...)
# -----------------------------------------------------------------------------
# シグネチャ:
#   to_csv_str(metrics: Dict[str, Any]) -> Tuple[str, str]
#
# 概要:
# - ダッシュボード集計向けの「単行サマリCSV」を生成します（ヘッダ行, データ行）。
# - 詳細は JSON に委譲し、ここでは代表的な数値のみを含めます。
#
# 返り値:
# - (header_csv: str, row_csv: str)
#
# 出力ヘッダ（順序固定）:
#   [
#     "phase", "pid", "wall_time_sec",
#     "cpu_rss_mb_start", "cpu_rss_mb_end", "cpu_rss_mb_delta",
#     "torch_peak_allocated_mb_max_from_devices",
#     "torch_peak_total_alloc_mb_from_sampler",
#     "torch_peak_total_reserved_mb_from_sampler",
#     "num_parameters", "num_trainable_parameters",
#     "note"
#   ]
#
# -----------------------------------------------------------------------------
# 6) to_torch_timeseries_csv_total(...), to_torch_timeseries_csv_per_device(...)
# -----------------------------------------------------------------------------
# シグネチャ:
#   to_torch_timeseries_csv_total(metrics: Dict[str, Any]) -> Tuple[str, str]
#   to_torch_timeseries_csv_per_device(metrics: Dict[str, Any]) -> Tuple[str, str]
#
# 概要:
# - cost_end() の metrics["gpu"]["torch_timeseries_*"] を CSV に整形します。
# - 保存は行いません（返り値をそのまま書き込んでください）。
#
# 返り値:
# - (header_csv: str, rows_csv: str)  # rows_csv は複数行を改行結合した文字列
#
# 各CSVのヘッダ:
# - total:
#     ["pid", "phase", "time_iso", "alloc_mb", "reserved_mb"]
# - per_device:
#     ["pid", "phase", "device_index", "time_iso", "alloc_mb", "reserved_mb"]
#
# 備考:
# - metrics に時系列が含まれない場合でも例外にせず空行を返します（呼び出し側で存在チェック推奨）。
#
# -----------------------------------------------------------------------------
# 使用例（最小）
# -----------------------------------------------------------------------------
#   token = cost_start(model=my_model, phase="train", note="trial-01")
#   # ... ここで学習処理 ...
#   m = cost_end(token)
#   json_str = to_json_str(m)
#   hdr, row = to_csv_str(m)
#   hdr_ts, rows_ts = to_torch_timeseries_csv_total(m)
#   # → 呼び出し側で保存:
#   # with open("train_cost.json","w",encoding="utf-8") as f: f.write(json_str)
#   # with open("train_cost.csv","w",encoding="utf-8") as f: f.write(hdr+"\n"+row+"\n")
#   # with open("torch_ts_total.csv","w",encoding="utf-8") as f: f.write(hdr_ts+"\n"+rows_ts+"\n")
#
# エラーハンドリングの方針:
# - psutil / torch が無い、CUDA 不可、デバイス特性取得失敗などは例外にせず warnings に追記。
# - 時系列サンプラは内部スレッドで動作。cost_end() 時に安全に停止・回収します。
# ========================================================

"""

from __future__ import annotations
import os, sys, json, time, threading, shutil, subprocess, datetime, platform
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Tuple

# ---- optional deps (graceful fallback) ----
try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False

try:
    import torch  # type: ignore
    _HAS_TORCH = True
except Exception:
    _HAS_TORCH = False


# =========================
# internal utils
# =========================

def _iso_now() -> str:
    return datetime.datetime.now().astimezone().isoformat()

def _mb(n_bytes: float) -> float:
    return round(n_bytes / (1024.0 * 1024.0), 2)

def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)

def _get_pid() -> int:
    return os.getpid()

def _is_probably_colab() -> bool:
    if "COLAB_GPU" in os.environ:
        return True
    try:
        import google.colab  # type: ignore
        return True
    except Exception:
        return False


# =========================
# sampler
# =========================

class _TorchMemSampler:
    """
    PyTorch ベースの VRAM ロガー（このプロセスのみ）。
    interval_sec ごとに各 GPU の
      - memory_allocated（実際にテンソルに割当）
      - memory_reserved （PyTorch が確保した領域）
    を取得し、MiB 単位の時系列を記録する。

    取得項目:
      - series_per_device[i] = [(iso, alloc_mb, reserved_mb), ...]
      - series_total         = [(iso, total_alloc_mb, total_reserved_mb), ...]
      - peak_alloc_mb_total / peak_reserved_mb_total
    """
    def __init__(self, interval_sec: float = 1.0):
        self.interval_sec = interval_sec
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.series_per_device: List[List[Tuple[str, float, float]]] = []
        self.series_total: List[Tuple[str, float, float]] = []
        self.peak_alloc_mb_total: float = 0.0
        self.peak_reserved_mb_total: float = 0.0

        self._n_devices = 0

    def start(self):
        if not (_HAS_TORCH and torch.cuda.is_available()):
            return
        self._n_devices = torch.cuda.device_count()
        self.series_per_device = [[] for _ in range(self._n_devices)]
        self.series_total = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=2.0)

    def _run(self):
        # 計測中はピーク統計の変化が反映されるよう、切り替えごとに同期を試みる
        while not self._stop.is_set():
            iso = _iso_now()
            total_alloc = 0.0
            total_resv = 0.0

            try:
                for i in range(self._n_devices):
                    # デバイスごとに current 値を取得
                    try:
                        alloc = torch.cuda.memory_allocated(i)   # bytes
                        resv  = torch.cuda.memory_reserved(i)    # bytes
                    except Exception:
                        alloc, resv = 0, 0
                    alloc_mb = round(alloc / (1024*1024), 2)
                    resv_mb  = round(resv  / (1024*1024), 2)
                    self.series_per_device[i].append((iso, alloc_mb, resv_mb))
                    total_alloc += alloc_mb
                    total_resv  += resv_mb
            except Exception:
                pass

            self.series_total.append((iso, round(total_alloc, 2), round(total_resv, 2)))
            if total_alloc > self.peak_alloc_mb_total:
                self.peak_alloc_mb_total = round(total_alloc, 2)
            if total_resv > self.peak_reserved_mb_total:
                self.peak_reserved_mb_total = round(total_resv, 2)

            time.sleep(self.interval_sec)

def to_torch_timeseries_csv_total(metrics: Dict[str, Any]) -> Tuple[str, str]:
    """
    torch の合計時系列（alloc/reserved）を CSV（ヘッダ, 複数行）で返す。
    """
    gpu = metrics.get("gpu") or {}
    series = gpu.get("torch_timeseries_total") or []
    headers = ["pid", "phase", "time_iso", "alloc_mb", "reserved_mb"]
    pid = metrics.get("pid")
    phase = metrics.get("phase")
    rows = []
    for it in series:
        rows.append(f"{pid},{phase},{it.get('t')},{it.get('alloc_mb')},{it.get('reserved_mb')}")
    return ",".join(headers), "\n".join(rows)


def to_torch_timeseries_csv_per_device(metrics: Dict[str, Any]) -> Tuple[str, str]:
    """
    torch のデバイス別時系列（alloc/reserved）を CSV（ヘッダ, 複数行）で返す。
    """
    gpu = metrics.get("gpu") or {}
    series_all = gpu.get("torch_timeseries_per_device") or []
    headers = ["pid", "phase", "device_index", "time_iso", "alloc_mb", "reserved_mb"]
    pid = metrics.get("pid")
    phase = metrics.get("phase")
    rows = []
    for di, seq in enumerate(series_all):
        for it in seq:
            rows.append(f"{pid},{phase},{di},{it.get('t')},{it.get('alloc_mb')},{it.get('reserved_mb')}")
    return ",".join(headers), "\n".join(rows)



# =========================
# token
# =========================

@dataclass
class CostToken:
    phase: str
    pid: int
    start_perf: float
    start_iso: str
    note: Optional[str] = None
    # CPU
    rss_mb_start: Optional[float] = None
    # GPU (torch)
    torch_cuda_available: bool = False
    torch_device_count: int = 0
    torch_device_names: List[str] = field(default_factory=list)
    torch_total_mb: List[Optional[float]] = field(default_factory=list)
    # samplers
    torch_sampler: Optional[_TorchMemSampler] = None   # ← 追加
    # model size
    num_parameters: Optional[int] = None
    num_trainable_parameters: Optional[int] = None
    # warnings
    warnings: List[str] = field(default_factory=list)


# =========================
# public API (no saving)
# =========================

def cost_start(model: Optional[Any] = None,
               phase: str = "train",
               note: Optional[str] = None) -> CostToken:
    """
    学習/推論の開始直前に呼ぶ。
    """
    pid = _get_pid()
    token = CostToken(
        phase=phase,
        pid=pid,
        start_perf=time.perf_counter(),
        start_iso=_iso_now(),
        note=note
    )

    # CPU RSS
    if _HAS_PSUTIL:
        try:
            p = psutil.Process(pid)
            token.rss_mb_start = _mb(p.memory_info().rss)
        except Exception:
            token.rss_mb_start = None
    else:
        token.warnings.append("psutil が見つかりませんでした。CPUメモリ(RSS)は一部 None になります。")

    # GPU via torch
    if _HAS_TORCH and torch.cuda.is_available():
        token.torch_cuda_available = True
        try:
            n = torch.cuda.device_count()
            token.torch_device_count = n
            for i in range(n):
                props = torch.cuda.get_device_properties(i)
                token.torch_device_names.append(props.name)
                token.torch_total_mb.append(round(props.total_memory / (1024*1024), 2))
            torch.cuda.reset_peak_memory_stats()
        except Exception as e:
            token.warnings.append(f"torch CUDA 情報の取得に失敗: {e}")

        # → PyTorch ベースの時系列サンプラを開始（このプロセスに確実に紐づく）
        sampler = _TorchMemSampler(interval_sec=1.0)
        sampler.start()
        token.torch_sampler = sampler

    else:
        if not _HAS_TORCH:
            token.warnings.append("torch が見つかりませんでした。torch ベースの GPU 統計は取得できません。")
        else:
            token.warnings.append("CUDA が利用不可です（torch.cuda.is_available() == False）。")

    _attach_model_parameters(token, model)
    return token



def cost_end(token: CostToken) -> Dict[str, Any]:
    if _HAS_TORCH and torch.cuda.is_available():
        try:
            torch.cuda.synchronize()
        except Exception:
            pass

    end_perf = time.perf_counter()
    end_iso = _iso_now()

    # CPU RSS
    rss_mb_end = None
    if _HAS_PSUTIL:
        try:
            p = psutil.Process(token.pid)
            rss_mb_end = _mb(p.memory_info().rss)
        except Exception:
            pass

    rss_mb_delta = None
    if token.rss_mb_start is not None and rss_mb_end is not None:
        rss_mb_delta = round(rss_mb_end - token.rss_mb_start, 2)

    # torch GPU peaks（既存：max_* は PyTorch が内部で計測）
    devices: List[Dict[str, Any]] = []
    if token.torch_cuda_available and _HAS_TORCH:
        try:
            for i in range(torch.cuda.device_count()):
                try:
                    torch.cuda.set_device(i)
                except Exception:
                    pass
                try:
                    max_alloc = torch.cuda.max_memory_allocated(i)
                    max_resv  = torch.cuda.max_memory_reserved(i)
                    max_alloc_mb = round(max_alloc / (1024*1024), 2)
                    max_resv_mb  = round(max_resv  / (1024*1024), 2)
                except Exception:
                    max_alloc_mb = None
                    max_resv_mb  = None
                name, total_mb = None, None
                try:
                    props = torch.cuda.get_device_properties(i)
                    name = props.name
                    total_mb = round(props.total_memory / (1024*1024), 2)
                except Exception:
                    pass
                devices.append({
                    "index": i,
                    "name": name,
                    "total_mb": total_mb,
                    "torch_max_allocated_mb": max_alloc_mb,
                    "torch_max_reserved_mb":  max_resv_mb,
                })
        except Exception as e:
            token.warnings.append(f"torch CUDA ピーク統計の取得に失敗: {e}")

    # === PyTorch サンプラの時系列を取得 ===
    torch_timeseries_per_device = None
    torch_timeseries_total = None
    torch_peak_alloc_total = None
    torch_peak_reserved_total = None

    if token.torch_sampler is not None:
        try:
            token.torch_sampler.stop()
            torch_timeseries_per_device = []
            for seq in token.torch_sampler.series_per_device:
                torch_timeseries_per_device.append([
                    {"t": t, "alloc_mb": a, "reserved_mb": r} for (t, a, r) in seq
                ])
            torch_timeseries_total = [
                {"t": t, "alloc_mb": a, "reserved_mb": r}
                for (t, a, r) in token.torch_sampler.series_total
            ]
            torch_peak_alloc_total = token.torch_sampler.peak_alloc_mb_total
            torch_peak_reserved_total = token.torch_sampler.peak_reserved_mb_total
        except Exception:
            pass

    metrics: Dict[str, Any] = {
        "phase": token.phase,
        "pid": token.pid,
        "host": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
        },
        "start_time": token.start_iso,
        "end_time": end_iso,
        "wall_time_sec": round(end_perf - token.start_perf, 4),
        "cpu": {
            "rss_mb_start": token.rss_mb_start,
            "rss_mb_end": rss_mb_end,
            "rss_mb_delta": rss_mb_delta
        },
        "gpu": {
            "available": token.torch_cuda_available,
            "devices": devices,

            # ==== 新規：このプロセスに紐づくトーチ時系列 ====
            "torch_timeseries_per_device": torch_timeseries_per_device,  # List[List[{t,alloc_mb,reserved_mb}]]
            "torch_timeseries_total": torch_timeseries_total,            # List[{t,alloc_mb,reserved_mb}]
            "torch_peak_total_alloc_mb": torch_peak_alloc_total,        # サンプリング時点の合計ピーク
            "torch_peak_total_reserved_mb": torch_peak_reserved_total,  # サンプリング時点の合計ピーク
        },
        "model": {
            "num_parameters": token.num_parameters,
            "num_trainable_parameters": token.num_trainable_parameters
        },
        "note": token.note,
        "warnings": token.warnings
    }
    return metrics



# =========================
# string formatters (no saving)
# =========================

def to_json_str(metrics: Dict[str, Any]) -> str:
    """
    保存用 JSON 文字列（インデント付き）を返す。保存はしない。
    - "wall_time_sec" を必ず含む
    """
    return json.dumps(metrics, ensure_ascii=False, indent=2)

def to_csv_str(metrics: Dict[str, Any]) -> Tuple[str, str]:
    """
    単行サマリ CSV（ヘッダ行, データ行）を返す。保存はしない。
    - "wall_time_sec" を含む
    - 詳細は JSON に委ね、ここはダッシュボード集計向けの最小項目
    """
    phase = metrics.get("phase")
    pid = metrics.get("pid")
    wt = metrics.get("wall_time_sec")
    cpu = metrics.get("cpu", {})
    gpu = metrics.get("gpu", {}) or {}

    # torch ピーク（デバイス別の max_memory_allocated の最大）
    torch_peak_alloc_from_devs = None
    devs = gpu.get("devices") or []
    if devs:
        torch_peak_alloc_from_devs = max([(d.get("torch_max_allocated_mb") or 0.0) for d in devs]) or None

    # サンプラ由来の合計ピーク
    torch_peak_total_alloc   = gpu.get("torch_peak_total_alloc_mb")
    torch_peak_total_reserved = gpu.get("torch_peak_total_reserved_mb")

    row = {
        "phase": phase,
        "pid": pid,
        "wall_time_sec": wt,  # ★学習/推論時間
        "cpu_rss_mb_start": cpu.get("rss_mb_start"),
        "cpu_rss_mb_end": cpu.get("rss_mb_end"),
        "cpu_rss_mb_delta": cpu.get("rss_mb_delta"),
        # torch 系に統一
        "torch_peak_allocated_mb_max_from_devices": torch_peak_alloc_from_devs,
        "torch_peak_total_alloc_mb_from_sampler": torch_peak_total_alloc,
        "torch_peak_total_reserved_mb_from_sampler": torch_peak_total_reserved,
        "num_parameters": (metrics.get("model") or {}).get("num_parameters"),
        "num_trainable_parameters": (metrics.get("model") or {}).get("num_trainable_parameters"),
        "note": metrics.get("note"),
    }
    headers = list(row.keys())
    def _fmt(x): return "" if x is None else str(x)
    values = [_fmt(row[h]) for h in headers]
    return ",".join(headers), ",".join(values)


# =========================
# helpers
# =========================

def _attach_model_parameters(token: CostToken, model: Any) -> None:
    if model is None:
        return
    try:
        total, trainable = 0, 0
        for p in model.parameters():
            n = int(p.numel())
            total += n
            if getattr(p, "requires_grad", False):
                trainable += n
        token.num_parameters = total
        token.num_trainable_parameters = trainable
    except Exception:
        pass


# =========================
# inference aliases
# =========================

def infer_cost_start(model: Optional[Any] = None,
                     note: Optional[str] = None) -> CostToken:
    return cost_start(model=model, phase="inference", note=note)

def infer_cost_end(token: CostToken) -> Dict[str, Any]:
    return cost_end(token)
