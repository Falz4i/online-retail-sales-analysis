"""Siapkan hasil analisis sebelum membuka JupyterLab di dalam container."""
import os

from src.download_data import download
from src.analyze import run
from src.plot_figures import plot


def main():
    print("Menyiapkan dataset UCI Online Retail...", flush=True)
    download()
    print("Menjalankan analisis dan membuat grafik...", flush=True)
    run()
    plot()
    print("Analisis selesai. Membuka JupyterLab; gunakan URL bertoken di log.", flush=True)
    os.execvp("jupyter", [
        "jupyter", "lab", "--ip=0.0.0.0", "--port=8888",
        "--ServerApp.port_retries=0", "--no-browser",
        "--ServerApp.root_dir=/workspace",
    ])


if __name__ == "__main__":
    main()
