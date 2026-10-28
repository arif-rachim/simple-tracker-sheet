# Simple Tracker Sheet

Tracker issue sederhana berbentuk grid, satu file HTML, tanpa server.

## Cara pakai

Buka `index.html` di browser (folder `vendor/` harus ikut).

- **+ Add Issue**: tambah baris baru (Issue Name, Description, Labels, Assignee).
- **Labels**: ketik lalu tekan `Enter` atau `,`, atau pilih dari saran label yang sudah ada. Satu issue bisa punya banyak label. `×` untuk hapus.
- **Label bertipe** (`tipe:nilai`), contoh `status:open`, `status:closed`, `priority:high`. Tampil dua bagian (tipe | nilai).
  Satu issue hanya punya satu nilai per tipe: menambah `status:closed` otomatis mengganti `status:open`.
- **Filter**: pilih label dari dropdown *Filter by label* (dikelompokkan per tipe, dengan jumlah issue), atau klik label di grid.
  Label dengan tipe yang sama = salah satu cocok (OR), tipe berbeda = semua harus cocok (AND).
  Contoh: `status:open` + `status:in-progress` + `feature` → issue *feature* yang open **atau** in-progress.
  Bisa juga filter per assignee (termasuk *Unassigned*) dan cari teks bebas.
- **Format** (toolbar muncul saat unlocked): klik sel, atau blok sebagian teksnya, lalu pilih
  **B** (bold), **I** (italic), **A** (warna teks), **Fill** (warna background sel), atau **Clear** (hapus format).
  Tanpa blok teks, format berlaku untuk seluruh sel. Ctrl+B / Ctrl+I juga bisa saat mengetik.
  Bold/italic/warna teks berlaku untuk Issue Name dan Description; warna background untuk semua kolom.
- **Manage Labels** (perlu PIN): lihat semua label per tipe dan jumlah issue-nya, lalu
  - **Add**: buat label baru tanpa harus dipasang ke issue (langsung muncul di saran);
  - **Rename**: ganti nama di semua issue sekaligus, misalnya `status:done` → `status:closed`. Kalau nama barunya sudah ada, kedua label digabung;
  - **Delete**: hapus label dari semua issue.
- **Assignee**: ketik nama; nama yang sudah pernah dipakai muncul sebagai saran.
- **Export Excel**: download `.xlsx` (kolom: ID, Issue Name, Description, Labels, Assignee; label dipisah koma), termasuk format bold/italic/warna teks dan warna background sel, plus sheet `Labels` berisi daftar semua label supaya label yang belum dipakai ikut tersimpan.
- **Import Excel**: baca sheet pertama dari `.xlsx`/`.xls`/`.csv` dengan header yang sama, lalu pilih *Append* atau *Replace all*.

## PIN

Data defaultnya **read-only**. Untuk mengubah (tambah, edit, hapus, import) harus masukkan PIN 4–8 digit.
Pertama kali, aplikasi minta buat PIN. Klik **Lock** untuk mengunci lagi; otomatis terkunci setelah 10 menit tidak aktif
atau saat halaman di-reload. PIN bisa diganti lewat **Change PIN** saat sedang unlocked.

Catatan: data dan PIN (dalam bentuk hash) disimpan di `localStorage` browser. PIN ini kunci sederhana di sisi browser,
bukan pengamanan sebenarnya — siapa pun yang punya akses ke browser/devtools tetap bisa mengubah datanya.
Lupa PIN: hapus key `sts.pinHash` di localStorage (data issue tetap aman).

Excel `.xlsx` diproses dengan [ExcelJS](https://github.com/exceljs/exceljs) 4.4.0 (`vendor/exceljs.min.js`) supaya format ikut tersimpan;
`.xls`/`.csv` dibaca dengan [SheetJS](https://sheetjs.com) 0.20.3 (`vendor/xlsx.full.min.js`), tanpa format.
