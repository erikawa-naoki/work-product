"""
p1_0_sample.py (BoW + MLP, CV対応)
動作例：python -m src.p1_0_sample_train --config ./src/configs/1_0/NN_config.json をルートディレクトリで実行
- 前処理は p1_0_1_preprocess.py（Sudachiで空白区切り）を想定
- 単一分割: data_dir/{train,val,test}.parquet
- CV形式 : data_dir/cv_kK/fold_*/{train,val}.parquet (+ test.parquet 任意)
- 中間生成物，可視化/集計およびモデルは result 側へ保存．どちらもgitで保存しない．

"""

from __future__ import annotations
import argparse, json, os, csv, random, re, io
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torch.backends.cudnn as cudnn
from collections import Counter
import matplotlib.pyplot as plt

from src.p4_0_compute_cost import (
    cost_start, cost_end, to_json_str, to_csv_str,
    infer_cost_start, infer_cost_end
)
from src.p4_0_output_train_result import (
    output_single_run, output_cv_fold, output_cv_summary
)


# -------------------------
# Utils
# -------------------------
def _to_npy_bytes(arr: np.ndarray) -> bytes:
    """np.ndarray を .npy バイナリ(bytes)に直列化"""
    import io
    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


def compute_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm

def metrics_from_confusion(cm: np.ndarray):
    K = cm.shape[0]
    per_class = []
    for k in range(K):
        tp = cm[k, k]
        fp = cm[:, k].sum() - tp
        fn = cm[k, :].sum() - tp
        support = cm[k, :].sum()
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = (2*prec*rec)/(prec+rec) if (prec+rec) > 0 else 0.0
        per_class.append(dict(precision=prec, recall=rec, f1=f1, support=int(support)))
    supports = np.array([pc["support"] for pc in per_class], dtype=np.int64)
    weights = supports / max(supports.sum(), 1)
    macro = dict(
        precision=float(np.mean([pc["precision"] for pc in per_class])),
        recall=float(np.mean([pc["recall"] for pc in per_class])),
        f1=float(np.mean([pc["f1"] for pc in per_class])),
        support=int(supports.sum())
    )
    weighted = dict(
        precision=float(np.sum([pc["precision"]*w for pc, w in zip(per_class, weights)])),
        recall=float(np.sum([pc["recall"]*w for pc, w in zip(per_class, weights)])),
        f1=float(np.sum([pc["f1"]*w for pc, w in zip(per_class, weights)])),
        support=int(supports.sum())
    )
    tp_sum = int(np.trace(cm))
    total = int(cm.sum())
    micro_prec = tp_sum / total if total > 0 else 0.0
    micro = dict(precision=float(micro_prec), recall=float(micro_prec), f1=float(micro_prec), support=int(supports.sum()))
    accuracy = float(tp_sum / max(total, 1))
    return per_class, macro, micro, weighted, accuracy

def print_report(split_name: str, y_true: np.ndarray, y_pred: np.ndarray, id2label: Dict[int,str], save_path: Path):
    save_path.mkdir(parents=True, exist_ok=True)
    cm = compute_confusion_matrix(y_true, y_pred, num_classes=len(id2label))
    per_class, macro, micro, weighted, acc = metrics_from_confusion(cm)

    # per-class CSV
    with open(save_path / f"{split_name}_per_class.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "precision", "recall", "f1", "support"])
        for i, pc in enumerate(per_class):
            w.writerow([id2label.get(i, str(i)), pc["precision"], pc["recall"], pc["f1"], pc["support"]])

    # summary JSON
    summary = dict(accuracy=acc, micro=micro, macro=macro, weighted=weighted)
    (save_path / f"{split_name}_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # 混同行列（npy + 可視化PNG）
    np.save(save_path / f"{split_name}_confusion.npy", cm)

    # 混同行列をPNGで
    plt.figure()
    plt.imshow(cm, interpolation="nearest")
    plt.title(f"Confusion Matrix ({split_name})")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(save_path / f"{split_name}_confusion.png", dpi=150)
    plt.close()

def set_seed(seed: int):
    random.seed(seed); np.random.seed(seed)
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    cudnn.deterministic = True; cudnn.benchmark = False
    os.environ["PYTHONHASHSEED"] = str(seed)
    print(f"[INFO] Random seed fixed to {seed}")

def load_json(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_default_config_path() -> str:
    return "./configs/1_0/NN_config.json"

def is_cv_root(p: Path) -> bool:
    """data_dir が cv_k*/fold_* 構造を持つか自動判定"""
    if not p.exists():
        return False
    # data_dir 直下が cv_k*/... の場合
    cv_dirs = [d for d in p.iterdir() if d.is_dir() and re.match(r"cv_k\d+", d.name)]
    if cv_dirs:
        return True
    # data_dir 自身が cv_k*/... の場合
    if re.match(r"cv_k\d+", p.name):
        return True
    # data_dir 直下に fold_* がある場合
    folds = [d for d in p.iterdir() if d.is_dir() and d.name.startswith("fold_")]
    return len(folds) > 0

def resolve_cv_root(data_dir: str) -> Path:
    """data_dir が cv_k*/fold_* を内包していればそのルートを返す"""
    p = Path(data_dir)
    if not p.exists():
        raise FileNotFoundError(f"data_dir not found: {data_dir}")
    # data_dir/cv_k*/...
    cv_dirs = [d for d in p.iterdir() if d.is_dir() and re.match(r"cv_k\d+", d.name)]
    if cv_dirs:
        # 一つに決め打ち（複数存在なら先頭）
        return cv_dirs[0]
    # data_dir 自身が cv_k* のとき
    if re.match(r"cv_k\d+", p.name):
        return p
    # data_dir 直下に fold_*
    folds = [d for d in p.iterdir() if d.is_dir() and d.name.startswith("fold_")]
    if folds:
        return p
    raise FileNotFoundError(f"cv root not found under: {data_dir}")

def load_single_splits(data_dir: str):
    p = Path(data_dir)
    train = pd.read_parquet(p / "train.parquet")
    val   = pd.read_parquet(p / "val.parquet")
    test  = pd.read_parquet(p / "test.parquet")
    for df in (train, val, test):
        assert "content" in df.columns and "category" in df.columns
    return train, val, test

def find_folds(cv_root: Path) -> List[Path]:
    folds = sorted([d for d in cv_root.iterdir() if d.is_dir() and d.name.startswith("fold_")],
                   key=lambda x: int(x.name.split("_")[1]))
    if not folds:
        raise FileNotFoundError(f"No fold_* directories under: {cv_root}")
    return folds

def load_fold_splits(fold_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    tr = pd.read_parquet(fold_dir / "train.parquet")
    va = pd.read_parquet(fold_dir / "val.parquet")
    for df in (tr, va):
        assert "content" in df.columns and "category" in df.columns
    return tr, va

def maybe_load_test(cv_root: Path) -> Optional[pd.DataFrame]:
    tp = cv_root / "test.parquet"
    return pd.read_parquet(tp) if tp.exists() else None

def build_ngrams(tokens: List[str], ngram_max: int) -> List[str]:
    if ngram_max <= 1:
        return tokens
    out = tokens[:]
    for n in range(2, ngram_max + 1):
        for i in range(len(tokens) - n + 1):
            out.append("§§".join(tokens[i:i+n]))
    return out


# -------------------------
# Vocabulary + IDF
# -------------------------

SPECIALS = ["<PAD>", "<UNK>"]
PAD, UNK = 0, 1

def build_vocab(train_texts: List[str], max_features: int, ngram_max: int) -> Tuple[Dict[str,int], np.ndarray]:
    df_counts = Counter(); tok_counts = Counter()
    for line in train_texts:
        toks = str(line).split()
        toks = build_ngrams(toks, ngram_max)
        tok_counts.update(toks)
        df_counts.update(set(toks))
    most_common = [w for w, _ in tok_counts.most_common(max_features - len(SPECIALS))]
    vocab = {sp: i for i, sp in enumerate(SPECIALS)}
    for w in most_common:
        vocab[w] = len(vocab)
    df_vec = np.zeros(len(vocab), dtype=np.int64)
    for w, df in df_counts.items():
        idx = vocab.get(w, None)
        if idx is not None:
            df_vec[idx] = df
    return vocab, df_vec

def compute_idf(df_vec: np.ndarray, n_docs: int) -> np.ndarray:
    idf = np.log((n_docs + 1) / (df_vec + 1)) + 1.0
    idf[PAD] = 0.0; idf[UNK] = 1.0
    return idf.astype(np.float32)


# -------------------------
# Dataset & Collate
# -------------------------

class BoWDataset(Dataset):
    def __init__(self, df: pd.DataFrame, vocab: Dict[str,int], idf: np.ndarray, ngram_max: int, label2id: Dict[str,int]):
        self.texts = df["content"].astype(str).tolist()
        self.labels = [label2id[str(y)] for y in df["category"].astype(str).tolist()]
        self.vocab = vocab; self.idf = idf; self.ngram_max = ngram_max
    def __len__(self): return len(self.texts)
    def _encode(self, text: str):
        toks = build_ngrams(text.split(), self.ngram_max)
        cnt = Counter(self.vocab.get(t, UNK) for t in toks)
        if not cnt:
            return torch.tensor([UNK], dtype=torch.long), torch.tensor([float(self.idf[UNK])], dtype=torch.float32)
        ids = torch.tensor(list(cnt.keys()), dtype=torch.long)
        ws  = torch.tensor([c * float(self.idf[i]) for i, c in cnt.items()], dtype=torch.float32)
        return ids, ws
    def __getitem__(self, idx):
        x_ids, x_w = self._encode(self.texts[idx])
        return x_ids, x_w, self.labels[idx]

def collate_bow(batch):
    flat_ids, flat_ws, offsets, labels = [], [], [0], []
    total = 0
    for ids, ws, y in batch:
        flat_ids.append(ids); flat_ws.append(ws)
        total += len(ids); offsets.append(total)
        labels.append(y)
    return (torch.cat(flat_ids, 0),
            torch.tensor(offsets[:-1], dtype=torch.long),
            torch.cat(flat_ws, 0),
            torch.tensor(labels, dtype=torch.long))


# -------------------------
# Model
# -------------------------

class BoWFFNN(nn.Module):
    def __init__(self, vocab_size: int, embed_dim: int, num_classes: int, hidden_dim: int, dropout: float):
        super().__init__()
        self.emb = nn.EmbeddingBag(vocab_size, embed_dim, mode="sum", include_last_offset=False)
        self.ff = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )
    def forward(self, flat_ids, offsets, per_sample_weights=None):
        x = self.emb(flat_ids, offsets, per_sample_weights=per_sample_weights)
        return self.ff(x)


# -------------------------
# Training / Eval
# -------------------------

@torch.no_grad()
def eval_loader(model, loader, device):
    ys, ps = [], []
    for flat_ids, offsets, flat_ws, labels in loader:
        flat_ids = flat_ids.to(device); offsets = offsets.to(device)
        flat_ws  = flat_ws.to(device);  labels  = labels.to(device)
        logits = model(flat_ids, offsets, per_sample_weights=flat_ws)
        preds = torch.argmax(logits, dim=1)
        ys.extend(labels.tolist()); ps.extend(preds.tolist())
    y_true = np.array(ys, dtype=np.int64); y_pred = np.array(ps, dtype=np.int64)
    acc = float((y_true == y_pred).mean()) if len(y_true)>0 else 0.0
    return acc, y_true, y_pred

def evaluate_loss_acc(model, loader, device, criterion):
    model.eval()
    total_loss = 0.0; total_n = 0; ys=[]; ps=[]
    with torch.no_grad():
        for flat_ids, offsets, flat_ws, labels in loader:
            flat_ids = flat_ids.to(device); offsets = offsets.to(device)
            flat_ws  = flat_ws.to(device);  labels  = labels.to(device)
            logits = model(flat_ids, offsets, per_sample_weights=flat_ws)
            loss = criterion(logits, labels)
            preds = torch.argmax(logits, dim=1)
            bs = labels.size(0)
            total_loss += loss.item() * bs; total_n += bs
            ys.extend(labels.tolist()); ps.extend(preds.tolist())
    acc = float((np.array(ys)==np.array(ps)).mean()) if total_n>0 else 0.0
    return total_loss/max(total_n,1), acc

def train_loop(model, train_loader, val_loader, device, epochs, lr, weight_decay, patience):
    criterion = nn.CrossEntropyLoss()
    optim = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    best_val = -1.0; best_state=None; wait=0

    hist = {"epoch": [], "train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    for ep in range(1, epochs+1):
        model.train(); running=0.0; n=0
        for flat_ids, offsets, flat_ws, labels in train_loader:
            flat_ids=flat_ids.to(device); offsets=offsets.to(device)
            flat_ws =flat_ws.to(device);  labels =labels.to(device)
            optim.zero_grad()
            logits = model(flat_ids, offsets, per_sample_weights=flat_ws)
            loss = criterion(logits, labels); loss.backward(); optim.step()
            running += loss.item()*labels.size(0); n += labels.size(0)
        tr_loss, tr_acc = evaluate_loss_acc(model, train_loader, device, criterion)
        va_loss, va_acc = evaluate_loss_acc(model, val_loader,   device, criterion)
        print(f"Epoch {ep:02d} | tr_loss={tr_loss:.4f} | tr_acc={tr_acc:.4f} | va_loss={va_loss:.4f} | va_acc={va_acc:.4f}")
        hist["epoch"].append(ep); hist["train_loss"].append(tr_loss); hist["val_loss"].append(va_loss)
        hist["train_acc"].append(tr_acc); hist["val_acc"].append(va_acc)
        if va_acc > best_val:
            best_val = va_acc
            best_state = {k: v.detach().cpu().clone() for k,v in model.state_dict().items()}
            wait=0
        else:
            wait+=1
            if wait>=patience:
                print(f"Early stopping at epoch {ep} (best val_acc={best_val:.4f})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    return best_val, hist



# -------------------------
# Main
# -------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=None,
                    help="JSON config path (default: ./configs/1_0/NN_config.json)")
    args = ap.parse_args()

    cfg_path = Path(args.config or get_default_config_path())
    cfg = load_json(cfg_path)

    paths = cfg.get("paths", {})
    model_conf = cfg.get("model", {})
    train_conf = cfg.get("train", {})
    report_conf = cfg.get("report", {})
    cv_conf = cfg.get("cv", {})  # 追加: { "enabled": true/false } を任意で指定可

    # パラメータ読み込み
    data_dir    = paths.get("data_dir", "./data/X_Y_please_set_output_dir")
    save_root   = paths.get("save_dir", "./result/X_Y_please_set_output_dir")
    max_features = int(model_conf.get("max_features", 80000))
    ngram_max    = int(model_conf.get("ngram_max", 1))
    embed_dim    = int(model_conf.get("embed_dim", 256))
    hidden_dim   = int(model_conf.get("hidden_dim", 256))
    dropout      = float(model_conf.get("dropout", 0.2))
    batch_size   = int(train_conf.get("batch_size", 128))
    epochs       = int(train_conf.get("epochs", 20))
    lr           = float(train_conf.get("lr", 1e-3))
    weight_decay = float(train_conf.get("weight_decay", 1e-4))
    patience     = int(train_conf.get("patience", 4))
    log_scale = bool(report_conf.get("log_scale", False))
    random_seed  = int(train_conf.get("random_seed", 42))
    set_seed(random_seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")

    # ===== CV か単一分割か判定 =====
    cv_enabled = bool(cv_conf.get("enabled", True))
    
    if cv_enabled:
        # ===== CV モード =====
        cv_root = resolve_cv_root(data_dir)
        folds = find_folds(cv_root)
        test_df = maybe_load_test(cv_root)
        has_test = test_df is not None
        print(f"[CV] root={cv_root}  folds={[f.name for f in folds]}  has_test={has_test}")

        fold_summaries = []

        for fi, fold_dir in enumerate(folds, start=1):
            print(f"\n===== FOLD {fi}/{len(folds)} : {fold_dir.name} =====")

            # 1) データ読み込み（foldごと）
            train_df, val_df = load_fold_splits(fold_dir)

            # 2) ラベル辞書（foldのtrainから）
            labels = sorted(train_df["category"].astype(str).unique().tolist())
            label2id = {lab: i for i, lab in enumerate(labels)}
            id2label = {i: lab for lab, i in label2id.items()}
            num_classes = len(labels)

            # 3) 語彙 + IDF（foldのtrainから）
            vocab, df_vec = build_vocab(
                train_df["content"].astype(str).tolist(),
                max_features=max_features,
                ngram_max=ngram_max
            )
            idf = compute_idf(df_vec, n_docs=len(train_df))

            # 4) Dataset / DataLoader
            train_ds = BoWDataset(train_df, vocab, idf, ngram_max, label2id)
            val_ds   = BoWDataset(val_df,   vocab, idf, ngram_max, label2id)
            train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  collate_fn=collate_bow, num_workers=0)
            val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, collate_fn=collate_bow, num_workers=0)

            # 5) モデル（vocab確定後に作成）
            model = BoWFFNN(
                vocab_size=len(vocab),
                embed_dim=embed_dim,
                num_classes=num_classes,
                hidden_dim=hidden_dim,
                dropout=dropout,
            ).to(device)

            # 6) 学習コスト開始（PyTorch時系列を有効化）
            fold_token = cost_start(
                model=model,
                phase="train",
                note=f"BoWFFNN CV {fold_dir.name}",
            )

            # 7) 学習（学習曲線は fold配下の reports へ）
            save_dir_fold = Path(save_root) / fold_dir.name
            best_val, hist = train_loop(
                model, train_loader, val_loader, device,
                epochs, lr, weight_decay, patience
            )

            # 8) 学習コスト終了（保存はしない）
            fold_cost_metrics = cost_end(fold_token)
            fold_cost_json = to_json_str(fold_cost_metrics)
            fold_cost_csv_header, fold_cost_csv_line = to_csv_str(fold_cost_metrics)

            # 9) 評価（val）
            val_acc, y_va, p_va = eval_loader(model, val_loader, device)
            print(f"[FOLD {fi}] val_acc={val_acc:.4f} (best_tracker={best_val:.4f})")

            # 10) test（あれば）
            test_acc = None
            test_pack = None
            if has_test:
                test_ds = BoWDataset(test_df, vocab, idf, ngram_max, label2id)
                test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_bow, num_workers=0)
                test_acc, y_te, p_te = eval_loader(model, test_loader, device)
                print(f"[FOLD {fi}] test_acc={test_acc:.4f}")
                test_pack = {"y_true": y_te, "y_pred": p_te, "id2label": id2label}

            # 11) 出力保存（result 側）
            rep_dir = (Path(save_root) / fold_dir.name / "reports")
            rep_dir.mkdir(parents=True, exist_ok=True)

            # ★ 中間生成物を result 側に保存（data 側には書かない）
            artifacts = {
                "vocab.json": vocab,                 # dict → JSON
                "label2id.json": label2id,           # dict → JSON
                "idf.npy": _to_npy_bytes(idf),       # ndarray → bytes(.npy)
            }
            promote = ["vocab.json", "label2id.json"]  # 推論時に参照しやすいよう models/ にも複製

            output_cv_fold(
                fold_name=fold_dir.name,
                out_dir=rep_dir,
                val={"y_true": y_va, "y_pred": p_va, "id2label": id2label},
                test=test_pack,  # NoneでもOK
                training_cost={
                    "json_str": fold_cost_json,
                    "csv_header": fold_cost_csv_header,
                    "csv_line": fold_cost_csv_line,
                },
                figures=True,
                config_content=cfg,
                history=hist,
                model=model,
                model_extra={},
                model_info={"vocab_size": len(vocab), "embed_dim": embed_dim},
                artifacts=artifacts,
            )

            # 13) まとめ
            fold_summaries.append({
                "fold": fold_dir.name,
                "val_acc": float(val_acc),
                "best_val": float(best_val),
                "test_acc": (None if test_acc is None else float(test_acc))
            })

        # 14) CV最終集計（result 側）
        output_cv_summary(out_dir=Path(save_root), fold_summaries=fold_summaries)

    else:
        # ===== 単一分割モード =====
        Path(save_root).mkdir(parents=True, exist_ok=True)
        train_df, val_df, test_df = load_single_splits(data_dir)

        labels = sorted(train_df["category"].astype(str).unique().tolist())
        label2id = {lab:i for i,lab in enumerate(labels)}
        num_classes = len(labels)

        vocab, df_vec = build_vocab(train_df["content"].astype(str).tolist(), max_features, ngram_max)
        idf = compute_idf(df_vec, n_docs=len(train_df))

        train_ds = BoWDataset(train_df, vocab, idf, ngram_max, label2id)
        val_ds   = BoWDataset(val_df,   vocab, idf, ngram_max, label2id)
        test_ds  = BoWDataset(test_df,  vocab, idf, ngram_max, label2id)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  collate_fn=collate_bow, num_workers=0)
        val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, collate_fn=collate_bow, num_workers=0)
        test_loader  = DataLoader(test_ds,  batch_size=batch_size, shuffle=False, collate_fn=collate_bow, num_workers=0)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = BoWFFNN(
            vocab_size=len(vocab),
            embed_dim=embed_dim,
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            dropout=dropout,
        ).to(device)

        # （モデル作成の直後）学習前コスト計測開始（PyTorch時系列を有効化）
        train_token = cost_start(
            model=model,
            phase="train",
            note="BoWFFNN single-split",
        )

        # 学習（学習曲線保存は既存のまま）
        best_val, hist = train_loop(model, train_loader, val_loader, device, 
                                    epochs, lr, weight_decay, patience)

        # 学習直後コスト取得（保存はしない）
        train_cost_metrics = cost_end(train_token)
        train_cost_json = to_json_str(train_cost_metrics)
        train_cost_csv_header, train_cost_csv_line = to_csv_str(train_cost_metrics)

        # === 評価 ===
        tr_acc, y_tr, p_tr = eval_loader(model, train_loader, device)
        va_acc, y_va, p_va = eval_loader(model, val_loader, device)
        te_acc, y_te, p_te = eval_loader(model, test_loader, device)
        id2label = {i: lab for lab, i in label2id.items()}

        # === 出力と保存 ===
        rep_dir = Path(save_root)
        rep_dir.mkdir(parents=True, exist_ok=True)

        # ★ 中間生成物（result 側へ）
        artifacts = {
            "vocab.json": vocab,
            "label2id.json": label2id,
            "idf.npy": _to_npy_bytes(idf),
        }
        promote = ["vocab.json", "label2id.json"]

        output_single_run(
            out_dir=rep_dir,
            splits={
                "train": {"y_true": y_tr, "y_pred": p_tr, "id2label": id2label},
                "val":   {"y_true": y_va, "y_pred": p_va, "id2label": id2label},
                "test":  {"y_true": y_te, "y_pred": p_te, "id2label": id2label},
            },
            training_cost={
                "json_str": train_cost_json,
                "csv_header": train_cost_csv_header,
                "csv_line": train_cost_csv_line,
            },
            figures=True,  # 混同行列PNGを保存
            config_content=cfg,
            history=hist,
            model=model,
            model_extra={},
            model_info={"vocab_size": len(vocab), "embed_dim": embed_dim},
            artifacts=artifacts,
        )


if __name__ == "__main__":
    main()
