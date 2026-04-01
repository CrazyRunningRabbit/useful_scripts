import math


def compute_display_metrics(
    res_x: int,
    res_y: int,
    diagonal_inch: float,
    viewing_distance_m: float,
    aspect_w: float = 16,
    aspect_h: float = 9,
) -> dict:
    """
    计算显示器的视角与 PPD（pixels per degree）。

    参数
    ----------
    res_x : int
        水平分辨率，例如 3840
    res_y : int
        垂直分辨率，例如 2160
    diagonal_inch : float
        屏幕对角线尺寸，单位：英寸，例如 32
    viewing_distance_m : float
        观看距离，单位：米，例如 0.5
    aspect_w : float
        屏幕宽高比的宽，默认 16
    aspect_h : float
        屏幕宽高比的高，默认 9

    返回
    -------
    dict
        包含视角、PPD、屏幕宽高、像素间距等信息
    """

    if res_x <= 0 or res_y <= 0:
        raise ValueError("分辨率必须为正整数。")
    if diagonal_inch <= 0:
        raise ValueError("屏幕对角线尺寸必须大于 0。")
    if viewing_distance_m <= 0:
        raise ValueError("观看距离必须大于 0。")
    if aspect_w <= 0 or aspect_h <= 0:
        raise ValueError("宽高比必须大于 0。")

    # 英寸转米
    diagonal_m = diagonal_inch * 0.0254

    # 根据宽高比求实际宽高
    aspect_diag = math.sqrt(aspect_w**2 + aspect_h**2)
    width_m = diagonal_m * aspect_w / aspect_diag
    height_m = diagonal_m * aspect_h / aspect_diag

    # 视角计算公式
    fov_h_deg = 2 * math.degrees(math.atan(width_m / (2 * viewing_distance_m)))
    fov_v_deg = 2 * math.degrees(math.atan(height_m / (2 * viewing_distance_m)))
    fov_d_deg = 2 * math.degrees(math.atan(diagonal_m / (2 * viewing_distance_m)))

    # PPD
    ppd_h = res_x / fov_h_deg
    ppd_v = res_y / fov_v_deg
    diagonal_pixels = math.sqrt(res_x**2 + res_y**2)
    ppd_d = diagonal_pixels / fov_d_deg

    # 像素间距
    pixel_pitch_x_mm = width_m / res_x * 1000
    pixel_pitch_y_mm = height_m / res_y * 1000

    # 单像素角宽（近似）
    pixel_angle_x_arcmin = math.degrees(math.atan((width_m / res_x) / viewing_distance_m)) * 60
    pixel_angle_y_arcmin = math.degrees(math.atan((height_m / res_y) / viewing_distance_m)) * 60

    return {
        "width_m": width_m,
        "height_m": height_m,
        "diagonal_m": diagonal_m,
        "fov_h_deg": fov_h_deg,
        "fov_v_deg": fov_v_deg,
        "fov_d_deg": fov_d_deg,
        "ppd_h": ppd_h,
        "ppd_v": ppd_v,
        "ppd_d": ppd_d,
        "pixel_pitch_x_mm": pixel_pitch_x_mm,
        "pixel_pitch_y_mm": pixel_pitch_y_mm,
        "pixel_angle_x_arcmin": pixel_angle_x_arcmin,
        "pixel_angle_y_arcmin": pixel_angle_y_arcmin,
    }


def pretty_print_metrics(metrics: dict) -> None:
    print("\n===== 计算结果 =====")
    print(f"屏幕实际宽度: {metrics['width_m']:.4f} m")
    print(f"屏幕实际高度: {metrics['height_m']:.4f} m")
    print(f"屏幕对角线:   {metrics['diagonal_m']:.4f} m")

    print("\n--- 三个视角 ---")
    print(f"水平视角: {metrics['fov_h_deg']:.2f}°")
    print(f"垂直视角: {metrics['fov_v_deg']:.2f}°")
    print(f"对角视角: {metrics['fov_d_deg']:.2f}°")

    print("\n--- 各方向 PPD ---")
    print(f"水平 PPD: {metrics['ppd_h']:.2f} px/deg")
    print(f"垂直 PPD: {metrics['ppd_v']:.2f} px/deg")
    print(f"对角 PPD: {metrics['ppd_d']:.2f} px/deg")

    print("\n--- 像素间距 ---")
    print(f"水平像素间距: {metrics['pixel_pitch_x_mm']:.4f} mm")
    print(f"垂直像素间距: {metrics['pixel_pitch_y_mm']:.4f} mm")

    print("\n--- 单像素对应角宽 ---")
    print(f"水平单像素角宽: {metrics['pixel_angle_x_arcmin']:.3f} arcmin")
    print(f"垂直单像素角宽: {metrics['pixel_angle_y_arcmin']:.3f} arcmin")


if __name__ == "__main__":
    print("请输入显示器参数：")

    try:
        res_x = int(input("水平分辨率（例如 3840）: ").strip())
        res_y = int(input("垂直分辨率（例如 2160）: ").strip())
        diagonal_inch = float(input("屏幕对角线寸数（例如 32）: ").strip())
        viewing_distance_m = float(input("观看距离，单位米（例如 0.5）: ").strip())

        aspect_input = input("宽高比（默认 16:9，可直接回车）: ").strip()
        if aspect_input == "":
            aspect_w, aspect_h = 16, 9
        else:
            parts = aspect_input.split(":")
            if len(parts) != 2:
                raise ValueError("宽高比格式错误，应为如 16:9")
            aspect_w = float(parts[0])
            aspect_h = float(parts[1])

        metrics = compute_display_metrics(
            res_x=res_x,
            res_y=res_y,
            diagonal_inch=diagonal_inch,
            viewing_distance_m=viewing_distance_m,
            aspect_w=aspect_w,
            aspect_h=aspect_h,
        )

        pretty_print_metrics(metrics)

    except Exception as e:
        print(f"\n输入或计算出错: {e}")