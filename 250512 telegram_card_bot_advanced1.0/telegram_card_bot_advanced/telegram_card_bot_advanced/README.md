# Telegram 卡牌价格 Bot 高级版

更强的卡牌查询机器人 带漂亮管理后台 支持本地上传背景图片作为页面背景

## 开始
1 复制 `.env.example` 为 `.env` 并填写
2 安装依赖 `pip install -r requirements.txt`
3 启动 `python main.py`
4 打开 http://127.0.0.1:8000 在 外观设置 处上传本地图片 即刻生效

## 亮点
- 后台管理 分类 卡牌字段 系列 编号 稀有度 语言 库存
- 外观设置 上传背景图 保存到 `app/static/uploads`
- 机器人：
  - `/start` 分类导航
  - 名称搜索
  - 发图片回显 `file_id`

## 结构
app/
  admin.py
  bot.py
  config.py
  db.py
  models.py
  server.py
  templates/
    dashboard.html
  static/
    uploads/
main.py
requirements.txt
.env.example
