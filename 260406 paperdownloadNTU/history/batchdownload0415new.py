#!/usr/bin/env python3
"""
batch_download_papers.py — NTU RemoteXS 批量下载论文PDF

安装:
    pip install selenium webdriver-manager

运行:
    python batch_download_papers.py
"""

import os
import re
import time
import sys
import getpass
from pathlib import Path

DOWNLOAD_DIR = Path(__file__).parent / "papers"
DELAY = 5
TIMEOUT = 45
MAX_RETRY = 2

NTU_USERNAME = "minda002"  # 留空则运行时输入

DOIS =  [
    # hasel
    "10.1007/s00158-019-02421-5",       # Moscatelli & Silva 2020 (SMO)
    "10.1016/j.ijmecsci.2025.110603",   # Moscatelli et al. 2025 (IJMS)
   
]

# 明确跳过 MDPI
SKIP_MDPI = True


def doi_to_filename(doi: str) -> str:
    return doi.replace("/", "_").replace(".", "-") + ".pdf"


def doi_to_remotexs_url(doi: str) -> str:
    """DOI -> NTU RemoteXS proxy URL"""
    target = f"https://doi.org/{doi}"
    return f"https://remotexs.ntu.edu.sg/user/login?dest={target}"


def wait_for_download(dl_dir: Path, before_count: int, timeout: int = TIMEOUT) -> bool:
    """
    等待本地下载完成。
    条件：
      1. pdf 文件数量增加
      2. 没有临时下载文件
    """
    t0 = time.time()
    while time.time() - t0 < timeout:
        temps = list(dl_dir.glob("*.crdownload")) + list(dl_dir.glob("*.tmp"))
        pdfs = list(dl_dir.glob("*.pdf"))
        if len(pdfs) > before_count and not temps:
            return True
        time.sleep(1)
    return False


def current_page_looks_like_pdf(driver) -> bool:
    """
    判断当前页面是否已经是 PDF 页面，即使浏览器没有自动下载到本地。
    """
    try:
        cur = (driver.current_url or "").lower()
    except Exception:
        cur = ""

    try:
        title = (driver.title or "").lower()
    except Exception:
        title = ""

    if ".pdf" in cur or "/pdf" in cur or "pdfft" in cur:
        return True
    if "pdf" in title:
        return True

    try:
        src = driver.page_source.lower()
        if "application/pdf" in src:
            return True
        if "<embed" in src and "pdf" in src:
            return True
        if "<iframe" in src and "pdf" in src:
            return True
    except Exception:
        pass

    return False


def setup_driver(dl_dir: Path):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    except ImportError:
        service = None

    opts = Options()
    prefs = {
        "download.default_directory": str(dl_dir.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_settings.popups": 0,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    if service:
        return webdriver.Chrome(service=service, options=opts)
    return webdriver.Chrome(options=opts)


def auto_login(driver, username: str, password: str):
    """自动填写 NTU RemoteXS 登录表单"""
    from selenium.webdriver.common.by import By

    driver.get("https://remotexs.ntu.edu.sg/user/login")
    time.sleep(3)

    for user_sel in [
        "input[name='user']",
        "input[name='username']",
        "input[id='username']",
        "input[type='text']",
    ]:
        try:
            uf = driver.find_element(By.CSS_SELECTOR, user_sel)
            uf.clear()
            uf.send_keys(username)
            break
        except Exception:
            continue

    for pass_sel in [
        "input[name='pass']",
        "input[name='password']",
        "input[id='password']",
        "input[type='password']",
    ]:
        try:
            pf = driver.find_element(By.CSS_SELECTOR, pass_sel)
            pf.clear()
            pf.send_keys(password)
            break
        except Exception:
            continue

    for btn_sel in [
        "input[type='submit']",
        "button[type='submit']",
        "input[value='Login']",
        "input[value='Sign In']",
        "button",
    ]:
        try:
            driver.find_element(By.CSS_SELECTOR, btn_sel).click()
            print("  Auto-login: submitted")
            break
        except Exception:
            continue

    time.sleep(5)


def debug_page(driver):
    """
    失败时打印更有用的调试信息。
    """
    try:
        print(f"           current_url: {driver.current_url}")
    except Exception as e:
        print(f"           current_url read failed: {e}")

    try:
        print(f"           title: {driver.title}")
    except Exception as e:
        print(f"           title read failed: {e}")

    try:
        src = driver.page_source[:1200].replace("\n", " ").replace("\r", " ")
        print(f"           page head: {src[:700]}")
    except Exception as e:
        print(f"           page_source read failed: {e}")


def try_open_sciencedirect_pdf(driver, url: str) -> bool:
    """
    Elsevier / ScienceDirect:
    文章页常见是 /science/article/pii/<PII>
    真正 PDF 常见是 /science/article/pii/<PII>/pdfft
    """
    if "sciencedirect" not in url:
        return False

    m = re.search(r"/pii/([A-Z0-9]+)", url, re.IGNORECASE)
    if not m:
        print("           sciencedirect detected but PII not found")
        return False

    pii = m.group(1)
    pdf_url = f"https://www-sciencedirect-com.remotexs.ntu.edu.sg/science/article/pii/{pii}/pdfft"
    print(f"           elsevier pdf: {pdf_url[:120]}")
    driver.get(pdf_url)
    time.sleep(6)
    return True


def try_open_science_pdf(driver, url: str) -> bool:
    """
    AAAS / Science / Science Advances:
    /doi/xxxx -> /doi/pdf/xxxx
    """
    if "science-org" not in url and "science.org" not in url:
        return False

    if "/doi/pdf/" in url:
        return True

    if "/doi/" in url:
        pdf_url = url.replace("/doi/", "/doi/pdf/")
        print(f"           science pdf: {pdf_url[:120]}")
        driver.get(pdf_url)
        time.sleep(6)
        return True

    return False


def try_open_wiley_pdf(driver, url: str) -> bool:
    """
    Wiley:
    /doi/full/ 或 /doi/abs/ -> /doi/pdfdirect/
    """
    if "onlinelibrary" not in url and "wiley" not in url:
        return False

    pdf_url = re.sub(r"/doi/(full/|abs/)?", "/doi/pdfdirect/", url)
    if pdf_url != url:
        print(f"           wiley pdfdirect: {pdf_url[:120]}")
        driver.get(pdf_url)
        time.sleep(6)
        return True

    return False


def try_open_springer_pdf(driver):
    """
    Springer 常见是 content/pdf 链接，通用策略通常已经能抓到。
    这里先保留占位，不额外强行构造。
    """
    return False


def try_get_pdf(driver, doi: str) -> bool:
    """
    在当前页面寻找 PDF。
    返回 True 仅表示“已经尝试跳去 PDF 页或点击 PDF 入口”，
    最终是否落盘由 download_one 再判断。
    """
    from selenium.webdriver.common.by import By

    url = driver.current_url
    print(f"           page: {url[:140]}")

    # 0. 明确跳过 MDPI
    if SKIP_MDPI and ("mdpi.com" in url or "mdpi-com" in url):
        print("           MDPI skipped intentionally")
        return False

    # 1. Elsevier / ScienceDirect
    if try_open_sciencedirect_pdf(driver, url):
        return True

    # 2. AAAS / Science
    if try_open_science_pdf(driver, url):
        return True

    # 3. Wiley
    if try_open_wiley_pdf(driver, url):
        return True

    # 4. IEEE Xplore
    if "ieeexplore" in url:
        m = re.search(r"/document/(\d+)", url)
        if m:
            base = re.match(r"(https?://[^/]+)", url).group(1)
            stamp = f"{base}/stamp/stamp.jsp?tp=&arnumber={m.group(1)}"
            print(f"           stamp: {stamp[:120]}")
            driver.get(stamp)
            time.sleep(6)
            try:
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                for frame in frames:
                    src = frame.get_attribute("src")
                    if src and "pdf" in src.lower():
                        print(f"           iframe: {src[:120]}")
                        driver.get(src)
                        time.sleep(5)
                        return True
            except Exception:
                pass
            return True
        else:
            print("           IEEE page but no /document/ID found")

    # 5. 更宽松的通用规则
    selectors = [
        "a[href$='.pdf']",
        "a[href*='/pdf']",
        "a[href*='pdf']",
        "a[title*='PDF']",
        "a[aria-label*='PDF']",
        "a[data-track-action*='PDF']",
        "button[title*='PDF']",
        "button[aria-label*='PDF']",
    ]

    for sel in selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for elem in elems:
                href = elem.get_attribute("href")
                text = (elem.text or "").strip().lower()
                title = (elem.get_attribute("title") or "").strip().lower()
                aria = (elem.get_attribute("aria-label") or "").strip().lower()

                # 跳过补充材料
                bad_words = ["supp", "supplement", "supporting", "appendix"]
                if href and any(w in href.lower() for w in bad_words):
                    continue
                if any(w in text for w in bad_words):
                    continue
                if any(w in title for w in bad_words):
                    continue
                if any(w in aria for w in bad_words):
                    continue

                # 优先直接打开 href
                if href:
                    print(f"           generic pdf: {href[:120]}")
                    driver.get(href)
                    time.sleep(5)
                    return True

                # 没 href 就尝试 click
                try:
                    print("           clicking PDF-like button")
                    elem.click()
                    time.sleep(5)
                    return True
                except Exception:
                    continue
        except Exception:
            continue

    print("           no PDF link found on this page")
    return False


def rename_newest_pdf(dl_dir: Path, target_name: str):
    pdfs = list(dl_dir.glob("*.pdf"))
    if not pdfs:
        return
    newest = max(pdfs, key=os.path.getmtime)
    target = dl_dir / target_name
    if newest.resolve() != target.resolve():
        try:
            if target.exists():
                target.unlink()
            newest.rename(target)
        except Exception as e:
            print(f"           rename failed: {e}")


def download_one(driver, doi: str, dl_dir: Path, idx: int, total: int) -> bool:
    fname = doi_to_filename(doi)
    target = dl_dir / fname

    if target.exists():
        print(f"  [{idx:2d}/{total}] SKIP  {doi}")
        return True

    # 如果用户明确不想要 MDPI，按 DOI 先跳过
    if SKIP_MDPI and doi.startswith("10.3390/"):
        print(f"  [{idx:2d}/{total}] SKIP  {doi}  (MDPI intentionally skipped)")
        return True

    # 首篇与后续篇保持你原来的逻辑
    if idx == 1:
        url = doi_to_remotexs_url(doi)
    else:
        url = f"https://doi-org.remotexs.ntu.edu.sg/{doi}"

    before = len(list(dl_dir.glob("*.pdf")))
    print(f"  [{idx:2d}/{total}] GET   {doi}")

    driver.get(url)
    time.sleep(8)

    tried = try_get_pdf(driver, doi)

    # 情况1：成功下载到本地
    if wait_for_download(dl_dir, before):
        rename_newest_pdf(dl_dir, fname)
        print(f"           ✓ {fname}")
        return True

    # 情况2：虽然没落盘，但当前页已经像 PDF
    if tried and current_page_looks_like_pdf(driver):
        print("           PDF page opened but no new local file detected")
        print("           Treating as success")
        return True

    # 情况3：失败，打印调试信息
    print(f"           ✗ FAILED (no new PDF in {TIMEOUT}s)")
    debug_page(driver)
    return False


def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("  NTU RemoteXS Paper Downloader")
    print(f"  {len(DOIS)} papers -> {DOWNLOAD_DIR.resolve()}")
    print("=" * 60)

    try:
        from selenium import webdriver  # noqa: F401
    except ImportError:
        print("\n  Run: pip install selenium webdriver-manager")
        sys.exit(1)

    username = NTU_USERNAME.strip() if NTU_USERNAME else input("\n  NTU Username: ").strip()

    try:
        password = getpass.getpass("  NTU Password: ")
    except KeyboardInterrupt:
        print("\n\n  Cancelled while entering password.")
        sys.exit(1)

    driver = setup_driver(DOWNLOAD_DIR)

    try:
        print("\n  Logging into RemoteXS...")
        auto_login(driver, username, password)

        cur = (driver.current_url or "").lower()
        if any(k in cur for k in ["login", "auth", "duo", "mfa", "factor"]):
            print("\n" + "=" * 60)
            print("  Please complete login/2FA in browser")
            print("  Then press Enter here")
            print("=" * 60)
            input("  >>> Press Enter <<<\n")
        else:
            print("  Login OK!")

        ok = 0
        fail = 0
        failed = []

        for i, doi in enumerate(DOIS, 1):
            done = False
            try:
                for retry in range(MAX_RETRY + 1):
                    if retry > 0:
                        print(f"           retry {retry}/{MAX_RETRY}...")
                        time.sleep(2)

                    if download_one(driver, doi, DOWNLOAD_DIR, i, len(DOIS)):
                        done = True
                        break

            except Exception as e:
                if "invalid session" in str(e).lower() or "disconnected" in str(e).lower():
                    print("\n  Browser was closed. Stopping.")
                    failed.append(doi)
                    failed.extend(DOIS[i:])
                    fail += len(DOIS) - i + 1
                    break
                print(f"           ✗ ERROR: {e}")

            if done:
                ok += 1
            else:
                fail += 1
                failed.append(doi)

            time.sleep(DELAY)

        print(f"\n{'=' * 60}")
        print(f"  Done!  Success: {ok}   Failed: {fail}")
        print(f"  Folder: {DOWNLOAD_DIR.resolve()}")

        if failed:
            print("\n  Failed DOIs:")
            for d in failed:
                print(f"    {d}")
            with open(DOWNLOAD_DIR / "failed.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(failed))

        print(f"{'=' * 60}")

    finally:
        try:
            input("\n  Press Enter to close browser...")
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()