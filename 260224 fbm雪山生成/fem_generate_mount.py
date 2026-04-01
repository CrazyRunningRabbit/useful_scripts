import numpy as np
from noise import pnoise2
from PIL import Image
import matplotlib.pyplot as plt

def fbm2(x, y, octaves=6, lacunarity=2.0, gain=0.5, base=0):
    """
    2D fBm: 多尺度 Perlin 噪声叠加
    返回值大致在 [-1, 1] 附近
    """
    amp = 1.0
    freq = 1.0
    s = 0.0
    amp_sum = 0.0
    for _ in range(octaves):
        s += amp * pnoise2(x * freq, y * freq, repeatx=4096, repeaty=4096, base=base)
        amp_sum += amp
        amp *= gain
        freq *= lacunarity
    return s / max(amp_sum, 1e-8)

def generate_heightmap(size=1024, scale=3.0, octaves=7, lacunarity=2.0, gain=0.5, seed=42):
    """
    生成高度场，输出 float32 数组，范围归一化到 [0, 1]
    """
    h = np.zeros((size, size), dtype=np.float32)
    for i in range(size):
        x = (i / size) * scale
        for j in range(size):
            y = (j / size) * scale
            h[i, j] = fbm2(x, y, octaves=octaves, lacunarity=lacunarity, gain=gain, base=seed)

    # 归一化到 [0, 1]
    h -= h.min()
    h /= (h.max() - h.min() + 1e-12)

    # 让“山”更像山：轻微提升高处，压低低处（可选，但很有用）
    # 数值越大，山峰越尖，山谷越平
    h = h ** 1.6
    return h

if __name__ == "__main__":
    SIZE = 1024          # 分辨率，建议 1024 或 2048
    SCALE = 3.5          # 控制地形“尺度”，越大越平缓
    OCTAVES = 7          # 多尺度层数，越大细节越多
    LACUNARITY = 2.0     # 频率倍增
    GAIN = 0.5           # 幅值衰减
    SEED = 7             # 换 seed 就换一座山

    h01 = generate_heightmap(
        size=SIZE,
        scale=SCALE,
        octaves=OCTAVES,
        lacunarity=LACUNARITY,
        gain=GAIN,
        seed=SEED
    )

    # 保存 16bit 高度图（UE5 最好用 16bit）
    h16 = (h01 * 65535.0).astype(np.uint16)
    Image.fromarray(h16).save("fbm_snow_mountain_16bit.png")
    print("Saved: fbm_snow_mountain_16bit.png")

    # 3D 预览
    step = max(SIZE // 256, 1)  # 降采样加速显示
    H = h01[::step, ::step]
    xs = np.linspace(0, 1, H.shape[0])
    ys = np.linspace(0, 1, H.shape[1])
    X, Y = np.meshgrid(xs, ys, indexing="ij")

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, H, linewidth=0, antialiased=True)
    ax.set_title("fBm terrain preview")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Height (normalized)")
    plt.show()