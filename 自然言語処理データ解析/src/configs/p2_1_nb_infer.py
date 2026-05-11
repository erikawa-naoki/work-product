#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
p2_1_nb_infer.py
Naive Bayes 版推論スクリプト
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime

import pandas as pd
import joblib
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# 共通のコスト計測/出力
from src.p4_0_compute_cost import cost_start, cost_end
from src.p4_0_output_train_result import output_single_run

# ================================================================
# 推論本体
# ================================================================
def run_infer(config_path: Path, model_path: Path, input_path: Path):

    # ------------------------
    # 設定ファイル読み込み
    # ------------------------
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = Path(config["paths"]["save_dir"]) / f"infer_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------
    # データ読み込み
    # ------------------------
    df = pd.read_parquet(input_path)
    X = df["content"].tolist()
    y_true = df["category"].tolist() if "category" in df.columns else None

    # ------------------------
    # モデル & TF-IDF 読み込み
    # ------------------------
    model_dir = Path(model_path)
    model = joblib.load(model_dir / "nb_model.pkl")
    vectorizer = joblib.load(model_dir / "tfidf.pkl")

    # ------------------------
    # TF-IDF変換
    # ------------------------
    X_vec = vectorizer.transform(X)

    # ------------------------
    # 推論コスト計測開始
    # ------------------------
    cost_token = cost_start(model=model, note="naive_bayes_inference")

    # ------------------------
    # 推論
    # ------------------------
    y_pred = model.predict(X_vec)

    # ------------------------
    # 推論コスト計測終了
    # ------------------------
    infer_cost = cost_end(cost_token)

    # ------------------------
    # 評価（もしラベルがある場合）
    # ------------------------
    metrics = {}
    if y_true is not None:
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "report": classification_report(y_true, y_pred, output_dict=True),
            "confusion": confusion_matrix(y_true, y_pred).tolist()
        }

    # ------------------------
    # 出力用辞書まとめ
    # ------------------------
    splits = {
        "infer": {"y_true": y_true, "y_pred": y_pred, "id2label": {lab: lab for lab in set(y_true) if y_true is not None}}
    }

    output_single_run(
        out_dir=out_dir,
        splits=splits,
        training_cost=False,  # 推論コストも記録
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
    print("  Naive Bayes 推論完了")
    if y_true is not None:
        print(f"accuracy = {metrics['accuracy']:.4f}")
    print(f"Saved to {out_dir}")

# ================================================================
# エントリーポイント
# ================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="JSON config path")
    parser.add_argument("--model_dir", required=True, help="学習済みモデルディレクトリ")
    parser.add_argument("--input", required=True, help="推論データ parquet path")
    args = parser.parse_args()

    run_infer(
        config_path=Path(args.config),
        model_path=Path(args.model_dir),
        input_path=Path(args.input)
    )
