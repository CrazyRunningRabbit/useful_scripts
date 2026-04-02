"""
=============================================================================
金属增材制造(AM) 逐层热-力耦合仿真 —— 正方体算例
Layer-by-layer Thermo-Mechanical AM Simulation (FEniCS / legacy dolfin)

  物理场:  瞬态温度场(T) → 准静态力学场(u)  [顺序弱耦合]
  材料沉积: Quiet Element 法 (生死单元, 缩放因子 1e-6)
  本构:    热弹性 (默认) 或 J2 von Mises + 线性各向同性硬化
  算例:    10×10×10 mm 正方体, 逐层打印在 10×10×5 mm 基板上

  运行:  python am_cube.py
  依赖:  FEniCS 2019.1.0 (legacy dolfin), numpy
  输出:  am_results/ 目录下 XDMF 文件 (ParaView 可视化)
=============================================================================
"""
from __future__ import print_function
from dolfin import *
import numpy as np
import os, json

parameters["form_compiler"]["cpp_optimize"] = True
parameters["form_compiler"]["representation"] = "uflacs"
set_log_level(30)

# ═══════════════════════════════════════════════════════════
#  参数定义
# ═══════════════════════════════════════════════════════════

# ── 几何 (m) ──
Lx, Ly    = 10e-3, 10e-3     # 正方体 xy 边长
H_part    = 10e-3             # 零件高度
H_sub     = 5e-3              # 基板厚度
N_layers  = 10                # 打印层数
dz_layer  = H_part / N_layers # 每层厚度

# ── 网格 ──
Nx, Ny    = 10, 10
Nz_sub    = 5
Nz_part   = N_layers          # 每层恰好1个单元
Nz        = Nz_sub + Nz_part

# ── 材料 (IN718 简化) ──
k_s       = 20.0              # 导热系数 [W/(m·K)]
rho_s     = 8190.0            # 密度 [kg/m³]
cp_s      = 435.0             # 比热容 [J/(kg·K)]
E_s       = 200e9             # 弹性模量 [Pa]
nu_s      = 0.3               # 泊松比
alpha_s   = 1.3e-5            # 热膨胀系数 [1/K]
sig_y0    = 600e6             # 屈服强度 [Pa]
H_iso     = 2.0e9             # 各向同性硬化模量 [Pa]

QUIET     = 1e-6              # quiet element 缩放
mu_s      = E_s / (2*(1+nu_s))
lam_s     = E_s * nu_s / ((1+nu_s)*(1-2*nu_s))

# ── 工艺 ──
T_amb     = 25.0              # 环境温度 [°C]
T_pre     = 200.0             # 基板预热 [°C]
T_dep     = 1300.0            # 沉积温度 [°C]
h_conv    = 15.0              # 对流系数 [W/(m²·K)]

# ── 时间步进 ──
dt        = 0.05              # 冷却步长 [s]
N_cool    = 20                # 每层冷却步数

# ── 开关 ──
USE_PLASTICITY = False        # True → J2弹塑性, False → 纯热弹性

# ── 输出 ──
outdir = "am_results"
os.makedirs(outdir, exist_ok=True)

# ═══════════════════════════════════════════════════════════
#  网格 & 函数空间
# ═══════════════════════════════════════════════════════════
mesh = BoxMesh(Point(0, 0, -H_sub), Point(Lx, Ly, H_part), Nx, Ny, Nz)

V_T   = FunctionSpace(mesh, "CG", 1)             # 标量 - 温度
V_u   = VectorFunctionSpace(mesh, "CG", 1)       # 矢量 - 位移
W_DG0 = FunctionSpace(mesh, "DG", 0)             # 分片常数 - 材料

print("="*60)
print(f" AM热变形仿真 | {Lx*1e3:.0f}×{Ly*1e3:.0f}×{H_part*1e3:.0f}mm 正方体")
print(f" 基板{H_sub*1e3:.0f}mm | {N_layers}层×{dz_layer*1e3:.1f}mm")
print(f" 网格: {mesh.num_vertices()} nodes, {mesh.num_cells()} cells")
print(f" 本构: {'J2弹塑性' if USE_PLASTICITY else '热弹性'}")
print("="*60)

# ═══════════════════════════════════════════════════════════
#  Quiet Element 工具
# ═══════════════════════════════════════════════════════════

# 每个单元的"所属层号": 基板=-1, 零件层=0..N_layers-1
cell_z     = np.array([c.midpoint().z() for c in cells(mesh)])
cell_layer = np.where(cell_z < 0, -1,
                      np.clip((cell_z / dz_layer).astype(int), 0, N_layers-1))

def set_field(func, val_active, val_quiet, max_layer):
    """按层激活状态设置 DG0 场"""
    v = func.vector().get_local()
    active = cell_layer <= max_layer
    v[active]  = val_active
    v[~active] = val_quiet
    func.vector().set_local(v)
    func.vector().apply("insert")

# 材料属性 DG0
kappa = Function(W_DG0, name="k")
rho_f = Function(W_DG0, name="rho")
cp_f  = Function(W_DG0, name="cp")
E_f   = Function(W_DG0, name="E")
act_f = Function(W_DG0, name="active")

# ═══════════════════════════════════════════════════════════
#  边界条件
# ═══════════════════════════════════════════════════════════

class BotFace(SubDomain):
    """基板底面 z = -H_sub"""
    def inside(self, x, on_boundary):
        return on_boundary and near(x[2], -H_sub, 1e-8)

class ConvFaces(SubDomain):
    """除底面外的所有外表面"""
    def inside(self, x, on_boundary):
        return on_boundary and not near(x[2], -H_sub, 1e-8)

bnd_mark = MeshFunction("size_t", mesh, 2, 0)
BotFace().mark(bnd_mark, 1)
ConvFaces().mark(bnd_mark, 2)
ds = Measure("ds", domain=mesh, subdomain_data=bnd_mark)

bc_T = DirichletBC(V_T, Constant(T_pre), BotFace())
bc_u = DirichletBC(V_u, Constant((0,0,0)), BotFace())

# ═══════════════════════════════════════════════════════════
#  温度场求解
# ═══════════════════════════════════════════════════════════

T_n = Function(V_T, name="T_prev")
T_h = Function(V_T, name="T")
w_T = TestFunction(V_T)

# 初始温度
T_n.interpolate(Expression("x[2]<0 ? Tp : Ta", Tp=T_pre, Ta=T_amb, degree=0))
T_h.assign(T_n)

def thermal_form():
    """瞬态热传导 + 对流边界"""
    return (
        rho_f * cp_f * (T_h - T_n) / Constant(dt) * w_T * dx
      + kappa * dot(grad(T_h), grad(w_T)) * dx
      + Constant(h_conv) * (T_h - Constant(T_amb)) * w_T * ds(2)
    )

def deposit_layer_temp(layer):
    """新层节点温度设为 T_dep"""
    arr = T_h.vector().get_local()
    coords = V_T.tabulate_dof_coordinates()
    z_lo = layer * dz_layer - 1e-8
    z_hi = (layer + 1) * dz_layer + 1e-8
    mask = (coords[:, 2] >= z_lo) & (coords[:, 2] <= z_hi)
    arr[mask] = T_dep
    T_h.vector().set_local(arr)
    T_h.vector().apply("insert")
    T_n.assign(T_h)

def solve_thermal(layer):
    """一层: 沉积 + 冷却"""
    set_field(kappa, k_s, k_s*QUIET, layer)
    set_field(rho_f, rho_s, rho_s*QUIET, layer)
    set_field(cp_f,  cp_s, cp_s*QUIET, layer)

    deposit_layer_temp(layer)

    F = thermal_form()
    J = derivative(F, T_h, TrialFunction(V_T))
    prob = NonlinearVariationalProblem(F, T_h, bcs=[bc_T], J=J)
    slv  = NonlinearVariationalSolver(prob)
    slv.parameters["newton_solver"]["linear_solver"] = "mumps"
    slv.parameters["newton_solver"]["relative_tolerance"] = 1e-8

    for _ in range(N_cool):
        slv.solve()
        T_n.assign(T_h)

    return T_h.vector().min(), T_h.vector().max()

# ═══════════════════════════════════════════════════════════
#  力学场求解
# ═══════════════════════════════════════════════════════════

u_h = Function(V_u, name="displacement")
w_u = TestFunction(V_u)

T_ref = Function(V_T, name="T_ref")
T_ref.interpolate(Constant(T_amb))

def eps_fn(u):
    return sym(grad(u))

def sigma_elas(eps_m, E_loc):
    """各向同性线弹性 Hooke 定律"""
    mu  = E_loc / (2*(1+nu_s))
    lam = E_loc * nu_s / ((1+nu_s)*(1-2*nu_s))
    return lam * tr(eps_m) * Identity(3) + 2*mu * eps_m

# ── 塑性内变量 (DG0 简化) ──
if USE_PLASTICITY:
    W_t = TensorFunctionSpace(mesh, "DG", 0)
    sig_n   = Function(W_t, name="stress")
    eps_p_n = Function(W_t, name="eps_plastic")
    p_n     = Function(W_DG0, name="p_cumul")

def return_mapping_update(layer):
    """
    J2 von Mises return mapping (全局 DG0 级别)

    步骤:
    1. 投影当前总应变 ε(u) 到 DG0
    2. 弹性预估: σ_trial = C : (ε_total - ε_thermal - ε_plastic_old)
    3. 屈服判断: f = σ_eq - (σ_y0 + H·p_old)
    4. 若 f>0: Δp = f/(3μ+H), 更新 σ, ε_p, p
    """
    # 投影总应变
    eps_proj = project(eps_fn(u_h), W_t)
    e_arr = eps_proj.vector().get_local().reshape(-1, 9)

    # 投影热应变标量
    T_DG = project(T_h, W_DG0)
    Tref_DG = project(T_ref, W_DG0)
    dT_arr = T_DG.vector().get_local() - Tref_DG.vector().get_local()

    s_arr  = sig_n.vector().get_local().reshape(-1, 9)
    ep_arr = eps_p_n.vector().get_local().reshape(-1, 9)
    p_arr  = p_n.vector().get_local()

    nc = len(p_arr)
    s_new  = np.zeros_like(s_arr)
    ep_new = np.zeros_like(ep_arr)
    p_new  = np.zeros_like(p_arr)

    I3 = np.eye(3)
    n_yield = 0

    for i in range(nc):
        if cell_layer[i] > layer:
            continue  # quiet → skip

        eps_tot = e_arr[i].reshape(3, 3)
        eps_th  = alpha_s * dT_arr[i] * I3
        eps_p   = ep_arr[i].reshape(3, 3)

        # 弹性试应变 & 试应力
        eps_e_tr = eps_tot - eps_th - eps_p
        tr_e = np.trace(eps_e_tr)
        sig_tr = lam_s * tr_e * I3 + 2*mu_s * eps_e_tr

        # 偏应力 & 等效应力
        sig_m   = np.trace(sig_tr) / 3.0
        s_dev   = sig_tr - sig_m * I3
        sig_eq  = np.sqrt(1.5 * np.sum(s_dev**2))

        f_trial = sig_eq - (sig_y0 + H_iso * p_arr[i])

        if f_trial <= 0:
            # 弹性
            s_new[i]  = sig_tr.flatten()
            ep_new[i] = eps_p.flatten()
            p_new[i]  = p_arr[i]
        else:
            # 塑性 return mapping
            n_yield += 1
            dp = f_trial / (3*mu_s + H_iso)
            n_dir = s_dev / (sig_eq + 1e-30)

            sig_corrected = sig_tr - 3*mu_s * dp * n_dir
            eps_p_new_i   = eps_p + 1.5 * dp * n_dir

            s_new[i]  = sig_corrected.flatten()
            ep_new[i] = eps_p_new_i.flatten()
            p_new[i]  = p_arr[i] + dp

    sig_n.vector().set_local(s_new.flatten());     sig_n.vector().apply("insert")
    eps_p_n.vector().set_local(ep_new.flatten());  eps_p_n.vector().apply("insert")
    p_n.vector().set_local(p_new);                 p_n.vector().apply("insert")
    return n_yield

def reset_plasticity(layer):
    """新层退火: 应力=0, 塑性应变=0"""
    s  = sig_n.vector().get_local().reshape(-1, 9)
    ep = eps_p_n.vector().get_local().reshape(-1, 9)
    p  = p_n.vector().get_local()
    mask = cell_layer == layer
    s[mask]  = 0; ep[mask] = 0; p[mask] = 0
    sig_n.vector().set_local(s.flatten());    sig_n.vector().apply("insert")
    eps_p_n.vector().set_local(ep.flatten()); eps_p_n.vector().apply("insert")
    p_n.vector().set_local(p);                p_n.vector().apply("insert")

def solve_mechanical(layer):
    """力学平衡求解"""
    set_field(E_f, E_s, E_s*QUIET, layer)

    eps_th = alpha_s * (T_h - T_ref) * Identity(3)
    eps_m  = eps_fn(u_h) - eps_th
    sig    = sigma_elas(eps_m, E_f)

    F = inner(sig, eps_fn(w_u)) * dx
    J = derivative(F, u_h, TrialFunction(V_u))

    prob = NonlinearVariationalProblem(F, u_h, bcs=[bc_u], J=J)
    slv  = NonlinearVariationalSolver(prob)
    slv.parameters["newton_solver"]["linear_solver"] = "mumps"
    slv.parameters["newton_solver"]["relative_tolerance"] = 1e-8
    slv.parameters["newton_solver"]["maximum_iterations"] = 50

    if USE_PLASTICITY:
        reset_plasticity(layer)
        # 固定点迭代: 弹性求解 → return mapping → 重复
        for fp in range(8):
            slv.solve()
            ny = return_mapping_update(layer)
            if ny == 0:
                break
        return ny
    else:
        slv.solve()
        return 0

# ═══════════════════════════════════════════════════════════
#  后处理: von Mises 应力
# ═══════════════════════════════════════════════════════════

def von_mises_from_u(layer):
    """从位移场计算 von Mises 等效应力"""
    set_field(E_f, E_s, E_s*QUIET, layer)
    eps_th = alpha_s * (T_h - T_ref) * Identity(3)
    eps_m  = eps_fn(u_h) - eps_th
    sig    = sigma_elas(eps_m, E_f)
    s = sig - tr(sig)/3 * Identity(3)
    vm = sqrt(1.5 * inner(s, s))
    return project(vm, W_DG0)

# ═══════════════════════════════════════════════════════════
#  主循环
# ═══════════════════════════════════════════════════════════

xf_T = XDMFFile(os.path.join(outdir, "temperature.xdmf"))
xf_u = XDMFFile(os.path.join(outdir, "displacement.xdmf"))
xf_v = XDMFFile(os.path.join(outdir, "vonmises.xdmf"))
xf_a = XDMFFile(os.path.join(outdir, "active.xdmf"))
for xf in [xf_T, xf_u, xf_v, xf_a]:
    xf.parameters["flush_output"] = True

results = []

print("\n" + "─"*60)

for L in range(N_layers):
    z_lo = L * dz_layer * 1e3
    z_hi = (L+1) * dz_layer * 1e3
    print(f"\n Layer {L+1}/{N_layers}  z=[{z_lo:.1f}, {z_hi:.1f}] mm")

    # (1) 激活标记
    set_field(act_f, 1.0, 0.0, L)

    # (2) 热分析
    Tmin, Tmax = solve_thermal(L)
    print(f"   热场: T=[{Tmin:.0f}, {Tmax:.0f}] °C")

    # (3) 力学分析
    ny = solve_mechanical(L)
    umax = np.max(np.abs(u_h.vector().get_local()))
    pmax = p_n.vector().max() if USE_PLASTICITY else 0.0
    print(f"   力学: |u|_max={umax*1e6:.2f} μm"
          + (f", 屈服单元={ny}, p_max={pmax:.5f}" if USE_PLASTICITY else ""))

    # (4) von Mises
    vm = von_mises_from_u(L)
    vm_max = vm.vector().max()
    print(f"   σ_vm_max = {vm_max/1e6:.1f} MPa")

    # (5) 输出
    t = float(L+1)
    xf_T.write(T_h, t)
    xf_u.write(u_h, t)
    xf_v.write(vm,  t)
    xf_a.write(act_f, t)

    results.append(dict(
        layer=L+1, z_mm=z_hi,
        Tmin=round(Tmin,1), Tmax=round(Tmax,1),
        u_um=round(umax*1e6, 2),
        vm_MPa=round(vm_max/1e6, 1),
        p_max=round(pmax, 6)
    ))

# ── 基板移除回弹 ──
print(f"\n{'━'*50}")
print(" 基板移除 → 回弹")
# 把基板层号改成 9999 使其变 quiet
cell_layer[cell_layer == -1] = 9999
set_field(E_f, E_s, E_s*QUIET, N_layers-1)
# 基板单元手动 quiet
earr = E_f.vector().get_local()
earr[cell_layer == 9999] = E_s * QUIET
E_f.vector().set_local(earr); E_f.vector().apply("insert")

# 新BC: 零件底面(z=0)约束z, 角点约束xyz
class ZeroZ(SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary and near(x[2], 0.0, 1e-8)
class Corner(SubDomain):
    def inside(self, x, on_boundary):
        return near(x[0],0,1e-6) and near(x[1],0,1e-6) and near(x[2],0,1e-6)

bc_sb = [
    DirichletBC(V_u.sub(2), Constant(0.0), ZeroZ()),
    DirichletBC(V_u, Constant((0,0,0)), Corner(), "pointwise"),
]

eps_th = alpha_s * (T_h - T_ref) * Identity(3)
sig = sigma_elas(eps_fn(u_h) - eps_th, E_f)
F = inner(sig, eps_fn(w_u)) * dx
J = derivative(F, u_h, TrialFunction(V_u))
prob = NonlinearVariationalProblem(F, u_h, bcs=bc_sb, J=J)
slv = NonlinearVariationalSolver(prob)
slv.parameters["newton_solver"]["linear_solver"] = "mumps"
slv.solve()

u_sb = np.max(np.abs(u_h.vector().get_local()))
print(f" 回弹: |u|_max = {u_sb*1e6:.2f} μm")
xf_u.write(u_h, float(N_layers+1))

for xf in [xf_T, xf_u, xf_v, xf_a]:
    xf.close()

# ── 汇总 ──
print("\n" + "="*60)
print(f"{'L':>3} | {'z':>5} | {'Tmin':>5} | {'Tmax':>5} | {'|u|':>8} | {'σ_vm':>7}"
      + (" | p_max" if USE_PLASTICITY else ""))
print("-"*55)
for r in results:
    line = (f"{r['layer']:>3} | {r['z_mm']:>5.1f} | {r['Tmin']:>5.0f} | "
            f"{r['Tmax']:>5.0f} | {r['u_um']:>7.2f}μ | {r['vm_MPa']:>6.1f}M")
    if USE_PLASTICITY:
        line += f" | {r['p_max']:.5f}"
    print(line)
print(f"\n回弹变形: {u_sb*1e6:.2f} μm")

with open(os.path.join(outdir, "summary.json"), "w") as f:
    json.dump(dict(results=results, springback_um=round(u_sb*1e6,2)), f, indent=2)

print(f"结果: {outdir}/  (ParaView打开 .xdmf)")
