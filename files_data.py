# -*- coding: utf-8 -*-
"""
Sound Downloader - 파일 생성기
templates/ 폴더의 모든 파일을 루트로 복사합니다.

- __pycache__, *.pyc, *.bak 등 자동 생성/백업 파일은 복사 대상에서 제외
- 콘솔 인코딩(cp949)에서도 안전하도록 ASCII 친화적 출력
"""
import os
import sys
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(ROOT, "templates")

# 복사 대상에서 제외할 폴더/확장자/파일 패턴
EXCLUDE_DIRS = {"__pycache__", ".git", ".idea", ".vscode"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".bak", ".tmp", ".swp"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}


def _safe_print(s):
    """현재 콘솔 인코딩으로 표현 불가능한 문자는 '?'로 대체해서 출력."""
    try:
        print(s)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        sys.stdout.write(s.encode(enc, errors="replace").decode(enc, errors="replace") + "\n")


def _should_skip(rel_path):
    parts = rel_path.replace("\\", "/").split("/")
    for p in parts[:-1]:
        if p in EXCLUDE_DIRS:
            return True
    fname = parts[-1]
    if fname in EXCLUDE_FILES:
        return True
    ext = os.path.splitext(fname)[1].lower()
    if ext in EXCLUDE_EXTS:
        return True
    return False


def write_files():
    """templates/ 폴더의 파일들을 ROOT로 복사 (제외 규칙 적용)."""
    if not os.path.isdir(TEMPLATES_DIR):
        _safe_print("[ERROR] templates 폴더가 없습니다: %s" % TEMPLATES_DIR)
        return

    file_list = []
    for dirpath, dirnames, filenames in os.walk(TEMPLATES_DIR):
        # 제외 폴더는 walk에서 가지치기
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            src = os.path.join(dirpath, fname)
            rel = os.path.relpath(src, TEMPLATES_DIR)
            if _should_skip(rel):
                continue
            file_list.append((src, rel))

    total = len(file_list)
    _safe_print("=" * 50)
    _safe_print("  templates -> ROOT  (%d files)" % total)
    _safe_print("=" * 50)

    for i, (src, rel) in enumerate(file_list, 1):
        dst = os.path.join(ROOT, rel)
        d = os.path.dirname(dst)
        if d:
            os.makedirs(d, exist_ok=True)
        shutil.copy2(src, dst)
        _safe_print("  [%d/%d] %s" % (i, total, rel))

    _safe_print("=" * 50)
    _safe_print("  [OK] Done!")
    _safe_print("=" * 50)


if __name__ == "__main__":
    write_files()
