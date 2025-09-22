#!/data/data/com.termux/files/usr/bin/python3
import sys, pathlib
CACHE = pathlib.Path("/storage/emulated/0/Download/TornadoAI/cache")
def resolve(fname: str) -> str:
    f = CACHE / fname
    pointer = f.with_suffix(f.suffix + ".path")
    if pointer.exists():
        return pointer.read_text().strip()
    return str(f)
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: pdf_path.py <hash>.pdf\n"); sys.exit(1)
    print(resolve(sys.argv[1]))
