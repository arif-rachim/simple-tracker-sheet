# Simple Tracker Sheet

Tracker issue sederhana berbentuk grid, satu file HTML, tanpa server.

## Menjalankan server

Butuh Python 3.8+ saja (tanpa install library apa pun):

```bash
python3 server.py                 # buka http://localhost:8000
python3 server.py --port 9000     # port lain
python3 server.py --set-pin       # set / reset PIN (ditanya), misalnya kalau lupa
python3 server.py --set-pin 5678  # set / reset PIN langsung
```

Orang lain di jaringan yang sama bisa membuka `http://<IP-komputer-server>:8000`.
Semua orang melihat dan mengedit data yang sama; perubahan dari orang lain muncul otomatis dalam beberapa detik.
Data disimpan di `data/tracker.json` (backup = copy file itu); PIN disimpan sebagai hash di `data/pin.json`.

Kalau `index.html` dibuka langsung tanpa server, aplikasi tetap jalan tapi data hanya tersimpan di browser itu
(status di kanan atas: *Saved in this browser only*). Untuk memindahkan data lama ke server: Export Excel dari
versi browser, lalu Import Excel di halaman server.

## Cara pakai

- **+ Add Issue**: tambah baris baru (Issue Name, Description, Status, Priority, Labels, Assignee, Approved By).
- **Status tersimpan atau belum**: badge di kanan atas menunjukkan *● Not saved yet* (kuning), *⟳ Saving…* (biru),
  *✓ All changes saved* (hijau), atau pesan merah kalau gagal. Baris yang perubahannya belum sampai ke server
  ditandai **●** kuning di kolom `#`, dan judul tab diawali `●`. Tutup halaman setelah muncul *✓ All changes saved*.
  Klik badge itu untuk menyimpan sekarang juga lalu mencocokkan dengan data di server: hasilnya
  *✓ All changes saved · checked jam:menit:detik*, atau *Server differs: #…* kalau versi di server berbeda
  (biasanya karena orang lain baru mengubah baris itu; reload halaman untuk melihatnya).
  Perubahan dikirim ±0,5 detik setelah berhenti mengetik (paling lambat 2 detik walau terus mengetik), dan langsung dikirim
  saat tab ditutup/di-reload/disembunyikan.
- **Status**: ketik bebas seperti Assignee; saran *Open*, *In Progress*, *Blocked*, *Done* plus status yang sudah pernah dipakai.
  Daftar saran ada di konstanta `STATUSES` di `index.html`.
- **Priority**: pilih *Critical*, *High*, *Medium*, *Low* (atau kosong). Daftar ada di konstanta `PRIORITIES`.
- **Urutan (sort)**: dropdown *Sort* di baris filter: *Priority* (default; Critical dulu, yang kosong paling bawah),
  *Manual order*, *Status*, *Assignee*, *Newest first*, *Oldest first*. Pilihan sort diingat per browser.
- **Drag & drop baris** (saat unlocked, di sort *Priority* atau *Manual order*): tarik ikon **⠿** di kolom `#`.
  Di sort *Priority*, baris hanya bisa dipindah di antara baris dengan priority yang sama. Urutan ini tersimpan di server.
- **Lebar kolom**: tarik tepi kanan judul kolom untuk resize, double-click untuk kembali ke lebar awal.
  Lebar kolom diingat per browser.
- **Labels**: ketik lalu tekan `Enter` atau `,`, atau pilih dari saran label yang sudah ada. Satu issue bisa punya banyak label. `×` untuk hapus.
- **Label bertipe** (`tipe:nilai`), contoh `status:open`, `status:closed`, `priority:high`. Tampil dua bagian (tipe | nilai).
  Satu issue hanya punya satu nilai per tipe: menambah `status:closed` otomatis mengganti `status:open`.
- **Filter**: pilih label dari dropdown *Filter by label* (dikelompokkan per tipe, dengan jumlah issue), atau klik label di grid.
  Label dengan tipe yang sama = salah satu cocok (OR), tipe berbeda = semua harus cocok (AND).
  Contoh: `status:open` + `status:in-progress` + `feature` → issue *feature* yang open **atau** in-progress.
  Bisa juga filter per assignee (termasuk *Unassigned*), status, priority, dan cari teks bebas.
- **Format** (toolbar muncul saat unlocked): klik sel, atau blok sebagian teksnya, lalu pilih
  **B** (bold), **I** (italic), **A** (warna teks), **Fill** (warna background sel), atau **Clear** (hapus format).
  Tanpa blok teks, format berlaku untuk seluruh sel. Ctrl+B / Ctrl+I juga bisa saat mengetik.
  Bold/italic/warna teks berlaku untuk Issue Name dan Description; warna background untuk semua kolom.
- **Approved By**: pilih *Capt Mohamed* atau *Capt Abdullah*; sel menampilkan "✔ Approved by Capt …" (atau *Not approved*).
  Bisa difilter (Not approved / Approved / per kapten). Daftar approver ada di konstanta `APPROVERS` di `index.html`.
- **Manage Labels** (perlu PIN): lihat semua label per tipe dan jumlah issue-nya, lalu
  - **Add**: buat label baru tanpa harus dipasang ke issue (langsung muncul di saran);
  - **Rename**: ganti nama di semua issue sekaligus, misalnya `status:done` → `status:closed`. Kalau nama barunya sudah ada, kedua label digabung;
  - **Delete**: hapus label dari semua issue.
- **Assignee**: ketik nama; nama yang sudah pernah dipakai muncul sebagai saran.
- **Export Excel**: download `.xlsx` (kolom: ID, Issue Name, Description, Status, Priority, Labels, Assignee, Approved By; label dipisah koma; baris sesuai urutan sort saat ini), termasuk format bold/italic/warna teks dan warna background sel, plus sheet `Labels` berisi daftar semua label supaya label yang belum dipakai ikut tersimpan.
- **Import Excel**: baca sheet pertama dari `.xlsx`/`.xls`/`.csv` dengan header yang sama, lalu pilih *Append* atau *Replace all*.

## PIN

Data defaultnya **read-only**. Untuk mengubah (tambah, edit, hapus, import, manage labels) harus masukkan PIN 4–8 digit.
PIN default **1234**; sebaiknya diganti lewat **Change PIN**. Klik **Lock** untuk mengunci lagi; otomatis terkunci setelah 10 menit tidak aktif
atau saat halaman di-reload. PIN bisa diganti lewat **Change PIN** saat sedang unlocked.

Dengan server, PIN dicek di server: tanpa PIN, server menolak semua perubahan. Setelah 5 PIN salah, perangkat itu
harus menunggu 5 menit. Lupa PIN: jalankan `python3 server.py --set-pin 1234` di komputer server.

Excel `.xlsx` diproses dengan [ExcelJS](https://github.com/exceljs/exceljs) 4.4.0 (`vendor/exceljs.min.js`) supaya format ikut tersimpan;
`.xls`/`.csv` dibaca dengan [SheetJS](https://sheetjs.com) 0.20.3 (`vendor/xlsx.full.min.js`), tanpa format.
