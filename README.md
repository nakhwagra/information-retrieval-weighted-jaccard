# Smart Retrieval System: Weighted Jaccard Similarity & Nazief-Adriani Stemming

Sistem Temu Balik Informasi (*Information Retrieval*) berbasis web yang dibangun menggunakan **Python** dan **Streamlit**. Aplikasi ini dirancang untuk mencari dokumen yang paling relevan berdasarkan kueri pengguna dengan menerapkan teknik pemrosesan bahasa alami (NLP) khusus Bahasa Indonesia.

## 🚀 Fitur Utama
* **Multi-Format Extraction**: Mendukung pembacaan dokumen berformat `.pdf`, `.docx`, dan `.txt`.
* **Preprocessing Terintegrasi**:
    * **Case Folding**: Menyeragamkan teks menjadi huruf kecil.
    * **Tokenizing**: Memecah kalimat menjadi kumpulan kata (token).
    * **Stopword Removal**: Menghapus kata umum yang tidak informatif menggunakan daftar kata dasar Bahasa Indonesia.
    * **Nazief & Adriani Stemming**: Algoritma stemming tingkat lanjut dengan mekanisme *safety-net* dan iterasi *prefix* hingga 3 kali untuk menangani imbuhan bertumpuk.
* **Weighted Jaccard Similarity**: Algoritma perhitungan kemiripan yang mempertimbangkan bobot frekuensi kemunculan kata (*Term Frequency*), memberikan hasil yang lebih akurat dibandingkan Jaccard standar.
* **Analisis Visual**: Dilengkapi dengan visualisasi **Heatmap** untuk sebaran kata dan **Word Cloud** untuk kata kunci dominan.

## 🛠️ Cara Menjalankan
1. Clone repositori ini:
   ```bash
   git clone [https://github.com/nakhwagra/information-retrieval-weighted-jaccard.git](https://github.com/nakhwagra/information-retrieval-weighted-jaccard.git)
   
2. Instal pustaka yang dibutuhkan:
   ```bash
   pip install -r requirements.txt

3. Dataset yang dibutuhkan :
   ```bash
   https://drive.google.com/drive/folders/1Gbp3FfNJlJzUsBvUyDjOu5oynM9C0mo2

4. Jalankan aplikasi :
   ```bash
   python -m streamlit run ui/app.py

## 👥 Kelompok 7 - Kelas EE (Informatika Itenas)
* Shafira Aprillia (152023170)
* Nakhwa Ghinayah Rahadatul Aisy (152023171)
* Melvina Cheda Rismayanta (152023175)
* Siti Raudatul Jannah Fadilah (152023179)
  




