# -*- coding: utf-8 -*-
"""
Sound Downloader - 앱 파일 재생성 (개발자용)
files_data.py를 호출해서 앱 코드만 빠르게 재생성합니다.
"""
import os
import sys

# 콘솔 코드페이지가 cp949여도 한글/이모지 출력으로 죽지 않도록 보정.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))


def _p(s):
    try:
        print(s)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        sys.stdout.write(s.encode(enc, errors="replace").decode(enc, errors="replace") + "\n")


def main():
    _p("=" * 50)
    _p("  앱 파일 재생성")
    _p("=" * 50)

    sys.path.insert(0, ROOT)
    try:
        import files_data
        files_data.write_files()
    except ImportError:
        _p("[ERROR] files_data.py를 찾을 수 없습니다.")
        sys.exit(1)
    except Exception as e:
        _p("[ERROR] 파일 생성 실패: %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
