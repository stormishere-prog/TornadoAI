#!/data/data/com.termux/files/usr/bin/python3
import os, sys, time, json, sqlite3, shutil, subprocess

ROOT = "/storage/emulated/0/Download/TornadoAI"
DB   = os.path.join(ROOT, "corpus.db")
BKDIR= os.path.join(ROOT, "backups")
os.makedirs(BKDIR, exist_ok=True)

def _busy_conn(db, to=30):
    c = sqlite3.connect(db, timeout=to)
    c.execute("PRAGMA busy_timeout=6000;")
    return c

def _has_sidefiles():
    for ext in ("-wal","-shm",".journal"):
        if os.path.exists(DB+ext): return True
    return False

def _ps_cmd(pid):
    try:
        with open(f"/proc/{pid}/cmdline","rb") as f:
            return f.read().replace(b"\x00", b" ").decode("utf-8","ignore").strip()
    except Exception:
        return ""

def _holders():
    holders = []
    target = os.path.realpath(DB)
    for pid in os.listdir("/proc"):
        if not pid.isdigit(): continue
        fd_dir = f"/proc/{pid}/fd"
        if not os.path.isdir(fd_dir): continue
        try:
            for fd in os.listdir(fd_dir):
                p = os.path.join(fd_dir, fd)
                try:
                    link = os.path.realpath(os.readlink(p))
                except Exception:
                    continue
                if link.startswith(target):
                    holders.append((int(pid), _ps_cmd(int(pid))))
                    break
        except Exception:
            continue
    return holders

def _kill_holders():
    killed = []
    for pid, cmd in _holders():
        if pid == os.getpid(): continue
        try:
            os.kill(pid, 15); killed.append((pid, cmd, "TERM"))
        except Exception:
            pass
    time.sleep(1.0)
    for pid, cmd in _holders():
        if pid == os.getpid(): continue
        try:
            os.kill(pid, 9); killed.append((pid, cmd, "KILL"))
        except Exception:
            pass
    return killed

def _backup(label="precheck"):
    ts = time.strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(BKDIR, f"corpus.{ts}.{label}.db")
    try:
        subprocess.check_call(["sqlite3", DB, f".backup '{dst}'"])
        return dst
    except Exception:
        shutil.copy2(DB, dst); return dst

def _restore(path):
    shutil.copy2(path, DB)
    for ext in ("-wal","-shm",".journal"):
        p = DB+ext
        if os.path.exists(p): os.remove(p)

def _integrity_ok():
    try:
        out = subprocess.check_output(["sqlite3","-cmd",".timeout 4000", DB, "PRAGMA integrity_check;"], stderr=subprocess.STDOUT)
        return out.decode().strip().splitlines()[-1].lower() == "ok"
    except subprocess.CalledProcessError as e:
        msg = e.output.decode("utf-8","ignore")
        return ("locked" not in msg.lower()) and ("malformed" not in msg.lower()) and ("error" not in msg.lower())

def _fts_rebuild():
    try:
        with _busy_conn(DB) as c:
            for fts in ("docs_fts","pages_fts"):
                try:
                    c.execute(f"INSERT INTO {fts}({fts}) VALUES('rebuild');")
                except sqlite3.OperationalError:
                    pass
    except Exception:
        pass

def _wal_checkpoint():
    try:
        with _busy_conn(DB) as c:
            c.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except Exception:
        pass

def _vacuum_into():
    tmp = os.path.join(ROOT, "corpus.compact.tmp")
    try:
        subprocess.check_call(["sqlite3", DB, f"VACUUM INTO '{tmp}'"])
        shutil.move(tmp, DB)
        for ext in ("-wal","-shm",".journal"):
            p = DB+ext
            if os.path.exists(p): os.remove(p)
        return True
    except Exception:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass
        return False

def guard():
    result = {"ok": True, "actions": []}

    if _has_sidefiles():
        result["actions"].append("sidefiles:present")
        _wal_checkpoint()

    try:
        out = subprocess.check_output(["sqlite3","-cmd",".timeout 1200", DB, "PRAGMA quick_check;"], stderr=subprocess.STDOUT)
        quick = out.decode("utf-8","ignore").strip()
        if "disk image is malformed" in quick.lower():
            result["ok"] = False
            result["actions"].append("quick_check:malformed")
    except subprocess.CalledProcessError as e:
        msg = e.output.decode("utf-8","ignore")
        if "locked" in msg.lower():
            killed = _kill_holders()
            if killed: result["actions"].append({"killed": killed})

    try:
        bkp = _backup("pre-guard"); result["actions"].append({"backup": bkp})
    except Exception:
        result["actions"].append("backup:failed")

    if not _integrity_ok():
        result["actions"].append("integrity:not-ok")
        if _vacuum_into():
            result["actions"].append("vacuum_into:ok")
        _fts_rebuild()
        if not _integrity_ok():
            _restore(bkp)
            result["actions"].append({"restore": bkp})
            _wal_checkpoint()
            _fts_rebuild()

    result["ok"] = _integrity_ok()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    sys.exit(guard())
