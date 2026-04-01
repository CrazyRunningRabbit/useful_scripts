# app/admin.py
from fastapi import APIRouter, Depends, Form, UploadFile, File, Request, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from io import BytesIO
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import shutil
from typing import Optional
from difflib import SequenceMatcher

from .db import SessionLocal, Base, engine
from .models import Card, Category, PriceHistory
from pathlib import Path

# ————————————————————————————————————
# ✅ 路径定义（全部基于当前模块位置，顺序正确！）
# ————————————————————————————————————
_APP_DIR = Path(__file__).resolve().parent  # /path/to/app
_STATIC_DIR = _APP_DIR / "static"
_UPLOAD_DIR = _STATIC_DIR / "uploads"
_PIC_DIR = _UPLOAD_DIR / "pic"
_BG_PATH = _UPLOAD_DIR / "_bg.txt"          # 注意：现在 _UPLOAD_DIR 已定义！

# 创建所有必要目录（模块导入时即创建，避免运行时崩溃）
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_PIC_DIR.mkdir(parents=True, exist_ok=True)
(_BG_PATH.parent).mkdir(parents=True, exist_ok=True)  # 确保 _bg.txt 父目录存在

# ————————————————————————————————————
# ✅ 辅助函数：生成前端可用的 URL 路径（从本地 Path → /static/...）
# ————————————————————————————————————
def _to_static_url(local_path: Path) -> Optional[str]:
    """
    将本地文件路径转换为 /static/ 开头的 URL 路径。
    例如：/.../app/static/uploads/pic/foo.jpg → /static/uploads/pic/foo.jpg
    要求 local_path 必须在 _STATIC_DIR 下，否则返回 None。
    """
    try:
        rel = local_path.relative_to(_STATIC_DIR)
        return f"/static/{rel.as_posix()}"
    except ValueError:
        return None

# ————————————————————————————————————
# ✅ 其余代码保持不变，仅修改涉及路径拼接/生成的地方
# ————————————————————————————————————
router = APIRouter()
_TEMPLATES_DIR = _APP_DIR / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _read_bg_path() -> Optional[str]:
    try:
        with open(_BG_PATH, "r", encoding="utf-8") as f:
            p = f.read().strip()
            return p or None
    except Exception:
        return None

def _write_bg_path(path: str):
    # path 是前端传来的 /static/xxx 形式，我们只存它（不需要转换回本地路径）
    # 但为安全，可校验它是否以 /static/uploads/ 开头
    if not path.startswith("/static/uploads/"):
        raise ValueError("Invalid background path")
    with open(_BG_PATH, "w", encoding="utf-8") as f:
        f.write(path)

def _get_or_create_category(db: Session, name: str) -> Category:
    c = db.query(Category).filter(Category.name == name).first()
    if c:
        return c
    c = Category(name=name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def _best_pic_for_name(cn_name: str) -> Optional[str]:
    if not cn_name:
        return None
    try:
        # ✅ 使用 Path 迭代
        files = [f for f in _PIC_DIR.iterdir() if f.is_file()]
    except Exception:
        return None
    if not files:
        return None
    base = str(cn_name).strip()

    for f in files:
        stem = f.stem
        if stem == base or stem.startswith(base):
            return _to_static_url(f)

    best_score = 0.0
    best_file = None
    for f in files:
        stem = f.stem
        score = SequenceMatcher(None, stem, base).ratio()
        if score > best_score:
            best_score = score
            best_file = f
    if best_file and best_score >= 0.6:
        return _to_static_url(best_file)
    return None

# ... 其余路由函数保持不变（如 dashboard, category_new 等）...

# 📌 关键修改点：`upload_bg` 中保存路径 + 生成 URL
@router.post("/appearance/bg")
def upload_bg(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    # 清理文件名（防止路径穿越）
    safe_name = Path(file.filename).name
    if not safe_name:
        safe_name = "bg.jpg"
    
    # 限制扩展名（可选增强安全）
    if not any(safe_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    save_path = _UPLOAD_DIR / safe_name

    # 保存文件
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    file.file.close()

    # ✅ 使用 _to_static_url 转为前端 URL
    web_url = _to_static_url(save_path)
    if not web_url:
        raise HTTPException(status_code=500, detail="Failed to generate static URL")

    _write_bg_path(web_url)
    return RedirectResponse(url="/?ok=1", status_code=303)

# 📌 修改：`_best_pic_for_name` 返回值已确保是 /static/... 格式
# 📌 修改：`card_history_page` 中 img_url 不变（它已是 /card/... 路由）

# ... 其余函数（import, history 等）无需改路径逻辑 ...