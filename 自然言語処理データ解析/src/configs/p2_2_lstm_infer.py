# src/p2_2_lstm_infer.py
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

from src.p4_0_compute_cost import infer_cost_start, infer_cost_end, to_json_str, to_csv_str  # 推論用エイリアス
from src.p4_0_output_infer_result import output_infer_run

PAD_ID, UNK_ID = 0, 1

class LSTMClassifier(torch.nn.Module):
    def __init__(self, num_embeddings, emb_dim, hidden, num_classes, bidir=True, num_layers=1, dropout=0.2):
        super().__init__()
        self.emb = torch.nn.Embedding(num_embeddings, emb_dim, padding_idx=PAD_ID)
        self.lstm = torch.nn.LSTM(emb_dim, hidden, num_layers=num_layers, batch_first=True,
                                  dropout=dropout if num_layers > 1 else 0.0, bidirectional=bidir)
        out_dim = hidden * (2 if bidir else 1)
        self.fc = torch.nn.Linear(out_dim, num_classes)

    def forward(self, x):
        e = self.emb(x)
        o, (h, c) = self.lstm(e)
        if self.lstm.bidirectional: h_last = torch.cat([h[-2], h[-1]], dim=1)
        else:                        h_last = h[-1]
        return self.fc(h_last)

class InferDataset(Dataset):
    def __init__(self, texts: List[str], vocab: Dict[str,int], max_len: int):
        self.texts = texts; self.vocab = vocab; self.max_len = max_len
    def __len__(self): return len(self.texts)
    def __getitem__(self, i):
        toks = str(self.texts[i]).split()
        ids = [self.vocab.get(t, UNK_ID) for t in toks][:self.max_len]
        if len(ids) < self.max_len: ids += [PAD_ID] * (self.max_len - len(ids))
        return torch.tensor(ids, dtype=torch.long)

def _read_parquet_texts(path: Path, max_samples: Optional[int]) -> List[str]:
    df = pd.read_parquet(path, columns=["content"])
    if max_samples: df = df.head(int(max_samples))
    return [("" if pd.isna(x) else str(x)) for x in df["content"].tolist()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", type=str, required=True, help="学習結果ディレクトリ（例: ./src/result/...）")
    ap.add_argument("--data", type=str, required=True, help="Parquet（content列）")
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--max-samples", type=int, default=None)
    ap.add_argument("--max-len", type=int, default=256)
    args = ap.parse_args()

    ts_dir = Path(args.ts_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # vocab / model / config を読む
    with open(ts_dir / "vocab.json", "r", encoding="utf-8") as f:
        vocab = json.load(f)
    with open(ts_dir / "config_used.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    model_path = ts_dir / "models" / "model.pt"
    if not model_path.exists():  # サンプル互換で .pt に状態辞書が入っている前提
        raise FileNotFoundError(f"モデルが見つかりません: {model_path}")

    model = LSTMClassifier(
        num_embeddings=len(vocab),
        emb_dim=int(cfg["model"]["emb_dim"]),
        hidden=int(cfg["model"]["hidden"]),
        num_classes=len(json.load(open(ts_dir / "label2id.json", "r", encoding="utf-8"))),
        bidir=bool(cfg["model"].get("bidirectional", True)),
        num_layers=int(cfg["model"].get("num_layers", 1)),
        dropout=float(cfg["model"].get("dropout", 0.2)),
    )
    # できれば state_dict をロード
    try:
        state = torch.load(str(model_path), map_location="cpu")
        model.load_state_dict(state, strict=False)
    except Exception:
        pass
    model = model.to(device).eval()

    texts = _read_parquet_texts(Path(args.data), args.max_samples)
    ds = InferDataset(texts, vocab, max_len=int(args.max_len))
    dl = DataLoader(ds, batch_size=int(args.batch_size), shuffle=False)

    # === コスト計測開始 ===
    token = infer_cost_start(model=model)

    with torch.inference_mode():
        for x in dl:
            x = x.to(device)
            _ = model(x)  # 予測は今回保存しない（コスト測定のみ）

    metrics = infer_cost_end(token)
    json_str = to_json_str(metrics); hdr, row = to_csv_str(metrics)

    output_infer_run(  # 推論一回分を <ts>/inference_*/ に保存
        ts_dir=ts_dir,
        infer_cost={"json_str": json_str, "csv_header": hdr, "csv_line": row},
        extra_meta={
            "device": str(device),
            "data_path": str(args.data),
            "batch_size": args.batch_size,
            "max_samples": args.max_samples,
        },
    )

    print("[INFER] wall_time_sec:", metrics.get("wall_time_sec"))

if __name__ == "__main__":
    main()
