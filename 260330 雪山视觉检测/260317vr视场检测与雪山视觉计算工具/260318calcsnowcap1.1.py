import math
import numpy as np
import matplotlib.pyplot as plt


DEFAULT_PARAMS = {
    "Ha": 1500.0,
    "Hmax": 3500.0,
    "Hmin": 1000.0,
    "s": 2000.0,
    "L": 10000.0,
    "summit_nearer": False,
    "Fv_deg": 130.0,
}

PARAM_ORDER = ["Ha", "Hmax", "Hmin", "s", "L"]


def get_endpoint_distances(Ha, Hmax, Hmin, s, L, summit_nearer=True):
    if Hmax <= Hmin:
        raise ValueError("必须满足 Hmax > Hmin。")

    eps = 1.0 if summit_nearer else -1.0
    xt = L - eps * s / 2.0
    xb = L + eps * s / 2.0

    if xt <= 0 or xb <= 0:
        raise ValueError(
            f"几何无效：xt={xt:.6f}, xb={xb:.6f}。请确保 L > s/2 且山体在观察者前方。"
        )

    return eps, xt, xb


def x_of_H(H, Hmax, Hmin, xt, xb):
    u = (H - Hmin) / (Hmax - Hmin)
    return xb + u * (xt - xb)


def theta_of_H(H, Ha, Hmax, Hmin, xt, xb):
    xH = x_of_H(H, Hmax, Hmin, xt, xb)
    if xH <= 0:
        raise ValueError(f"几何无效：x(H)={xH:.6f} <= 0")
    return math.atan2(H - Ha, xH)


def compute_geometry(Ha, Hmax, Hmin, s, L, summit_nearer=True, Fv_deg=130.0):
    if Fv_deg <= 0:
        raise ValueError("必须满足 Fv_deg > 0。")

    eps, xt, xb = get_endpoint_distances(Ha, Hmax, Hmin, s, L, summit_nearer)

    Hmid = 0.5 * (Hmax + Hmin)
    xmid = x_of_H(Hmid, Hmax, Hmin, xt, xb)

    theta_top = theta_of_H(Hmax, Ha, Hmax, Hmin, xt, xb)
    theta_mid = theta_of_H(Hmid, Ha, Hmax, Hmin, xt, xb)
    theta_bottom = theta_of_H(Hmin, Ha, Hmax, Hmin, xt, xb)

    afull_rad = theta_top - theta_bottom
    afull_deg = math.degrees(afull_rad)
    ratio_percent = afull_deg / Fv_deg * 100.0

    alpha_upper_rad = theta_top - theta_mid
    alpha_lower_rad = theta_mid - theta_bottom

    alpha_upper_deg = math.degrees(alpha_upper_rad)
    alpha_lower_deg = math.degrees(alpha_lower_rad)

    half_height = 0.5 * (Hmax - Hmin)

    amp_upper = alpha_upper_rad / half_height
    amp_lower = alpha_lower_rad / half_height

    amp_ratio = amp_upper / amp_lower
    amp_diff_percent = (amp_ratio - 1.0) * 100.0

    return {
        "eps": eps,
        "xt": xt,
        "xb": xb,
        "Hmid": Hmid,
        "xmid": xmid,
        "theta_top": theta_top,
        "theta_mid": theta_mid,
        "theta_bottom": theta_bottom,
        "afull_rad": afull_rad,
        "afull_deg": afull_deg,
        "ratio_percent": ratio_percent,
        "alpha_upper_rad": alpha_upper_rad,
        "alpha_upper_deg": alpha_upper_deg,
        "alpha_lower_rad": alpha_lower_rad,
        "alpha_lower_deg": alpha_lower_deg,
        "half_height": half_height,
        "amp_upper": amp_upper,
        "amp_lower": amp_lower,
        "amp_ratio": amp_ratio,
        "amp_diff_percent": amp_diff_percent,
    }


def compute_theta_partials(Ha, Hmax, Hmin, s, L, summit_nearer=True):
    eps, xt, xb = get_endpoint_distances(Ha, Hmax, Hmin, s, L, summit_nearer)

    Hmid = 0.5 * (Hmax + Hmin)
    xmid = 0.5 * (xt + xb)

    dt = Hmax - Ha
    dm = Hmid - Ha
    db = Hmin - Ha

    Qt = xt**2 + dt**2
    Qm = xmid**2 + dm**2
    Qb = xb**2 + db**2

    d_theta_top = {
        "Ha": -xt / Qt,
        "Hmax": xt / Qt,
        "Hmin": 0.0,
        "s": eps * dt / (2.0 * Qt),
        "L": -dt / Qt,
    }

    d_theta_mid = {
        "Ha": -xmid / Qm,
        "Hmax": xmid / (2.0 * Qm),
        "Hmin": xmid / (2.0 * Qm),
        "s": 0.0,
        "L": -dm / Qm,
    }

    d_theta_bottom = {
        "Ha": -xb / Qb,
        "Hmax": 0.0,
        "Hmin": xb / Qb,
        "s": -eps * db / (2.0 * Qb),
        "L": -db / Qb,
    }

    return d_theta_top, d_theta_mid, d_theta_bottom


def compute_all_partials(Ha, Hmax, Hmin, s, L, summit_nearer=True, Fv_deg=130.0):
    g = compute_geometry(Ha, Hmax, Hmin, s, L, summit_nearer, Fv_deg)
    dtt, dtm, dtb = compute_theta_partials(Ha, Hmax, Hmin, s, L, summit_nearer)

    alpha_u = g["alpha_upper_rad"]
    alpha_l = g["alpha_lower_rad"]
    h = g["half_height"]

    d_afull = {}
    d_alpha_u = {}
    d_alpha_l = {}

    for p in PARAM_ORDER:
        d_afull[p] = dtt[p] - dtb[p]
        d_alpha_u[p] = dtt[p] - dtm[p]
        d_alpha_l[p] = dtm[p] - dtb[p]

    scale_ratio = (180.0 / math.pi) * (100.0 / Fv_deg)
    d_ratio_percent = {p: scale_ratio * d_afull[p] for p in PARAM_ORDER}

    dh = {
        "Ha": 0.0,
        "Hmax": 0.5,
        "Hmin": -0.5,
        "s": 0.0,
        "L": 0.0,
    }

    d_amp_u = {}
    d_amp_l = {}
    for p in PARAM_ORDER:
        d_amp_u[p] = (d_alpha_u[p] * h - alpha_u * dh[p]) / (h**2)
        d_amp_l[p] = (d_alpha_l[p] * h - alpha_l * dh[p]) / (h**2)

    amp_u = g["amp_upper"]
    amp_l = g["amp_lower"]

    d_amp_ratio = {}
    for p in PARAM_ORDER:
        d_amp_ratio[p] = (d_amp_u[p] * amp_l - amp_u * d_amp_l[p]) / (amp_l**2)

    d_amp_diff_percent = {p: 100.0 * d_amp_ratio[p] for p in PARAM_ORDER}

    return {
        "afull_rad": d_afull,
        "ratio_percent": d_ratio_percent,
        "alpha_upper_rad": d_alpha_u,
        "alpha_lower_rad": d_alpha_l,
        "amp_upper": d_amp_u,
        "amp_lower": d_amp_l,
        "amp_ratio": d_amp_ratio,
        "amp_diff_percent": d_amp_diff_percent,
    }


def compute_relative_segment_magnifications(
    Ha, Hmax, Hmin, s, L, summit_nearer=True, n=4
):
    if not isinstance(n, int) or n <= 0:
        raise ValueError("n 必须是正整数。")

    _, xt, xb = get_endpoint_distances(Ha, Hmax, Hmin, s, L, summit_nearer)

    dH = Hmax - Hmin
    dh = dH / n

    H_nodes = np.array([Hmax - i * dh for i in range(n + 1)], dtype=float)

    theta_nodes = np.array(
        [theta_of_H(H, Ha, Hmax, Hmin, xt, xb) for H in H_nodes],
        dtype=float,
    )

    alpha_segments = theta_nodes[:-1] - theta_nodes[1:]
    magnifications = alpha_segments / dh

    top_mag = magnifications[0]
    relative_percent = magnifications / top_mag * 100.0

    return {
        "H_nodes_top_to_bottom": H_nodes,
        "theta_nodes_rad_top_to_bottom": theta_nodes,
        "alpha_segments_rad_top_to_bottom": alpha_segments,
        "magnifications_rad_per_m_top_to_bottom": magnifications,
        "relative_percent_top_to_bottom": relative_percent,
    }


def print_current_values(g):
    print("\n================ 当前关键函数值 ================\n")
    print(f"afull_rad         = {g['afull_rad']:.12f} rad")
    print(f"afull_deg         = {g['afull_deg']:.12f} deg")
    print(f"ratio_percent     = {g['ratio_percent']:.12f} %")
    print(f"alpha_upper_rad   = {g['alpha_upper_rad']:.12f} rad")
    print(f"alpha_upper_deg   = {g['alpha_upper_deg']:.12f} deg")
    print(f"alpha_lower_rad   = {g['alpha_lower_rad']:.12f} rad")
    print(f"alpha_lower_deg   = {g['alpha_lower_deg']:.12f} deg")
    print(f"amp_upper         = {g['amp_upper']:.12e} rad/m")
    print(f"amp_lower         = {g['amp_lower']:.12e} rad/m")
    print(f"amp_ratio         = {g['amp_ratio']:.12f}")
    print(f"amp_diff_percent  = {g['amp_diff_percent']:.12f} %")


def print_derivative_formulas():
    print("\n================ 导数推导依据 ================\n")
    print("1) 基础角函数")
    print("   theta = atan2(y, x)")
    print("   ∂theta/∂y = x / (x^2 + y^2)")
    print("   ∂theta/∂x = -y / (x^2 + y^2)")
    print()
    print("2) 端点与线性插值")
    print("   xt = L - eps*s/2")
    print("   xb = L + eps*s/2")
    print("   x(H) = xb + (H-Hmin)/(Hmax-Hmin) * (xt-xb)")
    print()
    print("3) 当前关键角")
    print("   theta_top    = atan2(Hmax - Ha, xt)")
    print("   theta_mid    = atan2((Hmax+Hmin)/2 - Ha, (xt+xb)/2)")
    print("   theta_bottom = atan2(Hmin - Ha, xb)")
    print("   其中在线性插值下，(xt+xb)/2 = L")
    print()
    print("4) 关键函数")
    print("   afull        = theta_top - theta_bottom")
    print("   ratio_percent= afull * (180/pi) * 100 / Fv_deg")
    print("   alpha_upper  = theta_top - theta_mid")
    print("   alpha_lower  = theta_mid - theta_bottom")
    print("   h            = (Hmax - Hmin)/2")
    print("   amp_upper    = alpha_upper / h")
    print("   amp_lower    = alpha_lower / h")
    print("   amp_ratio    = amp_upper / amp_lower")
    print("   amp_diff_pct = (amp_ratio - 1) * 100")
    print()
    print("5) 商函数求导")
    print("   若 f = u/v，则 df = (du*v - u*dv) / v^2")


def print_current_partials(partials):
    print("\n================ 当前参数下的偏导数值 ================\n")
    for fname, pdict in partials.items():
        print(f"[{fname}]")
        for p in PARAM_ORDER:
            print(f"  d({fname})/d({p}) = {pdict[p]: .12e}")
        print()


def make_domains(params):
    Ha = params["Ha"]
    Hmax = params["Hmax"]
    Hmin = params["Hmin"]
    s = params["s"]

    Ha_lo = max(-2000.0, Hmin - 5000.0)
    Ha_hi = Hmax + 5000.0

    Hmax_lo = Hmin + 1.0
    Hmax_hi = max(Hmax * 2.0, Hmin + 5000.0)

    Hmin_lo = max(-2000.0, Hmin - 3000.0)
    Hmin_hi = Hmax - 1.0

    s_lo = 0.0
    s_hi = 100000.0

    L_lo = max(1.0, 0.51 * s)
    L_hi = 100000.0

    return {
        "Ha": np.linspace(Ha_lo, Ha_hi, 500),
        "Hmax": np.linspace(Hmax_lo, Hmax_hi, 500),
        "Hmin": np.linspace(Hmin_lo, Hmin_hi, 500),
        "s": np.linspace(s_lo, s_hi, 500),
        "L": np.linspace(L_lo, L_hi, 500),
    }


def evaluate_derivative_curve(func_name, wrt_param, params):
    domains = make_domains(params)
    xvals = domains[wrt_param]
    yvals = []

    for x in xvals:
        local = params.copy()
        local[wrt_param] = float(x)

        try:
            p = compute_all_partials(
                Ha=local["Ha"],
                Hmax=local["Hmax"],
                Hmin=local["Hmin"],
                s=local["s"],
                L=local["L"],
                summit_nearer=local["summit_nearer"],
                Fv_deg=local["Fv_deg"],
            )
            yvals.append(p[func_name][wrt_param])
        except Exception:
            yvals.append(np.nan)

    return xvals, np.array(yvals)


def plot_all_derivative_curves(params):
    func_names = [
        "afull_rad",
        "ratio_percent",
        "alpha_upper_rad",
        "alpha_lower_rad",
        "amp_upper",
        "amp_lower",
        "amp_ratio",
        "amp_diff_percent",
    ]

    ylabels = {
        "afull_rad": "d(afull_rad)/d(param)",
        "ratio_percent": "d(ratio_percent)/d(param)",
        "alpha_upper_rad": "d(alpha_upper_rad)/d(param)",
        "alpha_lower_rad": "d(alpha_lower_rad)/d(param)",
        "amp_upper": "d(amp_upper)/d(param)",
        "amp_lower": "d(amp_lower)/d(param)",
        "amp_ratio": "d(amp_ratio)/d(param)",
        "amp_diff_percent": "d(amp_diff_percent)/d(param)",
    }

    for wrt_param in PARAM_ORDER:
        fig, axes = plt.subplots(4, 2, figsize=(14, 16))
        axes = axes.flatten()

        for ax, fname in zip(axes, func_names):
            x, y = evaluate_derivative_curve(fname, wrt_param, params)

            if wrt_param in ["L", "s"]:
                x_plot = x / 1000.0
                xlabel = f"{wrt_param} (km)"
            else:
                x_plot = x
                xlabel = f"{wrt_param} (m)"

            ax.plot(x_plot, y, linewidth=1.8)
            ax.axhline(0.0, linewidth=0.8)
            ax.set_title(f"{fname} wrt {wrt_param}")
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabels[fname])
            ax.grid(True, alpha=0.3)

        fig.suptitle(
            f"Partial derivative curves with respect to {wrt_param}", fontsize=14
        )
        plt.tight_layout()
        plt.show()


def main():
    print("===============================================")
    print(" 山体视角 / 放大比例 / 偏导 / n等分相对放大率 ")
    print("===============================================")

    use_manual = input("是否手动输入参数？输入 y / n : ").strip().lower()

    if use_manual == "y":
        Ha = float(input("人的海拔 Ha (m) = "))
        Hmax = float(input("山顶海拔 Hmax (m) = "))
        Hmin = float(input("山脚海拔 Hmin (m) = "))
        s = float(input("山顶到山脚水平距离 s (m) = "))
        L = float(input("人到山体水平中点距离 L (m) = "))

        mode = input("山顶是否比山脚更靠近你？输入 y / n : ").strip().lower()
        summit_nearer = mode == "y"

        Fv_deg = float(input("参考竖直视野角 Fv_deg (deg) = "))

        params = {
            "Ha": Ha,
            "Hmax": Hmax,
            "Hmin": Hmin,
            "s": s,
            "L": L,
            "summit_nearer": summit_nearer,
            "Fv_deg": Fv_deg,
        }
    else:
        params = DEFAULT_PARAMS.copy()
        print("\n使用默认参数：")
        for k, v in params.items():
            print(f"  {k} = {v}")

    print_derivative_formulas()

    g = compute_geometry(**params)
    print_current_values(g)

    partials = compute_all_partials(**params)
    print_current_partials(partials)

    do_plot = input("是否绘制偏导函数图像？输入 y / n : ").strip().lower()
    if do_plot == "y":
        plot_all_derivative_curves(params)

    do_n_segments = input("\n是否进行 n 等分探索？输入 y / n : ").strip().lower()
    if do_n_segments == "y":
        n = int(input("请输入 n（正整数）= ").strip())

        seg = compute_relative_segment_magnifications(
            Ha=params["Ha"],
            Hmax=params["Hmax"],
            Hmin=params["Hmin"],
            s=params["s"],
            L=params["L"],
            summit_nearer=params["summit_nearer"],
            n=n,
        )

        rel_vec = seg["relative_percent_top_to_bottom"]

        print("\n================ n 等分相对放大比例 ================\n")
        print("说明：从山顶向下排序；最顶段定义为 100%")
        print("relative_percent_top_to_bottom =")
        print(np.array2string(rel_vec, precision=6, separator=", "))


if __name__ == "__main__":
    main()