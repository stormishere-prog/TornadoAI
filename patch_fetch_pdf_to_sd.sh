#!/data/data/com.termux/files/usr/bin/sh
set -eu
. /storage/emulated/0/Download/TornadoAI/ta_paths.conf

PYFILE="$ROOT/fetch_and_ingest.py"

python3 - <<'PY'
import io, os, re, sys, textwrap

ROOT="/storage/emulated/0/Download/TornadoAI"
CONF=os.path.join(ROOT,"ta_paths.conf")
SDPDF="/storage/6F3A-4D77/Documents/TornadoAI/pdfs"

# load SDPDF from conf if present
try:
    for ln in open(CONF, "r", encoding="utf-8"):
        ln=ln.strip()
        if ln.startswith("SDPDF="):
            SDPDF = ln.split("=",1)[1].strip().strip('"').strip("'")
            break
except Exception:
    pass

path = os.path.join(ROOT,"fetch_and_ingest.py")
src = open(path,"r",encoding="utf-8").read()

# We replace the small block that defines pdf_path and writes the bytes.
pattern = r"""
        h=sha256_bytes\(b\)\[:16\]\s*\n
        \s*pdf_path=os\.path\.join\(CACHE,\s*f"\{h\}\.pdf"\)\s*\n
        \s*save_cache\(pdf_path,b\)
"""
replacement = textwrap.dedent(f"""
        h=sha256_bytes(b)[:16]
        # prefer SD card for large blobs
        os.makedirs("{SDPDF}", exist_ok=True)
        pdf_path_sd = os.path.join("{SDPDF}", f"{{h}}.pdf")
        pdf_path_cache = os.path.join(CACHE, f"{{h}}.pdf")
        # write to SD if not present
        if not os.path.exists(pdf_path_sd):
            open(pdf_path_sd, "wb").write(b)
        # ensure cache points to SD (symlink or tiny stub)
        try:
            os.makedirs(CACHE, exist_ok=True)
            # remove old file if not a symlink
            if os.path.exists(pdf_path_cache) and not os.path.islink(pdf_path_cache):
                try: os.remove(pdf_path_cache)
                except: pass
            if not os.path.islink(pdf_path_cache):
                try:
                    os.symlink(pdf_path_sd, pdf_path_cache)
                except OSError:
                    # fallback: tiny pointer file
                    open(pdf_path_cache, "wb").write(b"")
        except Exception:
            pass
        pdf_path = pdf_path_sd
""").strip("\n")

new = re.sub(pattern, replacement, src, flags=re.S|re.X)
if new == src:
    print("[patch] pattern not found (maybe already patched).")
else:
    open(path,"w",encoding="utf-8").write(new)
    print("[patch] fetch_and_ingest.py updated.")
PY
