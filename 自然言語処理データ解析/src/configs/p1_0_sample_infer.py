"""
p1_0_sample_infer.py
- 入力: --ts-dir（学習結果ディレクトリ）
- モデル: <ts>/models/model.pt を自動参照
- データ: --data で指定（Parquet、contentカラム必須）
- アダプタ: bowを指定しなければならない．過去の残骸
- 保存: p4_0_output_infer_result.py に一任（<ts>/inference_<時刻>/）
- 精度評価は行わず、推論コストのみ計測

例:
  python -m src.p1_0_sample_infer --ts-dir ./src/result/1_0_preprocess_sample/fold_1/reports/2025-10-30_00-10-24 --data ./src/data/1_0_no_cv_preprocessed/train.parquet --adapter bow --batch-size 256
"""

from __future__ import annotations
import sys, argparse, json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

# ---- コスト計測 ----
from src.p4_0_compute_cost import (
    infer_cost_start, infer_cost_end,
    to_json_str, to_csv_str,
)

# ---- 統一出力 ----
from src.p4_0_output_infer_result import output_infer_run


# ========= adapter クラス =========
class BowAdapter:
    """空白区切り済みテキストを vocab.json でID化"""
    def __init__(self, ts_dir: Path):
        cand = [
            ts_dir / "vocab.json",
            ts_dir / "models" / "vocab.json",
            ts_dir.parent / "vocab.json",
        ]
        vocab_path = next((p for p in cand if p.exists()), None)
        if vocab_path is None:
            raise FileNotFoundError(f"vocab.json が見つかりません: {cand}")
        with open(vocab_path, "r", encoding="utf-8") as f:
            self.vocab: Dict[str, int] = json.load(f)
        self.unk_id = self.vocab.get("[UNK]", None)

    def encode_batch(self, texts: List[str], device: torch.device) -> Dict[str, torch.Tensor]:
        all_ids: List[int] = []
        offsets: List[int] = []
        cur = 0
        for t in texts:
            toks = (t or "").split()
            if not toks and self.unk_id is not None:
                toks = ["[UNK]"]
            ids = [self.vocab.get(tok, self.unk_id) for tok in toks if self.vocab.get(tok) is not None or self.unk_id is not None]
            ids = [i for i in ids if i is not None]
            offsets.append(cur)
            all_ids.extend(ids)
            cur += len(ids)
        if len(all_ids) == 0:
            all_ids = [0]
            offsets = list(range(0, len(texts)))
        return {
            "indices": torch.tensor(all_ids, dtype=torch.long, device=device),
            "offsets": torch.tensor(offsets, dtype=torch.long, device=device),
        }

class HFAdapter:
    """HuggingFace Tokenizer を用いた入力変換"""
    def __init__(self, tokenizer_name_or_path: str):
        from transformers import AutoTokenizer  # type: ignore
        self.tok = AutoTokenizer.from_pretrained(tokenizer_name_or_path, use_fast=True)
    def encode_batch(self, texts: List[str], device: torch.device) -> Dict[str, torch.Tensor]:
        out = self.tok(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
        return {k: v.to(device) for k, v in out.items()}

class NoneAdapter:
    """モデル構造不明時にダミー入力を与える"""
    def __init__(self, dim: int = 1024):
        self.dim = int(dim)
    def encode_batch(self, texts: List[str], device: torch.device) -> Dict[str, torch.Tensor]:
        x = torch.zeros((len(texts), self.dim), dtype=torch.float32, device=device)
        return {"x": x}


# ========= dataset & util =========
class TextDataset(Dataset):
    def __init__(self, texts: List[str]): self.texts = texts
    def __len__(self): return len(self.texts)
    def __getitem__(self, i: int): return self.texts[i]

def _read_parquet_texts(path: Path, max_samples: Optional[int]) -> List[str]:
    df = pd.read_parquet(path, columns=["content"])
    if max_samples: df = df.head(int(max_samples))
    return [("" if pd.isna(x) else str(x)) for x in df["content"].tolist()]


# ========= 推論本体 =========
@torch.inference_mode()
def _do_infer(model: torch.nn.Module, adapter, texts: List[str], batch_size: int, device: torch.device) -> None:
    model.eval()
    dl = DataLoader(TextDataset(texts), batch_size=batch_size, shuffle=False)
    for batch_texts in dl:
        enc = adapter.encode_batch(batch_texts, device=device)
        tried = False
        try:
            if "indices" in enc and "offsets" in enc:
                _ = model(enc["indices"], enc["offsets"]); tried = True
        except Exception: pass
        if tried: continue
        try:
            if "input_ids" in enc and "attention_mask" in enc:
                _ = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"]); tried = True
        except Exception: pass
        if tried: continue
        try:
            if "x" in enc:
                _ = model(enc["x"]); tried = True
        except Exception: pass
        if not tried:
            continue


# ========= main =========
def main():
    ap = argparse.ArgumentParser(description="Run inference and record cost (outputs handled by p4_0_output_infer_result.py).")
    ap.add_argument("--ts-dir", type=str, required=True, help="学習結果ディレクトリ（例: ./result/2025-10-29_21-00-00）")
    ap.add_argument("--data", type=str, required=False, help="テストデータParquet（contentカラム必須）")
    ap.add_argument("--adapter", type=str, default="bow", choices=["bow", "hf", "none"])
    ap.add_argument("--hf-tokenizer", type=str, default=None)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--max-samples", type=int, default=None)
    ap.add_argument("--device", type=str, default=None)
    ap.add_argument("--dummy-shape", type=int, default=1024)
    args = ap.parse_args()

    ts_dir = Path(args.ts_dir).resolve()
    if not ts_dir.exists():
        raise FileNotFoundError(f"--ts-dir が存在しません: {ts_dir}")

    model_path = ts_dir / "models" / "model.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"モデルが見つかりません: {model_path}")

    device = torch.device(args.device) if args.device else torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # モデル読込
    try:
        obj = torch.load(str(model_path), map_location=device)
        if isinstance(obj, torch.nn.Module):
            model = obj
        elif isinstance(obj, dict):
            m = torch.nn.Identity()
            try: m.load_state_dict(obj, strict=False)
            except Exception: pass
            model = m
        else:
            model = torch.jit.load(str(model_path), map_location=device)
    except Exception:
        model = torch.nn.Identity()
    model.to(device)

    # Adapter 準備
    if args.adapter == "bow":
        if args.data is None:
            raise ValueError("--adapter bow には --data が必要です。")
        adapter = BowAdapter(ts_dir)
    elif args.adapter == "hf":
        if not args.hf_tokenizer or args.data is None:
            raise ValueError("--adapter hf には --hf-tokenizer と --data が必要です。")
        adapter = HFAdapter(args.hf_tokenizer)
    else:
        adapter = NoneAdapter(args.dummy_shape)

    # 入力テキスト
    if args.adapter == "none":
        n = args.max_samples or 1024
        texts = [""] * int(n)
    else:
        if not args.data: raise ValueError("--data を指定してください。")
        texts = _read_parquet_texts(Path(args.data), args.max_samples)

    # ====== 計測 ======
    token = infer_cost_start(model=model)
    _do_infer(model, adapter, texts, batch_size=int(args.batch_size), device=device)
    metrics = infer_cost_end(token)

    # ====== 統一出力 ======
    json_str = to_json_str(metrics)
    hdr, row = to_csv_str(metrics)
    output_infer_run(
        ts_dir=ts_dir,
        infer_cost={
            "json_str": json_str,
            "csv_header": hdr,
            "csv_line": row,
        },
        extra_meta={
            "adapter": args.adapter,
            "hf_tokenizer": args.hf_tokenizer,
            "batch_size": args.batch_size,
            "max_samples": args.max_samples,
            "device": str(device),
            "model_path": str(model_path),
            "data_path": str(args.data) if args.data else None,
        },
    )

    print("[INFER] wall_time_sec:", metrics.get("wall_time_sec"))

if __name__ == "__main__":
    main()
