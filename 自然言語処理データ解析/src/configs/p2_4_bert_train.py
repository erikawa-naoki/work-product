# =========================================================
# p2_4_bert_train.py (Parquet対応・p1_0_sample と同様の出力形式)
# =========================================================
# BERTによる日本語テキスト分類（CVあり／なし自動切り替え対応）
# 出力: foldごとの reports ディレクトリに per-class CSV / summary JSON / confusion .npy/.png,
#      result 側に model, artifacts (label2id.json など), 学習履歴, cost情報 を保存
# =========================================================

from __future__ import annotations
import os, json, random, csv, io, argparse, math
from pathlib import Path
from typing import Dict, Tuple, List, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from transformers import BertTokenizer, BertModel, get_linear_schedule_with_warmup
from torch.optim import AdamW
import matplotlib.pyplot as plt

# cost / output utilities (プロジェクト内にあることが前提)
from src.p4_0_compute_cost import cost_start, cost_end, to_json_str, to_csv_str
from src.p4_0_output_train_result import output_single_run, output_cv_fold, output_cv_summary

# -------------------------
# ユーティリティ（p1_0_sample と同等）
# -------------------------
def _to_npy_bytes(arr: np.ndarray) -> bytes:
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
        tp = int(cm[k, k])
        fp = int(cm[:, k].sum() - tp)
        fn = int(cm[k, :].sum() - tp)
        support = int(cm[k, :].sum())
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

def print_report_and_save(split_name: str, y_true: np.ndarray, y_pred: np.ndarray, id2label: Dict[int,str], save_path: Path):
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

    # confusion matrix (.npy + .png)
    np.save(save_path / f"{split_name}_confusion.npy", cm)
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

# Reuse CV helpers from sample (resolve_cv_root, find_folds, load_fold_splits, maybe_load_test, load_single_splits)
import re
def resolve_cv_root(data_dir: str) -> Path:
    p = Path(data_dir)
    if not p.exists():
        raise FileNotFoundError(f"data_dir not found: {data_dir}")
    cv_dirs = [d for d in p.iterdir() if d.is_dir() and re.match(r"cv_k\d+", d.name)]
    if cv_dirs:
        return cv_dirs[0]
    if re.match(r"cv_k\d+", p.name):
        return p
    folds = [d for d in p.iterdir() if d.is_dir() and d.name.startswith("fold_")]
    if folds:
        return p
    raise FileNotFoundError(f"cv root not found under: {data_dir}")

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

def load_single_splits(data_dir: str):
    p = Path(data_dir)
    train = pd.read_parquet(p / "train.parquet")
    val   = pd.read_parquet(p / "val.parquet")
    test  = pd.read_parquet(p / "test.parquet")
    for df in (train, val, test):
        assert "content" in df.columns and "category" in df.columns
    return train, val, test

# -------------------------
# Dataset / Model (BERT)
# -------------------------
class BERTDataset(Dataset):
    def __init__(self, df: pd.DataFrame, tokenizer, label2id: Dict[str,int], max_length: int = 256):
        self.texts = df["content"].astype(str).tolist()
        # category may be int; keep mapping via str keys consistent with sample output expectations
        self.labels = [label2id[str(y)] for y in df["category"].tolist()]
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self): return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = int(self.labels[idx])
        encoding = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label, dtype=torch.long)
        }

def collate_bert(batch):
    input_ids = torch.stack([b["input_ids"] for b in batch])
    attention_mask = torch.stack([b["attention_mask"] for b in batch])
    labels = torch.stack([b["labels"] for b in batch])
    return input_ids, attention_mask, labels

class BERTClassifier(nn.Module):
    def __init__(self, model_name: str, num_classes: int, dropout: float = 0.1):
        super().__init__()
        self.bert = BertModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes)
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        # some models may not have pooler_output; handle fallback
        pooled = getattr(outputs, "pooler_output", None)
        if pooled is None:
            # use first token [CLS] from last_hidden_state
            pooled = outputs.last_hidden_state[:, 0, :]
        return self.classifier(pooled)

# -------------------------
# Training / Evaluation helpers
# -------------------------
@torch.no_grad()
def eval_loader(model, loader, device):
    ys, ps = [], []
    model.eval()
    for input_ids, attention_mask, labels in loader:
        input_ids = input_ids.to(device); attention_mask = attention_mask.to(device)
        labels = labels.to(device)
        logits = model(input_ids, attention_mask)
        preds = torch.argmax(logits, dim=1)
        ys.extend(labels.cpu().tolist()); ps.extend(preds.cpu().tolist())
    y_true = np.array(ys, dtype=np.int64); y_pred = np.array(ps, dtype=np.int64)
    acc = float((y_true == y_pred).mean()) if len(y_true) > 0 else 0.0
    return acc, y_true, y_pred

def evaluate_loss_acc(model, loader, device, criterion):
    model.eval()
    total_loss = 0.0; total_n = 0; ys=[]; ps=[]
    with torch.no_grad():
        for input_ids, attention_mask, labels in loader:
            input_ids = input_ids.to(device); attention_mask = attention_mask.to(device)
            labels = labels.to(device)
            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)
            preds = torch.argmax(logits, dim=1)
            bs = labels.size(0)
            total_loss += loss.item() * bs; total_n += bs
            ys.extend(labels.cpu().tolist()); ps.extend(preds.cpu().tolist())
    acc = float((np.array(ys) == np.array(ps)).mean()) if total_n > 0 else 0.0
    return total_loss / max(total_n, 1), acc

def train_loop(model, train_loader, val_loader, device, cfg):
    epochs = int(cfg.get("epochs", 3))
    lr = float(cfg.get("lr", 2e-5))
    weight_decay = float(cfg.get("weight_decay", 0.0))
    patience = int(cfg.get("patience", 3))

    criterion = nn.CrossEntropyLoss()
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    total_steps = max(1, len(train_loader) * epochs)
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps)

    best_val_acc = -1.0
    best_state = None
    wait = 0

    history = {"epoch": [], "train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    for ep in range(1, epochs + 1):
        model.train()
        running_loss = 0.0; n = 0
        for input_ids, attention_mask, labels in train_loader:
            input_ids = input_ids.to(device); attention_mask = attention_mask.to(device); labels = labels.to(device)
            optimizer.zero_grad()
            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            running_loss += loss.item() * labels.size(0); n += labels.size(0)

        tr_loss, tr_acc = evaluate_loss_acc(model, train_loader, device, criterion)
        va_loss, va_acc = evaluate_loss_acc(model, val_loader, device, criterion)

        print(f"  Epoch {ep:02d}: tr_loss={tr_loss:.4f}, tr_acc={tr_acc:.4f}, va_loss={va_loss:.4f}, va_acc={va_acc:.4f}")

        history["epoch"].append(ep)
        history["train_loss"].append(tr_loss); history["val_loss"].append(va_loss)
        history["train_acc"].append(tr_acc); history["val_acc"].append(va_acc)

        if va_acc > best_val_acc:
            best_val_acc = va_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                print(f"  Early stopping at epoch {ep}")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    return best_val_acc, history

# -------------------------
# Main: CV / single split handling + outputs like p1_0_sample
# -------------------------
def main(config_path: str):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    paths = cfg.get("paths", {})
    model_conf = cfg.get("model", {})
    train_conf = cfg.get("train", {})
    report_conf = cfg.get("report", {})
    cv_conf = cfg.get("cv", {})

    data_dir = paths.get("data_dir", "./data/X_Y_please_set_output_dir")
    save_root = paths.get("save_dir", "./result/X_Y_please_set_output_dir")

    set_seed(int(train_conf.get("random_seed", 42)))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")

    tokenizer = BertTokenizer.from_pretrained(model_conf["model_name"])

    cv_enabled = bool(cv_conf.get("enabled", True))

    if cv_enabled:
        cv_root = resolve_cv_root(data_dir)
        folds = find_folds(cv_root)
        test_df = maybe_load_test(cv_root)
        has_test = test_df is not None
        print(f"[CV] root={cv_root}  folds={[f.name for f in folds]}  has_test={has_test}")

        fold_summaries = []

        for fi, fold_dir in enumerate(folds, start=1):
            print(f"\n===== FOLD {fi}/{len(folds)} : {fold_dir.name} =====")

            # load
            train_df, val_df = load_fold_splits(fold_dir)

            # label2id from train (string keys to match sample)
            labels = sorted(train_df["category"].astype(str).unique().tolist())
            label2id = {lab: i for i, lab in enumerate(labels)}
            id2label = {i: lab for lab, i in label2id.items()}
            num_classes = len(labels)

            # datasets & loaders
            train_ds = BERTDataset(train_df, tokenizer, label2id, max_length=int(model_conf.get("max_length", 256)))
            val_ds = BERTDataset(val_df, tokenizer, label2id, max_length=int(model_conf.get("max_length", 256)))
            batch_size = int(train_conf.get("batch_size", 16))
            train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_bert, num_workers=0)
            val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_bert, num_workers=0)

            # model
            model = BERTClassifier(model_conf["model_name"], num_classes=num_classes, dropout=float(model_conf.get("dropout", 0.1))).to(device)

            # cost start
            token = cost_start(model=model, phase="train", note=f"BERT CV {fold_dir.name}")

            # train
            best_val_acc, history = train_loop(model, train_loader, val_loader, device, train_conf)

            # cost end -> metrics
            fold_cost_metrics = cost_end(token)
            fold_cost_json = to_json_str(fold_cost_metrics)
            fold_cost_csv_header, fold_cost_csv_line = to_csv_str(fold_cost_metrics)

            # eval val
            val_acc, y_va, p_va = eval_loader(model, val_loader, device)
            print(f"[FOLD {fi}] val_acc={val_acc:.4f} (best_val={best_val_acc:.4f})")

            test_pack = None
            test_acc = None
            if has_test:
                test_ds = BERTDataset(test_df, tokenizer, label2id, max_length=int(model_conf.get("max_length", 256)))
                test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_bert, num_workers=0)
                test_acc, y_te, p_te = eval_loader(model, test_loader, device)
                test_pack = {"y_true": y_te, "y_pred": p_te, "id2label": id2label}
                print(f"[FOLD {fi}] test_acc={test_acc:.4f}")

            # save artifacts + reports
            rep_dir = (Path(save_root) / fold_dir.name / "reports")
            rep_dir.mkdir(parents=True, exist_ok=True)

            # create artifacts (label2id, ...). For BERT we don't build vocab; save label2id
            artifacts = {
                "label2id.json": label2id,
            }

            # save model state
            #model_dir = Path(save_root) / fold_dir.name
            #model_dir.mkdir(parents=True, exist_ok=True)
            model_dir = rep_dir
            torch.save(model.state_dict(), model_dir / "best_model.pt")

            # produce per-fold report files (per-class CSV, summary, confusion etc)
            #print_report_and_save("validation", y_va, p_va, id2label, rep_dir)
            #if has_test:
            #    print_report_and_save("test", y_te, p_te, id2label, rep_dir)

            # optionally save history and cost into reports
            #(rep_dir / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            #(rep_dir / "train_cost.json").write_text(json.dumps(fold_cost_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
            # also save training cost csv line/header
            #(rep_dir / "train_cost.csv").write_text(fold_cost_csv_header + "\n" + fold_cost_csv_line + "\n", encoding="utf-8")

            # promote artifacts (write as files)
            for name, obj in artifacts.items():
                p = model_dir / name
                if name.endswith(".json"):
                    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
                else:
                    # binary
                    p.write_bytes(obj if isinstance(obj, (bytes, bytearray)) else str(obj).encode("utf-8"))

            # use output helper to keep same shape as p1_0_sample
            output_cv_fold(
                fold_name=fold_dir.name,
                out_dir=rep_dir,
                val={"y_true": y_va, "y_pred": p_va, "id2label": id2label},
                test=test_pack,
                training_cost={
                    "json_str": fold_cost_json,
                    "csv_header": fold_cost_csv_header,
                    "csv_line": fold_cost_csv_line,
                },
                figures=True,
                config_content=cfg,
                history=history,
                model=model,
                model_extra={},
                model_info={"num_classes": num_classes, "model_name": model_conf["model_name"]},
                artifacts=artifacts,
            )

            fold_summaries.append({
                "fold": fold_dir.name,
                "val_acc": float(val_acc),
                "best_val": float(best_val_acc),
                "test_acc": (None if test_acc is None else float(test_acc))
            })

        # summary across folds
        output_cv_summary(out_dir=Path(save_root), fold_summaries=fold_summaries)
        print("\n===== CV Results =====")
        print(f"各Foldの精度: {[fs['val_acc'] for fs in fold_summaries]}")
        print(f"平均精度: {np.mean([fs['val_acc'] for fs in fold_summaries]):.4f} ± {np.std([fs['val_acc'] for fs in fold_summaries]):.4f}")

    else:
        # single split
        Path(save_root).mkdir(parents=True, exist_ok=True)
        train_df, val_df, test_df = load_single_splits(data_dir)
        labels = sorted(train_df["category"].astype(str).unique().tolist())
        label2id = {lab: i for i, lab in enumerate(labels)}
        id2label = {i: lab for lab, i in label2id.items()}
        num_classes = len(labels)

        # datasets
        batch_size = int(train_conf.get("batch_size", 16))
        train_ds = BERTDataset(train_df, tokenizer, label2id, max_length=int(model_conf.get("max_length", 256)))
        val_ds = BERTDataset(val_df, tokenizer, label2id, max_length=int(model_conf.get("max_length", 256)))
        test_ds = BERTDataset(test_df, tokenizer, label2id, max_length=int(model_conf.get("max_length", 256)))
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_bert, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_bert, num_workers=0)
        test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_bert, num_workers=0)

        model = BERTClassifier(model_conf["model_name"], num_classes=num_classes, dropout=float(model_conf.get("dropout", 0.1))).to(device)

        token = cost_start(model=model, phase="train", note="BERT single-split")
        best_val_acc, history = train_loop(model, train_loader, val_loader, device, train_conf)
        train_cost_metrics = cost_end(token)
        train_cost_json = to_json_str(train_cost_metrics)
        train_cost_csv_header, train_cost_csv_line = to_csv_str(train_cost_metrics)

        tr_acc, y_tr, p_tr = eval_loader(model, train_loader, device)
        va_acc, y_va, p_va = eval_loader(model, val_loader, device)
        te_acc, y_te, p_te = eval_loader(model, test_loader, device)
        id2label = {i: lab for lab, i in label2id.items()}

        # save model
        save_dir = Path(save_root)
        save_dir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), save_dir / "best_model.pt")

        rep_dir = save_dir / "reports"
        rep_dir.mkdir(parents=True, exist_ok=True)

        # artifacts
        artifacts = {
            "label2id.json": label2id,
        }
        for name, obj in artifacts.items():
            p = rep_dir / name
            p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

        # save reports
        #print_report_and_save("train", y_tr, p_tr, id2label, rep_dir)
        #print_report_and_save("validation", y_va, p_va, id2label, rep_dir)
        #print_report_and_save("test", y_te, p_te, id2label, rep_dir)

        #(rep_dir / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        #(rep_dir / "train_cost.json").write_text(json.dumps(train_cost_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        #(rep_dir / "train_cost.csv").write_text(train_cost_csv_header + "\n" + train_cost_csv_line + "\n", encoding="utf-8")

        output_single_run(
            out_dir=rep_dir,
            splits={
                "train": {"y_true": y_tr, "y_pred": p_tr, "id2label": id2label},
                "val": {"y_true": y_va, "y_pred": p_va, "id2label": id2label},
                "test": {"y_true": y_te, "y_pred": p_te, "id2label": id2label},
            },
            training_cost={
                "json_str": train_cost_json,
                "csv_header": train_cost_csv_header,
                "csv_line": train_cost_csv_line,
            },
            figures=True,
            config_content=cfg,
            history=history,
            model=model,
            model_extra={},
            model_info={"num_classes": num_classes, "model_name": model_conf["model_name"]},
            artifacts=artifacts,
        )

        print(f"✅ 学習完了（val acc = {va_acc:.4f}）")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="./configs/bert_finetune.json")
    args = ap.parse_args()
    main(args.config)
