"""Analisis deskriptif yang dapat dijalankan ulang: python -m src.analyze."""
from pathlib import Path
import hashlib
import json
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://archive.ics.uci.edu/dataset/352/online+retail"


def load_data(root=ROOT):
    # Selalu baca workbook sumber. Cache lokal tidak dipakai sebagai sumber analisis.
    return pd.read_excel(root / "data/raw/Online Retail.xlsx", engine="openpyxl")


def prepare_data(raw):
    """Deduplicasi adalah asumsi eksplisit; dampak nilai juga dilaporkan."""
    data = raw.drop_duplicates().copy()
    for col in ("InvoiceNo", "StockCode"):
        data[col] = data[col].astype("string").str.strip()
    data["Description"] = data["Description"].astype("string").str.strip()
    data["CustomerID"] = pd.to_numeric(data["CustomerID"], errors="raise").astype("Int64")
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="raise")
    data["LineValueGBP"] = data["Quantity"] * data["UnitPrice"]
    data["IsCancellation"] = data["InvoiceNo"].str.upper().str.startswith("C").fillna(False)
    valid = data["InvoiceDate"].notna() & data["InvoiceNo"].notna() & data["UnitPrice"].gt(0)
    sales = data.loc[valid & data["Quantity"].gt(0) & ~data["IsCancellation"]].copy()
    credits = data.loc[valid & data["Quantity"].lt(0)].copy()
    ambiguous = data.loc[valid & data["Quantity"].gt(0) & data["IsCancellation"]].copy()
    sales["Month"] = sales["InvoiceDate"].dt.to_period("M").astype(str)
    return data, sales, credits, ambiguous


def summarize(data, sales, credits):
    gross = float(sales["LineValueGBP"].sum())
    monthly = sales.groupby("Month").agg(
        GrossSalesGBP=("LineValueGBP", "sum"),
        Orders=("InvoiceNo", "nunique"),
        Units=("Quantity", "sum"),
        ObservedTradingDays=("InvoiceDate", lambda x: x.dt.normalize().nunique()),
    )
    monthly["CreditsGBP"] = -credits.groupby(credits["InvoiceDate"].dt.to_period("M").astype(str))["LineValueGBP"].sum()
    monthly["CreditsGBP"] = monthly["CreditsGBP"].fillna(0)
    monthly["NetRecordedGBP"] = monthly["GrossSalesGBP"] - monthly["CreditsGBP"]
    start, end = data["InvoiceDate"].min(), data["InvoiceDate"].max()
    # Boundary months only: coverage says nothing about sales on inactive dates.
    monthly["PartialCoverage"] = False
    if start.day != 1:
        monthly.loc[str(start.to_period("M")), "PartialCoverage"] = True
    if end.day != end.days_in_month:
        monthly.loc[str(end.to_period("M")), "PartialCoverage"] = True
    monthly["AOV_GBP"] = monthly["GrossSalesGBP"] / monthly["Orders"]
    monthly["MoM_GrossPct"] = monthly["GrossSalesGBP"].pct_change().mul(100)
    for i in range(1, len(monthly)):
        if monthly["PartialCoverage"].iloc[i] or monthly["PartialCoverage"].iloc[i - 1]:
            monthly.iloc[i, monthly.columns.get_loc("MoM_GrossPct")] = float("nan")

    # Ranking produk mengecualikan POST, DOT, M, D, BANK CHARGES dan kode layanan.
    goods = sales.loc[sales["StockCode"].str.fullmatch(r"\d{5}[A-Za-z]*", na=False)]
    products = goods.groupby("StockCode").agg(
        GrossSalesGBP=("LineValueGBP", "sum"), Units=("Quantity", "sum"), Orders=("InvoiceNo", "nunique")
    )
    names = goods.dropna(subset=["Description"]).groupby("StockCode")["Description"].agg(lambda x: x.mode().iloc[0])
    products.insert(0, "Description", names)
    products = products.sort_values("GrossSalesGBP", ascending=False)
    countries = sales.groupby("Country").agg(GrossSalesGBP=("LineValueGBP", "sum"), Orders=("InvoiceNo", "nunique"))
    countries["GrossSharePct"] = countries["GrossSalesGBP"] / gross * 100
    countries = countries.sort_values("GrossSalesGBP", ascending=False)

    identified = sales.dropna(subset=["CustomerID"])
    reference = end.normalize() + pd.Timedelta(days=1)
    customers = identified.groupby("CustomerID").agg(
        LastPurchase=("InvoiceDate", "max"), Frequency=("InvoiceNo", "nunique"), MonetaryGBP=("LineValueGBP", "sum")
    )
    customers["RecencyDays"] = (reference - customers["LastPurchase"].dt.normalize()).dt.days
    customers["RepeatedInObservedPeriod"] = customers["Frequency"].ge(2)
    customers = customers.sort_values("MonetaryGBP", ascending=False)
    repeat_rate = float(customers["RepeatedInObservedPeriod"].mean() * 100)
    summary = {
        "gross_sales_gbp": gross,
        "recorded_credits_gbp": float(-credits["LineValueGBP"].sum()),
        "net_recorded_gbp": float(gross + credits["LineValueGBP"].sum()),
        "orders": int(sales["InvoiceNo"].nunique()),
        "aov_gbp": gross / sales["InvoiceNo"].nunique(),
        "identified_customers": int(len(customers)),
        "repeat_customer_pct": repeat_rate,
        "gross_sales_without_customer_id_gbp": float(sales.loc[sales["CustomerID"].isna(), "LineValueGBP"].sum()),
        "start": str(start), "end": str(end), "rfm_reference_date": str(reference.date()),
        "non_product_gross_gbp": float(gross - goods["LineValueGBP"].sum()),
        "source": SOURCE,
    }
    # Rekonsiliasi antar-agregasi: kegagalan menghentikan pipeline.
    for table in (monthly, countries):
        if not math.isclose(float(table["GrossSalesGBP"].sum()), gross, abs_tol=0.01):
            raise AssertionError("Agregasi penjualan tidak cocok dengan nilai baris.")
    known = float(identified["LineValueGBP"].sum())
    if not math.isclose(float(customers["MonetaryGBP"].sum()), known, abs_tol=0.01):
        raise AssertionError("Agregasi pelanggan tidak cocok.")
    if not sales["Quantity"].gt(0).all() or sales["IsCancellation"].any():
        raise AssertionError("Transaksi penjualan tidak valid.")
    return monthly, products, countries, customers, summary


def write_report(summary, quality, monthly, products, countries):
    full = monthly.loc[~monthly["PartialCoverage"]]
    peak = full["GrossSalesGBP"].idxmax()
    top = products.iloc[0]
    uk_share = countries.loc["United Kingdom", "GrossSharePct"]
    report = f"""# Analisis penjualan toko online

## Pertanyaan proyek
1. Bagaimana tren nilai penjualan bulanan?
2. Produk mana yang paling laku menurut unit dan nilai penjualan?
3. Bagaimana frekuensi dan nilai belanja pelanggan yang dapat diidentifikasi?

## Data dan definisi
Sumber: [UCI Online Retail]({SOURCE}), Daqing Chen (2015), DOI 10.24432/C5BW33, lisensi CC BY 4.0.
Toko berbasis Inggris dengan banyak pelanggan grosir. Rentang: {summary['start']} sampai {summary['end']}.
Satu baris merupakan item dalam invoice, bukan satu pesanan. Semua nilai uang dalam GBP.
Nilai penjualan kotor (gross) = Quantity × UnitPrice untuk kuantitas dan harga positif, tanpa invoice C.
Nilai ini mencakup tagihan layanan seperti ongkir. Ranking produk hanya memakai kode lima digit dengan akhiran huruf opsional.
Kredit tercatat = nilai absolut baris berkuantitas negatif dengan harga positif. Net tercatat = gross dikurangi kredit tersebut.
Kredit tidak dicocokkan dengan invoice asal. Net ini bukan laba atau ukuran akuntansi audited.
Rata-rata pesanan (AOV) = gross / jumlah invoice penjualan unik.

## Hasil awal
- Baris sumber: {quality['raw_rows']:,}; duplikat persis: {quality['duplicate_rows']:,}.
- Baris penjualan setelah aturan pembersihan: {quality['sales_rows']:,}.
- Gross: GBP {summary['gross_sales_gbp']:,.2f}; kredit: GBP {summary['recorded_credits_gbp']:,.2f}; net tercatat: GBP {summary['net_recorded_gbp']:,.2f}.
- Pesanan unik: {summary['orders']:,}; AOV: GBP {summary['aov_gbp']:,.2f}.
- Bulan dengan gross tertinggi di antara bulan dengan cakupan penuh: **{peak}**, GBP {full.loc[peak, 'GrossSalesGBP']:,.2f}.
- Produk dengan nilai penjualan tertinggi: **{top['Description']}** ({products.index[0]}), GBP {top['GrossSalesGBP']:,.2f}.
- United Kingdom menyumbang {uk_share:.1f}% dari gross.
- Pelanggan teridentifikasi: {summary['identified_customers']:,}; {summary['repeat_customer_pct']:.1f}% memiliki minimal dua invoice penjualan selama periode observasi.
- Penjualan tanpa CustomerID: GBP {summary['gross_sales_without_customer_id_gbp']:,.2f}. Baris ini tetap dihitung untuk analisis penjualan, tetapi dikeluarkan dari analisis pelanggan.

## Visualisasi
![Tren penjualan](figures/monthly_sales.png)

Desember 2011 hanya tercakup sampai 9 Desember. Penurunannya tidak dapat disimpulkan sebagai penurunan bisnis satu bulan penuh.

![Produk teratas berdasarkan nilai dan unit](figures/top_products.png)

![Frekuensi belanja](figures/customer_frequency.png)

## Keputusan pembersihan dan keterbatasan
- Duplikat persis dihapus sebagai asumsi kerja. Tanpa ID item invoice, sebagian pengulangan mungkin sah. Selisih gross sebelum/sesudah deduplikasi: GBP {quality['gross_removed_by_dedup_gbp']:,.2f}.
- Deskripsi dan CustomerID kosong tidak diisi dengan nilai buatan. Label produk memakai deskripsi yang paling sering muncul untuk StockCode.
- Harga nol/negatif dan kuantitas nol dikeluarkan dari analisis nilai penjualan. Invoice pembatalan C dan baris kuantitas negatif diperiksa terpisah.
- CustomerID hanya memungkinkan analisis pelanggan yang teridentifikasi. Belanja berulang di sini bukan retensi cohort, churn, atau bukti loyalitas jangka panjang.
- RFM adalah ringkasan recency, frequency, monetary. Tanggal acuan historis: {summary['rfm_reference_date']}. Monetary memakai gross, bukan net.
- Satu tahun data tidak cukup untuk membuktikan pola musiman yang konsisten. Grosir, pembelian besar, dan kode layanan dapat memengaruhi ranking serta AOV.
- Tidak ada data biaya atau stok, sehingga profitabilitas dan kebutuhan persediaan belum dapat dihitung.
- Ranking produk dan RFM memakai penjualan kotor. Pesanan yang kemudian dibatalkan bisa tetap berkontribusi pada gross. Untuk analisis pembelian yang dipertahankan, perlu pencocokan kredit dengan pesanan asal.

## Tindak lanjut yang didukung analisis
1. Tinjau produk teratas menurut unit dan nilai bersama data stok sebelum menentukan prioritas pengadaan.
2. Telusuri peningkatan penjualan menjelang November dengan membandingkan jumlah pesanan dan AOV. Hubungan dengan promosi atau musim perlu data tambahan.
3. Gunakan tabel RFM untuk mempelajari pelanggan berulang. Evaluasi promosi melalui eksperimen sebelum menyimpulkan dampaknya.

## Belajar berikutnya
Buka notebook dan jalankan sel berurutan. Coba ubah ranking dari nilai penjualan ke unit, lalu jelaskan mengapa hasilnya berbeda.
"""
    (ROOT / "reports/hasil_analisis.md").write_text(report, encoding="utf-8")


def run():
    out = ROOT / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    raw = load_data()
    data, sales, credits, ambiguous = prepare_data(raw)
    monthly, products, countries, customers, summary = summarize(data, sales, credits)
    raw_is_c = raw["InvoiceNo"].astype("string").str.upper().str.startswith("C").fillna(False)
    raw_positive = raw.loc[raw["Quantity"].gt(0) & raw["UnitPrice"].gt(0) & ~raw_is_c]
    quality = {
        "raw_rows": len(raw), "duplicate_rows": int(raw.duplicated().sum()),
        "missing_by_column": {k: int(v) for k, v in raw.isna().sum().items()},
        "deduplicated_rows": len(data), "sales_rows": len(sales), "credit_rows": len(credits),
        "nonpositive_price_rows": int(data["UnitPrice"].le(0).sum()),
        "zero_quantity_rows": int(data["Quantity"].eq(0).sum()),
        "ambiguous_positive_cancellation_rows": len(ambiguous),
        "gross_removed_by_dedup_gbp": float((raw_positive["Quantity"] * raw_positive["UnitPrice"]).sum() - summary["gross_sales_gbp"]),
        "source_sha256": hashlib.sha256((ROOT / "data/raw/Online Retail.xlsx").read_bytes()).hexdigest(),
    }
    for name, table in (("monthly_sales", monthly), ("products", products), ("countries", countries), ("customers_rfm", customers)):
        table.to_csv(out / f"{name}.csv", encoding="utf-8-sig")
    sales.to_csv(out / "sales.csv.gz", index=False, compression="gzip")
    for name, content in (("summary", summary), ("data_quality", quality)):
        (out / f"{name}.json").write_text(json.dumps(content, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    write_report(summary, quality, monthly, products, countries)
    print(json.dumps({"summary": summary, "quality": quality}, indent=2))
    return monthly, products, countries, customers, summary, quality


if __name__ == "__main__":
    run()
