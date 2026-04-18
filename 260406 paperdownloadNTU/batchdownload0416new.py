#!/usr/bin/env python3
"""
batch_download_papers.py — NTU RemoteXS 批量下载论文 PDF（最终整合版）

安装:
    pip install selenium webdriver-manager

运行:
    python batch_download_papers.py
"""

import os
import re
import time
import sys
from pathlib import Path

DOWNLOAD_DIR = Path(__file__).parent / "papers"
DELAY = 5
TIMEOUT = 45
MAX_RETRY = 2

DOIS = [
    "10.1016/j.compfluid.2022.105561", 
# Moscatelli et al. 2022
 "10.1016/j.cma.2023.116058", # Moscatelli et al. 2023
"10.1016/j.ijmecsci.2025.110603", # Moscatelli et al. 2025

]

# 按你的要求，明确跳过 MDPI
SKIP_MDPI = True


def doi_to_filename(doi: str) -> str:
    return doi.replace("/", "_").replace(".", "-") + ".pdf"


def doi_to_remotexs_url(doi: str) -> str:
    """
    统一使用这个入口，不再混用 doi-org.remotexs.ntu.edu.sg/<doi>
    避免部分 DOI 被 RemoteXS 直接打成 'DOI Not Found'
    """
    target = f"https://doi.org/{doi}"
    return f"https://remotexs.ntu.edu.sg/user/login?dest={target}"


def wait_for_download(dl_dir: Path, before_count: int, timeout: int = TIMEOUT) -> bool:
    """
    等待本地下载完成：
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
    判断当前页面是否已经像 PDF 页面。
    即使 Chrome 没有真正把文件落到本地，也允许视为成功。
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


def manual_login(driver):
    """
    不再在命令行输入用户名密码。
    直接打开 RemoteXS 登录页，让用户在浏览器中手动登录并完成 2FA。
    """
    driver.get("https://remotexs.ntu.edu.sg/user/login")
    print("\n" + "=" * 60)
    print("  Please log into NTU RemoteXS in the browser")
    print("  Complete 2FA if needed, then press Enter here")
    print("=" * 60)
    input("  >>> Press Enter after login <<<\n")


def debug_page(driver):
    try:
        print(f"           current_url: {driver.current_url}")
    except Exception as e:
        print(f"           current_url read failed: {e}")

    try:
        print(f"           title: {driver.title}")
    except Exception as e:
        print(f"           title read failed: {e}")

    try:
        src = driver.page_source[:1600].replace("\n", " ").replace("\r", " ")
        print(f"           page head: {src[:1000]}")
    except Exception as e:
        print(f"           page_source read failed: {e}")


def try_open_sciencedirect_pdf(driver, url: str) -> bool:
    """
    Elsevier / ScienceDirect
    优先尝试 /pdfft
    """
    if "sciencedirect" not in url:
        return False

    m = re.search(r"/pii/([A-Z0-9]+)", url, re.IGNORECASE)
    if not m:
        print("           sciencedirect detected but PII not found")
        return False

    pii = m.group(1)
    pdf_url = f"https://www-sciencedirect-com.remotexs.ntu.edu.sg/science/article/pii/{pii}/pdfft"
    print(f"           elsevier pdf: {pdf_url[:140]}")
    driver.get(pdf_url)
    time.sleep(6)

    cur = (driver.current_url or "").lower()
    if "ref=cra_js_challenge" in cur:
        print("           elsevier challenge page detected")
        return False

    return True


def try_open_science_pdf(driver, url: str) -> bool:
    """
    AAAS / Science / Science Advances / Science Robotics
    """
    if "science-org" not in url and "science.org" not in url:
        return False

    if "/doi/pdf/" in url:
        return True

    if "/doi/" in url:
        pdf_url = url.replace("/doi/", "/doi/pdf/")
        print(f"           science pdf: {pdf_url[:140]}")
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
        print(f"           wiley pdfdirect: {pdf_url[:140]}")
        driver.get(pdf_url)
        time.sleep(6)
        return True

    return False


def try_open_sage_pdf(driver, url: str) -> bool:
    """
    Sage 平台常见 PDF 入口：
    /doi/xxxx -> /doi/pdf/xxxx
    """
    if "sagepub" not in url:
        return False

    if "/doi/pdf/" in url:
        return True

    if "/doi/" in url:
        pdf_url = url.replace("/doi/", "/doi/pdf/")
        print(f"           sage pdf: {pdf_url[:140]}")
        driver.get(pdf_url)
        time.sleep(6)
        return True

    return False


def try_click_download_buttons(driver) -> bool:
    """
    针对没有 href 的按钮型 PDF 入口做兜底。
    """
    from selenium.webdriver.common.by import By

    xpaths = [
        "//a[contains(translate(., 'PDF', 'pdf'), 'pdf')]",
        "//button[contains(translate(., 'PDF', 'pdf'), 'pdf')]",
        "//a[contains(@aria-label, 'PDF') or contains(@title, 'PDF')]",
        "//button[contains(@aria-label, 'PDF') or contains(@title, 'PDF')]",
    ]

    for xp in xpaths:
        try:
            elems = driver.find_elements(By.XPATH, xp)
            for elem in elems:
                txt = (elem.text or "").lower()
                if any(bad in txt for bad in ["supp", "supplement", "supporting", "appendix"]):
                    continue
                try:
                    print("           clicking PDF-like button")
                    driver.execute_script("arguments[0].click();", elem)
                    time.sleep(6)
                    return True
                except Exception:
                    continue
        except Exception:
            continue

    return False


def try_get_pdf(driver, doi: str) -> bool:
    """
    在当前页面寻找 PDF。
    返回 True 表示已经尝试跳去 PDF 页或点击 PDF 入口，
    最终是否成功由 download_one 再判定。
    """
    from selenium.webdriver.common.by import By

    url = driver.current_url
    print(f"           page: {url[:140]}")

    # MDPI 按你的要求直接跳过
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

    # 4. Sage
    if try_open_sage_pdf(driver, url):
        return True

    # 5. IEEE Xplore
    if "ieeexplore" in url:
        m = re.search(r"/document/(\d+)", url)
        if m:
            base = re.match(r"(https?://[^/]+)", url).group(1)
            stamp = f"{base}/stamp/stamp.jsp?tp=&arnumber={m.group(1)}"
            print(f"           stamp: {stamp[:140]}")
            driver.get(stamp)
            time.sleep(6)

            try:
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                for frame in frames:
                    src = frame.get_attribute("src")
                    if src and "pdf" in src.lower():
                        print(f"           iframe: {src[:140]}")
                        driver.get(src)
                        time.sleep(5)
                        return True
            except Exception:
                pass

            return True

    # 6. 通用 href / button 规则
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

                bad_words = ["supp", "supplement", "supporting", "appendix"]
                if href and any(w in href.lower() for w in bad_words):
                    continue
                if any(w in text for w in bad_words):
                    continue
                if any(w in title for w in bad_words):
                    continue
                if any(w in aria for w in bad_words):
                    continue

                if href:
                    print(f"           generic pdf: {href[:140]}")
                    driver.get(href)
                    time.sleep(5)
                    return True

                try:
                    print("           clicking generic PDF-like element")
                    driver.execute_script("arguments[0].click();", elem)
                    time.sleep(5)
                    return True
                except Exception:
                    continue
        except Exception:
            continue

    # 7. 最后再试按钮点击
    if try_click_download_buttons(driver):
        return True

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

    if SKIP_MDPI and doi.startswith("10.3390/"):
        print(f"  [{idx:2d}/{total}] SKIP  {doi}  (MDPI intentionally skipped)")
        return True

    # 所有 DOI 统一从这个入口走
    url = doi_to_remotexs_url(doi)

    before = len(list(dl_dir.glob("*.pdf")))
    print(f"  [{idx:2d}/{total}] GET   {doi}")

    driver.get(url)
    time.sleep(8)

    tried = try_get_pdf(driver, doi)

    # 情况 1：成功下载到本地
    if wait_for_download(dl_dir, before):
        rename_newest_pdf(dl_dir, fname)
        print(f"           ✓ {fname}")
        return True

    cur = (driver.current_url or "").lower()

    # 情况 2：Elsevier challenge，切人工接管
    if "sciencedirect" in cur and "ref=cra_js_challenge" in cur:
        print("           Elsevier challenge page detected")
        print("           Please solve it manually in the browser or click PDF once, then press Enter here")
        input("           >>> Press Enter to continue <<< ")

        if wait_for_download(dl_dir, before, timeout=TIMEOUT):
            rename_newest_pdf(dl_dir, fname)
            print(f"           ✓ {fname}")
            return True

        if current_page_looks_like_pdf(driver):
            print("           PDF page opened after manual intervention")
            print("           Treating as success")
            return True

        print("           ✗ FAILED (Elsevier challenge still blocked download)")
        debug_page(driver)
        return False

    # 情况 3：虽然没落盘，但当前页已经像 PDF
    if tried and current_page_looks_like_pdf(driver):
        print("           PDF page opened but no new local file detected")
        print("           Treating as success")
        return True

    # 情况 4：失败
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

    driver = setup_driver(DOWNLOAD_DIR)

    try:
        print("\n  Opening NTU RemoteXS login page...")
        manual_login(driver)

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