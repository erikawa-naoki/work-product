# tools/ldcc_to_parquet.py
import os, glob, argparse, random
from pathlib import Path
import pandas as pd

def read_ldcc(ldcc_dir: str):
    rows = []
    cats = sorted([d for d in os.listdir(ldcc_dir) if (Path(ldcc_dir)/d).is_dir()])
    if not cats:
        raise FileNotFoundError(f"No category folders under: {ldcc_dir}")
    for cat in cats:
        for fp in glob.glob(str(Path(ldcc_dir)/cat/"*.txt")):
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()
            # 1行目=URL, 2行目=日時, 3行目=空行, 4行目以降が本文
            body = "\n".join(lines[3:]) if len(lines) >= 4 else "\n".join(lines)
            rows.append({"content": body, "category": cat})
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No .txt files found. Check LDCC path.")
    return df

def split_save(df: pd.DataFrame, out_dir: str, seed=42, ratios=(0.8, 0.1, 0.1)):
    assert abs(sum(ratios) - 1.0) < 1e-8, "ratios must sum to 1.0"
    random.seed(seed)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    n = len(df)
    n_tr = int(n * ratios[0])
    n_va = int(n * ratios[1])
    train = df.iloc[:n_tr]
    val   = df.iloc[n_tr:n_tr+n_va]
    test  = df.iloc[n_tr+n_va:]
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    train.to_parquet(out/"train.parquet", index=False)
    val.to_parquet(out/"val.parquet", index=False)
    test.to_parquet(out/"test.parquet", index=False)
    print(f"[OK] saved to {out.resolve()}")
    print(f"  train={len(train)}  val={len(val)}  test={len(test)}")

def main():
    ap = argparse.ArgumentParser(description="Convert Livedoor (LDCC) to parquet train/val/test")
    ap.add_argument("--src", required=True, help="Path to ldcc-20140209 dir")
    ap.add_argument("--out", default="src/data/1_0_no_cv_preprocessed", help="Output dir for parquet")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ratios", type=float, nargs=3, default=(0.8, 0.1, 0.1),
                    help="Split ratios: train val test (sum=1.0)")
    args = ap.parse_args()

    df = read_ldcc(args.src)
    df["content"] = df["content"].astype(str)
    df["category"] = df["category"].astype(str)
    split_save(df, args.out, seed=args.seed, ratios=tuple(args.ratios))

if __name__ == "__main__":
    main()
