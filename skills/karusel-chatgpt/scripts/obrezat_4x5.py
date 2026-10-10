#!/usr/bin/env python3
"""Готовит нарисованные слайды к выкладке: обрезает до 4:5, сохраняет JPEG 1080x1350 и собирает лист превью.

Запуск:  python3 obrezat_4x5.py /абсолютный/путь/W/<slug>

Берёт  W/<slug>/slaydy/NN.png  (как отдал image_generate: portrait это 1024x1536, то есть 2:3).
Пишет  W/<slug>/gotovo/<slug>-NN.jpg  и  W/<slug>/gotovo/list.jpg.
Исходники не трогает и ничего не удаляет. Готовый файл с тем же именем перезаписывает.

Зачем обрезка. Instagram берёт карусель 4:5. Из кадра 2:3 срезается по 1/12 высоты сверху и снизу
(из 1536 остаётся 1280). Поэтому в запросе на картинку сказано держать верх и низ пустыми.
Имена с именем карусели внутри: одинаковые `slayd-01.jpg` у разных каруселей 09.10.2026 дали чужую обложку.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def ffmpeg_na_meste() -> bool:
    if shutil.which("ffmpeg"):
        return True
    print("НЕТ ffmpeg: без него слайды не обрезать. Поставить на сервере: apt-get install -y ffmpeg "
          "(в Docker это делается внутри контейнера агента). Проверка: ffmpeg -version.")
    return False


def main() -> int:
    razbor = argparse.ArgumentParser(description="Обрезать слайды до 4:5, сохранить JPEG 1080x1350 и лист превью")
    razbor.add_argument("papka", type=Path, help="папка карусели: в ней slaydy/NN.png")
    a = razbor.parse_args()
    if not ffmpeg_na_meste():
        return 2

    papka = a.papka.resolve()
    slaydy = sorted((papka / "slaydy").glob("[0-9][0-9].png"))
    if not slaydy:
        print(f"НЕТ слайдов: жду файлы {papka}/slaydy/01.png, 02.png и дальше.")
        return 2
    gotovo = papka / "gotovo"
    gotovo.mkdir(exist_ok=True)
    slug = papka.name

    for png in slaydy:
        jpg = gotovo / f"{slug}-{png.stem}.jpg"
        # если кадр уже 4:5, crop ничего не срезает: берётся середина нужной высоты
        ffmpeg("-i", str(png), "-vf", "crop=iw:min(ih\\,iw*5/4),scale=1080:1350:flags=lanczos", "-q:v", "2", str(jpg))
        print(f"{png.name} -> {jpg.name}")

    stolbcov = 4
    ryadov = (len(slaydy) + stolbcov - 1) // stolbcov
    # номера идут подряд с 01: шаблон по номеру надёжнее glob (тот спотыкается о скобки в ffmpeg)
    ffmpeg("-start_number", "1", "-i", str(gotovo / f"{slug}-%02d.jpg"),
           "-vf", f"scale=540:675,tile={stolbcov}x{ryadov}:padding=12:margin=12:color=white",
           "-frames:v", "1", "-q:v", "3", str(gotovo / "list.jpg"))
    print(f"ГОТОВО: слайдов {len(slaydy)}, лист {gotovo / 'list.jpg'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
