# -*- coding: utf-8 -*-
import os
import sys
import json
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.manager import DownloaderManager
from core.downloader_base import SortOption
from providers.youtube import FORMAT_PRESETS as YT_FORMATS, DEFAULT_FORMAT as YT_DEFAULT_FMT
from providers.opengameart import CATEGORY_LABELS as OGA_CATEGORIES


CONFIG_PATH = "config.json"

# 다운로드 베이스 폴더 / provider 별 기본 하위폴더
DEFAULT_BASE_DIR = "downloads"
DEFAULT_FREESOUND_SUBDIR = "freesound"
DEFAULT_YOUTUBE_SUBDIR = "youtube"
DEFAULT_OGA_SUBDIR = "opengameart"


def freesound_default_dir(config_data):
    """config 우선 → 없으면 <save_dir>/freesound."""
    v = config_data.get("freesound_save_dir")
    if v:
        return v
    base = config_data.get("save_dir") or DEFAULT_BASE_DIR
    return os.path.join(base, DEFAULT_FREESOUND_SUBDIR)


def youtube_default_dir(config_data):
    v = config_data.get("youtube_save_dir")
    if v:
        return v
    base = config_data.get("save_dir") or DEFAULT_BASE_DIR
    return os.path.join(base, DEFAULT_YOUTUBE_SUBDIR)


def oga_default_dir(config_data):
    v = config_data.get("opengameart_save_dir")
    if v:
        return v
    base = config_data.get("save_dir") or DEFAULT_BASE_DIR
    return os.path.join(base, DEFAULT_OGA_SUBDIR)

SORT_MENU = [
    ("1", "downloads",       SortOption.DOWNLOADS,       "다운로드 많은순"),
    ("2", "rating",          SortOption.RATING,          "평점 높은순"),
    ("3", "newest",          SortOption.NEWEST,          "최신순"),
    ("4", "duration_short",  SortOption.DURATION_SHORT,  "짧은 길이순"),
    ("5", "duration_long",   SortOption.DURATION_LONG,   "긴 길이순"),
    ("6", "relevance",       SortOption.RELEVANCE,       "관련도순"),
]
SORT_BY_NUM = {n: v for n, _, v, _ in SORT_MENU}
SORT_BY_NAME = {k: v for _, k, v, _ in SORT_MENU}

# 길이 필터 메뉴 (label, max_seconds)
DURATION_MENU = [
    ("1", "0~15초",   15),
    ("2", "0~30초",   30),
    ("3", "0~45초",   45),
    ("4", "0~1분",    60),
    ("5", "0~2분",    120),
    ("6", "0~3분",    180),
    ("7", "제한 없음", None),
]

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def progress_bar(current, total, prefix="", length=30):
    if total == 0:
        return
    pct = current / total
    filled = int(length * pct)
    bar = "█" * filled + "░" * (length - filled)
    print(f"\r  {prefix} [{bar}] {current}/{total} ({pct*100:.1f}%)", end="", flush=True)


def print_header(title, icon="🎵"):
    """이모지는 폭 2칸으로 처리 (cmd 기준)"""
    width = 46
    inner = f" {icon}  {title} "
    # 이모지 1개당 +1 보정 (실제 출력 폭이 +1 더 차지)
    visual_len = len(inner) + sum(1 for c in inner if ord(c) > 0x1F000)
    pad = width - visual_len
    print()
    print("  ╔" + "═" * width + "╗")
    print("  ║" + inner + " " * max(0, pad) + "║")
    print("  ╚" + "═" * width + "╝")


def do_download(provider, items, top_m, save_dir):
    targets = items[:top_m]
    total = len(targets)

    print(f"\n  📥 {total}개 파일 다운로드 시작")
    print(f"  📁 {os.path.abspath(save_dir)}\n")

    done_count = [0]
    fail_count = [0]
    lock = threading.Lock()

    def worker(item):
        try:
            provider.download(item, save_dir)
            return True, item, None
        except Exception as e:
            return False, item, str(e)

    progress_bar(0, total, prefix="진행")
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(worker, t) for t in targets]
        for fu in as_completed(futures):
            ok, item, err = fu.result()
            with lock:
                if ok:
                    done_count[0] += 1
                else:
                    fail_count[0] += 1
                    print(f"\n  ❌ [실패] {item.name}: {err}")
                progress_bar(done_count[0] + fail_count[0], total, prefix="진행")

    print(f"\n")
    print(f"  ✅ 완료!  성공 {done_count[0]}개  /  실패 {fail_count[0]}개")
    print(f"  📁 {os.path.abspath(save_dir)}")


def search_and_show(provider, query, max_results, sort_key, top_m, duration_max=None):
    dur_info = f", 최대길이 {duration_max}초" if duration_max else ""
    print(f"\n  🔍 '{query}' 검색 중... (정렬={sort_key}, 최대 {max_results}개{dur_info})")
    items = provider.search(query, max_results=max_results, sort=sort_key,
                            duration_max=duration_max)
    if not items:
        print("  ⚠️  검색 결과가 없습니다")
        return None

    show_n = min(top_m, len(items))
    print(f"\n  ✨ 총 {len(items)}개 검색됨 → 상위 {show_n}개\n")
    print("  " + "─" * 76)
    for i, it in enumerate(items[:show_n], 1):
        name = it.name[:55]
        print(f"  [{i:2}] 🎵 {name}")
        print(f"        ⬇ {it.downloads:>6}   ⭐ {it.rating:.2f}   ⏱ {it.duration:>6.1f}초   👤 {it.username}")
    print("  " + "─" * 76)
    return items


def cmd_search_interactive(manager, config_data):
    provider = manager.get("Freesound")

    if not config_data.get("freesound_api_key"):
        print("\n  ⚠️  API Key가 설정되지 않았습니다. 메뉴 '2. 설정'에서 먼저 입력하세요.")
        return

    print()
    query = input("  🔍 검색어: ").strip()
    if not query:
        print("  ⚠️  검색어가 필요합니다")
        return

    max_str = input("  📊 검색할 최대 개수 [50]: ").strip()
    max_results = int(max_str) if max_str.isdigit() else 50

    print("\n  📋 정렬 방식:")
    for n, _, _, label in SORT_MENU:
        print(f"     {n}. {label}")
    sort_str = input("  ➤ 선택 [1]: ").strip() or "1"
    sort_key = SORT_BY_NUM.get(sort_str, SortOption.DOWNLOADS)

    print("\n  ⏱  검색할 음원 길이:")
    for n, label, _ in DURATION_MENU:
        print(f"     {n}. {label}")
    dur_str = input("  ➤ 선택 [4]: ").strip() or "4"
    duration_max = next((sec for n, _, sec in DURATION_MENU if n == dur_str), 60)

    top_str = input("  ⬇️  다운로드할 개수 [10]: ").strip()
    top_m = int(top_str) if top_str.isdigit() else 10

    default_dir = freesound_default_dir(config_data)
    save_dir = input(f"  📁 저장 폴더 [{default_dir}]: ").strip() or default_dir
    config_data["freesound_save_dir"] = save_dir
    save_config(config_data)

    try:
        items = search_and_show(provider, query, max_results, sort_key, top_m, duration_max)
    except Exception as e:
        print(f"\n  ❌ 검색 실패: {e}")
        return

    if not items:
        return

    confirm = input(f"\n  ⬇️  상위 {min(top_m, len(items))}개를 다운로드할까요? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("  ❎ 취소되었습니다")
        return

    do_download(provider, items, top_m, save_dir)


def cmd_settings_interactive(config_data, manager_ref):
    print_header("설정", "⚙️ ")

    cur = config_data.get("freesound_api_key", "")
    masked = (cur[:4] + "..." + cur[-4:]) if len(cur) > 8 else ("(없음)" if not cur else "(설정됨)")
    print(f"\n  🔑 현재 API Key: {masked}")
    new_key = input("  새 API Key (Enter=유지): ").strip()
    if new_key:
        config_data["freesound_api_key"] = new_key

    cur_oauth = config_data.get("freesound_oauth_token", "")
    print(f"\n  🔐 현재 OAuth Token: {'(설정됨)' if cur_oauth else '(없음)'}")
    new_oauth = input("  새 OAuth Token (Enter=유지, '-'=삭제): ").strip()
    if new_oauth == "-":
        config_data["freesound_oauth_token"] = ""
    elif new_oauth:
        config_data["freesound_oauth_token"] = new_oauth

    save_config(config_data)
    manager_ref[0] = DownloaderManager(config_data)
    print("\n  ✅ 저장 완료!")


# ===========================================================================
# YouTube (yt-dlp) 메뉴
# ===========================================================================

def _yt_pick_format():
    """포맷 선택 입력 → format_key 반환."""
    keys = list(YT_FORMATS.keys())
    print("\n  🎚  포맷 선택:")
    for i, k in enumerate(keys, 1):
        print(f"     {i}. {k.upper():4}  - {YT_FORMATS[k]['label']}")
    default_idx = keys.index(YT_DEFAULT_FMT) + 1 if YT_DEFAULT_FMT in keys else 1
    s = input(f"  ➤ 선택 [{default_idx}]: ").strip() or str(default_idx)
    if s.isdigit() and 1 <= int(s) <= len(keys):
        return keys[int(s) - 1]
    if s.lower() in YT_FORMATS:
        return s.lower()
    return YT_DEFAULT_FMT


def _yt_resolve_save_dir(config_data, prompt_default=None):
    default_dir = prompt_default or youtube_default_dir(config_data)
    s = input(f"  📁 저장 폴더 [{default_dir}]: ").strip() or default_dir
    config_data["youtube_save_dir"] = s
    save_config(config_data)
    return s


def cmd_youtube_single(provider, config_data):
    """단일 URL 다운로드."""
    if not provider.is_ready():
        print("\n  ❌ yt-dlp / ffmpeg 가 준비되지 않았습니다.")
        print("  " + provider.status_text().replace("\n", "\n  "))
        return

    print()
    url = input("  🔗 YouTube 링크: ").strip()
    if not url:
        print("  ⚠️  링크가 필요합니다")
        return
    prefix = input("  🏷  파일명 접두사 (Enter=없음): ").strip()
    fmt_key = _yt_pick_format()
    save_dir = _yt_resolve_save_dir(config_data)

    print(f"\n  📥 다운로드 시작 ({fmt_key.upper()}): {url}")
    print(f"  📁 {os.path.abspath(save_dir)}\n")
    try:
        rc, _ = provider.download_url(url, save_dir,
                                      format_key=fmt_key, prefix=prefix)
        if rc == 0:
            print("\n  ✅ 완료")
        else:
            print(f"\n  ❌ yt-dlp 종료코드 {rc}")
    except Exception as e:
        print(f"\n  ❌ 실패: {e}")


def cmd_youtube_batch(provider, config_data):
    """youtube_links.csv 일괄 다운로드."""
    if not provider.is_ready():
        print("\n  ❌ yt-dlp / ffmpeg 가 준비되지 않았습니다.")
        print("  " + provider.status_text().replace("\n", "\n  "))
        return

    default_csv = config_data.get("youtube_links_csv") or "youtube_links.csv"
    print()
    csv_path = input(f"  📄 CSV 경로 [{default_csv}]: ").strip() or default_csv
    csv_path = os.path.abspath(csv_path)

    if not os.path.isfile(csv_path):
        print(f"\n  ⚠️  파일이 없어 새로 만듭니다: {csv_path}")
        try:
            os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
            # 헤더 + 사용 예시 주석 + 빈 예시 라인 (사용자 편집 가이드)
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                f.write("접두사,링크\n")
                f.write("# 위 한 줄은 헤더입니다. 이 줄(#)도 자동으로 무시됩니다.\n")
                f.write("# 아래 형식대로 한 줄에 한 개씩 입력하세요. 접두사는 비워둬도 됩니다.\n")
                f.write("# 예시:\n")
                f.write("# 1,https://www.youtube.com/watch?v=AAAAAAAAAAA\n")
                f.write("# 2,https://youtu.be/BBBBBBBBBBB\n")
            print("  📝 메모장으로 엽니다. '접두사,링크' 형식으로 입력 후 저장하세요.")
            try:
                os.startfile(csv_path)
            except Exception:
                pass
        except Exception as e:
            print(f"  ❌ 생성 실패: {e}")
        return

    config_data["youtube_links_csv"] = csv_path
    fmt_key = _yt_pick_format()
    save_dir = _yt_resolve_save_dir(config_data)
    log_path = os.path.join(save_dir, "youtube_log.csv")

    confirm = input(f"\n  ⬇️  '{csv_path}' 의 링크를 모두 다운로드할까요? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("  ❎ 취소되었습니다")
        return

    print(f"\n  📥 일괄 다운로드 시작 ({fmt_key.upper()})")
    print(f"  📁 {os.path.abspath(save_dir)}\n")

    def on_item(idx, total, prefix, url, status, fname, msg):
        icon = {"ok": "✅", "fail": "❌", "skip": "⏭"}.get(status, "•")
        head = f"  [{idx}/{total}] {icon} [{prefix or '-'}]"
        print(f"{head} {url}")
        if fname and fname != "-":
            print(f"          파일: {fname}")
        if msg:
            print(f"          비고: {msg}")
        print()

    try:
        result = provider.download_csv(csv_path, save_dir,
                                       format_key=fmt_key,
                                       log_path=log_path,
                                       on_item=on_item)
    except Exception as e:
        print(f"\n  ❌ 실패: {e}")
        return

    print("  " + "─" * 60)
    print(f"  요약: 성공 {result['success']} / 실패 {result['fail']} / 건너뜀 {result['skip']}  (총 {result['total']})")
    print(f"  로그: {log_path}")


def cmd_youtube_update(provider):
    """yt-dlp 자체 업데이트."""
    print("\n  🔄 yt-dlp 업데이트 시도...")
    try:
        rc = provider.update_ytdlp()
        if rc == 0:
            print("\n  ✅ 업데이트 완료(또는 최신)")
        else:
            print(f"\n  ❌ 종료코드 {rc}")
    except Exception as e:
        print(f"\n  ❌ 실패: {e}")


def cmd_youtube_interactive(manager, config_data):
    provider = manager.get("YouTube")
    while True:
        print_header("YouTube 다운로드", "🎬")
        print()
        print("     1. 🔗  단일 링크 다운로드")
        print("     2. 📄  youtube_links.csv 일괄 다운로드")
        print("     3. 🛠   yt-dlp 업데이트")
        print("     4. 🔎  bin / 환경 상태 보기")
        print("     0. ↩   메인 메뉴로")
        print()
        try:
            sel = input("  ➤ 선택: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if sel == "1":
            try:
                cmd_youtube_single(provider, config_data)
            except KeyboardInterrupt:
                print("\n  ❎ 취소되었습니다")
        elif sel == "2":
            try:
                cmd_youtube_batch(provider, config_data)
            except KeyboardInterrupt:
                print("\n  ❎ 취소되었습니다")
        elif sel == "3":
            cmd_youtube_update(provider)
        elif sel == "4":
            print("\n  " + provider.status_text().replace("\n", "\n  "))
        elif sel == "0":
            return
        else:
            print("\n  ⚠️  잘못된 선택입니다")


# ===========================================================================
# OpenGameArt 메뉴 / CLI
# ===========================================================================

# OGA 정렬 메뉴 (DownloaderBase SortOption 일부만 사용)
OGA_SORT_MENU = [
    ("1", "downloads", SortOption.DOWNLOADS, "인기순 (favorites)"),
    ("2", "newest",    SortOption.NEWEST,    "최신순"),
    ("3", "relevance", SortOption.RELEVANCE, "관련도순"),
]
OGA_SORT_BY_NUM = {n: v for n, _, v, _ in OGA_SORT_MENU}
OGA_SORT_BY_NAME = {k: v for _, k, v, _ in OGA_SORT_MENU}


def _oga_pick_category():
    """카테고리 선택 입력 → 'music' / 'sfx' / 'both'."""
    keys = list(OGA_CATEGORIES.keys())  # music, sfx, both
    print("\n  🎮 카테고리:")
    for i, k in enumerate(keys, 1):
        label, _ = OGA_CATEGORIES[k]
        print(f"     {i}. {label}")
    s = input("  ➤ 선택 [3]: ").strip() or "3"
    if s.isdigit() and 1 <= int(s) <= len(keys):
        return keys[int(s) - 1]
    return "both"


def _oga_show_results(items, top_m):
    show_n = min(top_m, len(items))
    print(f"\n  ✨ 총 {len(items)}개 검색됨 → 상위 {show_n}개\n")
    print("  " + "─" * 76)
    for i, it in enumerate(items[:show_n], 1):
        name = it.name[:55]
        n_files = it.extra.get("file_count", 0)
        cat = it.extra.get("category", "?")
        print(f"  [{i:2}] 🎮 {name}")
        print(f"        ⭐ favs={it.downloads:>4}  📦 {n_files} 파일  🗂 {cat}  👤 {it.username}")
        if it.license:
            print(f"        ⚖  {it.license[:60]}")
    print("  " + "─" * 76)


def cmd_oga_interactive(manager, config_data):
    provider = manager.get("OpenGameArt")

    print()
    print("  ℹ️  OpenGameArt 게시물의 라이선스는 다양합니다 (CC0/CC-BY/GPL 등).")
    print("     상업 이용 시 각 게시물의 라이선스를 반드시 확인하세요.")
    print("     다운로드된 폴더의 README.txt 에 출처/라이선스가 자동 기록됩니다.")

    cat = _oga_pick_category()
    provider.category_key = cat

    print()
    query = input("  🔍 검색어 (Enter=전체 브라우징): ").strip()

    max_str = input("  📊 검색할 최대 개수 [50]: ").strip()
    max_results = int(max_str) if max_str.isdigit() else 50

    print("\n  📋 정렬 방식:")
    for n, _, _, label in OGA_SORT_MENU:
        print(f"     {n}. {label}")
    sort_str = input("  ➤ 선택 [1]: ").strip() or "1"
    sort_key = OGA_SORT_BY_NUM.get(sort_str, SortOption.DOWNLOADS)

    top_str = input("  ⬇️  다운로드할 상위 개수 [10]: ").strip()
    top_m = int(top_str) if top_str.isdigit() else 10

    default_dir = oga_default_dir(config_data)
    save_dir = input(f"  📁 저장 폴더 [{default_dir}]: ").strip() or default_dir
    config_data["opengameart_save_dir"] = save_dir
    save_config(config_data)

    label_for_log = OGA_CATEGORIES[cat][0]
    print(f"\n  🔍 OGA '{query or '(전체)'}' 검색 중... (카테고리={label_for_log}, "
          f"정렬={sort_key}, 최대 {max_results}개)")

    try:
        items = provider.search(query, max_results=max_results, sort=sort_key)
    except Exception as e:
        print(f"\n  ❌ 검색 실패: {e}")
        return

    if not items:
        print("  ⚠️  검색 결과가 없습니다 (또는 다운로드 가능한 파일이 있는 항목이 없음)")
        return

    _oga_show_results(items, top_m)

    confirm = input(f"\n  ⬇️  상위 {min(top_m, len(items))}개 게시물을 다운로드할까요? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("  ❎ 취소되었습니다")
        return

    do_download(provider, items, top_m, save_dir)
    print("\n  ℹ️  각 게시물 폴더의 README.txt 에서 라이선스/출처를 확인하세요.")


def cmd_oga_args(manager, config_data, args):
    """CLI 서브커맨드 진입점: run.bat oga "ambient" --category music ..."""
    provider = manager.get("OpenGameArt")
    provider.category_key = args.category
    sort_key = OGA_SORT_BY_NAME.get(args.sort, SortOption.DOWNLOADS)
    save_dir = args.dir or oga_default_dir(config_data)
    config_data["opengameart_save_dir"] = save_dir
    save_config(config_data)

    label_for_log = OGA_CATEGORIES[args.category][0]
    print(f"\n  🔍 OGA '{args.query or '(전체)'}' 검색 중... "
          f"(카테고리={label_for_log}, 정렬={args.sort}, 최대 {args.max}개)")

    try:
        items = provider.search(args.query, max_results=args.max, sort=sort_key)
    except Exception as e:
        print(f"\n  ❌ {e}")
        sys.exit(1)

    if not items:
        print("  ⚠️  검색 결과가 없습니다")
        return

    _oga_show_results(items, args.top)

    if not args.yes:
        confirm = input(f"\n  ⬇️  상위 {min(args.top, len(items))}개 게시물을 다운로드할까요? [Y/n]: ").strip().lower()
        if confirm == "n":
            print("  ❎ 취소되었습니다")
            return

    do_download(provider, items, args.top, save_dir)
    print("\n  ℹ️  각 게시물 폴더의 README.txt 에서 라이선스/출처를 확인하세요.")


# ===========================================================================
# 메인 메뉴
# ===========================================================================

def interactive_mode(manager, config_data):
    manager_ref = [manager]
    while True:
        print_header("Sound Downloader", "🎵")
        print()
        print("     1. 🔍  Freesound 검색 & 다운로드")
        print("     2. 🎬  YouTube 다운로드 (yt-dlp)")
        print("     3. 🎮  OpenGameArt 검색 & 다운로드")
        print("     4. ⚙️  설정 (Freesound API Key)")
        print("     5. 📁  다운로드 폴더 열기")
        print("     0. 🚪  종료")
        print()
        try:
            choice = input("  ➤ 선택: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  👋 종료합니다")
            return

        if choice == "1":
            try:
                cmd_search_interactive(manager_ref[0], config_data)
            except KeyboardInterrupt:
                print("\n  ❎ 취소되었습니다")
        elif choice == "2":
            try:
                cmd_youtube_interactive(manager_ref[0], config_data)
            except KeyboardInterrupt:
                print("\n  ❎ 취소되었습니다")
        elif choice == "3":
            try:
                cmd_oga_interactive(manager_ref[0], config_data)
            except KeyboardInterrupt:
                print("\n  ❎ 취소되었습니다")
        elif choice == "4":
            cmd_settings_interactive(config_data, manager_ref)
        elif choice == "5":
            d = config_data.get("save_dir", "downloads")
            os.makedirs(d, exist_ok=True)
            os.startfile(os.path.abspath(d))
            print(f"\n  📁 폴더 열림: {os.path.abspath(d)}")
        elif choice == "0":
            print("\n  👋 종료합니다")
            return
        else:
            print("\n  ⚠️  잘못된 선택입니다")


def cmd_search_args(manager, config_data, args):
    provider = manager.get("Freesound")
    sort_key = SORT_BY_NAME.get(args.sort, SortOption.DOWNLOADS)
    save_dir = args.dir or freesound_default_dir(config_data)
    config_data["freesound_save_dir"] = save_dir
    save_config(config_data)

    try:
        items = search_and_show(provider, args.query, args.max, sort_key, args.top,
                                duration_max=args.duration_max)
    except Exception as e:
        print(f"\n  ❌ {e}")
        sys.exit(1)

    if not items:
        return

    if not args.yes:
        confirm = input(f"\n  ⬇️  상위 {min(args.top, len(items))}개를 다운로드할까요? [Y/n]: ").strip().lower()
        if confirm == "n":
            print("  ❎ 취소되었습니다")
            return

    do_download(provider, items, args.top, save_dir)


def cmd_config_args(config_data, args):
    if args.api_key:
        config_data["freesound_api_key"] = args.api_key
    if args.oauth_token:
        config_data["freesound_oauth_token"] = args.oauth_token
    save_config(config_data)
    print("  ✅ 설정 저장 완료")


def main():
    config_data = load_config()
    manager = DownloaderManager(config_data)

    parser = argparse.ArgumentParser(prog="SoundDownloader")
    sub = parser.add_subparsers(dest="cmd")

    p_search = sub.add_parser("search", help="검색 및 다운로드")
    p_search.add_argument("query")
    p_search.add_argument("--max", type=int, default=50)
    p_search.add_argument("--top", type=int, default=10)
    p_search.add_argument("--sort", default="downloads", choices=list(SORT_BY_NAME.keys()))
    p_search.add_argument("--dir", default=None)
    p_search.add_argument("--duration-max", type=int, default=None,
                          help="최대 길이(초)")
    p_search.add_argument("-y", "--yes", action="store_true", help="확인 없이 다운로드")

    p_config = sub.add_parser("config", help="API Key / OAuth 설정")
    p_config.add_argument("--api-key", default=None)
    p_config.add_argument("--oauth-token", default=None)

    p_yt = sub.add_parser("youtube", help="YouTube 다운로드 (yt-dlp)")
    p_yt.add_argument("url_or_csv", help="YouTube URL 또는 .csv 경로")
    p_yt.add_argument("--format", default=YT_DEFAULT_FMT,
                      choices=list(YT_FORMATS.keys()),
                      help="오디오 포맷 (기본: mp3)")
    p_yt.add_argument("--prefix", default="", help="파일명 접두사 (단일 URL 시)")
    p_yt.add_argument("--dir", default=None, help="저장 폴더")
    p_yt.add_argument("--update", action="store_true",
                      help="실행 전 yt-dlp 업데이트")

    p_oga = sub.add_parser("oga", help="OpenGameArt 검색 및 다운로드")
    p_oga.add_argument("query", nargs="?", default="",
                       help="검색어 (생략 가능: 전체 브라우징)")
    p_oga.add_argument("--category", default="both",
                       choices=list(OGA_CATEGORIES.keys()),
                       help="카테고리: music / sfx / both (기본: both)")
    p_oga.add_argument("--max", type=int, default=50,
                       help="검색할 최대 게시물 수 (기본: 50)")
    p_oga.add_argument("--top", type=int, default=10,
                       help="다운로드할 상위 N개 (기본: 10)")
    p_oga.add_argument("--sort", default="downloads",
                       choices=list(OGA_SORT_BY_NAME.keys()),
                       help="정렬: downloads(인기) / newest / relevance")
    p_oga.add_argument("--dir", default=None, help="저장 폴더")
    p_oga.add_argument("-y", "--yes", action="store_true",
                       help="확인 없이 다운로드")

    args = parser.parse_args()

    if args.cmd == "search":
        cmd_search_args(manager, config_data, args)
    elif args.cmd == "config":
        cmd_config_args(config_data, args)
    elif args.cmd == "youtube":
        provider = manager.get("YouTube")
        save_dir = args.dir or youtube_default_dir(config_data)
        if args.update:
            try:
                provider.update_ytdlp()
            except Exception as e:
                print(f"  ❌ 업데이트 실패: {e}")
        target = args.url_or_csv
        try:
            if target.lower().endswith(".csv"):
                result = provider.download_csv(
                    os.path.abspath(target), save_dir,
                    format_key=args.format,
                    log_path=os.path.join(save_dir, "youtube_log.csv"),
                    on_item=lambda i, t, p, u, s, f, m: print(
                        f"  [{i}/{t}] {s.upper():4} [{p or '-'}] {u}"
                        + (f"  ({m})" if m else "")
                    ),
                )
                print(f"\n  요약: 성공 {result['success']} / 실패 {result['fail']} / 건너뜀 {result['skip']}")
            else:
                rc, _ = provider.download_url(target, save_dir,
                                              format_key=args.format,
                                              prefix=args.prefix)
                sys.exit(rc)
        except Exception as e:
            print(f"  ❌ {e}")
            sys.exit(1)
    elif args.cmd == "oga":
        try:
            cmd_oga_args(manager, config_data, args)
        except KeyboardInterrupt:
            print("\n  ❎ 취소되었습니다")
    else:
        try:
            interactive_mode(manager, config_data)
        except KeyboardInterrupt:
            print("\n  👋 종료합니다")
