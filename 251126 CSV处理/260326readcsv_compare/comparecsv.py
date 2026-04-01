import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ========= 用户需要改的部分 =========
folder = Path(r".")   # 改成你的文件夹路径；如果脚本和csv在同一目录，保持 "."
file_base = folder / "centroid_logmeshsize3.csv"   # 原始值 / 基准
file_cmp  = folder / "centroid_logmeshsize5.csv"   # 对比值
step_col = "step"

# 如果你的列名真的是 hij 和 nopqrs，就保留下面这一行
target_cols = ["cog_x", "cog_y", "cog_z"]

# 如果运行时报“列不存在”，把上一行改成实际列名
# 例如你这两个已上传 csv 里实际存在的是：
# target_cols = ["cog_x", "cog_y", "cog_z"]
# ===================================


def main():
    df_base = pd.read_csv(file_base)
    df_cmp = pd.read_csv(file_cmp)

    # 只保留前10步；如果本身只有10步，也能正常工作
    df_base = df_base.sort_values(step_col).head(10).copy()
    df_cmp = df_cmp.sort_values(step_col).head(10).copy()

    # 检查列是否存在
    missing_base = [c for c in [step_col] + target_cols if c not in df_base.columns]
    missing_cmp = [c for c in [step_col] + target_cols if c not in df_cmp.columns]

    if missing_base or missing_cmp:
        print("你指定的列在文件中不存在。")
        print(f"meshsize3 可用列: {list(df_base.columns)}")
        print(f"meshsize5 可用列: {list(df_cmp.columns)}")
        print(f"meshsize3 缺失: {missing_base}")
        print(f"meshsize5 缺失: {missing_cmp}")
        raise KeyError("请把 target_cols 改成实际列名。")

    # 合并
    merged = pd.merge(
        df_base[[step_col] + target_cols],
        df_cmp[[step_col] + target_cols],
        on=step_col,
        suffixes=("_meshsize3", "_meshsize5"),
        how="inner"
    ).sort_values(step_col)

    # 计算差值和相对 meshsize3 的百分比
    for c in target_cols:
        base = merged[f"{c}_meshsize3"].astype(float)
        cmpv = merged[f"{c}_meshsize5"].astype(float)

        merged[f"{c}_diff"] = cmpv - base
        merged[f"{c}_pct_vs_meshsize3"] = np.where(
            np.isclose(base, 0.0),
            np.nan,   # 基准值为0时，百分比没有意义
            (cmpv - base) / base * 100.0
        )

    # 导出结果表
    out_csv = folder / "meshsize3_vs_meshsize5_percent_diff.csv"
    merged.to_csv(out_csv, index=False, encoding="utf-8-sig")

    # =========================
    # 科研风格绘图
    # =========================
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.dpi": 150,
        "savefig.dpi": 600,
        "axes.linewidth": 1.0,
        "lines.linewidth": 1.8,
    })

    fig, ax = plt.subplots(figsize=(7.2, 4.8))

    for c in target_cols:
        ax.plot(
            merged[step_col],
            merged[f"{c}_pct_vs_meshsize3"],
            marker="o",
            markersize=4.5,
            label=f"{c}"
        )

    ax.axhline(0.0, linewidth=1.0, linestyle="--")
    ax.set_xlabel("Step")
    ax.set_ylabel("Relative difference vs meshsize3 (%)")
    ax.set_title("Relative column deviation over first 10 steps")
    ax.set_xticks(merged[step_col].to_list())
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)
    fig.tight_layout()

    out_eps = folder / "meshsize3_vs_meshsize5_percent_diff.eps"
    out_png = folder / "meshsize3_vs_meshsize5_percent_diff.png"

    fig.savefig(out_eps, format="eps", bbox_inches="tight")
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)

    print(f"结果表已输出: {out_csv}")
    print(f"EPS 图已输出: {out_eps}")
    print(f"PNG 图已输出: {out_png}")


if __name__ == "__main__":
    main()