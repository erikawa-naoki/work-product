"""
p2_3_transformer_train.py
- TransformerEncoder を用いたテキスト分類モデルの学習
- p1_0_sample_train.py をベースに作成
- 設定ファイルに基づき、単一分割 or 交差検証モードで動作
- 入力:
    - config.json: 学習パラメータ、モデルパラメータ、データパスなどを定義
- 出力:
    - 学習済みモデル (model.pt)
    - 評価レポート (metrics.csv, metrics.json)
    - 混同行列 (confusion_matrix.png)
    - 学習曲線 (learning_curve.png)
    - 語彙ファイル (vocab.json)
    - ラベル対応 (label2id.json)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

# ---- コスト計測 ----
from src.p4_0_compute_cost import (
    cost_start, cost_end, to_json_str, to_csv_str,
    infer_cost_start, infer_cost_end
)

# ---- 統一出力 ----
from src.p4_0_output_train_result import (
    output_single_run, output_cv_fold, output_cv_summary
)


# ========= util =========
def set_seed(seed: int):
    """乱数シードを固定する"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def read_parquet_texts(path: Path) -> List[str]:
    """Parquetファイルからテキストリストを読み込む"""
    df = pd.read_parquet(path, columns=["content"])
    return [("" if pd.isna(x) else str(x)) for x in df["content"].tolist()]

def read_parquet_labels(path: Path) -> List[str]:
    """Parquetファイルからラベルリストを読み込む"""
    df = pd.read_parquet(path, columns=["category"])
    return df["category"].tolist()


# ========= dataset =========
class TextDataset(Dataset):
    def __init__(self, texts: List[str], labels: Optional[List[int]] = None):
        self.texts = texts
        self.labels = labels

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, i: int) -> Dict[str, Any]:
        item = {"text": self.texts[i]}
        if self.labels is not None:
            item["label"] = self.labels[i]
        return item


# ========= model =========
class PositionalEncoding(nn.Module):
    """位置エンコーディング"""
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor, shape [seq_len, batch_size, embedding_dim]
        """
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)

class TransformerClassifier(nn.Module):
    """Transformer Encoderを用いた分類モデル"""
    def __init__(self, vocab_size: int, embed_dim: int, nhead: int, dim_feedforward: int,
                 num_layers: int, num_classes: int, dropout: float = 0.5):
        super().__init__()
        self.embed_dim = embed_dim
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.pos_encoder = PositionalEncoding(embed_dim, dropout)
        encoder_layers = nn.TransformerEncoderLayer(embed_dim, nhead, dim_feedforward, dropout, batch_first=False)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        self.classifier = nn.Linear(embed_dim, num_classes)

        self.init_weights()

    def init_weights(self) -> None:
        initrange = 0.1
        self.embedding.weight.data.uniform_(-initrange, initrange)
        self.classifier.bias.data.zero_()
        self.classifier.weight.data.uniform_(-initrange, initrange)

    def forward(self, src: torch.Tensor, src_key_padding_mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            src: (seq_len, batch_size)
            src_key_padding_mask: (batch_size, seq_len)
        """
        src = self.embedding(src) * math.sqrt(self.embed_dim)
        src = self.pos_encoder(src)
        output = self.transformer_encoder(src, src_key_padding_mask=src_key_padding_mask)
        # 平均プーリング
        output = output.permute(1, 0, 2) # (batch, seq, dim)
        pooled_output = output.mean(dim=1)
        return self.classifier(pooled_output)


# ========= trainer =========
def build_vocab(texts: List[str], min_freq: int) -> Dict[str, int]:
    """語彙を構築する"""
    counter = Counter(tok for text in texts for tok in text.split())
    vocab = {
        "<pad>": 0,
        "<unk>": 1,
    }
    for word, freq in counter.items():
        if freq >= min_freq:
            vocab[word] = len(vocab)
    return vocab

def create_collate_fn(vocab: Dict[str, int]):
    """DataLoader用のcollate_fnを作成する"""
    def collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        texts = [item["text"] for item in batch]
        
        # テキストをIDに変換
        sequences = [
            torch.tensor([vocab.get(tok, vocab["<unk>"]) for tok in text.split()])
            for text in texts
        ]
        
        # パディング
        padded_sequences = pad_sequence(sequences, batch_first=False, padding_value=vocab["<pad>"])
        
        # パディングマスクの作成 (batch_size, seq_len)
        # padの部分がTrueになるようにする
        padding_mask = (padded_sequences == vocab["<pad>"]).transpose(0, 1)

        collated = {"texts": padded_sequences, "padding_mask": padding_mask}

        if "label" in batch[0]:
            labels = torch.tensor([item["label"] for item in batch])
            collated["labels"] = labels
        
        return collated
    return collate_fn

def train_loop(
    model: nn.Module,
    data_loader: DataLoader,
    loss_fn: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
) -> Tuple[float, float]:
    """1エポックの学習"""
    model.train()
    total_loss = 0.0
    all_preds, all_labels = [], []

    for batch in tqdm(data_loader, desc="Training"):
        texts = batch["texts"].to(device)
        padding_mask = batch["padding_mask"].to(device)
        labels = batch["labels"].to(device)

        optimizer.zero_grad()
        outputs = model(texts, padding_mask)
        loss = loss_fn(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        all_preds.extend(outputs.argmax(1).cpu().tolist())
        all_labels.extend(labels.cpu().tolist())

    avg_loss = total_loss / len(data_loader)
    accuracy = accuracy_score(all_labels, all_preds)
    return avg_loss, accuracy


@torch.inference_mode()
def eval_loop(
    model: nn.Module,
    data_loader: DataLoader,
    loss_fn: nn.Module,
    device: torch.device,
) -> Tuple[float, float, List[int], List[int]]:
    """評価"""
    model.eval()
    total_loss = 0.0
    all_preds, all_labels = [], []

    for batch in tqdm(data_loader, desc="Evaluating"):
        texts = batch["texts"].to(device)
        padding_mask = batch["padding_mask"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(texts, padding_mask)
        loss = loss_fn(outputs, labels)

        total_loss += loss.item()
        all_preds.extend(outputs.argmax(1).cpu().tolist())
        all_labels.extend(labels.cpu().tolist())

    avg_loss = total_loss / len(data_loader)
    accuracy = accuracy_score(all_labels, all_preds)
    return avg_loss, accuracy, all_preds, all_labels


def run_fold(
    cfg: Dict[str, Any],
    save_dir: Path,
    train_texts: List[str],
    train_labels: List[str],
    val_texts: List[str],
    val_labels: List[str],
    test_texts: List[str],
    test_labels: List[str],
    device: torch.device,
    fold_name: Optional[str] = None,
) -> Dict[str, Any]:
    """1フォールドの学習・評価を実行"""
    save_dir.mkdir(exist_ok=True, parents=True)
    
    # ラベルをIDに変換
    label_names = sorted(list(set(train_labels)))
    label2id = {name: i for i, name in enumerate(label_names)}
    id2label = {i: name for i, name in enumerate(label_names)}
    train_labels_id = [label2id[l] for l in train_labels]
    val_labels_id = [label2id[l] for l in val_labels]
    test_labels_id = [label2id[l] for l in test_labels]

    # 語彙の構築
    vocab = build_vocab(train_texts, cfg["min_freq"])
    
    # データセットとデータローダー
    collate_fn = create_collate_fn(vocab)
    train_ds = TextDataset(train_texts, train_labels_id)
    val_ds = TextDataset(val_texts, val_labels_id)
    test_ds = TextDataset(test_texts, test_labels_id)
    train_dl = DataLoader(train_ds, batch_size=cfg["batch_size"], shuffle=True, collate_fn=collate_fn)
    val_dl = DataLoader(val_ds, batch_size=cfg["batch_size"], shuffle=False, collate_fn=collate_fn)
    test_dl = DataLoader(test_ds, batch_size=cfg["batch_size"], shuffle=False, collate_fn=collate_fn)

    # モデル、損失関数、オプティマイザ
    model = TransformerClassifier(
        vocab_size=len(vocab),
        embed_dim=cfg["embed_dim"],
        nhead=cfg["nhead"],
        dim_feedforward=cfg["dim_feedforward"],
        num_layers=cfg["num_layers"],
        num_classes=len(label_names),
        dropout=cfg["dropout"],
    ).to(device)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=cfg["lr"])

    # 学習ループ
    best_val_acc = -1.0
    best_epoch = -1
    history = { "epoch": [], "train_loss": [], "train_acc": [], "val_loss": [], "val_acc": [] }
    
    time_hist = cost_start(model=model, phase="train", note=f"Transformer {fold_name or 'single'}")

    for epoch in range(cfg["epochs"]):
        print(f"Epoch {epoch+1}/{cfg['epochs']}")
        train_loss, train_acc = train_loop(model, train_dl, loss_fn, optimizer, device)
        val_loss, val_acc, _, _ = eval_loop(model, val_dl, loss_fn, device)
        
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
        print(f"Val   Loss: {val_loss:.4f}, Val   Acc: {val_acc:.4f}")

        history["epoch"].append(epoch + 1)
        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            torch.save(model.state_dict(), save_dir / "model.pt")
            print(f"Best model saved at epoch {epoch+1}")

        if cfg["early_stopping_patience"] > 0 and epoch - best_epoch >= cfg["early_stopping_patience"]:
            print("Early stopping.")
            break
    
    cost_metrics = cost_end(time_hist)

    # テスト
    best_model = TransformerClassifier(
        vocab_size=len(vocab),
        embed_dim=cfg["embed_dim"],
        nhead=cfg["nhead"],
        dim_feedforward=cfg["dim_feedforward"],
        num_layers=cfg["num_layers"],
        num_classes=len(label_names),
    ).to(device)
    best_model.load_state_dict(torch.load(save_dir / "model.pt"))
    
    # 評価: train, val, test
    _, _, train_preds, train_labels_raw = eval_loop(best_model, train_dl, loss_fn, device)
    _, val_acc, val_preds, val_labels_raw = eval_loop(best_model, val_dl, loss_fn, device)
    test_loss, test_acc, test_preds, test_labels_raw = eval_loop(best_model, test_dl, loss_fn, device)

    print(f"Val Accuracy: {val_acc:.4f}")
    print(f"Test Accuracy: {test_acc:.4f}")

    # 評価指標（test用）
    test_metrics = {
        "accuracy": accuracy_score(test_labels_raw, test_preds),
        "precision_macro": precision_score(test_labels_raw, test_preds, average="macro", zero_division=0),
        "recall_macro": recall_score(test_labels_raw, test_preds, average="macro", zero_division=0),
        "f1_macro": f1_score(test_labels_raw, test_preds, average="macro", zero_division=0),
        "precision_weighted": precision_score(test_labels_raw, test_preds, average="weighted", zero_division=0),
        "recall_weighted": recall_score(test_labels_raw, test_preds, average="weighted", zero_division=0),
        "f1_weighted": f1_score(test_labels_raw, test_preds, average="weighted", zero_division=0),
    }
    
    # コスト計測結果を文字列化
    cost_json_str = to_json_str(cost_metrics)
    cost_csv_header, cost_csv_line = to_csv_str(cost_metrics)
    
    # 中間生成物
    artifacts = {
        "vocab.json": vocab,
        "label2id.json": label2id,
    }
    
    # CVモードか単一分割モードかで出力を分ける
    if fold_name:
        # CVモード: output_cv_fold を使用
        output_cv_fold(
            fold_name=fold_name,
            out_dir=save_dir,
            val={
                "y_true": np.array(val_labels_raw),
                "y_pred": np.array(val_preds),
                "id2label": id2label,
            },
            test={
                "y_true": np.array(test_labels_raw),
                "y_pred": np.array(test_preds),
                "id2label": id2label,
            },
            training_cost={
                "json_str": cost_json_str,
                "csv_header": cost_csv_header,
                "csv_line": cost_csv_line,
            },
            figures=True,
            config_content=cfg,
            history=history,
            model=best_model,
            model_extra={},
            model_info={"vocab_size": len(vocab), "embed_dim": cfg["embed_dim"]},
            artifacts=artifacts,
        )
    else:
        # 単一分割モード: output_single_run を使用
        output_single_run(
            out_dir=save_dir,
            splits={
                "train": {
                    "y_true": np.array(train_labels_raw),
                    "y_pred": np.array(train_preds),
                    "id2label": id2label,
                },
                "val": {
                    "y_true": np.array(val_labels_raw),
                    "y_pred": np.array(val_preds),
                    "id2label": id2label,
                },
                "test": {
                    "y_true": np.array(test_labels_raw),
                    "y_pred": np.array(test_preds),
                    "id2label": id2label,
                },
            },
            training_cost={
                "json_str": cost_json_str,
                "csv_header": cost_csv_header,
                "csv_line": cost_csv_line,
            },
            figures=True,
            config_content=cfg,
            history=history,
            model=best_model,
            model_extra={},
            model_info={"vocab_size": len(vocab), "embed_dim": cfg["embed_dim"]},
            artifacts=artifacts,
        )
    
    return {
        "val_acc": val_acc,
        "test_acc": test_acc,
        "best_val": best_val_acc,
        **test_metrics
    }


# ========= main =========
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, required=True, help="設定ファイルへのパス")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    set_seed(cfg["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    base_dir = Path(cfg["data_dir"])
    save_base_dir = Path(cfg["save_dir"])

    # cv_k* ディレクトリの自動検出
    cv_dirs = sorted([p for p in base_dir.iterdir() if p.is_dir() and re.match(r"cv_k\d+", p.name)])
    if cv_dirs:
        # cv_k* ディレクトリが見つかった場合、最初のものを使用
        base_dir = cv_dirs[0]
        print(f"Using CV directory: {base_dir.name}")

    # CVモードか単一分割モードか判定
    fold_dirs = sorted([p for p in base_dir.iterdir() if p.is_dir() and re.match(r"fold_\d+", p.name)])

    if fold_dirs:
        # CVモード
        print("Running in Cross-Validation mode.")
        fold_summaries = []
        
        # 共通testセットの確認（cv_k*直下）
        common_test_path = base_dir / "test.parquet"
        has_common_test = common_test_path.exists()
        
        if has_common_test:
            common_test_texts = read_parquet_texts(common_test_path)
            common_test_labels = read_parquet_labels(common_test_path)
            print(f"Using common test set: {common_test_path}")
        
        for fold_dir in fold_dirs:
            fold_name = fold_dir.name
            print(f"\n=== {fold_name} ===")
            save_dir = save_base_dir / fold_name / "reports"
            
            train_texts = read_parquet_texts(fold_dir / "train.parquet")
            train_labels = read_parquet_labels(fold_dir / "train.parquet")
            val_texts = read_parquet_texts(fold_dir / "val.parquet")
            val_labels = read_parquet_labels(fold_dir / "val.parquet")
            
            # fold内のtestがあればそれを使用、なければ共通test、それもなければvalを使用
            fold_test_path = fold_dir / "test.parquet"
            if fold_test_path.exists():
                test_texts = read_parquet_texts(fold_test_path)
                test_labels = read_parquet_labels(fold_test_path)
            elif has_common_test:
                test_texts = common_test_texts
                test_labels = common_test_labels
            else:
                test_texts = val_texts
                test_labels = val_labels

            metrics = run_fold(
                cfg, save_dir, 
                train_texts, train_labels, 
                val_texts, val_labels, 
                test_texts, test_labels, 
                device,
                fold_name=fold_name
            )
            
            fold_summaries.append({
                "fold": fold_name,
                "val_acc": float(metrics["val_acc"]),
                "best_val": float(metrics["best_val"]),
                "test_acc": float(metrics["test_acc"]),
            })
            
            print(f"[{fold_name}] Val Acc: {metrics['val_acc']:.4f}, Test Acc: {metrics['test_acc']:.4f}")
        
        # CV全体の集計
        output_cv_summary(out_dir=save_base_dir, fold_summaries=fold_summaries)
        
        # 平均スコアを表示
        avg_val_acc = np.mean([m["val_acc"] for m in fold_summaries])
        avg_test_acc = np.mean([m["test_acc"] for m in fold_summaries])
        print("\n=== CV Summary ===")
        print(f"Average Val Acc:  {avg_val_acc:.4f}")
        print(f"Average Test Acc: {avg_test_acc:.4f}")

    else:
        # 単一分割モード
        print("Running in Single-Split mode.")
        save_dir = save_base_dir
        
        train_texts = read_parquet_texts(base_dir / "train.parquet")
        train_labels = read_parquet_labels(base_dir / "train.parquet")
        val_texts = read_parquet_texts(base_dir / "val.parquet")
        val_labels = read_parquet_labels(base_dir / "val.parquet")
        test_texts = read_parquet_texts(base_dir / "test.parquet")
        test_labels = read_parquet_labels(base_dir / "test.parquet")

        metrics = run_fold(
            cfg, save_dir, 
            train_texts, train_labels, 
            val_texts, val_labels, 
            test_texts, test_labels, 
            device,
            fold_name=None
        )
        
        print(f"\nFinal Results:")
        print(f"Val Acc:  {metrics['val_acc']:.4f}")
        print(f"Test Acc: {metrics['test_acc']:.4f}")


if __name__ == "__main__":
    main()
