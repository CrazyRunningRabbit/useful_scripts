import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def moving_average(x, w=20):
    return np.convolve(x, np.ones(w)/w, mode='same')

def plot_convergence(csv_path, out_png="convergence.png"):
    iters = []
    Js = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            try:
                it = int(row[0])
                val = float(row[1])
                iters.append(it)
                Js.append(val)
            except ValueError:
                # 处理 BOM 和表头行：iter, J
                continue
    
    iters = np.array(iters)
    Js = np.array(Js)

    # 科研风格参数
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams["figure.figsize"] = (7, 5)
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["font.size"] = 16
    plt.rcParams["axes.linewidth"] = 1.2

    fig, ax = plt.subplots()

    # 主曲线
    ax.plot(iters, Js, "-", lw=2.2, label="Objective $J$", color="black")

    # 平滑曲线
    Xsmooth = moving_average(Js, w=30)
    ax.plot(iters, Xsmooth, "--", lw=2.0, color="gray", label="Smoothed")

    # 辅助散点
    ax.scatter(iters[::max(1, len(iters)//60)],
               Js[::max(1, len(iters)//60)],
               s=18, color="blue", alpha=0.4)

    ax.set_xlabel("Iteration", fontsize=18)
    ax.set_ylabel("Objective $J$", fontsize=18)

    # 去上右边框更科研
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(frameon=True, fontsize=14)

    plt.tight_layout()
    plt.savefig(out_png, dpi=400)
    plt.close()

    print("科研级收敛曲线已保存：", out_png)


if __name__ == "__main__":
    plot_convergence("objective.csv")
