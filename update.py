#!/usr/bin/env python3
import os, shutil, subprocess, requests, tempfile, sys, zipfile

USER = "cpfain"                # <- ชื่อ GitHub ของพี่
REPO = "smartfarm-pi-code-v1"
BRANCH = "main"
REPO_ZIP = f"https://codeload.github.com/{USER}/{REPO}/zip/refs/heads/{BRANCH}"
RAW_VERSION = f"https://raw.githubusercontent.com/{USER}/{REPO}/{BRANCH}/VERSION"

APP_DIR = "/opt/smartfarm"
VERSION_FILE = os.path.join(APP_DIR, "VERSION")

def get_remote_version():
    try:
        r = requests.get(RAW_VERSION, timeout=10)
        r.raise_for_status()
        return r.text.strip()
    except Exception as e:
        print("Fetch remote version failed:", e)
        return None

def get_local_version():
    try:
        return open(VERSION_FILE).read().strip()
    except:
        return "0.0.0"

def clean_dir_keep_update_py(dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    for name in os.listdir(dest_dir):
        path = os.path.join(dest_dir, name)
        # กันพลาด: อย่าลบทิ้งตัว updater เอง
        if name == "update.py":
            continue
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
        except Exception as e:
            print("Warn: cannot remove", path, e)

def extract_zip_to(zip_path, dest_dir, inner_prefix):
    with zipfile.ZipFile(zip_path) as z:
        for m in z.infolist():
            if m.is_dir(): 
                continue
            if not m.filename.startswith(inner_prefix):
                continue
            rel = m.filename[len(inner_prefix):]
            # อย่าทับ update.py ในเครื่อง
            if rel == "update.py":
                continue
            out_path = os.path.join(dest_dir, rel)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with z.open(m) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

def update_code():
    print("🔄 Downloading latest code (zip)…")
    tmp = tempfile.mkstemp(suffix=".zip")[1]
    with requests.get(REPO_ZIP, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1<<20):
                f.write(chunk)

    inner_prefix = f"{REPO}-{BRANCH}/"

    # ลบเฉพาะ "ข้างใน" ไม่ลบโฟลเดอร์ /opt/smartfarm เอง
    clean_dir_keep_update_py(APP_DIR)

    # แตกไฟล์ใหม่เข้าไป
    extract_zip_to(tmp, APP_DIR, inner_prefix)

    # ตั้งสิทธิ์รันให้ไฟล์หลัก
    app_path = os.path.join(APP_DIR, "app.py")
    if os.path.exists(app_path):
        os.chmod(app_path, 0o755)
    print("✅ Code updated at", APP_DIR)

def main():
    remote = get_remote_version()
    if not remote:
        print("❌ Cannot get remote version")
        sys.exit(1)
    local = get_local_version()

    if remote != local:
        print(f"🚀 New version found: {local} → {remote}")
        update_code()
        with open(VERSION_FILE, "w") as f:
            f.write(remote)
        # รันโปรแกรมหลักโชว์ผล
        subprocess.run(["/usr/bin/python3", os.path.join(APP_DIR, "app.py")])
    else:
        print(f"✅ Already up to date: {local}")

if __name__ == "__main__":
    main()
