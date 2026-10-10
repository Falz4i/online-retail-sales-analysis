"""Unduh sumber publik tanpa mengubah workbook aslinya."""
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
import shutil

ROOT = Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"


def download():
    folder = ROOT / "data" / "raw"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "Online Retail.xlsx"
    if target.exists():
        return target
    archive = folder / "online_retail.zip"
    temporary = archive.with_suffix(".download")
    with urlopen(URL, timeout=120) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    temporary.replace(archive)
    with ZipFile(archive) as source:
        # Ambil hanya anggota yang diketahui; jangan ekstrak path sembarang.
        member = next(n for n in source.namelist() if Path(n).name == target.name)
        with source.open(member) as stream, target.open("wb") as output:
            shutil.copyfileobj(stream, output)
    return target


if __name__ == "__main__":
    print(download())
