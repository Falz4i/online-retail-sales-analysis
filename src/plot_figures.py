"""Buat grafik dari tabel hasil analisis: python -m src.plot_figures."""
from pathlib import Path
import textwrap
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]


def plot():
    data = ROOT / "data/processed"
    output = ROOT / "reports/figures"
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    monthly = pd.read_csv(data / "monthly_sales.csv")
    products = pd.read_csv(data / "products.csv", dtype={"StockCode": "string"})
    customers = pd.read_csv(data / "customers_rfm.csv")
    fig, ax = plt.subplots(figsize=(12, 5.5), layout="constrained")
    x = range(len(monthly))
    colors = ["#d99536" if partial else "#237b83" for partial in monthly["PartialCoverage"]]
    ax.bar(x, monthly["GrossSalesGBP"], color=colors, label="Penjualan kotor")
    ax.plot(x, monthly["NetRecordedGBP"], color="#343e55", marker="o", label="Net tercatat setelah kredit")
    ax.set_xticks(list(x), monthly["Month"], rotation=45, ha="right")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y / 1e6:.1f}"))
    ax.set_ylabel("Juta GBP")
    ax.set_title("Penjualan bulanan | Desember 2011 hanya sampai tanggal 9", loc="left", pad=15)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.15)
    fig.savefig(output / "monthly_sales.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), layout="constrained")
    for ax, metric, title, xlabel in zip(axes, ["GrossSalesGBP", "Units"], ["10 produk menurut nilai penjualan", "10 produk menurut unit terjual"], ["GBP", "Unit"]):
        top = products.nlargest(10, metric).sort_values(metric)
        labels = ["\n".join(textwrap.wrap(str(v), 25)) for v in top["Description"]]
        ax.barh(labels, top[metric], color="#237b83")
        ax.set_title(title, loc="left", pad=15)
        ax.set_xlabel(xlabel)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.tick_params(axis="y", labelsize=9)
        ax.grid(axis="x", alpha=0.15)
    fig.savefig(output / "top_products.png", dpi=160)
    plt.close(fig)

    groups = pd.cut(customers["Frequency"], bins=[0, 1, 2, 5, 10, float("inf")], labels=["1", "2", "3–5", "6–10", "11+"])
    counts = groups.value_counts(sort=False)
    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    bars = ax.bar(counts.index.astype(str), counts, color="#237b83")
    ax.bar_label(bars, padding=4)
    ax.set_xlabel("Jumlah invoice penjualan selama periode observasi")
    ax.set_ylabel("Jumlah pelanggan teridentifikasi")
    ax.set_title("Frekuensi belanja pelanggan", loc="left", pad=15)
    ax.set_ylim(0, counts.max() * 1.15)
    ax.grid(axis="y", alpha=0.15)
    fig.savefig(output / "customer_frequency.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    plot()
