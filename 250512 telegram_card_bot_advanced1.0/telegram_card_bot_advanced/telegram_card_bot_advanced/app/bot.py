# app/bot.py
import os
import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType, FSInputFile
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import Category, Card
from aiogram.types import ChatMemberUpdated

# =============== DB 会话 ===============
def get_db() -> Session:
    return SessionLocal()

# =============== 文案 ===============
def fmt_price(p: float) -> str:
    try:
        return f"{float(p):.2f}"
    except Exception:
        return "0.00"


WELCOME_TEXT = (
    "Hello, PokePeach here～\n"
)



def display_name(card: Card) -> str:
    """
    同时存在中文与英文时优先显示英文名
    只有其一时返回存在的那个
    """
    cn = (card.name or "").strip()
    en = (card.lang or "").strip()
    if en and cn:
        return en
    return en or cn

def build_caption(card: Card) -> str:
    title = display_name(card) or "(未命名)"
    parts = [f"<b>{title}</b>", f"价格：{fmt_price(card.price)}"]
    if card.category:
        parts.append(f"类别：{card.category.name}")
    if card.series:
        parts.append(f"系列：{card.series}")
    if card.code:
        parts.append(f"编号：{card.code}")
    if card.rarity:
        parts.append(f"稀有度：{card.rarity}")
    return "\n".join(parts)

# =============== 内联键盘 ===============
def category_keyboard(db: Session) -> InlineKeyboardMarkup:
    buttons = []
    for c in db.query(Category).order_by(Category.name).all():
        buttons.append([InlineKeyboardButton(text=c.name, callback_data=f"cat:{c.id}")])
    if not buttons:
        buttons = [[InlineKeyboardButton(text="暂无分类", callback_data="noop")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cards_keyboard(cat_id: int, db: Session) -> InlineKeyboardMarkup:
    buttons = []
    for card in db.query(Card).filter(Card.category_id == cat_id).order_by(Card.name).all():
        shown = display_name(card) or card.name or ""
        price = fmt_price(card.price)
        buttons.append([InlineKeyboardButton(text=f"{shown} • {price}", callback_data=f"card:{card.id}")])
    buttons.append([InlineKeyboardButton(text="返回分类", callback_data="back:cats")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# =============== 本地图像候选 ===============
PIC_DIR = os.path.join("app", "static", "uploads", "pic")

def _candidate_paths(card_name: str):
    if not card_name:
        return
    stems = [
        card_name,
        card_name.replace(" ", ""),
        card_name.replace("（", "(").replace("）", ")"),
    ]
    exts = [".jpg", ".jpeg", ".png", ".webp"]
    for s in stems:
        for e in exts:
            yield os.path.join(PIC_DIR, f"{s}{e}")
    # 前缀兜底
    try:
        for f in os.listdir(PIC_DIR):
            stem, _ = os.path.splitext(f)
            if stem.startswith(card_name):
                yield os.path.join(PIC_DIR, f)
    except FileNotFoundError:
        return

# =============== 发送卡图：优先 file_id 其次本地上传并回写 file_id 最后纯文字 ===============
async def send_card_photo(message: Message, card: Card):
    caption = build_caption(card)

    # 1) 有 file_id 直接用
    if card.image_file_id:
        await message.answer_photo(card.image_file_id, caption=caption)
        return

    # 2) 找本地图 上传一次并把 file_id 写回库
    for p in _candidate_paths(card.name or ""):
        if os.path.isfile(p):
            msg = await message.answer_photo(FSInputFile(p), caption=caption)
            try:
                fid = msg.photo[-1].file_id
                with SessionLocal() as db:
                    obj: Card = db.get(Card, card.id)
                    if obj:
                        obj.image_file_id = fid
                        db.commit()
            except Exception:
                pass
            return

    # 3) 无图就发纯文字
    await message.answer(caption + "\n（暂缺图片）")

# =============== 绑定本地图像为 file_id（批量） ===============
router = Router()

@router.message(Command("bind_pics"))
async def bind_pics(message: Message):
    count_try = 0
    count_ok = 0
    with SessionLocal() as db:
        cards = db.query(Card).order_by(Card.id.asc()).all()
        for c in cards:
            if c.image_file_id:
                continue
            sent = False
            for p in _candidate_paths(c.name or ""):
                if os.path.isfile(p):
                    count_try += 1
                    msg = await message.bot.send_photo(
                        chat_id=message.chat.id,
                        photo=FSInputFile(p),
                        caption=f"绑定：{display_name(c) or c.name}"
                    )
                    try:
                        fid = msg.photo[-1].file_id
                        obj: Card = db.get(Card, c.id)
                        if obj:
                            obj.image_file_id = fid
                            db.commit()
                            count_ok += 1
                            sent = True
                    except Exception:
                        pass
                    # 不保留现场消息 防刷屏 可按需注释掉
                    try:
                        await message.bot.delete_message(message.chat.id, msg.message_id)
                    except Exception:
                        pass
                    break
    await message.answer(f"尝试 {count_try} 张 成功 {count_ok} 张")

# =============== 常用指令 ===============
@router.message(Command("start"))
async def start(m: Message):
    db = get_db()
    try:
        text = "欢迎使用卡牌价格助手\n请选择分类或发送关键词搜索"
        await m.answer(text, reply_markup=category_keyboard(db))
    finally:
        db.close()

@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer("发送卡牌名称进行搜索 可以先用 /bind_pics 绑定图片 file_id 发送一张图片也会回显它的 file_id")

@router.message(F.content_type == ContentType.PHOTO)
async def echo_file_id(m: Message):
    file_id = m.photo[-1].file_id
    await m.answer(f"图片 file_id：\n<code>{file_id}</code>\n复制到对应卡牌的 image_file_id 即可秒发")

# =============== 文本搜索 ===============
@router.message()
async def search(m: Message):
    q = (m.text or "").strip()
    if not q:
        return
    db = get_db()
    try:
        results = (
            db.query(Card)
            .filter(Card.name.ilike(f"%{q}%"))
            .order_by(Card.name)
            .limit(10)
            .all()
        )
        if not results:
            await m.answer("没有找到匹配的卡牌")
            return

        for card in results:
            await send_card_photo(m, card)
    finally:
        db.close()

# =============== 回调交互 ===============
@router.callback_query(F.data == "back:cats")
async def back_cats(c: CallbackQuery):
    db = get_db()
    try:
        await c.message.edit_text("请选择分类", reply_markup=category_keyboard(db))
        await c.answer()
    finally:
        db.close()

@router.callback_query(F.data.startswith("cat:"))
async def open_cat(c: CallbackQuery):
    _, sid = c.data.split(":")
    cat_id = int(sid)
    db = get_db()
    try:
        cat = db.get(Category, cat_id)
        if not cat:
            await c.answer("分类不存在", show_alert=True)
            return
        await c.message.edit_text(f"类别：{cat.name}\n选择卡牌", reply_markup=cards_keyboard(cat_id, db))
        await c.answer()
    finally:
        db.close()

@router.callback_query(F.data.startswith("card:"))
async def show_card(c: CallbackQuery):
    _, sid = c.data.split(":")
    card_id = int(sid)
    db = get_db()
    try:
        card = db.get(Card, card_id)
        if not card:
            await c.answer("未找到", show_alert=True)
            return
        # 删除原消息再发图 体验更好
        try:
            await c.message.delete()
        except Exception:
            pass
        await send_card_photo(c.message, card)
        await c.answer()
    finally:
        db.close()

# =============== 启动 ===============
async def setup_bot():
    # v3 正确初始化 使用 default=DefaultBotProperties(parse_mode="HTML")
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()
    dp.include_router(router)
    return dp, bot


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, bot: Bot):
    chat = event.chat
    old = event.old_chat_member
    new = event.new_chat_member

    # 私聊用户首次启用机器人
    try:
        is_private = (chat.type == "private")
    except Exception:
        is_private = False

    if is_private:
        if getattr(old, "status", "") in {"kicked", "left"} and getattr(new, "status", "") == "member":
            await bot.send_message(chat.id, WELCOME_TEXT)
            # 顺便给分类键盘
            db = get_db()
            try:
                await bot.send_message(chat.id, "请选择分类或直接发送卡牌名", reply_markup=category_keyboard(db))
            finally:
                db.close()
            return

    # 机器人被加进群或超群时打招呼
    if chat.type in {"group", "supergroup"}:
        if getattr(old, "status", "") in {"kicked", "left"} and getattr(new, "status", "") in {"member", "administrator"}:
            await bot.send_message(chat.id, "Hello everyone! I’m the PokePeach Bot. My database is constantly expanding, and I’m currently in closed beta. Feel free to share what card-search features you’d like to see!")



async def run_bot():
    dp, bot = await setup_bot()
    await dp.start_polling(bot)
