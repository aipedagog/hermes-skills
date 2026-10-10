#!/usr/bin/env python3
"""Сверка текста на слайдах карусели с тем, что просили написать. Ничего не меняет, только читает.

Запуск:  python3 sverka_teksta.py /абсолютный/путь/W/<slug>

Что лежит в папке:
  tekst.md              под заголовками «## Слайд N» строки, которые должны быть на слайде, каждая в «ёлочках»
  prochitano/NN.txt     что на готовом слайде N прочитано глазами модели (vision_analyze), как есть

Ответ: по каждому слайду «совпал» или список расхождений; в конце «ТЕКСТ СОВПАЛ» либо «ЕСТЬ РАСХОЖДЕНИЯ».
Код выхода 0 только когда совпали все слайды.

Почему с поправкой на похожие буквы. Читающая модель путает латинские и русские буквы одного вида:
«AI» приходит как «Al» и «АІ», «В TELEGRAM» как «B TELEGRAM», «3.» рвётся на «3» и точку (замер 10.10.2026,
три ложные тревоги на восьми верных слайдах). Поэтому перед сравнением похожие буквы сводятся к одной,
ё к е, знаки препинания убираются. Настоящую опечатку («СТОРК» вместо «СТРОК») это не прячет.

Отдельно ловится заглавная буква посреди слова («праВильными», первая карусель Гермеса 10.10.2026: сверка без
учёта регистра её пропустила). Слово с такой буквой проходит, только если в tekst.md оно написано так же
(«ChatGPT», «YouTube»).

И висячий предлог: строка из двух и более слов, которая кончается коротким предлогом или союзом
(«Держите примеры с»). Прочитанное сохраняется построчно, поэтому переносы видны.
"""
import argparse
import re
import sys
from pathlib import Path

POHOZHIE = str.maketrans({
    "a": "а", "b": "в", "c": "с", "e": "е", "h": "н", "k": "к", "m": "м", "o": "о", "p": "р",
    "t": "т", "x": "х", "y": "у", "ё": "е", "і": "i", "l": "i",
    "|": " ",  # черта между карточками с цифрами: «3|4» это «3» и «4», а не слово
})


def slova(text: str) -> list[str]:
    text = text.lower().translate(POHOZHIE)
    return re.findall(r"[0-9a-zа-я]+", text)


def s_registrom(text: str) -> list[tuple[str, tuple[bool, ...]]]:
    """Слова как в slova(), но с рисунком регистра: какие буквы заглавные."""
    return [(slova(s)[0], tuple(b.isupper() for b in s))
            for s in re.findall(r"[0-9A-Za-zА-Яа-яЁёІі]+", text) if slova(s)]


def zaglavnye_vnutri(prochitano: str, frazy: list[str]) -> list[str]:
    mozhno = {para for fraza in frazy for para in s_registrom(fraza)}
    naydeno = []
    for syroe in re.findall(r"[0-9A-Za-zА-Яа-яЁёІі]+", prochitano):
        if not re.search(r"[a-zа-яё][A-ZА-ЯЁ]", syroe) or not slova(syroe):
            continue
        if (slova(syroe)[0], tuple(b.isupper() for b in syroe)) not in mozhno:
            naydeno.append(syroe)
    return list(dict.fromkeys(naydeno))


VISYACHIE = {"а", "и", "в", "к", "о", "с", "у", "я", "на", "но", "по", "за", "из", "от", "до", "об", "во", "со", "не"}


def visyachie_predlogi(prochitano: str) -> list[str]:
    stroki = [s.strip() for s in prochitano.splitlines() if s.strip()]
    naydeno = []
    for stroka in stroki[:-1]:
        slova_stroki = re.findall(r"[0-9A-Za-zА-Яа-яЁё]+", stroka)
        if len(slova_stroki) >= 2 and stroka[-1].isalpha() and slova_stroki[-1].lower() in VISYACHIE:
            naydeno.append(stroka)
    return naydeno


def ozhidaemoe(tekst_md: str) -> dict[int, list[str]]:
    po_slaydam: dict[int, list[str]] = {}
    nomer = None
    for stroka in tekst_md.splitlines():
        m = re.match(r"\s*##\s*Слайд\s+(\d+)", stroka, flags=re.I)
        if m:
            nomer = int(m.group(1))
            po_slaydam[nomer] = []
            continue
        if nomer is not None:
            po_slaydam[nomer].extend(re.findall(r"«([^«»]+)»", stroka))
    return po_slaydam


def est_podryad(chto: list[str], gde: list[str]) -> bool:
    n = len(chto)
    return n == 0 or any(gde[i:i + n] == chto for i in range(len(gde) - n + 1))


def main() -> int:
    razbor = argparse.ArgumentParser(description="Сверить текст на слайдах карусели с tekst.md (только чтение)")
    razbor.add_argument("papka", type=Path, help="папка карусели: в ней tekst.md и prochitano/NN.txt")
    a = razbor.parse_args()

    fayl = a.papka / "tekst.md"
    if not fayl.is_file():
        print(f"НЕТ {fayl}: сначала запиши тексты слайдов.")
        return 2
    nado = ozhidaemoe(fayl.read_text(encoding="utf-8"))
    if not nado:
        print("В tekst.md нет ни одного заголовка «## Слайд N» со строками в «ёлочках».")
        return 2

    plokho = 0
    for nomer in sorted(nado):
        prochitano = a.papka / "prochitano" / f"{nomer:02d}.txt"
        if not prochitano.is_file():
            print(f"Слайд {nomer}: НЕТ {prochitano.name}: слайд не прочитан.")
            plokho += 1
            continue
        syroy_tekst = prochitano.read_text(encoding="utf-8")
        est = slova(syroy_tekst)
        zamechaniya = []
        razresheno: set[str] = set()
        for fraza in nado[nomer]:
            nuzhno = slova(fraza)
            razresheno.update(nuzhno)
            if not est_podryad(nuzhno, est):
                zamechaniya.append(f"нет строки «{fraza}»")
        lishnee = [s for s in est if len(s) >= 3 and s not in razresheno]
        if lishnee:
            zamechaniya.append("лишний текст на слайде: " + " ".join(dict.fromkeys(lishnee)))
        vnutri = zaglavnye_vnutri(syroy_tekst, nado[nomer])
        if vnutri:
            zamechaniya.append("заглавная буква посреди слова: " + " ".join(vnutri))
        visyat = visyachie_predlogi(syroy_tekst)
        if visyat:
            zamechaniya.append("предлог в конце строки: " + "; ".join(f"«{s}»" for s in visyat))
        if zamechaniya:
            plokho += 1
            print(f"Слайд {nomer}: РАСХОЖДЕНИЕ: " + "; ".join(zamechaniya))
        else:
            print(f"Слайд {nomer}: совпал ({len(nado[nomer])} строк)")
    print("ТЕКСТ СОВПАЛ" if not plokho else f"ЕСТЬ РАСХОЖДЕНИЯ: слайдов {plokho} из {len(nado)}")
    return 0 if not plokho else 1


if __name__ == "__main__":
    sys.exit(main())
