#!/usr/bin/env python3
"""
batch_download_papers.py — NTU EZproxy 一键下载50篇论文PDF

首次: pip install selenium webdriver-manager
运行: python batch_download_papers.py
"""
import os, re, time, sys, getpass
from pathlib import Path

DOWNLOAD_DIR = Path(__file__).parent / "papers"
DELAY = 4
TIMEOUT = 30
MAX_RETRY = 2

# ============================================================
# ★ 在这里填你的NTU账号，密码运行时输入（不写入代码更安全）
# ============================================================
NTU_USERNAME = ""   # 例如 "rabbit001"，留空则运行时提示输入

DOIS = [
    "10.1109/LRA.2018.2800115","10.1109/LRA.2021.3056369","10.1109/LRA.2023.3236883",
    "10.1109/LRA.2017.2669367","10.1109/LRA.2021.3064247","10.1109/LRA.2018.2876734",
    "10.1109/LRA.2022.3147890","10.1109/LRA.2022.3158379","10.1109/LRA.2021.3086425",
    "10.1109/LRA.2021.3070305","10.1109/LRA.2022.3154050","10.1109/LRA.2024.3446287",
    "10.1109/LRA.2024.3490393","10.1109/LRA.2024.3495579","10.1109/LRA.2019.2894424",
    "10.1109/LRA.2019.2898430","10.1109/LRA.2022.3211785","10.1109/LRA.2024.3375086",
    "10.1109/LRA.2022.3146903","10.1109/LRA.2021.3068117","10.1109/LRA.2021.3095268",
    "10.1109/LRA.2018.2859441",
    "10.1002/aisy.202100086","10.1002/aisy.202300505","10.1002/aisy.202000187",
    "10.1002/aisy.202500929","10.1002/aisy.202500400","10.1002/aisy.202100239",
    "10.1002/aisy.202200239","10.1002/aisy.202100006","10.1002/aisy.202000282",
    "10.1002/aisy.202300047","10.1002/aisy.202300865","10.1002/aisy.202100061",
    "10.1002/aisy.202200233","10.1002/aisy.202200435","10.1002/aisy.202000223",
    "10.1002/aisy.202200330","10.1002/aisy.201900171","10.1002/aisy.202400576",
    "10.1002/aisy.202300899","10.1002/aisy.202500696","10.1002/aisy.202100163",
    "10.1002/aisy.202100165","10.1002/aisy.202200023","10.1002/aisy.202500916",
    "10.1002/aisy.202400294","10.1002/aisy.202501204","10.1002/aisy.201900031",
    "10.1002/aisy.202400514",
]

def doi_to_filename(doi):
    return doi.replace("/", "_").replace(".", "-") + ".pdf"

def wait_for_download(dl_dir, before_count, timeout=TIMEOUT):
    t0 = time.time()
    while time.time() - t0 < timeout:
        crdownloads = list(dl_dir.glob("*.crdownload")) + list(dl_dir.glob("*.tmp"))
        pdfs = list(dl_dir.glob("*.pdf"))
        if len(pdfs) > before_count and not crdownloads:
            return True
        time.sleep(1)
    return False

def setup_driver(dl_dir):
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

def auto_login(driver, username, password):
    """自动填写NTU EZproxy登录表单"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver.get("https://login.ezproxy.ntu.edu.sg/login")
    time.sleep(3)

    # EZproxy登录页可能直接是表单，也可能先跳转到NTU SSO
    current = driver.current_url

    # --- 情况1: EZproxy自己的登录表单 ---
    try:
        user_field = driver.find_element(By.CSS_SELECTOR,
            "input[name='user'], input[name='username'], input[id='username'], input[type='text']")
        pass_field = driver.find_element(By.CSS_SELECTOR,
            "input[name='pass'], input[name='password'], input[id='password'], input[type='password']")
        user_field.clear(); user_field.send_keys(username)
        pass_field.clear(); pass_field.send_keys(password)
        # 找提交按钮
        for selector in ["input[type='submit']", "button[type='submit']", "input[value='Login']",
                          "button", "input.btn"]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                btn.click(); break
            except: continue
        print("  Auto-login: credentials submitted")
        time.sleep(5)
        return
    except:
        pass

    # --- 情况2: 跳转到NTU SSO (Microsoft/ADFS) ---
    try:
        user_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                "input[name='loginfmt'], input[name='UserName'], input[type='email']")))
        user_field.clear(); user_field.send_keys(username + "@e.ntu.edu.sg")
        # 点Next
        for selector in ["input[type='submit']", "button[type='submit']", "#idSIButton9"]:
            try: driver.find_element(By.CSS_SELECTOR, selector).click(); break
            except: continue
        time.sleep(3)
        # 输入密码
        pass_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                "input[name='passwd'], input[name='Password'], input[type='password']")))
        pass_field.clear(); pass_field.send_keys(password)
        for selector in ["input[type='submit']", "button[type='submit']", "#idSIButton9"]:
            try: driver.find_element(By.CSS_SELECTOR, selector).click(); break
            except: continue
        print("  Auto-login: SSO credentials submitted")
        time.sleep(5)
        return
    except:
        pass

    print("  Auto-login: could not find login form, please login manually")

def try_get_pdf(driver, doi):
    from selenium.webdriver.common.by import By
    url = driver.current_url
    if "ieeexplore" in url:
        m = re.search(r'/document/(\d+)', url)
        if m:
            stamp = url.split("/document/")[0] + f"/stamp/stamp.jsp?tp=&arnumber={m.group(1)}"
            driver.get(stamp); time.sleep(3)
            try:
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                for frame in frames:
                    src = frame.get_attribute("src")
                    if src and "pdf" in src.lower():
                        driver.get(src); return True
            except: pass
            return True
    if "onlinelibrary" in url and "wiley" in url:
        pdf_url = re.sub(r'/doi/(full/|abs/)?', '/doi/pdfdirect/', url)
        if pdf_url != url:
            driver.get(pdf_url); return True
        try:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='pdfdirect'], a[href*='epdf']")
            for link in links:
                href = link.get_attribute("href")
                if href: driver.get(href); return True
        except: pass
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href$='.pdf'], a[title*='PDF']")
        for link in links:
            href = link.get_attribute("href")
            if href and "pdf" in href.lower():
                link.click(); return True
    except: pass
    return False

def download_one(driver, doi, dl_dir, idx, total):
    fname = doi_to_filename(doi)
    target = dl_dir / fname
    if target.exists():
        print(f"  [{idx:2d}/{total}] SKIP  {doi}")
        return True
    url = f"https://doi-org.ezproxy.ntu.edu.sg/{doi}"
    before = len(list(dl_dir.glob("*.pdf")))
    print(f"  [{idx:2d}/{total}] GET   {doi}")
    driver.get(url); time.sleep(3)
    try_get_pdf(driver, doi); time.sleep(2)
    if wait_for_download(dl_dir, before):
        newest = max(dl_dir.glob("*.pdf"), key=os.path.getmtime)
        if newest.name != fname:
            newest.rename(dl_dir / fname)
        print(f"           ✓ {fname}")
        return True
    print(f"           ✗ FAILED")
    return False

def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    print("=" * 60)
    print(f"  NTU EZproxy Paper Downloader")
    print(f"  {len(DOIS)} papers → {DOWNLOAD_DIR.resolve()}")
    print("=" * 60)

    try:
        from selenium import webdriver
    except ImportError:
        print("\n  Run: pip install selenium webdriver-manager")
        sys.exit(1)

    # ---- 获取账号密码 ----
    username = NTU_USERNAME
    if not username:
        username = input("\n  NTU Username (e.g. rabbit001): ").strip()
    password = getpass.getpass("  NTU Password: ")

    driver = setup_driver(DOWNLOAD_DIR)

    try:
        # ---- 自动登录 ----
        print("\n  Logging in...")
        auto_login(driver, username, password)

        # ---- 检查是否需要2FA ----
        time.sleep(3)
        current = driver.current_url
        if "duo" in current.lower() or "mfa" in current.lower() or "factor" in current.lower():
            print("\n" + "=" * 60)
            print("  2FA detected — please approve on your phone")
            print("  Then press Enter here")
            print("=" * 60)
            input("  >>> Press Enter after 2FA <<<\n")
        elif "login" in current.lower():
            # 还在登录页，可能登录失败或需要手动操作
            print("\n  Still on login page. Please complete login manually.")
            input("  >>> Press Enter when logged in <<<\n")
        else:
            print("  Login successful!")
            time.sleep(1)

        # ---- 逐篇下载 ----
        ok, fail = 0, 0
        failed = []
        for i, doi in enumerate(DOIS, 1):
            done = False
            for retry in range(MAX_RETRY + 1):
                if retry > 0:
                    print(f"           retry ({retry}/{MAX_RETRY})...")
                    time.sleep(2)
                if download_one(driver, doi, DOWNLOAD_DIR, i, len(DOIS)):
                    done = True; break
            if done: ok += 1
            else: fail += 1; failed.append(doi)
            time.sleep(DELAY)

        # ---- 报告 ----
        print(f"\n{'=' * 60}")
        print(f"  Done!  Success: {ok}   Failed: {fail}")
        print(f"  Folder: {DOWNLOAD_DIR.resolve()}")
        if failed:
            print(f"\n  Failed DOIs:")
            for d in failed: print(f"    {d}")
            with open(DOWNLOAD_DIR / "failed.txt", 'w') as f:
                f.write('\n'.join(failed))
        print(f"{'=' * 60}")

    finally:
        input("\n  Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    main()