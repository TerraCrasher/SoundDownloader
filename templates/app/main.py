# -*- coding: utf-8 -*-
import os
import sys

# 콘솔 코드페이지가 cp949여도 박스/이모지/한글 출력으로 죽지 않도록 보정.
# (run.bat 의 chcp 65001 만으로는 Python stdout encoding 이 cp949 로 잡힐 수 있음)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)

sys.path.insert(0, os.path.join(ROOT_DIR, "packages"))
sys.path.insert(0, APP_DIR)

os.chdir(ROOT_DIR)

from cli.app import main

if __name__ == "__main__":
    main()
