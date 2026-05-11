# src/p2_2_lstm_train.py
from __future__ import annotations
import argparse, json, os, re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import torch.backends.cudnn as cudnn

# ==== 共通のコスト記録/出力 ====
from src.p4_0_compute_cost import cost_start, cost_end, to_json_str, to_csv_str  # 学習時間・GPUメモリなどの計測:contentReference[oaicite:4]{index=4}
from src.p4_0_output_train_result import (  # 既存サンプルと同じ形式で混同行列/履歴などを保存
    output_single_run, output_cv_fold, output_cv_summary
)

# --------- ユーティリティ（p1_0_sample_train.py の流儀を踏襲）---------
def set_seed(seed: int):
    import random
    random.seed(seed); np.random.seed(seed)
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    cudnn.deterministic = True; cudnn.benchmark = False
    os.environ["PYTHONHASHSEED"] = str(seed)

def is_cv_root(p: Path) -> bool:
    if not p.exists(): return False
    if any(re.match(r"cv_k\d+", d.name) for d in p.iterdir() if d.is_dir()): return True
    if re.match(r"cv_k\d+", p.name): return True
    if any(d.name.startswith("fold_") for d in p.iterdir() if d.is_dir()): return True
    return False

def resolve_cv_root(data_dir: str) -> Path:
    p = Path(data_dir)
    cv_dirs = [d for d in p.iterdir() if d.is_dir() and re.match(r"cv_k\d+", d.name)]
    if cv_dirs: return cv_dirs[0]
    if re.match(r"cv_k\d+", p.name): return p
    folds = [d for d in p.iterdir() if d.is_dir() and d.name.startswith("fold_")]
    if folds: return p
    raise FileNotFoundError(f"cv root not found under: {data_dir}")

def find_folds(cv_root: Path) -> List[Path]:
    return sorted([d for d in cv_root.iterdir() if d.is_dir() and d.name.startswith("fold_")],
                  key=lambda x: int(x.name.split("_")[1]))

def load_single_splits(data_dir: str):
    p = Path(data_dir)
    tr = pd.read_parquet(p / "train.parquet")
    va = pd.read_parquet(p / "val.parquet")
    te = pd.read_parquet(p / "test.parquet")
    for df in (tr, va, te):
        assert "content" in df.columns and "category" in df.columns
    return tr, va, te

def load_fold_splits(fold_dir: Path):
    tr = pd.read_parquet(fold_dir / "train.parquet")
    va = pd.read_parquet(fold_dir / "val.parquet")
    for df in (tr, va):
        assert "content" in df.columns and "category" in df.columns
    return tr, va

# --------- データセット（空白区切り済みトークン列をID列に）---------
PAD_ID, UNK_ID = 0, 1

class LSTMDataset(Dataset):
    def __init__(self, df: pd.DataFrame, label2id: Dict[str, int], vocab: Dict[str, int], max_len: int):
        self.labels = [label2id[str(y)] for y in df["category"].astype(str).tolist()]
        self.seqs = [str(x).split() for x in df["content"].astype(str).tolist()]
        self.vocab = vocab
        self.max_len = int(max_len)

    def __len__(self): return len(self.labels)

    def _encode(self, toks: List[str]) -> List[int]:
        ids = [self.vocab.get(t, UNK_ID) for t in toks][:self.max_len]
        if len(ids) < self.max_len:
            ids = ids + [PAD_ID] * (self.max_len - len(ids))
        return ids

    def __getitem__(self, i):
        x = torch.tensor(self._encode(self.seqs[i]), dtype=torch.long)
        y = torch.tensor(self.labels[i], dtype=torch.long)
        return x, y

# --------- fastText 語彙・埋め込みの作成 ---------
def build_vocab_from_train(train_texts: List[str], max_features: int) -> Dict[str, int]:
    from collections import Counter
    cnt = Counter()
    for line in train_texts:
        cnt.update(str(line).split())
    most = [w for w, _ in cnt.most_common(max_features - 2)]
    vocab = {"<PAD>": PAD_ID, "<UNK>": UNK_ID}
    for w in most:
        vocab[w] = len(vocab)
    return vocab

def load_fasttext_subset(vec_path: str, vocab: Dict[str,int], dim: int) -> np.ndarray:
    """
    .vec 形式（1行=単語＋次元）の簡易ローダ。vocab にある語だけ読み込む。
    未登場語はランダム小値、PADは0、UNKは平均0.0の正規分布。
    """
    emb = np.random.normal(0, 0.01, (len(vocab), dim)).astype(np.float32)
    emb[PAD_ID] = 0.0
    seen = 0
    with open(vec_path, "r", encoding="utf-8", errors="ignore") as f:
        first = f.readline()
        for line in f:
            parts = line.rstrip("\n").split(" ")
            if len(parts) < dim + 1: continue
            w = parts[0]
            if w in vocab:
                vec = np.asarray(parts[1:1+dim], dtype=np.float32)
                if vec.shape[0] == dim:
                    emb[vocab[w]] = vec
                    seen += 1
    # UNK は埋め込みの平均で初期化（簡易）
    emb[UNK_ID] = emb.mean(axis=0)
    print(f"[fastText] loaded vectors for {seen}/{len(vocab)} tokens")
    return emb

# --------- モデル ---------
class LSTMClassifier(nn.Module):
    def __init__(self, num_embeddings: int, emb_dim: int, hidden: int, num_classes: int,
                 embeddings: Optional[np.ndarray] = None, freeze_emb: bool = False,
                 num_layers: int = 1, bidir: bool = True, dropout: float = 0.2):
        super().__init__()
        self.emb = nn.Embedding(num_embeddings, emb_dim, padding_idx=PAD_ID)
        if embeddings is not None:
            self.emb.weight.data.copy_(torch.from_numpy(embeddings))
        self.emb.weight.requires_grad = not freeze_emb

        self.lstm = nn.LSTM(
            input_size=emb_dim, hidden_size=hidden,
            num_layers=num_layers, batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=bidir
        )
        out_dim = hidden * (2 if bidir else 1)
        self.fc = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(out_dim, num_classes)
        )

    def forward(self, x):
        e = self.emb(x)              # (B, L, D)
        o, (h, c) = self.lstm(e)     # 最終層の双方向隠れ状態を結合
        if self.lstm.bidirectional:
            h_last = torch.cat([h[-2], h[-1]], dim=1)  # (B, 2H)
        else:
            h_last = h[-1]                              # (B, H)
        return self.fc(h_last)

# --------- 評価ユーティリティ（混同行列/指標）---------
def confusion_and_metrics(y_true: np.ndarray, y_pred: np.ndarray, K: int):
    cm = np.zeros((K, K), dtype=np.int64)
    for t, p in zip(y_true, y_pred): cm[t, p] += 1
    per_class = []
    for k in range(K):
        tp = cm[k, k]; fp = cm[:, k].sum() - tp; fn = cm[k, :].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = (2*prec*rec)/(prec+rec) if (prec+rec) > 0 else 0.0
        per_class.append(dict(precision=prec, recall=rec, f1=f1, support=int(cm[k, :].sum())))
    acc = float(np.trace(cm) / max(cm.sum(), 1))
    return cm, per_class, acc

@torch.no_grad()
def eval_loader(model, loader, device):
    ys, ps = [], []
    for x, y in loader:
        x = x.to(device); y = y.to(device)
        logits = model(x); preds = torch.argmax(logits, dim=1)
        ys.extend(y.tolist()); ps.extend(preds.tolist())
    ys = np.array(ys, dtype=np.int64); ps = np.array(ps, dtype=np.int64)
    return ys, ps, float((ys == ps).mean()) if len(ys) else 0.0

# --------- 学習ループ ---------
def train(
    train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: Optional[pd.DataFrame],
    cfg: dict, save_dir: Path
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] device={device}")

    # ラベル辞書
    labels = sorted(train_df["category"].astype(str).unique().tolist())
    label2id = {lab: i for i, lab in enumerate(labels)}
    id2label = {i: lab for lab, i in label2id.items()}
    num_classes = len(labels)

    # 語彙と埋め込み
    vocab = build_vocab_from_train(train_df["content"].astype(str).tolist(),
                                   max_features=int(cfg["model"]["max_features"]))
    emb_dim = int(cfg["model"]["emb_dim"])
    ft_path = cfg["model"]["fasttext_vec_path"]
    emb = load_fasttext_subset(ft_path, vocab, emb_dim)  # fastText を読み込み（プロジェクト規則）

    # Dataset/DataLoader
    max_len = int(cfg["train"]["max_len"])
    bs = int(cfg["train"]["batch_size"])
    tr_ds = LSTMDataset(train_df, label2id, vocab, max_len)
    va_ds = LSTMDataset(val_df,   label2id, vocab, max_len)
    tr_loader = DataLoader(tr_ds, batch_size=bs, shuffle=True)
    va_loader = DataLoader(va_ds, batch_size=bs, shuffle=False)

    te_loader = None
    if test_df is not None:
        te_ds = LSTMDataset(test_df, label2id, vocab, max_len)
        te_loader = DataLoader(te_ds, batch_size=bs, shuffle=False)

    # モデル
    model = LSTMClassifier(
        num_embeddings=len(vocab), emb_dim=emb_dim,
        hidden=int(cfg["model"]["hidden"]),
        num_classes=num_classes,
        embeddings=emb, freeze_emb=bool(cfg["model"].get("freeze_emb", False)),
        num_layers=int(cfg["model"].get("num_layers", 1)),
        bidir=bool(cfg["model"].get("bidirectional", True)),
        dropout=float(cfg["model"].get("dropout", 0.2))
    ).to(device)

    # コスト計測開始（規則②）
    token = cost_start(model=model, phase="train", note="LSTM single/CV")

    # 学習設定
    opt = torch.optim.AdamW(model.parameters(), lr=float(cfg["train"]["lr"]),
                            weight_decay=float(cfg["train"].get("weight_decay", 1e-4)))
    crit = nn.CrossEntropyLoss()
    epochs = int(cfg["train"]["epochs"]); patience = int(cfg["train"].get("patience", 4))
    best_va = -1.0; best_state = None; wait = 0
    hist = {"epoch": [], "train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    for ep in range(1, epochs+1):
        model.train(); run_loss=0.0; n=0
        for x, y in tr_loader:
            x=x.to(device); y=y.to(device)
            opt.zero_grad()
            logits = model(x); loss = crit(logits, y)
            loss.backward(); opt.step()
            run_loss += loss.item()*y.size(0); n += y.size(0)

        # 評価
        model.eval()
        y_tr, p_tr, tr_acc = eval_loader(model, tr_loader, device)
        y_va, p_va, va_acc = eval_loader(model, va_loader, device)
        va_loss = 0.0  # 省略（必要なら再計算）

        print(f"Epoch {ep:02d} | tr_acc={tr_acc:.4f} | va_acc={va_acc:.4f}")
        hist["epoch"].append(ep); hist["train_loss"].append(run_loss/max(n,1)); hist["val_loss"].append(va_loss)
        hist["train_acc"].append(tr_acc); hist["val_acc"].append(va_acc)

        if va_acc > best_va:
            best_va = va_acc; best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}; wait = 0
        else:
            wait += 1
            if wait >= patience:
                print(f"Early stopping at epoch {ep} (best val_acc={best_va:.4f})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    # コスト計測終了
    cost_metrics = cost_end(token)
    cost_json = to_json_str(cost_metrics); cost_hdr, cost_row = to_csv_str(cost_metrics)

    # 予備評価 & 出力（規則③・⑭）
    y_tr, p_tr, _ = eval_loader(model, tr_loader, device)
    y_va, p_va, _ = eval_loader(model, va_loader, device)
    if te_loader is not None:
        y_te, p_te, _ = eval_loader(model, te_loader, device)
    else:
        y_te, p_te = np.array([], dtype=np.int64), np.array([], dtype=np.int64)

    # アーティファクト（語彙など）を保存しておくと推論側が楽（サンプルに倣う）
    artifacts = {
        "vocab.json": {k: int(v) for k, v in vocab.items()},
        "label2id.json": {k: int(v) for k, v in label2id.items()},
        "config_used.json": cfg,
    }

    output_single_run(
        out_dir=save_dir,
        splits={
            "train": {"y_true": y_tr, "y_pred": p_tr, "id2label": id2label},
            "val":   {"y_true": y_va, "y_pred": p_va, "id2label": id2label},
            "test":  {"y_true": y_te, "y_pred": p_te, "id2label": id2label},
        },
        training_cost={"json_str": cost_json, "csv_header": cost_hdr, "csv_line": cost_row},
        figures=True,
        config_content=cfg,
        history=hist,
        model=model,
        model_extra={},
        model_info={"vocab_size": len(vocab), "emb_dim": emb_dim},
        artifacts=artifacts,
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, required=True, help="JSON config for LSTM")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    set_seed(int(cfg["train"].get("random_seed", 42)))

    data_dir = cfg["paths"]["data_dir"]
    save_dir = Path(cfg["paths"]["save_dir"]); save_dir.mkdir(parents=True, exist_ok=True)

    if is_cv_root(Path(data_dir)):
        # CV ルート直下の fold_* を順に学習
        cv_root = resolve_cv_root(data_dir)
        folds = find_folds(cv_root)
        summaries = []
        for fi, fold_dir in enumerate(folds, start=1):
            print(f"===== FOLD {fi}/{len(folds)} : {fold_dir.name} =====")
            tr_df, va_df = load_fold_splits(fold_dir)
            maybe_test = (cv_root / "test.parquet")
            te_df = pd.read_parquet(maybe_test) if maybe_test.exists() else None

            fold_save = save_dir / fold_dir.name; fold_save.mkdir(parents=True, exist_ok=True)
            train(tr_df, va_df, te_df, cfg, fold_save)

            # ここでは fold ごとの集約は簡略化。必要なら accuracy を読み戻して output_cv_fold に集約可能。
        output_cv_summary(out_dir=save_dir, fold_summaries=[])
    else:
        tr, va, te = load_single_splits(data_dir)
        train(tr, va, te, cfg, save_dir)

if __name__ == "__main__":
    main()
