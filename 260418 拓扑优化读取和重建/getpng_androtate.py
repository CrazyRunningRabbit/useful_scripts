import argparse
from pathlib import Path

import cv2
import gmsh
import numpy as np
from scipy.interpolate import splprep, splev


def read_grayscale(path):
    path = Path(path)
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return image


def write_png(path, image_bgr):
    path = Path(path)
    ok, encoded = cv2.imencode(path.suffix or ".png", image_bgr)
    if not ok:
        raise OSError(f"Cannot encode image: {path}")
    encoded.tofile(str(path))


def preprocess(image, threshold=200, invert=False, smooth=3, mirror=False):
    if smooth > 0:
        k = smooth if smooth % 2 == 1 else smooth + 1
        image = cv2.GaussianBlur(image, (k, k), 0)

    if invert:
        _, binary = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
    else:
        _, binary = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY_INV)

    if mirror:
        binary = binary[:, binary.shape[1] // 2:]

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    return binary


def extract_main_contour(binary, min_area_ratio=0.01, simplify_eps=1.0):
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("No contours found")

    total_area = binary.shape[0] * binary.shape[1]
    min_area = total_area * min_area_ratio
    valid = [c for c in contours if cv2.contourArea(c) > min_area]
    if not valid:
        raise ValueError(f"No contour is larger than {min_area:.0f} px^2")

    contour = max(valid, key=cv2.contourArea)
    if simplify_eps > 0:
        contour = cv2.approxPolyDP(contour, simplify_eps, True)

    contour = contour.squeeze().astype(float)
    if contour.ndim != 2:
        raise ValueError("Extracted contour is invalid")
    return contour


def extract_main_edge_centers(binary, min_area_ratio=0.01):
    """Use every outer edge cell center as a control point for smoothing."""
    return extract_main_contour(
        binary,
        min_area_ratio=min_area_ratio,
        simplify_eps=0.0,
    )


def extract_upper_edge(binary, simplify_eps=1.0):
    material = binary > 0
    xs = np.flatnonzero(material.any(axis=0))
    if xs.size == 0:
        raise ValueError("No black/material pixels found")

    upper_y = np.array([np.flatnonzero(material[:, x])[0] for x in xs], dtype=float)
    upper = np.column_stack([xs.astype(float), upper_y])

    if simplify_eps > 0 and len(upper) > 2:
        approx = cv2.approxPolyDP(
            upper.astype(np.float32).reshape(-1, 1, 2),
            simplify_eps,
            False,
        )
        upper = approx.reshape(-1, 2).astype(float)

    return upper


def extract_upper_edge_centers(binary):
    """Use every upper edge cell center as a control point for smoothing."""
    material = binary > 0
    xs = np.flatnonzero(material.any(axis=0))
    if xs.size == 0:
        raise ValueError("No black/material pixels found")

    upper_y = np.array([np.flatnonzero(material[:, x])[0] for x in xs], dtype=float)
    return np.column_stack([xs.astype(float), upper_y])


def points_to_physical(points_px, img_shape, width_mm, height_mm):
    h_px, w_px = img_shape[:2]
    sx = width_mm / w_px
    sy = height_mm / h_px

    physical = np.zeros_like(points_px, dtype=float)
    physical[:, 0] = points_px[:, 0] * sx
    physical[:, 1] = (h_px - points_px[:, 1]) * sy
    return physical


def remove_consecutive_duplicates(points, tol=1e-9):
    cleaned = [points[0]]
    for point in points[1:]:
        if np.linalg.norm(point - cleaned[-1]) > tol:
            cleaned.append(point)
    if len(cleaned) > 1 and np.linalg.norm(cleaned[0] - cleaned[-1]) <= tol:
        cleaned.pop()
    return np.array(cleaned, dtype=float)


def build_nonsup_profile(upper_edge_phys, width_mm):
    upper = upper_edge_phys[np.argsort(upper_edge_phys[:, 0])]
    right_x = float(width_mm)

    points = [
        [0.0, 0.0],
        [right_x, 0.0],
        [right_x, float(upper[-1, 1])],
    ]

    if upper[-1, 0] < right_x:
        points.append([float(upper[-1, 0]), float(upper[-1, 1])])

    points.extend([p.tolist() for p in upper[::-1]])

    if upper[0, 0] > 0:
        points.append([0.0, float(upper[0, 1])])

    return remove_consecutive_duplicates(np.array(points, dtype=float))


def fit_nurbs_like_curve(points, closed=False, sample_count=800, smoothing_rms=0.75):
    """Fit a cubic B-spline; this is a NURBS curve with all weights equal to 1."""
    points = remove_consecutive_duplicates(np.asarray(points, dtype=float))
    if len(points) < 4:
        return points

    k = min(3, len(points) - 1)
    s = max(0.0, float(smoothing_rms)) ** 2 * len(points)

    try:
        tck, _ = splprep(
            [points[:, 0], points[:, 1]],
            s=s,
            per=bool(closed),
            k=k,
        )
        u_new = np.linspace(
            0.0,
            1.0,
            max(int(sample_count), 8),
            endpoint=not closed,
        )
        x_new, y_new = splev(u_new, tck)
        fitted = np.column_stack([x_new, y_new])
        fitted[:, 0] = np.maximum(fitted[:, 0], 0.0)
        return remove_consecutive_duplicates(fitted)
    except Exception as exc:
        print(f"spline fitting failed, using original points: {exc}")
        return points


def add_line_sequence(point_tags):
    line_tags = []
    n = len(point_tags)
    for i in range(n):
        p1 = point_tags[i]
        p2 = point_tags[(i + 1) % n]
        if p1 != p2:
            line_tags.append(gmsh.model.occ.addLine(p1, p2))
    return line_tags


def add_closed_spline_sequence(point_tags, segment_count=8):
    curve_tags = []
    n = len(point_tags)
    if n < 4:
        return add_line_sequence(point_tags)

    segment_count = max(1, min(int(segment_count), n // 3))
    split_indices = np.linspace(0, n, segment_count + 1, dtype=int)

    for i in range(segment_count):
        start = int(split_indices[i])
        end = int(split_indices[i + 1])

        if i == segment_count - 1:
            segment_tags = point_tags[start:n] + [point_tags[0]]
        else:
            segment_tags = point_tags[start:end + 1]

        if len(segment_tags) >= 4:
            try:
                curve_tags.append(gmsh.model.occ.addSpline(segment_tags))
            except Exception as exc:
                print(f"gmsh spline segment failed, using lines: {exc}")
                for j in range(len(segment_tags) - 1):
                    curve_tags.append(
                        gmsh.model.occ.addLine(segment_tags[j], segment_tags[j + 1])
                    )
        else:
            for j in range(len(segment_tags) - 1):
                curve_tags.append(
                    gmsh.model.occ.addLine(segment_tags[j], segment_tags[j + 1])
                )

    return curve_tags


def export_revolved_step(profile_points, output_path, angle_deg=360, use_spline=False):
    output_path = Path(output_path)
    gmsh.initialize()
    try:
        gmsh.model.add(output_path.stem)
        profile_points = remove_consecutive_duplicates(np.asarray(profile_points, dtype=float))

        point_tags = [
            gmsh.model.occ.addPoint(float(x), float(y), 0.0)
            for x, y in profile_points
        ]

        if use_spline and len(point_tags) >= 4:
            line_tags = add_closed_spline_sequence(point_tags)
        else:
            line_tags = add_line_sequence(point_tags)

        loop = gmsh.model.occ.addCurveLoop(line_tags)
        surface = gmsh.model.occ.addPlaneSurface([loop])

        angle_rad = float(angle_deg) * np.pi / 180.0
        gmsh.model.occ.revolve([(2, surface)], 0, 0, 0, 0, 1, 0, angle_rad)
        gmsh.model.occ.synchronize()
        gmsh.write(str(output_path))
    finally:
        gmsh.finalize()


def export_nonsup_revolved_step(upper_edge_phys, output_path, width_mm,
                                angle_deg=360, use_top_spline=False):
    output_path = Path(output_path)
    upper = upper_edge_phys[np.argsort(upper_edge_phys[:, 0])]
    upper = remove_consecutive_duplicates(upper)
    right_x = float(width_mm)

    gmsh.initialize()
    try:
        gmsh.model.add(output_path.stem)

        bottom_left = gmsh.model.occ.addPoint(0.0, 0.0, 0.0)
        bottom_right = gmsh.model.occ.addPoint(right_x, 0.0, 0.0)
        right_top = gmsh.model.occ.addPoint(right_x, float(upper[-1, 1]), 0.0)

        curve_tags = [
            gmsh.model.occ.addLine(bottom_left, bottom_right),
            gmsh.model.occ.addLine(bottom_right, right_top),
        ]

        top_tags = []
        if upper[-1, 0] < right_x:
            upper_right = gmsh.model.occ.addPoint(
                float(upper[-1, 0]),
                float(upper[-1, 1]),
                0.0,
            )
            curve_tags.append(gmsh.model.occ.addLine(right_top, upper_right))
            top_tags.append(upper_right)
        else:
            top_tags.append(right_top)

        for x, y in upper[-2::-1]:
            top_tags.append(gmsh.model.occ.addPoint(float(x), float(y), 0.0))

        if use_top_spline and len(top_tags) >= 4:
            curve_tags.append(gmsh.model.occ.addSpline(top_tags))
        else:
            for i in range(len(top_tags) - 1):
                curve_tags.append(gmsh.model.occ.addLine(top_tags[i], top_tags[i + 1]))

        curve_tags.append(gmsh.model.occ.addLine(top_tags[-1], bottom_left))

        loop = gmsh.model.occ.addCurveLoop(curve_tags)
        surface = gmsh.model.occ.addPlaneSurface([loop])

        angle_rad = float(angle_deg) * np.pi / 180.0
        gmsh.model.occ.revolve([(2, surface)], 0, 0, 0, 0, 1, 0, angle_rad)
        gmsh.model.occ.synchronize()
        gmsh.write(str(output_path))
    finally:
        gmsh.finalize()


def save_profile_preview(binary, contour_px, upper_px, nonsup_profile_phys,
                         img_shape, width_mm, height_mm, output_prefix):
    h, w = binary.shape[:2]
    preview = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    contour_i = np.round(contour_px).astype(np.int32).reshape(-1, 1, 2)
    upper_i = np.round(upper_px).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(preview, [contour_i], True, (0, 0, 255), 1)
    cv2.polylines(preview, [upper_i], False, (0, 255, 255), 2)

    phys = nonsup_profile_phys.copy()
    phys[:, 0] = phys[:, 0] / width_mm * w
    phys[:, 1] = h - phys[:, 1] / height_mm * h
    phys_i = np.round(phys).astype(np.int32).reshape(-1, 1, 2)
    overlay = preview.copy()
    cv2.fillPoly(overlay, [phys_i], (80, 180, 255))
    preview = cv2.addWeighted(overlay, 0.35, preview, 0.65, 0)
    cv2.polylines(preview, [phys_i], True, (255, 80, 0), 2)

    write_png(f"{output_prefix}_nonsup_profile_preview.png", preview)


def output_with_suffix(output_path, suffix):
    output_path = Path(output_path)
    return output_path.with_name(f"{output_path.stem}{suffix}{output_path.suffix}")


def main():
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", default=str(script_dir / "image.png"))
    parser.add_argument("-o", "--output", default="part.step")
    parser.add_argument("-W", "--width", type=float, default=None)
    parser.add_argument("-H", "--height", type=float, default=None)
    parser.add_argument("--angle", type=float, default=360)
    parser.add_argument("--smooth", type=int, default=3)
    parser.add_argument("--simplify", type=float, default=1.0)
    parser.add_argument("--threshold", type=int, default=200)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--mirror", action="store_true")
    parser.add_argument("--min-area", type=float, default=0.01)
    parser.add_argument("--nurbs-points", type=int, default=800)
    parser.add_argument("--nurbs-smoothing", type=float, default=1.75)
    parser.add_argument("--no-preview", action="store_true")
    args = parser.parse_args()

    image = read_grayscale(args.input)
    binary = preprocess(
        image,
        threshold=args.threshold,
        invert=args.invert,
        smooth=args.smooth,
        mirror=args.mirror,
    )

    if args.width is None:
        args.width = float(binary.shape[1])
    if args.height is None:
        args.height = float(binary.shape[0])

    contour_px = extract_main_contour(
        binary,
        min_area_ratio=args.min_area,
        simplify_eps=args.simplify,
    )
    contour_phys = points_to_physical(
        contour_px,
        binary.shape,
        args.width,
        args.height,
    )

    upper_edge_px = extract_upper_edge(binary, simplify_eps=args.simplify)
    upper_edge_phys = points_to_physical(
        upper_edge_px,
        binary.shape,
        args.width,
        args.height,
    )
    nonsup_profile = build_nonsup_profile(upper_edge_phys, args.width)

    main_edge_centers_px = extract_main_edge_centers(
        binary,
        min_area_ratio=args.min_area,
    )
    main_edge_centers_phys = points_to_physical(
        main_edge_centers_px,
        binary.shape,
        args.width,
        args.height,
    )
    upper_edge_centers_px = extract_upper_edge_centers(binary)
    upper_edge_centers_phys = points_to_physical(
        upper_edge_centers_px,
        binary.shape,
        args.width,
        args.height,
    )
    smooth_contour_phys = fit_nurbs_like_curve(
        main_edge_centers_phys,
        closed=True,
        sample_count=args.nurbs_points,
        smoothing_rms=args.nurbs_smoothing,
    )
    smooth_upper_edge_phys = fit_nurbs_like_curve(
        upper_edge_centers_phys,
        closed=False,
        sample_count=args.nurbs_points,
        smoothing_rms=args.nurbs_smoothing,
    )
    nonsup_smooth_profile = build_nonsup_profile(smooth_upper_edge_phys, args.width)

    output_path = Path(args.output)
    nonsup_path = output_with_suffix(output_path, "_nonsup")
    smooth_path = output_with_suffix(output_path, "_smooth")
    nonsup_smooth_path = output_with_suffix(output_path, "_nonsup_smooth")

    print(f"image size: {binary.shape[1]} x {binary.shape[0]} px")
    print(f"physical size: {args.width:.3f} x {args.height:.3f} mm")
    print(f"main contour points: {len(contour_phys)}")
    print(f"upper edge points: {len(upper_edge_phys)}")
    print(f"nonsup profile points: {len(nonsup_profile)}")
    print(f"smooth main control points: {len(main_edge_centers_phys)}")
    print(f"smooth upper control points: {len(upper_edge_centers_phys)}")
    print(f"smooth main fitted points: {len(smooth_contour_phys)}")
    print(f"smooth nonsup profile points: {len(nonsup_smooth_profile)}")

    export_revolved_step(contour_phys, output_path, args.angle)
    print(f"exported: {output_path}")

    export_nonsup_revolved_step(
        upper_edge_phys,
        nonsup_path,
        args.width,
        args.angle,
        use_top_spline=False,
    )
    print(f"exported: {nonsup_path}")

    export_revolved_step(
        smooth_contour_phys,
        smooth_path,
        args.angle,
        use_spline=False,
    )
    print(f"exported: {smooth_path}")

    export_nonsup_revolved_step(
        smooth_upper_edge_phys,
        nonsup_smooth_path,
        args.width,
        args.angle,
        use_top_spline=True,
    )
    print(f"exported: {nonsup_smooth_path}")

    if not args.no_preview:
        output_prefix = str(output_path.with_suffix(""))
        save_profile_preview(
            binary,
            contour_px,
            upper_edge_px,
            nonsup_profile,
            binary.shape,
            args.width,
            args.height,
            output_prefix,
        )
        print(f"preview: {output_prefix}_nonsup_profile_preview.png")


if __name__ == "__main__":
    main()
