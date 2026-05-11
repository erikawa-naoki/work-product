# 1_0_1_preprocess.py
# datasetsは3.6.0推奨．4.0.0以降は動作しない．
# pip install datasets==3.6.0 sudachipy pandas numpy pyarrow

# 使用例
# python -m src.p1_0_preprocess --config ./src/configs/x_y/preprocess_example_config.json
# --check_category 1 で train のカテゴリ '1' の例を表示

from __future__ import annotations
from datasets import load_dataset
from datasets.utils.logging import disable_progress_bar
from pathlib import Path
import pandas as pd
import numpy as np
import json, re, unicodedata as U, html
from typing import Dict, Tuple

# =========================
# ユーティリティ
# =========================
_RED = "\033[31m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

def _warn(msg: str):
    """赤太字で[警告]を出力"""
    print(f"{_RED}{_BOLD}[警告]{_RESET} {msg}")

def _error_msg(msg: str) -> str:
    """赤太字で[エラー]ラベルを付けた文字列（例外メッセージ用）"""
    return f"{_RED}{_BOLD}[エラー]{_RESET} {msg}"

def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

# ---- サブセット抽出 ----
def _subset_df(df: pd.DataFrame, category_col: str, subset_cfg: Dict, seed: int) -> pd.DataFrame:
    if not subset_cfg or not subset_cfg.get("enabled", False):
        return df

    rng = np.random.RandomState(seed)
    mode = subset_cfg.get("mode", "")
    val = subset_cfg.get("value", 0)

    n_total = len(df)
    if n_total == 0:
        _warn("subset: 入力 DataFrame が空です。処理をスキップします。")

        return df

    # ---- fraction ----
    if mode == "fraction":
        frac = float(val)
        if frac > 1.0:
            _warn(f"subset: fraction={frac} は 1.0 を超えています。1.0 に切り詰めます。")
            frac = 1.0
        if frac < 0.0:
            raise ValueError(_error_msg(f"subset: fraction={frac} は負の値です。0.0〜1.0 の範囲で指定してください。"))
        return df.sample(frac=frac, random_state=rng)

    # ---- absolute ----
    elif mode == "absolute":
        n = int(val)
        if n > n_total:
            _warn(f"subset: 要求件数 {n} が総件数 {n_total} を超えています。全件 {n_total} を使用します。")
            n = n_total
        if n < 0:
            raise ValueError(_error_msg(f"subset: absolute の n={n} は負の値です。0 以上を指定してください。"))


    # ---- per_class ----
    elif mode == "per_class" and category_col in df.columns:
        k = int(val)
        parts = []
        if k < 0:
            raise ValueError(_error_msg(f"subset: per_class の値 {k} は負の値です。0 以上を指定してください。"))
        for cat, g in df.groupby(category_col):
            if k > len(g):
                _warn(f"subset: per_class の値 {k} がカテゴリ '{cat}' の件数 {len(g)} を超えています。利用可能な全件を使用します。")
                take = len(g)
            else:
                take = k
            parts.append(g.sample(n=take, random_state=rng))
        return pd.concat(parts, ignore_index=True)

    # ---- balanced_absolute ----
    elif mode == "balanced_absolute" and category_col in df.columns:
        n_target = int(val)
        if n_target > n_total:
            _warn(f"subset: balanced_absolute の目標 {n_target} が総件数 {n_total} を超えています。{n_total} に切り詰めます。")
            n_target = n_total

        # クラスごとの件数
        groups = list(df.groupby(category_col))
        total_len = sum(len(g) for _, g in groups)
        if total_len == 0:
            return df.iloc[0:0]

        # 各クラスの比率に応じて件数を配分
        ratios = [len(g) / total_len for _, g in groups]
        n_per_class = [max(1, int(round(n_target * r))) for r in ratios]

        # 端数調整（合計がずれたら調整）
        diff = n_target - sum(n_per_class)
        if diff != 0:
            order = np.argsort(ratios)[::-1] if diff > 0 else np.argsort(ratios)
            for i in order[:abs(diff)]:
                n_per_class[i] += np.sign(diff)

        sampled_parts = []
        for (cat, g), n_take in zip(groups, n_per_class):
            take = min(len(g), n_take)
            if n_take > len(g):
                _warn(f"subset: カテゴリ '{cat}' に対して要求 {n_take} > 利用可能 {len(g)}。利用可能な全件を使用します。")
            sampled_parts.append(g.sample(n=take, random_state=rng))
        return pd.concat(sampled_parts, ignore_index=True)

    # ---- fallback ----
    else:
        return df



# ---- クリーニング ----
_URL_RE = re.compile(r"https?://\S+")
_HTML_RE = re.compile(r"<[^>]+>")
_DIGIT_RE = re.compile(r"\d")

# Sudachi 初期化（必要時に一度だけ）
_SUDACHI = None
def _get_sudachi(mode_str: str = "C"):
    global _SUDACHI
    if _SUDACHI is not None:
        return _SUDACHI
    from sudachipy import tokenizer as s_tokenizer
    from sudachipy import dictionary
    obj = dictionary.Dictionary().create()
    mode = {"A": s_tokenizer.Tokenizer.SplitMode.A,
            "B": s_tokenizer.Tokenizer.SplitMode.B,
            "C": s_tokenizer.Tokenizer.SplitMode.C}.get(mode_str.upper(),
                                                        s_tokenizer.Tokenizer.SplitMode.C)
    _SUDACHI = (obj, mode)
    return _SUDACHI


def _tokenize_ja_sudachi(text: str, tok_cfg: Dict, joiner: str) -> str:
    if not tok_cfg or not tok_cfg.get("enabled", False):
        return text

    # Sudachi の設定
    sudachi_mode = tok_cfg.get("sudachi_mode", "C")
    keep_base = tok_cfg.get("keep_baseform", False)
    remove_pos = set(tok_cfg.get("remove_pos", []))

    # ストップワード設定（任意）
    stop_enabled = bool(tok_cfg.get("stopwords_enabled", False))
    stop_list = set(tok_cfg.get("stopwords_list", [])) if stop_enabled else set()

    tok, mode = _get_sudachi(sudachi_mode)

    toks = []
    for m in tok.tokenize(text, mode):
        # 品詞（大分類）
        pos_info = m.part_of_speech()
        pos = pos_info[0] if pos_info and len(pos_info) > 0 else ""
        if pos in remove_pos:
            continue

        surface = m.surface()
        base = m.dictionary_form()

        # 見出し語 or 表層形
        word = base if (keep_base and base not in ("*", None)) else surface

        # ストップワード除去
        if stop_enabled and word in stop_list:
            continue

        toks.append(word)

    return joiner.join(toks)

def remove_symbols_punct(s: str, cfg_symbols: dict) -> str:
    if not cfg_symbols:
        return s
    x = s
    cats = set(cfg_symbols.get("unicode_categories_to_remove", []))
    if cats:
        x = "".join(ch for ch in x if U.category(ch) not in cats)

    # 句読点除去
    if cfg_symbols.get("remove_punct", False):
        x = re.sub(r"[、。．，，：；？！]", " ", x)

    # 記号除去（括弧や装飾系）
    if cfg_symbols.get("remove_symbols", False):
        x = re.sub(r"[「」『』【】（）［］｛｝〈〉《》★☆♪※♯→←±∞§]", " ", x)

    if cfg_symbols.get("collapse_spaces", True):
        x = re.sub(r"\s+", " ", x).strip()
    return x



def clean_text_series(s: pd.Series, cleaning_cfg: Dict, symbols_cfg: Dict, tokenize_cfg: Dict) -> pd.Series:
    def _clean(x: str) -> str:
        if not isinstance(x, str):
            return "" if pd.isna(x) else str(x)     # 文字列でない場合の対処
        if cleaning_cfg.get("normalize_unicode", True):
            x = U.normalize("NFKC", x)              # Unicode正規化（Ａ→A，ｱ→ア等）
        if cleaning_cfg.get("lower", True):
            x = x.lower()                           # 小文字化
        if cleaning_cfg.get("strip", True):
            x = x.strip()                           # 文頭・文末の空白，改行除去
        if cleaning_cfg.get("rm_html", True):
            x = html.unescape(_HTML_RE.sub(" ", x)) # HTMLタグ除去＋エスケープ解除(&amp→&など)
        if cleaning_cfg.get("rm_url", True):
            x = _URL_RE.sub(" ", x)                 # URL除去
        if cleaning_cfg.get("replace_digits_to_zero", False):
            x = _DIGIT_RE.sub("0", x)               # 数字を0に置換

        # --- 形態素解析（Sudachi） ---
        if tokenize_cfg and tokenize_cfg.get("enabled", False):
            # jsonのtokenize.joiner
            joiner = tokenize_cfg.get("joiner", " ") if tokenize_cfg else " "
            x = _tokenize_ja_sudachi(x, tokenize_cfg, joiner)
            
        # --- 記号除去 ---
        x = remove_symbols_punct(x, symbols_cfg)

        return x
    return s.astype(str).map(_clean)


def _normalize_cat_values(series: pd.Series) -> pd.Series:
    # category列をすべて文字列扱いに統一（JSONの指定が "1" などなので）
    return series.map(lambda v: "" if pd.isna(v) else str(v))

def _sample_pool(df_pool: pd.DataFrame, n: int, rng: np.random.RandomState, oversample: bool, who: str) -> pd.DataFrame:
    if n < 0: # 負の値はエラー扱い
        raise ValueError(_error_msg(f"サンプリング数 n={n} が負です（対象: '{who}'）。0 以上を指定してください。"))
    if n == 0:
        return df_pool.iloc[0:0]
    if len(df_pool) == 0:
        return df_pool.iloc[0:0]
    if n <= len(df_pool):
        return df_pool.sample(n=n, random_state=rng, replace=False)

    # 欲しい数 > プール数
    if oversample:
        _warn(f"オーバーサンプリング（対象: '{who}'）: 要求 {n} > 利用可能 {len(df_pool)}。復元抽出で補います。")
        idx = rng.choice(df_pool.index.values, size=n, replace=True)
        return df_pool.loc[idx]

    # oversample=False の場合は「ある分だけ」＋警告を出す
    _warn(f"サンプル不足（対象: '{who}'）: 要求 {n} > 利用可能 {len(df_pool)}。重複なしで利用可能な全件を使用します。")
    return df_pool.sample(n=len(df_pool), random_state=rng, replace=False)


def _make_imbalanced(df: pd.DataFrame, category_col: str, cfg: Dict, seed: int) -> pd.DataFrame:
    """
    仕様：
      - imbalance.n_group1 / n_group2 / n_others は「各カテゴリあたりの目標件数」
      - group1_categories / group2_categories に含まれるカテゴリは、各カテゴリごとに n_group1 / n_group2 件サンプル
      - others（どちらにも属さないカテゴリ）は、各カテゴリごとに n_others 件サンプル
      - oversample_if_small=True のとき、カテゴリ内の母数 < 目標件数 なら重複抽出で補い、警告を出す
      - oversample_if_small=False のときは、ある分だけ（重複なし・静かに切り詰め）
    """
    if not cfg or not cfg.get("enabled", False):
        return df

    rng = np.random.RandomState(seed)

    # カテゴリ集合の準備（文字列化）
    cats_series = _normalize_cat_values(df[category_col])
    df = df.assign(**{category_col: cats_series})

    g1_set = set(map(str, cfg.get("group1_categories", [])))
    g2_set = set(map(str, cfg.get("group2_categories", [])))

    # 重複指定は group1 を優先
    overlap = g1_set & g2_set
    if overlap:
        _warn(f"カテゴリが group1 と group2 の両方に指定されています。group1 を優先します: {sorted(overlap)}")
        g2_set -= overlap

    n_g1 = int(cfg.get("n_group1", -1)) # 値無しはエラー扱い
    n_g2 = int(cfg.get("n_group2", -1))
    n_oth = int(cfg.get("n_others", -1))
    oversample = bool(cfg.get("oversample_if_small", False))

    parts = []

    # --- group1: 各カテゴリあたり n_g1 件 ---
    if g1_set:
        if n_g1 < 0:
            raise ValueError(_error_msg("imbalance: group1 の n_group1 が負の値です。0 以上を指定してください。"))
        for cat in sorted(g1_set):
            pool = df[df[category_col] == cat]
            if len(pool) == 0:
                _warn(f"group1 のカテゴリ '{cat}' が見つかりません。スキップします。")
                continue
            take = _sample_pool(pool, n_g1, rng, oversample, who=f"group1:{cat}")
            parts.append(take)

    # --- group2: 各カテゴリあたり n_g2 件 ---
    if g2_set:
        if n_g2 < 0:
            raise ValueError(_error_msg("imbalance: group2 の n_group2 が負の値です。0 以上を指定してください。"))
        for cat in sorted(g2_set):
            pool = df[df[category_col] == cat]
            if len(pool) == 0:
                _warn(f"group2 のカテゴリ '{cat}' が見つかりません。スキップします。")
                continue
            take = _sample_pool(pool, n_g2, rng, oversample, who=f"group2:{cat}")
            parts.append(take)

    # --- others: g1/g2 以外のカテゴリを対象に、各カテゴリあたり n_oth 件 ---
    others_cats = sorted(set(df[category_col].unique()) - (g1_set | g2_set))
    if others_cats:
        for cat in others_cats:
            pool = df[df[category_col] == cat]
            if len(pool) == 0:
                continue
            take = _sample_pool(pool, n_oth, rng, oversample, who=f"others:{cat}")
            parts.append(take)

    if not parts:
        # 何も指定がなければ元の df を返す
        return df

    out = pd.concat(parts, ignore_index=True)
    out = out.sample(frac=1.0, random_state=rng).reset_index(drop=True)
    return out


# ---- 分割（層化 stratified / ランダム）----
def split_df(
    df: pd.DataFrame,
    random_seed: int,
    stratified: bool,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    category_col: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6
    rng = np.random.RandomState(random_seed)

    if stratified and category_col in df.columns:
        parts = []
        for category, g in df.groupby(category_col):
            idx = rng.permutation(len(g))
            n = len(g)
            n_train = int(n * train_ratio)
            n_val = int(n * val_ratio)
            train_idx = idx[:n_train]
            val_idx = idx[n_train:n_train + n_val]
            test_idx = idx[n_train + n_val:]
            parts.append((g.iloc[train_idx], g.iloc[val_idx], g.iloc[test_idx]))
        train = pd.concat([p[0] for p in parts], ignore_index=True)
        val = pd.concat([p[1] for p in parts], ignore_index=True)
        test = pd.concat([p[2] for p in parts], ignore_index=True)
    else:
        idx = rng.permutation(len(df))
        n = len(df)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        train = df.iloc[idx[:n_train]]
        val = df.iloc[idx[n_train:n_train + n_val]]
        test = df.iloc[idx[n_train + n_val:]]
    return train, val, test

def _holdout_test(
    df: pd.DataFrame,
    category_col: str,
    ratio: float,
    seed: int,
    stratified: bool
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    ratio > 0 のとき、df からテスト分を一度だけ切り出す（層化対応）。
    戻り値: (trainval_df, test_df)
    """
    rng = np.random.RandomState(seed)
    if ratio <= 0.0 or len(df) == 0:
        return df, df.iloc[0:0]

    if stratified and (category_col in df.columns):
        tr_parts, te_parts = [], []
        for _, g in df.groupby(category_col):
            idx = rng.permutation(len(g))
            n = len(g)
            n_te = int(round(n * ratio))
            te = g.iloc[idx[:n_te]]
            tr = g.iloc[idx[n_te:]]
            tr_parts.append(tr)
            te_parts.append(te)
        trainval = pd.concat(tr_parts, ignore_index=True)
        test = pd.concat(te_parts, ignore_index=True)
    else:
        idx = rng.permutation(len(df))
        n = len(df)
        n_te = int(round(n * ratio))
        test = df.iloc[idx[:n_te]]
        trainval = df.iloc[idx[n_te:]]

    # 以降の処理が楽になるように連番indexにしておく
    return trainval.reset_index(drop=True), test.reset_index(drop=True)


def _assign_folds(
    df: pd.DataFrame,
    category_col: str,
    k: int,
    seed: int,
    stratified: bool
) -> np.ndarray:
    """
    df の各行に fold番号 [0..k-1] を割り当てる。層化対応。
    戻り値は長さ len(df) の np.ndarray[int32]
    """
    rng = np.random.RandomState(seed)
    n = len(df)
    fold_idx = np.empty(n, dtype=np.int32)

    if n == 0:
        return fold_idx  # 空でも返す

    if stratified and (category_col in df.columns):
        # カテゴリごとにシャッフル→k等分
        start = 0
        for _, g in df.groupby(category_col):
            idx = g.index.to_numpy()
            perm = rng.permutation(idx)
            chunks = np.array_split(perm, k)
            for f, ch in enumerate(chunks):
                fold_idx[ch] = f
    else:
        perm = rng.permutation(n)
        chunks = np.array_split(perm, k)
        for f, ch in enumerate(chunks):
            fold_idx[np.array(ch, dtype=int)] = f

    return fold_idx


# ---- 保存（Parquet固定）----
def _save_parquet(df: pd.DataFrame, path: Path):
    df.to_parquet(path, index=False)

# =========================
# 前処理の本体
# =========================
def run_preprocess_on_df(
    df: pd.DataFrame,
    config_path: str,
    out_dir: str | None = None,
) -> Dict[str, str]:
    """
    要件：
      - コンフィグは JSON
      - 出力は Parquet（統一）
      - split.stratified / cv.stratified を尊重
      - cv.enabled: true の場合は k-fold 用に保存
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    random_seed = int(cfg.get("random_seed", 42))
    cleaning_cfg = cfg.get("cleaning", {})
    symbols_cfg = cfg.get("symbols", {})
    tokenize_cfg = cfg.get("tokenize", {})
    subset_cfg = cfg.get("subset", {})
    imbalance_cfg = cfg.get("imbalance", {})
    split_cfg = cfg.get("split", {})
    split_stratified = bool(split_cfg.get("stratified", True))
    train_ratio = float(split_cfg.get("train", 0.8))
    val_ratio = float(split_cfg.get("val", 0.1))
    test_ratio = float(split_cfg.get("test", 0.1))

    cv_cfg = cfg.get("cv", {})
    cv_enabled = bool(cv_cfg.get("enabled", False))
    k = int(cv_cfg.get("k", 5))
    cv_stratified = bool(cv_cfg.get("stratified", True))
    make_test = bool(cv_cfg.get("make_test", True))
    cv_test_ratio = float(cv_cfg.get("test_ratio", 0.1))

    # カラム名は固定（content/category）で扱う
    content_col = "content"
    category_col = "category"
    if content_col not in df.columns:
        raise KeyError(f"'{content_col}' column is required, but not found. got: {list(df.columns)}")

    # まず必要カラムだけに絞る
    df = df.copy()
    keep_cols = [content_col] + ([category_col] if category_col in df.columns else [])
    df = df[keep_cols].reset_index(drop=True)

    # サブセット抽出
    df = _subset_df(df, category_col=category_col, subset_cfg=subset_cfg, seed=random_seed)

    # クリーニング
    df[content_col] = clean_text_series(df[content_col], cleaning_cfg, symbols_cfg, tokenize_cfg)

    # 不均衡化
    df = _make_imbalanced(df, category_col=category_col, cfg=imbalance_cfg, seed=random_seed)

    # 出力ディレクトリ
    if out_dir is None:
        out_dir = "./data/X_Y_please_set_output_dir"
    out_base = Path(out_dir)
    _ensure_dir(out_base)

    # ===== 通常3分割（cv.disabled） =====
    if not cv_enabled:
        train, val, test = split_df(
            df,
            random_seed=random_seed,
            stratified=split_stratified,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            category_col=category_col,
        )
        paths = {
            "train": str(out_base / "train.parquet"),
            "val": str(out_base / "val.parquet"),
            "test": str(out_base / "test.parquet"),
        }
        _save_parquet(train, Path(paths["train"]))
        _save_parquet(val, Path(paths["val"]))
        _save_parquet(test, Path(paths["test"]))
        return paths

    # ===== k-fold クロスバリデーション =====
    # 1) 固定テスト切り出し（必要なら）
    use_strat = cv_stratified if cv_cfg.get("stratified", None) is not None else split_stratified
    df_trainval, df_test = _holdout_test(
        df=df,
        category_col=category_col,
        ratio=(cv_test_ratio if make_test else 0.0),
        seed=random_seed,
        stratified=use_strat
    )

    # 念のため index を詰める（fold割当がシンプルになる）
    df_trainval = df_trainval.reset_index(drop=True)
    df_test = df_test.reset_index(drop=True)

    # 2) fold 割当
    if k <= 1 or len(df_trainval) == 0:
        raise ValueError(_error_msg("cv.enabled=true の場合、k>=2 かつ 学習用データが1件以上必要です。"))
    fold_idx = _assign_folds(
        df=df_trainval,
        category_col=category_col,
        k=k,
        seed=random_seed,
        stratified=use_strat
    )

    # 3) 保存
    out_cv = out_base / f"cv_k{k}"
    _ensure_dir(out_cv)

    folds_map: Dict[str, Dict[str, str]] = {}
    for f in range(k):
        val_mask = (fold_idx == f)
        train_part = df_trainval.loc[~val_mask]
        val_part = df_trainval.loc[val_mask]

        fold_dir = out_cv / f"fold_{f+1}"
        _ensure_dir(fold_dir)
        p_train = fold_dir / "train.parquet"
        p_val = fold_dir / "val.parquet"
        _save_parquet(train_part, p_train)
        _save_parquet(val_part, p_val)

        folds_map[f"fold_{f+1}"] = {
            "train": str(p_train),
            "val": str(p_val),
        }

    paths: Dict[str, Dict[str, str]] = {"folds": folds_map}
    if make_test and len(df_test) > 0:
        p_test = out_cv / "test.parquet"
        _save_parquet(df_test, p_test)
        paths["test"] = str(p_test)

    return paths

def check(ds_dict, category_value: str | None = None):
    disable_progress_bar()
    pd.set_option("display.max_colwidth", None)

    # 1) カテゴリ別件数（train / validation / test / total）
    print("=== カテゴリ別件数（train / validation / test / total） ===")

    # --- 全カテゴリを収集 ---
    all_cats = set()
    for split in ["train", "validation", "test"]:
        if split in ds_dict:
            all_cats.update(set(ds_dict[split]["category"]))
    all_cats = sorted(list(all_cats), key=lambda x: str(x))

    # --- 各カテゴリの件数を計算 ---
    rows = []
    for cat in all_cats:
        counts = []
        for split in ["train", "validation", "test"]:
            if split in ds_dict:
                subset = ds_dict[split].filter(lambda ex: str(ex.get("category", "")) == str(cat))
                counts.append(len(subset))
            else:
                counts.append(0)
        total = sum(counts)
        rows.append((cat, *counts, total))

    # --- DataFrame化して出力 ---
    df_counts = pd.DataFrame(rows, columns=["category", "train", "validation", "test", "total"])
    print(df_counts.to_string(index=False))
    print()

    # --- 任意のカテゴリ内容（train のみ） ---
    if category_value is not None and "train" in ds_dict:
        subset = ds_dict["train"].filter(lambda ex: str(ex.get("category", "")) == str(category_value))
        n = len(subset)
        print(f"=== train : category == {category_value} | {n} rows ===")
        if n > 0:
            df_sub = subset.to_pandas().head(1)[["content", "category"]].copy()
            df_sub["content"] = (
                df_sub["content"]
                .astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
            row = df_sub.iloc[0]
            print(f"content: {row['content']}\n\ncategory: {row['category']}")
        else:
            print("(no rows)")

    # 2) サンプル表示（train のみ先頭1件）
    if category_value is not None and "train" in ds_dict:
        subset = ds_dict["train"].filter(lambda ex: str(ex.get("category", "")) == str(category_value))
        n = len(subset)
        print(f"=== train : category == {category_value} | {n} rows ===")
        if n > 0:
            df_sub = subset.to_pandas().head(1)[["content", "category"]].copy()
            # 改行や連続空白を詰めて1行で表示
            df_sub["content"] = (
                df_sub["content"]
                .astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
            row = df_sub.iloc[0]
            print(f"content: {row['content']}\n\ncategory: {row['category']}")
        else:
            print("(no rows)")

def check_cv_categories(paths: Dict, fold: int | str = 0):
    """
    CV保存物(paths)から、指定foldのカテゴリ別件数（train/validation）と
    固定テスト（存在する場合）の件数、合計を表で表示する。

    Parameters
    ----------
    paths : dict
        preprocess() の戻り値のうち paths を渡す。
        期待形: {"folds": {"fold_1": {"train": "...", "val": "..."}, ...}, "test": "...(任意)"}
    fold : int | str
        表示対象のfold。0 or 1 or "fold_1" のように柔軟に指定可能。
        - 0    → "fold_1"
        - 1    → "fold_2"
        - "fold_1" → そのまま
    """


    # --- fold名を正規化（0/1/… か "fold_1" のどちらでもOK）---
    if isinstance(fold, int):
        fold_name = f"fold_{fold+1}"  # 0→fold_1, 1→fold_2...
    else:
        fold_name = str(fold)
        if not fold_name.startswith("fold_"):
            raise ValueError("fold は 0 始まりの整数 or 'fold_1' 形式で指定してください。")

    if "folds" not in paths or fold_name not in paths["folds"]:
        raise KeyError(f"{fold_name} が paths に見つかりません。利用可能: {list(paths.get('folds', {}).keys())}")

    p_train = Path(paths["folds"][fold_name]["train"])
    p_val   = Path(paths["folds"][fold_name]["val"])
    p_test  = Path(paths["test"]) if "test" in paths else None

    # --- 読み込み（category列が必須） ---
    def _vc(path: Path) -> pd.Series:
        if path is None:
            return pd.Series(dtype=int)
        df = pd.read_parquet(path, columns=["category"])
        # 安全のため文字列化（元コードの方針と一致）
        cats = df["category"].astype(str)
        return cats.value_counts().sort_index()

    vc_train = _vc(p_train)
    vc_val   = _vc(p_val)
    vc_test  = _vc(p_test) if p_test is not None else pd.Series(dtype=int)

    # --- 統合表を作成 ---
    cats_all = sorted(set(vc_train.index) | set(vc_val.index) | set(vc_test.index))
    df_out = pd.DataFrame(index=cats_all)
    df_out["train"] = df_out.index.map(lambda c: int(vc_train.get(c, 0)))
    df_out["validation"] = df_out.index.map(lambda c: int(vc_val.get(c, 0)))
    if p_test is not None:
        df_out["test"] = df_out.index.map(lambda c: int(vc_test.get(c, 0)))
    else:
        df_out["test"] = 0
    df_out["total"] = df_out[["train", "validation", "test"]].sum(axis=1)

    # --- 見やすく表示 ---
    print()
    print(f"=== Category counts for {fold_name} ===")
    print(df_out.to_string())
    print("\n--- totals ---")
    print("train      :", int(df_out["train"].sum()))
    print("validation :", int(df_out["validation"].sum()))
    if p_test is not None:
        print("test       :", int(df_out["test"].sum()))
    print("overall    :", int(df_out["total"].sum()))
    print()
    
    # 前処理済みの代表文字列を一つ表示
    print("\n=== Sample content from train ===")
    ds_train = load_dataset("parquet", data_files={"train": str(p_train)})["train"]
    if len(ds_train) > 0:
        row = ds_train[0]
        content = str(row.get("content", "")).replace("\n", " ").strip()
        print(f"content: {content}\n\ncategory: {row.get('category', '')}")
        print()


# =========================
# 外部からも呼べる前処理の入口
# =========================
def preprocess(
    df: pd.DataFrame,
    config_path: str,
    check_category: str | None = None,
):
    """
    DataFrame と config_path を受け取り、前処理・分割・保存・再ロードまでを実行。

    Returns
    -------
    cv.enabled = false:
        paths : {"train": "...", "val": "...", "test": "..."}
        ds_processed : DatasetDict(train, validation, test)
    cv.enabled = true:
        paths : {"folds": {"fold_1": {"train": "...", "val": "..."}, ...}, "test": "...(任意)"}
        ds_processed : {"folds": {fold_name: DatasetDict(train, validation)}, "test": DatasetDict(test) or None}
    """
    print("Start preprocessing...")
    print("config path:", config_path)

    # コンフィグ読込（out_dirと、念のためcv.enabledも把握）
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    out_dir = cfg.get("output", {}).get("dir", None)
    cv_enabled = bool(cfg.get("cv", {}).get("enabled", False))

    # 1) 実行（保存パスを受け取る）
    paths = run_preprocess_on_df(
        df,
        config_path=config_path,
        out_dir=out_dir,
    )
    print("Saved:", paths)

    # 2) ロード（CVあり/なしで分岐）
    if "folds" in paths:
        # ---- CV のとき ----
        ds_folds = {}
        for fold_name, pp in paths["folds"].items():
            data_files = {"train": pp["train"], "validation": pp["val"]}
            ds_folds[fold_name] = load_dataset("parquet", data_files=data_files)

        ds_test = None
        if "test" in paths:
            ds_test = load_dataset("parquet", data_files={"test": paths["test"]})

        ds_processed = {"folds": ds_folds, "test": ds_test}

        check_cv_categories(paths, fold=0)
        return paths, ds_processed

    else:
        # ---- 通常3分割のとき ----
        data_files = {
            "train": paths["train"],
            "validation": paths["val"],
            "test": paths["test"],
        }
        ds_processed = load_dataset("parquet", data_files=data_files)
        print(ds_processed)
        print()

        if check_category is not None:
            check(ds_processed, category_value=check_category)

        return paths, ds_processed



# =========================
# CLI からの実行（__main__）
# =========================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run preprocessing pipeline.")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to JSON config file (default: %(default)s)",
    )
    parser.add_argument(
        "--check_category",
        type=str,
        default="8",
        help="Show one sample of this category from train after preprocessing (default: 8, set empty to disable)",
    )
    args = parser.parse_args()

    # 0) データ取得（必要に応じて他のデータに差し替え可能）
    ds = load_dataset(
        "shunk031/livedoor-news-corpus",
        split="all",
        download_mode="reuse_cache_if_exists",
    )
    df = ds.to_pandas()

    # 空文字が来たら無効化
    check_cat = None if (args.check_category is None or args.check_category == "") else args.check_category

    # 実行
    preprocess(
        df=df,
        config_path=args.config,
        check_category=check_cat,
    )