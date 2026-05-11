#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
p2_1_nb_train.py
Naive Bayes 版学習スクリプト（学習コスト取得版）
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# 共通のコスト計測/出力
from src.p4_0_compute_cost import cost_start, cost_end
from src.p4_0_output_train_result import output_single_run

# ================================================================
# TF-IDF構築
# ================================================================
def build_tfidf_vectorizer(config: dict):
    return TfidfVectorizer(
        max_features=config["vectorizer"]["max_features"],
        ngram_range=tuple(config["vectorizer"]["ngram_range"]),
        min_df=config["vectorizer"]["min_df"]
    )

# ================================================================
# Naive Bayesモデル構築
# ================================================================
def build_nb_model(config: dict):
    return MultinomialNB(alpha=config["model"]["alpha"])

# ================================================================
# 学習本体
# ================================================================
def run_training(config_path: Path):

    # ------------------------
    # 設定ファイル読み込み
    # ------------------------
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = Path(config["paths"]["save_dir"]) / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    data_dir = Path(config["paths"]["data_dir"])
    train_df = pd.read_parquet(data_dir / "train.parquet")
    val_df   = pd.read_parquet(data_dir / "val.parquet")

    X_train, y_train = train_df["content"].tolist(), train_df["category"].tolist()
    X_val,   y_val   = val_df["content"].tolist(),   val_df["category"].tolist()

    # ------------------------
    # TF-IDF構築
    # ------------------------
    vectorizer = build_tfidf_vectorizer(config)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec   = vectorizer.transform(X_val)

    # ------------------------
    # モデル構築（NB）
    # ------------------------
    model = build_nb_model(config)

    # ------------------------
    # 学習コスト計測開始
    # ------------------------
    cost_token = cost_start(model=model, note="naive_bayes_training")

    # ------------------------
    # 学習
    # ------------------------
    model.fit(X_train_vec, y_train)

    # ------------------------
    # 学習コスト計測終了
    # ------------------------
    train_cost = cost_end(cost_token)  # ← ここに計測結果が入る

    # ------------------------
    # 評価
    # ------------------------
    y_pred_train = model.predict(X_train_vec)
    y_pred_val   = model.predict(X_val_vec)

    metrics = {
        "train_acc": accuracy_score(y_train, y_pred_train),
        "val_acc":   accuracy_score(y_val,   y_pred_val),
        "train_report": classification_report(y_train, y_pred_train, output_dict=True),
        "val_report":   classification_report(y_val,   y_pred_val,   output_dict=True),
        "train_confusion": confusion_matrix(y_train, y_pred_train).tolist(),
        "val_confusion":   confusion_matrix(y_val,   y_pred_val).tolist()
    }

    # ------------------------
    # モデル保存
    # ------------------------
    model_dir = out_dir / "model"
    model_dir.mkdir(exist_ok=True)
    import joblib
    joblib.dump(model, model_dir / "nb_model.pkl")
    joblib.dump(vectorizer, model_dir / "tfidf.pkl")

    # ------------------------
    # 出力用辞書まとめ
    # ------------------------
    splits = {
        "train": {"y_true": y_train, "y_pred": y_pred_train, "id2label": {lab: lab for lab in set(y_train)}},
        "val":   {"y_true": y_val,   "y_pred": y_pred_val,   "id2label": {lab: lab for lab in set(y_val)}}
    }

    output_single_run(
        out_dir=out_dir,
        splits=splits,
        training_cost=False,      # ← None ではなくここに渡す
        figures=False,
        config_content=config,
        history=None,
        model=model,
        model_extra={},
        model_info={"model_type": "MultinomialNB"},
        artifacts={
            "nb_model.pkl": str(model_dir / "nb_model.pkl"),
            "tfidf.pkl": str(model_dir / "tfidf.pkl")
        }
    )

    print("===========================================")
    print("  Naive Bayes トレーニング完了")
    print("===========================================")
    print(f"train acc = {metrics['train_acc']:.4f}")
    print(f"val   acc = {metrics['val_acc']:.4f}")
    print(f"Saved to {out_dir}")

# ================================================================
# エントリーポイント
# ================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="JSON config path")
    args = parser.parse_args()

    run_training(Path(args.config))
