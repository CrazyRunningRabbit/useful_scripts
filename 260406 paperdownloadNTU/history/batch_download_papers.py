#!/usr/bin/env python3
"""
batch_download_papers.py — NTU RemoteXS 一键下载50篇论文PDF

pip install selenium webdriver-manager
python batch_download_papers.py
"""
import os, re, time, sys, getpass
from pathlib import Path

DOWNLOAD_DIR = Path(__file__).parent / "papers"
DELAY = 5
TIMEOUT = 30
MAX_RETRY = 2

NTU_USERNAME = "minda002"  # 填你的NTU用户名，留空则运行时输入
###############################################################在这里复制
DOIS =  [
    # Moscatelli 系列
    "10.1007/s00158-019-02421-5",       # Moscatelli & Silva 2020 (SMO)
    "10.1016/j.ijmecsci.2025.110603",   # Moscatelli et al. 2025 (IJMS)
    # Ortigosa 电活性聚合物 TO 系列
    "10.1007/s00158-021-02886-3",       # Ortigosa et al. 2021 - EAP TO
    "10.1007/s00158-021-03047-2",       # Ortigosa 2021 - DE stiffener layout
    "10.1007/s00158-025-04117-5",       # Wallin et al. 2025 - electrode+EAP layout
    # 软体机器人 TO 前沿
    "10.1126/sciadv.adn6129",           # Sato/Kobayashi 2024 - locomotive soft robots (Science Adv)
    "10.1016/j.cma.2024.116751",        # Dalklint et al. 2024 - inflatable soft robots
    "10.1089/soro.2022.0247",           # Wu et al. 2024 - compliant actuator (Soft Robotics)
    # 超弹 TO 最新进展
    "10.1007/s00158-024-03860-5",       # Goh et al. 2024 - explicit hyperelastic composite TO
    "10.1007/s00158-024-03944-2",       # Wein et al. 2024 - pressurized nonlinear TO
    # 压力载荷 TO (Darcy 系列)
    "10.1007/s00158-019-02339-y",       # Kumar et al. 2020 - Darcy method
    # HASEL 建模与优化
    "10.1016/j.eml.2023.102072",        # Wang et al. 2023 - HASEL parametric optimization
    "10.1002/adma.202003375",           # Rothemund et al. 2021 - HASEL review
    "10.3390/biomimetics10030152",      # Tynan et al. 2025 - EHA review (confirms zero TO)
    # 稳定化方法最新
    "10.1002/nme.7574",                 # Scherz et al. 2024 - condition number
]

def doi_to_filename(doi):
    return doi.replace("/", "_").replace(".", "-") + ".pdf"

def doi_to_remotexs_url(doi):
    """DOI → NTU RemoteXS proxy URL"""
    target = f"https://doi.org/{doi}"
    return f"https://remotexs.ntu.edu.sg/user/login?dest={target}"

def wait_for_download(dl_dir, before_count, timeout=TIMEOUT):
    t0 = time.time()
    while time.time() - t0 < timeout:
        temps = list(dl_dir.glob("*.crdownload")) + list(dl_dir.glob("*.tmp"))
        pdfs = list(dl_dir.glob("*.pdf"))
        if len(pdfs) > before_count and not temps:
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
    """自动填写NTU RemoteXS登录表单"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver.get("https://remotexs.ntu.edu.sg/user/login")
    time.sleep(3)

    # RemoteXS自己的登录表单
    for user_sel in ["input[name='user']", "input[name='username']",
                     "input[id='username']", "input[type='text']"]:
        try:
            uf = driver.find_element(By.CSS_SELECTOR, user_sel)
            uf.clear(); uf.send_keys(username)
            break
        except: continue

    for pass_sel in ["input[name='pass']", "input[name='password']",
                     "input[id='password']", "input[type='password']"]:
        try:
            pf = driver.find_element(By.CSS_SELECTOR, pass_sel)
            pf.clear(); pf.send_keys(password)
            break
        except: continue

    for btn_sel in ["input[type='submit']", "button[type='submit']",
                    "input[value='Login']", "input[value='Sign In']", "button"]:
        try:
            driver.find_element(By.CSS_SELECTOR, btn_sel).click()
            print("  Auto-login: submitted")
            break
        except: continue

    time.sleep(5)

def try_get_pdf(driver):
    """在当前页面找PDF下载链接"""
    from selenium.webdriver.common.by import By
    url = driver.current_url
    print(f"           page: {url[:100]}")

    # IEEE Xplore
    if "ieeexplore" in url:
        m = re.search(r'/document/(\d+)', url)
        if m:
            base = re.match(r'(https?://[^/]+)', url).group(1)
            stamp = f"{base}/stamp/stamp.jsp?tp=&arnumber={m.group(1)}"
            print(f"           stamp: {stamp[:80]}")
            driver.get(stamp); time.sleep(6)
            # stamp页可能直接是PDF iframe
            try:
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                for frame in frames:
                    src = frame.get_attribute("src")
                    if src and "pdf" in src.lower():
                        print(f"           iframe: {src[:80]}")
                        driver.get(src); return True
            except: pass
            # 或者stamp页直接触发了PDF下载
            return True
        else:
            print(f"           IEEE page but no /document/ID found")

    # Wiley
    if "onlinelibrary" in url or "wiley" in url:
        pdf_url = re.sub(r'/doi/(full/|abs/)?', '/doi/pdfdirect/', url)
        if pdf_url != url:
            print(f"           wiley pdfdirect: {pdf_url[:80]}")
            driver.get(pdf_url); return True
        try:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='pdfdirect'], a[href*='epdf']")
            for link in links:
                href = link.get_attribute("href")
                if href:
                    print(f"           wiley link: {href[:80]}")
                    driver.get(href); return True
        except: pass

    # 通用
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href$='.pdf'], a[title*='PDF']")
        for link in links:
            href = link.get_attribute("href")
            if href and "pdf" in href.lower():
                print(f"           generic pdf: {href[:80]}")
                link.click(); return True
    except: pass

    print(f"           no PDF link found on this page")
    return False

def download_one(driver, doi, dl_dir, idx, total):
    fname = doi_to_filename(doi)
    target = dl_dir / fname
    if target.exists():
        print(f"  [{idx:2d}/{total}] SKIP  {doi}")
        return True

    if idx == 1:
        url = doi_to_remotexs_url(doi)
    else:
        url = f"https://doi-org.remotexs.ntu.edu.sg/{doi}"

    before = len(list(dl_dir.glob("*.pdf")))
    print(f"  [{idx:2d}/{total}] GET   {doi}")
    driver.get(url); time.sleep(8)  # 代理慢，等久一点

    try_get_pdf(driver); time.sleep(3)

    if wait_for_download(dl_dir, before):
        newest = max(dl_dir.glob("*.pdf"), key=os.path.getmtime)
        if newest.name != fname:
            newest.rename(dl_dir / fname)
        print(f"           ✓ {fname}")
        return True
    print(f"           ✗ FAILED (no new PDF in {TIMEOUT}s)")
    return False

def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    print("=" * 60)
    print(f"  NTU RemoteXS Paper Downloader")
    print(f"  {len(DOIS)} papers → {DOWNLOAD_DIR.resolve()}")
    print("=" * 60)

    try:
        from selenium import webdriver
    except ImportError:
        print("\n  Run: pip install selenium webdriver-manager")
        sys.exit(1)

    username = NTU_USERNAME or input("\n  NTU Username: ").strip()
    password = getpass.getpass("  NTU Password: ")

    driver = setup_driver(DOWNLOAD_DIR)

    try:
        print("\n  Logging into RemoteXS...")
        auto_login(driver, username, password)

        cur = driver.current_url
        if any(k in cur.lower() for k in ["login", "auth", "duo", "mfa", "factor"]):
            print("\n" + "=" * 60)
            print("  Please complete login/2FA in browser")
            print("  Then press Enter here")
            print("=" * 60)
            input("  >>> Press Enter <<<\n")
        else:
            print("  Login OK!")

        ok, fail = 0, 0
        failed = []
        for i, doi in enumerate(DOIS, 1):
            done = False
            try:
                for retry in range(MAX_RETRY + 1):
                    if retry > 0:
                        print(f"           retry {retry}/{MAX_RETRY}...")
                        time.sleep(2)
                    if download_one(driver, doi, DOWNLOAD_DIR, i, len(DOIS)):
                        done = True; break
            except Exception as e:
                if "invalid session" in str(e).lower() or "disconnected" in str(e).lower():
                    print(f"\n  Browser was closed. Stopping.")
                    failed.append(doi)
                    failed.extend(DOIS[i:])  # 剩余全部标记失败
                    fail += len(DOIS) - i + 1
                    break
                print(f"           ✗ ERROR: {e}")
            if done: ok += 1
            else: fail += 1; failed.append(doi)
            time.sleep(DELAY)

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
        try:
            input("\n  Press Enter to close browser...")
            driver.quit()
        except:
            pass  # browser already gone

if __name__ == "__main__":
    main()