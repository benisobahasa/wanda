# Lembar kerja dialek

`pantura-rembang.csv` berisi semua kata standar di kamus Wanda dengan kolom kosong untuk bentuk di dialek Pantura Rembang.
Buka di Excel, Google Sheets, atau Numbers.

1. Isi kolom `dialect_form`: bentuk kata itu di dialek Anda, atau `=` jika sama dengan bentuk standar.
2. Kosongkan baris yang Anda tidak yakin. Jangan menebak: hanya yang Anda ketik yang akan diimpor.
3. Isi `dialect_variants` (pisahkan dengan titik koma), `pronunciation_note`, dan `notes` jika ada.
4. Simpan sebagai CSV (UTF-8), lalu: `wanda dialect-import pantura-rembang.csv --dry-run`, periksa hasilnya, dan ulangi tanpa `--dry-run`.
5. Jalankan `wanda check` dan `python scripts/build_web.py`, lalu commit.

Kata hasil impor berstatus `unreviewed` sampai penutur lain mereviewnya.
