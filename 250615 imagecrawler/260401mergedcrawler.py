"""
喜马拉雅图片爬虫 — 整合版
合并自 0615crawlermultianti.py 与 0615crawler2_0.py，
取两者之长并补充：
  - safe_filename 清洗（来自 2_0）
  - 完整 targets 列表（来自 multi）
  - 全局 Session 复用（新增）
  - 下载计数 & 跳过/失败统计（新增）
  - 已下载文件去重（新增）
  - 可选日志写文件（新增）
"""

import os
import re
import random
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from time import sleep
import urllib3

# ────────────────────────────────────────
# 基础配置
# ────────────────────────────────────────

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 日志：同时输出到终端和文件
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crawl.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ────────────────────────────────────────
# 反爬配置
# ────────────────────────────────────────

PROXIES = [
    None,
    # "http://127.0.0.1:7890",  # 按需添加
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/110.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
]

SKIP_LIST = {"button_home.jpg", "icon_back.jpg", "logo.jpg", "button_no.jpg"}

IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp"}

# 随机延迟范围（秒）
DELAY_MIN, DELAY_MAX = 1.2, 3.5
RETRY_DELAY_MIN, RETRY_DELAY_MAX = 1.5, 4.0

# ────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────

def safe_filename(name: str) -> str:
    """清除 Windows/Linux 下的非法文件名字符"""
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.replace("+", "_")
    return name


def is_image_filename(fname: str) -> bool:
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    return ext in IMAGE_EXTS


def get_headers(referer: str) -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": referer,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }


def get_proxy():
    proxy = random.choice(PROXIES)
    return {"http": proxy, "https": proxy} if proxy else None


def wait_random(lo: float = DELAY_MIN, hi: float = DELAY_MAX):
    delay = random.uniform(lo, hi)
    log.debug(f"[等待] {delay:.2f}s")
    sleep(delay)


# ────────────────────────────────────────
# 核心逻辑
# ────────────────────────────────────────

class ImageCrawler:
    """带状态的爬虫：Session 复用、去重、统计"""

    def __init__(self):
        self.session = requests.Session()
        self.downloaded = set()          # 全局已下载 URL 去重
        self.stats = {"saved": 0, "skipped": 0, "failed": 0}

    # ---------- 下载单张图片 ----------
    def download_image(self, img_url: str, save_dir: str, referer: str, retries: int = 3):
        full_url = urljoin(referer, img_url)

        # 去重
        if full_url in self.downloaded:
            log.debug(f"[跳过-重复] {full_url}")
            self.stats["skipped"] += 1
            return

        filename = safe_filename(os.path.basename(urlparse(full_url).path))

        if filename in SKIP_LIST or not is_image_filename(filename):
            self.stats["skipped"] += 1
            return

        save_dir = safe_filename(save_dir)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        headers = get_headers(referer)
        proxy = get_proxy()

        for attempt in range(1, retries + 1):
            try:
                resp = self.session.get(
                    full_url, headers=headers, proxies=proxy,
                    timeout=10, verify=False,
                )
                resp.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(resp.content)

                size_kb = len(resp.content) / 1024
                log.info(f"[保存成功] {filename} ({size_kb:.1f} KB) → {save_dir}")
                self.downloaded.add(full_url)
                self.stats["saved"] += 1
                return
            except Exception as e:
                log.warning(f"[失败 - 第 {attempt} 次] {filename} → {e}")
                wait_random(RETRY_DELAY_MIN, RETRY_DELAY_MAX)

        log.error(f"[最终失败] {filename}")
        self.stats["failed"] += 1

    # ---------- 抓取单个页面 ----------
    def crawl_page(self, page_url: str, save_dir: str):
        save_dir = safe_filename(save_dir)
        os.makedirs(save_dir, exist_ok=True)

        headers = get_headers(page_url)
        proxy = get_proxy()

        try:
            wait_random()
            resp = self.session.get(
                page_url, headers=headers, proxies=proxy,
                timeout=10, verify=False,
            )
            resp.raise_for_status()
        except Exception as e:
            log.error(f"[页面请求失败] {page_url} → {e}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")

        for img in soup.find_all("img"):
            parent = img.parent
            # 优先取 <a> 链接里的高清大图
            if parent.name == "a" and parent.get("href"):
                href = parent["href"]
                fname = os.path.basename(urlparse(href).path)
                if is_image_filename(fname) and fname not in SKIP_LIST:
                    self.download_image(href, save_dir, page_url)
                    wait_random()
                    continue

            src = img.get("src")
            if src:
                self.download_image(src, save_dir, page_url)
                wait_random()

    # ---------- 运行全部任务 ----------
    def run(self, targets):
        for i, target in enumerate(targets, 1):
            url = target["url"]
            folder = safe_filename(target["folder"])
            log.info(f"\n{'='*50}")
            log.info(f"[{i}/{len(targets)}] 🔍 抓取: {url}")
            log.info(f"{'='*50}")
            self.crawl_page(url, folder)

        log.info(f"\n✅ 全部完成  |  "
                 f"保存: {self.stats['saved']}  "
                 f"跳过: {self.stats['skipped']}  "
                 f"失败: {self.stats['failed']}")


# ────────────────────────────────────────
# 任务列表（来自 0615crawlermultianti.py 完整列表）
# ────────────────────────────────────────

TARGETS = [
    {"url": "https://www.himalaya-info.org/himalaya-flug.htm",              "folder": "Flight Garhwal to Bhutan"},
    {"url": "https://www.himalaya-info.org/Khumbu_Helicopter.htm",          "folder": "Khumbu_Helicopter"},
    {"url": "https://www.himalaya-info.org/Langtang_helicopter.htm",        "folder": "Langtang_helicopter"},
    {"url": "https://www.himalaya-info.org/annapurna_helicopter.htm",       "folder": "annapurna_helicopter"},
    {"url": "https://www.himalaya-info.org/flug%20delhi-leh.htm",           "folder": "Flight delhi to leh"},
    {"url": "https://www.himalaya-info.org/Parchamo.htm",                   "folder": "Parchamo"},
    {"url": "https://www.himalaya-info.org/tengkangboche_panorama.htm",     "folder": "tengkangboche_panorama"},
    {"url": "https://www.himalaya-info.org/kyajo_ri.htm",                   "folder": "kyajo_ri"},
    {"url": "https://www.himalaya-info.org/Lobuche%20East-panorama.htm",    "folder": "Lobuche_East-panorama"},
    {"url": "https://www.himalaya-info.org/ama_dablam_panorama.htm",        "folder": "ama_dablam_panorama"},
    {"url": "https://www.himalaya-info.org/mera_peak.htm",                  "folder": "Mera_peak_panorama"},
    {"url": "https://www.himalaya-info.org/lhotse-nuptse_panorama.htm",     "folder": "lhotse-nuptse_panorama"},
    {"url": "https://www.himalaya-info.org/Everest_Panorama.htm",           "folder": "Everest_Panorama"},
    {"url": "https://www.himalaya-info.org/island_peak.htm",                "folder": "island_peak"},
    {"url": "https://www.himalaya-info.org/baruntse-panorama.htm",          "folder": "baruntse-panorama"},
    {"url": "https://www.himalaya-info.org/makalu_panorama.htm",            "folder": "makalu_panorama"},
    {"url": "https://www.himalaya-info.org/kangchenjunga_panorama.htm",     "folder": "kangchenjunga_panorama"},
]

# ────────────────────────────────────────
# 入口
# ────────────────────────────────────────

if __name__ == "__main__":
    crawler = ImageCrawler()
    crawler.run(TARGETS)