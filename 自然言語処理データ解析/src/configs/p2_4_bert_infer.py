import argparse, torch, pandas as pd, json, csv, io
from transformers import BertTokenizer
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import datetime
import time

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

from src.p4_0_output_train_result import (
    _compute_confusion,
    _metrics_from_confusion,
    _annotate_matrix,
    _normalize_confusion
)
from src.p2_4_bert_train import BERTClassifier, BERTDataset, collate_bert, eval_loader, metrics_from_confusion, compute_confusion_matrix
from src.p4_0_compute_cost import infer_cost_start, infer_cost_end, to_json_str, to_csv_str, to_torch_timeseries_csv_total

def print_report_and_save(split_name, y_true, y_pred, id2label, save_path: Path, normalize_mode="true"):
    """
    強化版の精度レポート生成
    - per-class CSV
    - summary JSON
    - 混同行列 npy
    - 混同行列 PNG（件数＋割合表示）
    """
    save_path.mkdir(parents=True, exist_ok=True)

    num_classes = len(id2label)
    # 混同行列（件数）
    cm_counts = _compute_confusion(y_true, y_pred, num_classes=num_classes)
    # 正規化混同行列
    cm_ratios = _normalize_confusion(cm_counts, mode=normalize_mode)
    # metrics 計算
    per_class, macro, micro, weighted, accuracy = _metrics_from_confusion(cm_counts)

    # per-class CSV
    with open(save_path / f"{split_name}_per_class.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "precision", "recall", "f1", "support"])
        for i, pc in enumerate(per_class):
            writer.writerow([id2label.get(i, str(i)), pc["precision"], pc["recall"], pc["f1"], pc["support"]])

    # summary JSON
    summary = dict(accuracy=accuracy, micro=micro, macro=macro, weighted=weighted)
    (save_path / f"{split_name}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 混同行列を npy 形式で保存
    np.save(save_path / f"{split_name}_confusion.npy", cm_counts)

    # 混同行列 PNG（件数 / 割合）
    fig, ax = plt.subplots(figsize=(max(6, num_classes*0.5), max(6, num_classes*0.5)))
    im = ax.imshow(cm_ratios, interpolation="nearest", cmap="Blues")
    _annotate_matrix(ax, cm_counts, cm_ratios)
    ax.set_title(f"Confusion Matrix ({split_name})")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_xticks(range(num_classes))
    ax.set_yticks(range(num_classes))
    ax.set_xticklabels([id2label[i] for i in range(num_classes)], rotation=45, ha="right")
    ax.set_yticklabels([id2label[i] for i in range(num_classes)])
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(save_path / f"{split_name}_confusion.png", dpi=150)
    plt.close()

def save_inference_cost_summary(token, save_path: Path):
    """
    cost_start() が返した token を使って、推論区間の簡易サマリ JSON を出力
    例:
    {
      "phase": "inference",
      "started_at": "...",
      "ended_at": "...",
      "duration_sec": ...,
      "cuda_available": true,
      "gpu_name": "...",
      "gpu_mem_peak_mib": ...,
      "pid": 12345
    }
    """
    save_path.mkdir(parents=True, exist_ok=True)

    end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    duration_sec = round(time.perf_counter() - token.start_perf, 4)

    gpu_name = None
    gpu_mem_peak = None
    if token.torch_cuda_available and token.torch_device_names:
        gpu_name = token.torch_device_names[0]  # 最初のGPU名
        # PyTorchのピーク割当メモリを取得
        try:
            if _HAS_TORCH and torch.cuda.is_available():
                gpu_mem_peak = round(torch.cuda.max_memory_allocated(0) / (1024*1024), 2)
        except Exception:
            pass

    summary = {
        "phase": token.phase,
        "started_at": token.start_iso,
        "ended_at": end_time,
        "duration_sec": duration_sec,
        "cuda_available": token.torch_cuda_available,
        "gpu_name": gpu_name,
        "gpu_mem_peak_mib": gpu_mem_peak,
        "pid": token.pid
    }

    file_path = save_path / f"{token.phase}_cost_summary.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts-dir", type=str, required=True, help="学習済みモデルや関連ファイルのディレクトリ")
    ap.add_argument("--data", type=str, required=True, help="推論対象の Parquet ファイル")
    ap.add_argument("--output", type=str, default=None, help="推論結果の出力ファイル（CSV/Parquet）")
    ap.add_argument("--device", type=str, default="cuda", help="cuda または cpu")
    args = ap.parse_args()

    ts_dir = Path(args.ts_dir)
    model_path = list((ts_dir / "models").glob("*.pt"))[0]

    # label2id 読み込み
    label2id_path = ts_dir / "models" / "label2id.json"
    label2id = json.loads(label2id_path.read_text(encoding="utf-8"))
    id2label = {v: k for k, v in label2id.items()}
    num_classes = len(label2id)

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    tokenizer = BertTokenizer.from_pretrained("cl-tohoku/bert-base-japanese")

    # モデルロード
    model_name = "cl-tohoku/bert-base-japanese"
    model = BERTClassifier(model_name=model_name, num_classes=num_classes)
    state = torch.load(model_path, map_location=device)
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    # データ読み込み
    df = pd.read_parquet(args.data)
    ds = BERTDataset(df, tokenizer=tokenizer, label2id=label2id)
    loader = torch.utils.data.DataLoader(ds, batch_size=16, shuffle=False, collate_fn=collate_bert)

    # =============================
    # 推論コスト計測開始
    # =============================
    token = infer_cost_start(model=model, note=f"推論 {args.data}")
    
    # 推論
    _, y_true, y_pred = eval_loader(model, loader, device)
    
    # 推論コスト計測終了
    metrics = infer_cost_end(token)
    
    out_path = Path(args.ts_dir)
    report_dir = out_path / "inference"
    # =============================
    # 推論結果保存
    # =============================
    df["pred_category"] = [id2label[i] for i in y_pred]
    out_path = Path(args.ts_dir).with_name("pred_test_parquet")
    df.to_parquet(out_path, index=False)
    print(f"✅ 推論結果を保存しました: {out_path}")

    # =============================
    # 精度評価と混同行列
    # =============================
    print_report_and_save("prediction", y_true, y_pred, id2label, report_dir)
    print(f"✅ 精度評価と混同行列を保存しました: {report_dir}")

    # =============================
    # 推論コスト JSON / CSV
    # =============================
    cost_json_path = report_dir / "inference_cost.json"
    cost_csv_path  = report_dir / "inference_cost.csv"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    cost_json_path.write_text(to_json_str(metrics), encoding="utf-8")
    hdr, row = to_csv_str(metrics)
    cost_csv_path.write_text(hdr + "\n" + row + "\n", encoding="utf-8")
    print(f"✅ 推論コストを保存しました: {cost_json_path}, {cost_csv_path}")
    save_inference_cost_summary(token, report_dir)

    # =============================
    # torch メモリ時系列 CSV / PNG
    # =============================
    gpu_dir = report_dir / "gpu"
    gpu_dir.mkdir(exist_ok=True, parents=True)
    ts_csv_path = gpu_dir / "torch_mem_timeseries_total.csv"
    hdr_ts, rows_ts = to_torch_timeseries_csv_total(metrics)
    ts_csv_path.write_text(hdr_ts + "\n" + rows_ts + "\n", encoding="utf-8")
    print(f"✅ Torch GPUメモリ時系列 CSV を保存しました: {ts_csv_path}")

    # PNG 可視化
    if rows_ts.strip():
        times, allocs, resvs = [], [], []
        for line in rows_ts.split("\n"):
            _, _, t, alloc, resv = line.split(",")
            times.append(t)
            allocs.append(float(alloc))
            resvs.append(float(resv))
        plt.figure(figsize=(10,4))
        plt.plot(times, allocs, label="allocated_mb")
        plt.plot(times, resvs, label="reserved_mb")
        plt.xticks(rotation=45)
        plt.ylabel("MB")
        plt.xlabel("time")
        plt.title("Torch GPU Memory Timeseries (total)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(gpu_dir / "torch_mem_timeseries_total.png", dpi=150)
        plt.close()
        print(f"✅ Torch GPUメモリ時系列 PNG を保存しました: {gpu_dir / 'torch_mem_timeseries_total.png'}")

if __name__ == "__main__":
    main()
