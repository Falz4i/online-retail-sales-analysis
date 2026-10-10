# Analisis penjualan toko online

Proyek belajar data science menggunakan **UCI Online Retail**. Hasilnya berupa notebook, grafik, tabel ringkasan, dan laporan dalam bahasa Indonesia.

## Pertanyaan yang dijawab

1. Kapan nilai penjualan tinggi, dan bagaimana tren bulanannya?
2. Produk mana yang terlaris berdasarkan unit dan nilai penjualan?
3. Seberapa sering pelanggan berbelanja, dan bagaimana ringkasan RFM mereka?

## Mulai belajar

Buka `notebooks/01_analisis_penjualan.ipynb`, lalu baca dan jalankan sel dari atas ke bawah. Notebook menyertakan penjelasan pembersihan dan latihan lanjutan. Laporan hasil ada di `reports/hasil_analisis.md`.

Setelah clone dari GitHub, jalankan langkah Docker atau pipeline Python di bawah sebelum menjalankan sel notebook. Dataset dan tabel olahan tidak disimpan di repository; pipeline mengunduh sumber UCI dan membuatnya kembali. Notebook menyimpan contoh output, sedangkan [laporan hasil](reports/hasil_analisis.md) dan grafik ikut disimpan untuk melihat hasil tanpa menjalankan kode.

Dataset terdiri dari item invoice toko berbasis Inggris, 1 Desember 2010–9 Desember 2011. Mata uang **GBP**. Ini bukan data toko Indonesia atau data penjualan terkini.

## Menjalankan dengan Docker

Gunakan Docker Desktop dengan Linux containers. Dari folder proyek:

```powershell
docker compose up --build
```

Saat pertama kali dijalankan, Docker mengunduh image Python dan memasang dependensi. Container memakai dataset lokal jika sudah tersedia, menjalankan ulang analisis, membuat grafik, lalu membuka JupyterLab. Membaca workbook dapat memerlukan sekitar satu menit, tergantung komputer.

Buka [JupyterLab lokal](http://localhost:8888/lab), lalu masukkan token dari log terminal. Atau buka URL `http://127.0.0.1:8888/lab?token=...` yang muncul di log. Autentikasi token tetap aktif. Di panel file JupyterLab, buka `notebooks/01_analisis_penjualan.ipynb`.

Folder proyek dihubungkan ke `/workspace` dalam container. Perubahan notebook, tabel, dan laporan tersimpan di folder proyek Windows. Dataset tidak dimasukkan ke image. Hentikan server dengan `Ctrl+C`, lalu bersihkan container proyek:

```powershell
docker compose down
```

Untuk menjalankan analisis tanpa membuka JupyterLab, bangun image terlebih dahulu dan jalankan:

```powershell
docker compose build
docker compose run --rm lab python -m src.download_data
docker compose run --rm lab python -m src.analyze
docker compose run --rm lab python -m src.plot_figures
```

Jika port 8888 sedang digunakan, ubah port di kiri pada `compose.yaml` menjadi `127.0.0.1:8889:8888` dan buka `http://localhost:8889/lab`. Jika koneksi ke Docker engine gagal, pastikan Docker Desktop sudah berjalan dan memakai Linux containers.

Referensi: [bind mounts Docker Compose](https://docs.docker.com/reference/compose-file/services/), [port localhost](https://docs.docker.com/engine/network/port-publishing/), dan [autentikasi Jupyter Server](https://jupyter-server.readthedocs.io/en/latest/operators/security.html).

## Menjalankan tanpa Docker

Gunakan Python 3.11 atau lebih baru. Dari folder proyek:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.download_data
.\.venv\Scripts\python.exe -m src.analyze
.\.venv\Scripts\python.exe -m src.plot_figures
.\.venv\Scripts\python.exe -m jupyterlab
```

Unduhan membutuhkan koneksi internet. Jika workbook sudah ada di `data/raw/Online Retail.xlsx`, proses unduhan melewatinya. Pipeline membaca workbook asli setiap kali dijalankan; data mentah tidak ditimpa.

## Isi proyek

- `src/analyze.py`: pembersihan, agregasi, RFM, dan rekonsiliasi nilai.
- `src/plot_figures.py`: grafik berdasarkan tabel hasil.
- `notebooks/01_analisis_penjualan.ipynb`: alur belajar interaktif.
- `data/processed/`: tabel bulanan, produk, negara, RFM, kualitas data, dan ringkasan.
- `reports/hasil_analisis.md`: hasil, interpretasi, dan batasan.

## Aturan analisis

Satu baris adalah satu item invoice. Pesanan dihitung berdasarkan `InvoiceNo` unik, bukan jumlah baris. Penjualan kotor memakai kuantitas dan harga positif, tanpa invoice pembatalan `C`. Kredit dengan kuantitas negatif dilaporkan terpisah. Net tercatat adalah penjualan kotor dikurangi kredit, bukan laba.

Duplikat persis dihapus sebagai asumsi kerja dan dampaknya dilaporkan. CustomerID kosong tetap masuk analisis penjualan, tetapi tidak masuk analisis pelanggan. Ranking produk memakai StockCode lima digit dengan akhiran huruf opsional, sehingga kode layanan tidak ikut ranking. Desember 2011 merupakan bulan parsial. Persentase pertumbuhan terhadap bulan parsial tidak ditampilkan.

RFM: Recency adalah hari sejak pembelian terakhir, Frequency adalah jumlah invoice unik, Monetary adalah gross selama periode observasi. Tanggal acuan sehari setelah tanggal terakhir dalam dataset. Belum ada clustering, prediksi, atau klaim sebab-akibat.

## Sumber

Chen, D. (2015). [Online Retail, UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/352/online+retail). [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33). Lisensi CC BY 4.0.

## Latihan berikutnya

1. Bandingkan ranking berdasarkan unit dan nilai: apakah produk yang sama selalu teratas?
2. Hitung median nilai invoice untuk melihat pengaruh pesanan grosir terhadap rata-rata.
3. Analisis United Kingdom saja, lalu bandingkan dengan seluruh negara.
4. Setelah memahami hasil, tambahkan dashboard atau segmentasi pelanggan dengan tujuan yang jelas.
