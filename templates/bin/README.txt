YouTube 다운로드 기능을 사용하려면 이 폴더에 두 개의 실행파일이 필요합니다.

1) yt-dlp.exe
   다운로드: https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
   메뉴 안에서 "🛠 yt-dlp 업데이트" 항목으로 자동 업데이트할 수도 있습니다.

2) ffmpeg.exe
   다운로드: https://www.gyan.dev/ffmpeg/builds/
   "release essentials" 빌드 → 압축 해제 후 bin 폴더 안의 ffmpeg.exe 만 이 폴더에 복사하세요.

배치 후 폴더 구조 예:
   <프로젝트 루트>/
       bin/
           yt-dlp.exe
           ffmpeg.exe
           README.txt   <-- 이 파일

설정으로 다른 위치를 쓰고 싶다면 config.json 의 "youtube_bin_dir" 값을 절대경로로 지정하세요.
