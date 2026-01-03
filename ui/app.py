import sys
import os
import re
import pandas as pd
import base64
import matplotlib.pyplot as plt
import streamlit as st
import time
import PyPDF2
import tkinter as tk
from tkinter import filedialog
from docx import Document
from streamlit_option_menu import option_menu
from wordcloud import WordCloud
from collections import Counter

from preprocessing.stopword import remove_stopwords
from preprocessing.stemming import stemming
from main import build_indices, preprocess, term_frequency, extract_text
from similarity.weighted_jaccard import weighted_jaccard

# Akses root project
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# ==========================================
# CONFIG & CSS THEME ENGINE
# ==========================================
st.set_page_config(
    page_title="Smart Retrieval System", 
    page_icon="🔍",
    layout="wide"
)

def local_css():
    st.markdown("""
    <style>
        /* 1. Mengubah Warna Header (H1, H2, H3) menjadi Biru Logo */
        h1, h2, h3 {
            color: #0d3b66 !important; /* Biru Tua Elegan */
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
        }
        
        /* 2. Mengubah Warna Divider (Garis Pembatas) menjadi Oranye */
        hr {
            margin-top: 1em;
            margin-bottom: 1em;
            border: 0;
            border-top: 3px solid #FF8C00 !important; /* Oranye Logo */
            opacity: 0.8;
        }

        /* 3. Style Khusus untuk Highlight Teks */
        .highlight-blue {
            color: #007BFF;
            font-weight: bold;
        }
        .highlight-orange {
            color: #FF8C00;
            font-weight: bold;
        }
        
        /* 4. Mempercantik Metrics */
        div[data-testid="stMetricValue"] {
            color: #0d3b66;
        }
        
        /* 5. Sidebar Tweaks */
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================================
# FUNGSI LOAD DOKUMEN MULTI-FORMAT
# ==========================================
def load_documents(folder_path):
    documents = {}
    
    # 1. Cek Folder
    if not os.path.exists(folder_path):
        st.error(f"❌ Folder tidak ditemukan: {folder_path}")
        return {}

    files = os.listdir(folder_path)
    if not files:
        st.warning(f"⚠️ Folder '{folder_path}' kosong.")
        return {}

    # Indikator loading kecil
    status_text = st.empty()
    
    count = 0
    for filename in files:
        file_path = os.path.join(folder_path, filename)
        
        # Lewati jika folder, bukan file
        if not os.path.isfile(file_path):
            continue

        try:
            text = ""
            # --- JIKA FORMAT .TXT ---
            if filename.lower().endswith(".txt"):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            
            # --- JIKA FORMAT .PDF ---
            elif filename.lower().endswith(".pdf"):
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    # Loop setiap halaman PDF
                    for page in pdf_reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
            
            # --- JIKA FORMAT .DOCX (WORD) ---
            elif filename.lower().endswith(".docx"):
                doc = Document(file_path)
                # Loop setiap paragraf di Word
                for para in doc.paragraphs:
                    text += para.text + "\n"

            # Simpan jika ada isinya
            if text.strip():
                documents[filename] = text
                count += 1
                status_text.caption(f"Sedang membaca: {filename}...")
            
        except Exception as e:
            st.warning(f"Gagal membaca {filename}: {e}")

    status_text.empty() # Hapus status loading
    
    if count > 0:
        st.success(f"✅ Berhasil memuat {count} dokumen (PDF/DOCX/TXT).")
    else:
        st.error("❌ Tidak ada file yang valid (PDF/DOCX/TXT) yang bisa dibaca.")
        
    return documents


def show_pdf(file_path):
    """Fungsi untuk menampilkan PDF di dalam Streamlit"""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    # Kode HTML untuk embed PDF (menggunakan iframe)
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def get_custom_progress_bar(score, max_score):
    """
    Membuat progress bar HTML dengan warna dinamis.
    - score: Nilai similarity dokumen ini
    - max_score: Nilai similarity tertinggi di hasil pencarian (untuk skala visual)
    """
    # 1. Hitung Persentase Visual (Agar bar terlihat penuh untuk ranking 1)
    if max_score == 0:
        percent = 0
    else:
        # Ranking 1 akan selalu 100% panjangnya secara visual
        percent = (score / max_score) * 100 
    
    # 2. Tentukan Warna Berdasarkan Skor Relatif
    if percent >= 75:
        color = "#28a745" # Hijau (Sangat Relevan)
    elif percent >= 40:
        color = "#ffc107" # Kuning/Oranye (Cukup Relevan)
    else:
        color = "#dc3545" # Merah (Kurang Relevan)

    # 3. Buat HTML Bar
    return f"""
    <div style="background-color: #e9ecef; border-radius: 5px; width: 100%; height: 20px;">
        <div style="background-color: {color}; width: {percent}%; height: 100%; border-radius: 5px; text-align: right; padding-right: 5px; color: white; line-height: 20px; font-size: 12px; font-weight: bold;">
            {score:.5f}
        </div>
    </div>
    """

# Config
st.set_page_config(page_title="Information Retrieval System - Weighted Jaccard", layout="wide")

# ==========================================
# 🎨 SIDEBAR: CLEAN & PROFESSIONAL STYLE
# ==========================================
with st.sidebar:
    # 1. HEADER / LOGO AREA
    st.image("logo.png", use_container_width=True)     
    st.divider()

    # 2. NAVIGASI UTAMA
    menu = option_menu(
        menu_title=None,  
        options=["Home", "Preprocessing", "Term Weight", "Matrix", "Similarity"],
        icons=["house", "gear", "list-task", "grid", "search"], 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#6c757d", "font-size": "16px"}, 
            "nav-link": {
                "font-size": "14px", 
                "text-align": "left", 
                "margin": "5px", 
                "--hover-color": "#f0f2f6"
            },
            "nav-link-selected": {
                "background-color": "#007bff", 
                "color": "white",
                "font-weight": "500"
            }, 
        }
    )

    st.write("") 

    # 3. KONFIGURASI DATA
    with st.expander("📂 Sumber Data", expanded=True):
        st.caption("Pilih lokasi folder dokumen:")

        # --- INIT STATE ---
        if "folder_path" not in st.session_state:
            st.session_state["folder_path"] = "dataset" # Default

        col_text, col_btn = st.columns([4, 1])

        with col_btn:
            if st.button("📂", help="Cari folder"):
                try:
                    root = tk.Tk()
                    root.withdraw() 
                    root.wm_attributes('-topmost', 1) 
                    
                    # Buka Dialog
                    selected_dir = filedialog.askdirectory(master=root)
                    root.destroy()
                    
                    if selected_dir:
                        # --- VALIDASI ISI FOLDER ---
                        # Cek apakah di folder tersebut ada file .pdf, .docx, atau .txt
                        valid_extensions = ('.pdf', '.docx', '.txt')
                        files_in_dir = os.listdir(selected_dir)
                        
                        # Cek logic: Apakah ada setidaknya 1 file yang berakhiran valid?
                        has_valid_file = any(f.lower().endswith(valid_extensions) for f in files_in_dir)
                        
                        if has_valid_file:
                            st.session_state["folder_path"] = selected_dir
                            st.success("Folder Valid! ✅")
                            time.sleep(0.5) 
                            st.rerun()
                        else:
                            st.toast("❌ Folder ditolak! Tidak ada file PDF/DOCX/TXT.", icon="🚫")
                            
                except Exception as e:
                    st.error(f"Error: {e}")

        with col_text:
            # Input Text (Otomatis terisi jika validasi sukses)
            path_input = st.text_input(
                "Path Folder", 
                value=st.session_state["folder_path"], 
                label_visibility="collapsed"
            )
            
            # Jika user ketik manual, validasi juga perlu dilakukan saat tombol Load ditekan nanti
            st.session_state["folder_path"] = path_input

        st.write("") 
        
        st.caption("ℹ️ Hanya menerima folder berisi file: **.pdf, .docx, .txt**")

        # Tombol Load (Proses Indexing)
        if st.button("🔄 Load & Index", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            current_path = st.session_state["folder_path"]
            
            # Validasi lagi sebelum processing (jaga-jaga user ketik manual path ngawur)
            if not os.path.isdir(current_path):
                status_text.error(f"❌ Path tidak ditemukan: {current_path}")
            else:
                # Validasi isi lagi (untuk input manual)
                valid_extensions = ('.pdf', '.docx', '.txt')
                has_valid = any(f.lower().endswith(valid_extensions) for f in os.listdir(current_path))
                
                if not has_valid:
                    status_text.error("❌ Folder kosong atau tidak ada dokumen valid (PDF/DOCX/TXT).")
                else:
                    try:
                        status_text.caption(f"Membaca dari: {os.path.basename(current_path)}...")
                        progress_bar.progress(20)
                        
                        # PANGGIL FUNGSI UTAMA
                        doc_index, inverted_index = build_indices(current_path)
                        
                        st.session_state["doc_index"] = doc_index
                        st.session_state["inverted_index"] = inverted_index
                        
                        progress_bar.progress(100)
                        status_text.success("Index berhasil dibangun!")
                        time.sleep(1)
                        progress_bar.empty()
                        status_text.empty()
                        st.rerun()
                        
                    except Exception as e:
                        status_text.error(f"Error processing: {e}")

    # 4. STATUS MONITOR (Native Container)
    st.markdown("### Status")
    
    # Cek status data
    has_data = "doc_index" in st.session_state and st.session_state["doc_index"]
    
    if has_data:
        with st.container(border=True):
            st.markdown("🟢 **System Online**")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Docs", len(st.session_state["doc_index"]))
            with c2:
                st.metric("Terms", len(st.session_state["inverted_index"]))
            st.caption("✅ Data siap dicari.")
    else:
        with st.container(border=True):
            st.markdown("🔴 **System Offline**")
            st.caption("Data index belum dimuat dalam memori.")
            st.warning("Silakan klik tombol **Load** di atas.")

    # 5. FOOTER
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: grey; font-size: 11px;'>© 2025 Data Mining & Information Retrieval<br>v1.0.0 Stable</div>", 
        unsafe_allow_html=True
    )
# ===============================
# HOME
# ===============================
if menu != "Home":
    st.title("Sistem Temu Balik Informasi")
    st.markdown("**Metode: Weighted Jaccard Similarity**")
    st.markdown("---")

if menu == "Home":
    # 1. HERO SECTION (JUDUL UTAMA)
    st.markdown("<h1 style='text-align: center;'>📚 Sistem Temu Balik Informasi 📚</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: gray;'>Implementasi Weighted Jaccard Similarity</h3>", unsafe_allow_html=True)
    st.divider()
    # --- HEADER ALUR PEMROSESAN ---
    st.subheader("🚀 Alur Pemrosesan Sistem")
    
    c1, c2, c3, c4 = st.columns(4)
    
    st.markdown("""
    <style>
    .element-container { margin-bottom: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

    # --- TAHAP 1: INPUT ---
    with c1:
        with st.container(border=True):
            st.markdown("#### 📄 1. Input")
            st.markdown("**Upload & Baca Dokumen**")
            st.write("Format: PDF, TXT, DOCX")

    # --- TAHAP 2: PREPROCESSING ---
    with c2:
        with st.container(border=True):
            st.markdown("#### ⚙️ 2. Preprocessing")
            st.markdown("**Membersihkan Teks**")
            st.write("Tokenizing, Case Folding, Stopword Removal, Stemming")

    # --- TAHAP 3: INDEXING ---
    with c3:
        with st.container(border=True):
            st.markdown("#### 🔢 3. Indexing")
            st.markdown("**Pembobotan Kata**")
            st.write("TF Counting & Inverted Index")

    # --- TAHAP 4: RETRIEVAL ---
    with c4:
        with st.container(border=True):
            st.markdown("#### 🔎 4. Retrieval")
            st.markdown("**Pencarian Dokumen**")
            st.write("Weighted Jaccard Similarity")
            
    # 3. DASHBOARD STATUS (DINAMIS)
    st.markdown("---")
    st.subheader("📊 Status Sistem")

    # Cek apakah index sudah ada di session_state
    if "doc_index" in st.session_state and "inverted_index" in st.session_state:
        # TAMPILAN JMETRICS
        st.success("✅ Sistem SIAP digunakan! Data index telah dimuat.")
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(label="Total Dokumen", value=f"{len(st.session_state['doc_index'])} File")
        with m2:
            st.metric(label="Total Term Unik", value=f"{len(st.session_state['inverted_index'])} Kata")
        with m3:
            st.metric(label="Metode", value="Weighted Jaccard")
            
        with st.expander("ℹ️ Panduan Singkat"):
            st.write("""
            1. Pilih menu **Preprocessing** untuk melihat detail token per dokumen.
            2. Pilih menu **Term Weight** untuk melihat bobot kata.
            3. Pilih menu **Matrix** untuk melihat tabel **Term-Document Matrix** (sebaran kata).
            3. Pilih ke menu **Similarity** untuk melakukan pencarian query.
            """)

        # ============================================================
        # MENAMPILKAN TABEL INDEX (HANYA DI HOME)
        # ============================================================
        st.markdown("---")
        st.subheader("📂 Struktur Data Index")
        
        tab1, tab2 = st.tabs(["📄 Document Index", "🔍 Inverted Index"])
        
        # --- TAB 1: Document Index ---
        with tab1:
            st.caption("Daftar dokumen dan jumlah term unik di dalamnya:")
            
            # Siapkan data untuk tabel
            doc_data = []
            for doc, terms in st.session_state["doc_index"].items():
                # Ambil 5 kata dengan frekuensi tertinggi untuk preview
                top_terms = sorted(terms.items(), key=lambda x: x[1], reverse=True)[:5]
                top_terms_str = ", ".join([t[0] for t in top_terms])
                
                doc_data.append({
                    "Nama Dokumen": doc,
                    "Jumlah Term Unik": len(terms),
                    "Top Term (Preview)": top_terms_str
                })
            
            # Tampilkan Tabel
            df_doc = pd.DataFrame(doc_data)
            st.dataframe(
                df_doc, 
                use_container_width=True,
                column_config={
                    "Nama Dokumen": st.column_config.TextColumn("Nama Dokumen", width="medium"),
                    "Top Term (Preview)": st.column_config.TextColumn("Top Term (Preview)", width="large"),
                }
            )
            
            # Opsi lihat JSON mentah
            with st.expander("🛠️ Lihat Raw JSON Document Index"):
                st.json(st.session_state["doc_index"])

        # --- TAB 2: Inverted Index ---
        with tab2:
            st.caption("Mapping dari Kata (Term) ke Dokumen:")
            
            # Siapkan data (batasi 100 kata pertama agar tidak lag jika data banyak)
            inv_items = list(st.session_state["inverted_index"].items())
            limit = 100
            
            inv_data = []
            for term, posting in inv_items[:limit]:
                # Cek format posting (apakah dict atau list)
                doc_list = list(posting.keys()) if isinstance(posting, dict) else list(posting)
                
                inv_data.append({
                    "Term (Kata)": term,
                    "Muncul di (Jml Dokumen)": len(doc_list),
                    "List Dokumen": ", ".join(doc_list)
                })
            
            df_inv = pd.DataFrame(inv_data)
            st.dataframe(df_inv, use_container_width=True)
            
            if len(inv_items) > limit:
                st.caption(f"ℹ️ Menampilkan {limit} kata pertama dari total {len(inv_items)} kata.")
            
            with st.expander("🛠️ Lihat Full Inverted Index (JSON)"):
                st.json(st.session_state["inverted_index"])

    else:
        st.warning("⚠️ Index belum dibangun. Silakan tekan tombol 'Load & Index Dokumen' di sidebar kiri.")
    
# ===============================
# PREPROCESSING 
# ===============================
elif menu == "Preprocessing":
    st.header("🔎 Proses Preprocessing")

    dataset_path = st.session_state.get("folder_path", "dataset")

    # Validasi Folder
    if not os.path.isdir(dataset_path):
        st.error(f"❌ Folder tidak ditemukan: {dataset_path}")
    else:
        files = [
            f for f in os.listdir(dataset_path) 
            if f.lower().endswith(('.txt', '.pdf', '.docx'))
        ]
        files.sort()

        if not files:
            st.warning("⚠️ Folder ini kosong atau tidak ada dokumen valid.")
        else:
            selected_file = st.selectbox("Pilih Dokumen untuk Dilihat Prosesnya:", files)

            if selected_file:
                file_path = os.path.join(dataset_path, selected_file)
                
                try:
                    # Baca teks asli
                    raw_text = extract_text(file_path) 
                    
                    if not raw_text:
                        st.warning("File terbaca kosong/tidak ada teks.")
                    else:
                        with st.spinner('Sedang memproses langkah demi langkah (Algoritma Nazief-Adriani)...'):

                            # 1. Tokenizing (Raw) 
                            tokens_original = re.findall(r'[a-zA-Z]+', raw_text)
                            
                            # 2. Case Folding
                            tokens_casefolded = [t.lower() for t in tokens_original]
                            
                            # 3. Stopword Removal
                            tokens_filter = remove_stopwords(tokens_casefolded)
                            
                            # 4. Stemming
                            tokens_stem = stemming(tokens_filter)
                            
                            # 5. TF Data (DataFrame)
                            tf_counts = Counter(tokens_stem)
                            df_tf = pd.DataFrame(list(tf_counts.items()), columns=['Kata (Term)', 'Frekuensi'])
                            # Urutkan dari yang terbanyak
                            df_tf = df_tf.sort_values(by='Frekuensi', ascending=False).reset_index(drop=True)
                        
                        # --- VISUALISASI HASIL (5 KOLOM) ---
                        st.success("Proses Selesai!")
                        st.subheader(f"Detail Proses: {selected_file}")
                        st.caption(f"Lokasi File: {file_path}")

                        col1, col2, col3, col4, col5 = st.columns(5)
                        
                        # --- KOLOM 1: TOKENIZING ---
                        with col1:
                            st.info("1. Tokenizing")
                            st.caption("Memecah kata (Kapital)")
                            with st.container(height=400):
                                st.write(tokens_original) 
                            st.markdown(f"<p style='text-align: center; color: #1E90FF; font-weight:bold;'>Total: {len(tokens_original)}</p>", unsafe_allow_html=True)

                        # --- KOLOM 2: CASE FOLDING ---
                        with col2:
                            st.warning("2. Case Folding")
                            st.caption("Huruf kecil semua")
                            with st.container(height=400):
                                st.write(tokens_casefolded) 
                            st.markdown(f"<p style='text-align: center; color: #FFC300; font-weight:bold;'>Total: {len(tokens_casefolded)}</p>", unsafe_allow_html=True)

                        # --- KOLOM 3: FILTERING ---
                        with col3:
                            st.success("3. Filtering")
                            st.caption("Manual Stopword")
                            with st.container(height=400):
                                st.write(tokens_filter) 
                            st.markdown(f"<p style='text-align: center; color: #E67E22; font-weight:bold;'>Total: {len(tokens_filter)}</p>", unsafe_allow_html=True)

                        # --- KOLOM 4: STEMMING ---
                        with col4:
                            st.info("4. Stemming") 
                            st.caption("Kata Dasar (Nazief-Adriani)")
                            with st.container(height=400):
                                st.write(tokens_stem) 
                            st.markdown(f"<p style='text-align: center; color: #27AE60; font-weight:bold;'>Total: {len(tokens_stem)}</p>", unsafe_allow_html=True)
                        
                        # --- KOLOM 5: TF (SUDAH DIPERBAIKI) ---
                        with col5:
                            st.error("5. Term Frequency")
                            st.caption("Hitung Kemunculan Hasil Akhir")
                            with st.container(height=400):
                                # Tampilkan sebagai Tabel Dataframe
                                st.dataframe(df_tf, hide_index=True, use_container_width=True)
                            st.markdown(f"<p style='text-align: center; color: #C0392B; font-weight:bold;'>Unik: {len(df_tf)}</p>", unsafe_allow_html=True)
                
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")

# ===============================
# TERM WEIGHT
# ===============================
elif menu == "Term Weight":
    st.title("⚖️ Term Weight (TF)")
    st.markdown("Frekuensi kemunculan kata (Term Frequency) dalam setiap dokumen.")

    # Cek apakah index sudah ada
    if "doc_index" in st.session_state and st.session_state["doc_index"]:
        
        doc_index = st.session_state["doc_index"]
        filenames = list(doc_index.keys())

        # --- BAGIAN 1: CONTROLLER (PILIH DOKUMEN) ---
        with st.container(border=True):
            col_sel1, col_sel2 = st.columns([3, 1])
            
            with col_sel1:
                # Dropdown untuk memilih dokumen
                selected_file = st.selectbox(
                    "📂 Pilih Dokumen untuk Dilihat:", 
                    filenames,
                    index=0
                )
            
            with col_sel2:
                st.write("") 
                st.write("") 
                st.button("🔄 Refresh View")

        # --- BAGIAN 2: STATISTIK DOKUMEN (SUMMARY) ---
        # Ambil data TF untuk file yang dipilih
        tf_data = doc_index[selected_file]
        
        import pandas as pd
        df_tf = pd.DataFrame(list(tf_data.items()), columns=["Term", "Frequency (TF)"])
        
        # Urutkan dari TF terbesar
        df_tf = df_tf.sort_values(by="Frequency (TF)", ascending=False).reset_index(drop=True)

        # Tampilkan Metrics Sederhana
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Kata Unik", f"{len(df_tf)} Kata")
        with m2:
            top_term = df_tf.iloc[0]['Term'] if not df_tf.empty else "-"
            st.metric("Top Term (Terbanyak)", top_term)
        with m3:
            max_tf = df_tf.iloc[0]['Frequency (TF)'] if not df_tf.empty else 0
            st.metric("Max Frekuensi", f"{max_tf}")

        # --- BAGIAN 3: TABEL DATA ---
        st.markdown(f"### 📊 Detail TF: `{selected_file}`")
        
        st.dataframe(
            df_tf, 
            use_container_width=True, 
            height=400,  
            hide_index=True # Sembunyikan index angka 0,1,2...
        )

    else:
        st.warning("⚠️ Data belum diproses. Silakan kembali ke Home dan klik 'Load & Index Dokumen'.") 

# ===============================
# MATRIX (ALL-IN-ONE ANALYTICS)
# ===============================
elif menu == "Matrix":
    st.title("🧮 Analisis & Visualisasi Matrix")
    st.markdown("Analisis mendalam hubungan antara Query dan Dokumen (Angka & Visual).")

    # --- INPUT QUERY ---
    with st.container(border=True):
        col_q1, col_q2 = st.columns([4, 1])
        with col_q1:
            query_input = st.text_input(
                "Masukkan Query:", 
                placeholder="Ketik kata kunci pencarian... (misal: teknologi digital)",
                value="" 
            )
        with col_q2:
            st.write("") 
            st.write("")
            btn_analyze = st.button("🔍 Analisis", type="primary", use_container_width=True)

    # --- LOGIKA UTAMA ---
    if (query_input or btn_analyze) and "doc_index" in st.session_state:
        
        # 1. PREPROCESSING QUERY
        try:
            _, _, q_tokens = preprocess(query_input)
            tf_query = term_frequency(q_tokens)
        except NameError:
            st.error("❌ Fungsi 'preprocess' atau 'term_frequency' tidak ditemukan.")
            st.stop()

        if not tf_query:
            st.warning("⚠️ Query tidak menghasilkan kata kunci valid (stopword/kosong).")
            st.stop()

        # 2. PERSIAPAN DATA
        import pandas as pd
        import matplotlib.pyplot as plt
        import seaborn as sns
        from wordcloud import WordCloud

        docs_list = st.session_state["doc_index"]
        
        # A. Bangun DataFrame TF Matrix (Hanya untuk kata yang ada di Query)
        matrix_data = {}
        for term in tf_query.keys():
            row_data = []
            for doc_name, tf_doc in docs_list.items():
                row_data.append(tf_doc.get(term, 0)) 
            matrix_data[term] = row_data
            
        df_matrix = pd.DataFrame(matrix_data, index=list(docs_list.keys())).T
        
        # B. Hitung Skor Similarity
        score_data = []
        for doc_name, tf_doc in docs_list.items():
            intersection = 0
            union = 0
            all_terms = set(tf_query.keys()) | set(tf_doc.keys())
            
            for term in all_terms:
                w_q = tf_query.get(term, 0)
                w_d = tf_doc.get(term, 0)
                intersection += min(w_q, w_d)
                union += max(w_q, w_d)
            
            score = intersection / union if union > 0 else 0
            score_data.append({"Dokumen": doc_name, "Similarity": score})
            
        df_scores = pd.DataFrame(score_data)
        df_scores = df_scores.sort_values("Similarity", ascending=True)

        st.success(f"Analisis selesai untuk query: **'{query_input}'**")

        # --- TAMPILAN TABS ---
        tab1, tab2, tab3, tab4 = st.tabs(["🔢 Data & Perhitungan", "🔥 Heatmap", "📊 Grafik Ranking", "☁️ Word Cloud"])

        # ================= TAB 1: DATA & PERHITUNGAN =================
        with tab1:
            st.subheader("A. Normalized TF Matrix")
            st.dataframe(df_matrix.style.background_gradient(cmap="Blues"), use_container_width=True)
            
            st.divider()

            st.subheader("B. Rincian Perhitungan (Trace)")
            
            if df_scores.empty:
                 st.warning("Belum ada proses perhitungan.")
            else:
                # --- FITUR BARU: PILIH DOKUMEN ---
                # Default-nya pilih dokumen dengan skor tertinggi (paling bawah di list sorted)
                sorted_docs = df_scores["Dokumen"].tolist()[::-1] # Balik urutan jadi Ranking 1 di atas
                
                selected_doc = st.selectbox(
                    "🔍 Pilih Dokumen untuk Dibedah:", 
                    options=sorted_docs,
                    index=0 # Otomatis pilih yang pertama (Juara 1)
                )

                # Ambil data berdasarkan dokumen yang DIPILIH user
                target_doc_row = df_scores[df_scores["Dokumen"] == selected_doc].iloc[0]
                target_score = target_doc_row["Similarity"]

                st.info(f"Fokus Analisis: Query vs **{selected_doc}**")
                
                # --- LOGIKA HITUNGAN (Sama seperti sebelumnya, tapi pakai variabel selected_doc) ---
                tf_doc_target = docs_list[selected_doc]
                all_terms_trace = sorted(list(set(tf_query.keys()) | set(tf_doc_target.keys())))
                
                calc_details = []
                sum_min = 0
                sum_max = 0
                
                for term in all_terms_trace:
                    w_q = tf_query.get(term, 0)
                    w_d = tf_doc_target.get(term, 0)
                    val_min = min(w_q, w_d)
                    val_max = max(w_q, w_d)
                    sum_min += val_min
                    sum_max += val_max
                    
                    if val_max > 0:
                        calc_details.append({
                            "Term": term, "TF Query": w_q, "TF Dokumen": w_d,
                            "Min (Irisan)": val_min, "Max (Gabungan)": val_max
                        })
                
                df_calc = pd.DataFrame(calc_details)
                
                # Sorting & Total Row 
                df_calc = df_calc.sort_values(by=['Min (Irisan)', 'TF Query'], ascending=[False, False])
                
                total_row = pd.DataFrame([{
                    "Term": ">>> TOTAL (SUM) <<<", "TF Query": 0, "TF Dokumen": 0,
                    "Min (Irisan)": sum_min, "Max (Gabungan)": sum_max
                }])
                df_display = pd.concat([df_calc, total_row], ignore_index=True)

                def highlight_jaccard(row):
                    if row['Term'] == ">>> TOTAL (SUM) <<<":
                        return ['font-weight: bold; background-color: #e2e3e5; color: black'] * len(row)
                    if row['Min (Irisan)'] > 0:
                        return ['background-color: #d1e7dd; color: black'] * len(row)
                    elif row['TF Query'] > 0 and row['TF Dokumen'] == 0:
                        return ['background-color: #f8d7da; color: black'] * len(row)
                    else:
                        return [''] * len(row)
                
                st.dataframe(df_display.style.apply(highlight_jaccard, axis=1), use_container_width=True)
                
                st.markdown("#### Hasil Akhir:")
                latex_str = r"J(Q, D) = \frac{|Q \cap D|}{|Q \cup D|} = \frac{" + str(sum_min) + "}{" + str(sum_max) + "} = " + f"{target_score:.5f}"
                st.latex(latex_str)

        # ================= TAB 2: HEATMAP =================
        with tab2:
            st.subheader("🌡️ Heatmap Distribusi Kata")
            if df_matrix.empty:
                st.info("Tidak ada data.")
            else:
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.heatmap(
                    df_matrix, 
                    annot=True, 
                    cmap="YlGnBu", 
                    fmt='g', 
                    ax=ax,
                    vmin=0,      # Warna paling terang di angka 0
                    vmax=15      # Warna paling gelap berhenti di angka 15 (sisanya tetap gelap)
                )                
                plt.xticks(rotation=45, ha='right')
                st.pyplot(fig)

        # ================= TAB 3: RANKING (FIXED) =================
        with tab3:
            st.subheader("🏆 Peringkat Relevansi Dokumen")
            
            df_top = df_scores.tail(10) 
            fig2, ax2 = plt.subplots(figsize=(8, len(df_top)*0.8 + 1))
            
            colors = ['#4b7bec'] * (len(df_top) - 1) + ['#28a745']
            bars = ax2.barh(df_top["Dokumen"], df_top["Similarity"], color=colors)
            
            # --- FIX 1: Tentukan Max Score dari Data ---
            max_val = df_top["Similarity"].max() if not df_top.empty else 0
            
            ax2.set_xlabel("Weighted Jaccard Score")
            # --- FIX 2: Dynamic Scaling yang Aman ---
            ax2.set_xlim(0, max_val * 1.3 if max_val > 0 else 1) 
            ax2.grid(axis='x', linestyle='--', alpha=0.5)
            
            # --- FIX 3: Bar Label (Lebih Rapi & Otomatis) ---
            ax2.bar_label(bars, fmt='%.5f', padding=5, fontsize=10)

            st.pyplot(fig2)

        # ================= TAB 4: WORDCLOUD =================
        with tab4:
            st.subheader(f"☁️ Word Cloud: {selected_doc}")
            if selected_doc in docs_list:
                wc = WordCloud(width=800, height=400, background_color='white', colormap='viridis')
                wc.generate_from_frequencies(docs_list[selected_doc])
                
                fig_wc, ax_wc = plt.subplots(figsize=(10, 5))
                ax_wc.imshow(wc, interpolation='bilinear')
                ax_wc.axis("off")
                st.pyplot(fig_wc)
            else:
                st.error("Dokumen tidak ditemukan.")

    elif not query_input and not btn_analyze:
        st.info("👋 Silakan masukkan kata kunci di atas untuk memulai analisis.")
    else:
        st.warning("⚠️ Database kosong. Silakan muat dokumen di menu Home terlebih dahulu.")

# ===============================
# SIMILARITY
# ===============================
elif menu == "Similarity":
    st.title("🔎 Pencarian Dokumen")
    st.markdown("Cari dokumen yang paling relevan dengan query Anda.")

    # --- HELPER 1: TAMPILKAN PDF (Asli Iframe) ---
    import base64
    def show_pdf_embedded(file_path):
        try:
            with open(file_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Gagal menampilkan PDF: {e}")

# --- HELPER 2: TAMPILKAN DOCX (Update CSS Layout) ---
    def show_docx_embedded(file_path):
        try:
            import mammoth
            import textwrap
            
            with open(file_path, "rb") as docx_file:
                # Konversi ke HTML
                result = mammoth.convert_to_html(docx_file)
                html_content = result.value
                
                viewer_html = textwrap.dedent(f"""
                <style>
                    .docx-container {{
                        background-color: white; 
                        color: black; 
                        max-width: 800px; 
                        margin: 0 auto; 
                        padding: 60px; 
                        box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
                        min-height: 900px; 
                        font-family: 'Times New Roman', Times, serif; 
                        line-height: 1.8;
                        font-size: 16px;
                        text-align: justify; /* Default isi paragraf rata kiri-kanan */
                    }}
                    
                    /* MEMAKSA JUDUL (Heading) RATA TENGAH */
                    .docx-container h1, .docx-container h2, .docx-container h3, .docx-container h4 {{
                        text-align: center !important;
                        margin-top: 25px;
                        margin-bottom: 20px;
                    }}

                    /* TRIK BARU: Mendeteksi paragraf Cover yang isinya HANYA BOLD */
                    /* Selector :has() didukung di Chrome/Edge modern */
                    .docx-container p:has(> strong:only-child) {{
                        text-align: center !important;
                        margin-bottom: 10px;
                    }}
                    
                    /* Trik tambahan jika Bold + Italic */
                    .docx-container p:has(> strong > em) {{
                         text-align: center !important;
                    }}

                    /* Memperbaiki tampilan tabel */
                    .docx-container table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    .docx-container td, .docx-container th {{ border: 1px solid #333; padding: 8px; }}
                </style>
                
                <div style="width: 100%; height: 700px; overflow-y: auto; background-color: #525659; padding: 30px; border-radius: 8px; border: 1px solid #ccc;">
                    <div class="docx-container">
                        {html_content}
                    </div>
                </div>
                """)
                
                st.markdown(viewer_html, unsafe_allow_html=True)

        except ImportError:
            st.error("⚠️ Library 'mammoth' belum diinstall. Ketik: pip install mammoth")
        except Exception as e:
            st.error(f"Gagal menampilkan DOCX: {e}")

    # --- HELPER 3: PROGRESS BAR WARNA ---
    def get_custom_progress_bar(score, max_score):
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        if percentage >= 80: color = "#28a745"
        elif percentage >= 50: color = "#ffc107"
        else: color = "#dc3545"

        return f"""
        <div style="width: 100%; background-color: #f0f2f6; border-radius: 5px; height: 25px; margin-bottom: 5px;">
            <div style="width: {percentage}%; background-color: {color}; height: 100%; border-radius: 5px; text-align: right; padding-right: 5px; color: white; line-height: 25px; font-weight: bold; font-size: 14px;">
               {score:.5f}
            </div>
        </div>
        """

    # --- LOGIKA UTAMA ---
    with st.container(border=True):
        c_search, c_setting = st.columns([3, 1])
        with c_search:
            query = st.text_input("Masukkan Kata Kunci:", placeholder="Contoh: metode pembelajaran...", help="Tekan Enter")
        with c_setting:
            top_k = st.number_input("Top-K:", min_value=1, max_value=20, value=5)

    if query.strip():
        # Gunakan regex untuk tokenisasi awal
        tokens_orig = re.findall(r'[a-zA-Z]+', query.lower())
        
        # Panggil fungsi manual yang sudah diimport di bagian atas app.py
        from preprocessing.stopword import remove_stopwords
        from preprocessing.stemming import stemming
        
        tokens_filt = remove_stopwords(tokens_orig)
        q_tokens = stemming(tokens_filt) # Hasil stemming manual Nazief-Adriani
        
        # Hitung Term Frequency (TF)
        from collections import Counter
        tf_query = dict(Counter(q_tokens))
        
        # Simpan ke session state agar bisa dihitung skor Jaccard-nya nanti
        st.session_state["tf_query"] = tf_query 
        
        with st.expander("📊 Lihat Statistik Query (Term Frequency)", expanded=True):
            s1, s2 = st.columns([1, 3])
            with s1: st.metric("Total Term", sum(tf_query.values()))
            with s2: 
                st.markdown("Rincian Kata Kunci (TF)")
                st.json(tf_query)
    
    if st.button("🚀 Cari Dokumen", type="primary", use_container_width=True):
        if "doc_index" not in st.session_state or not st.session_state["doc_index"]:
            st.error("⚠️ Database kosong! Lakukan 'Load & Index' di sidebar dulu.")
        elif not query.strip():
            st.warning("⚠️ Masukkan kata kunci!")
        else:
            from main import weighted_jaccard 
            results = []
            tf_query = st.session_state.get("tf_query", {}) 

            for doc, tf_doc in st.session_state["doc_index"].items():
                score = weighted_jaccard(tf_doc, tf_query)
                if score > 0: results.append((doc, score))

            results.sort(key=lambda x: x[1], reverse=True)
            if "opened_doc_rank" in st.session_state: del st.session_state["opened_doc_rank"]
            st.session_state["search_results"] = results
            st.session_state["has_searched"] = True 
            st.rerun()

    if st.session_state.get("has_searched"):
        results = st.session_state.get("search_results", [])
        st.divider()

        if not results:
            st.info("😔 Tidak ditemukan dokumen yang cocok.")
        else:
            st.subheader(f"📑 Hasil Pencarian ({min(len(results), top_k)} Teratas)")
            folder_path = st.session_state.get("folder_path", "dataset")
            max_score_val = results[0][1] 

            for rank, (doc, score) in enumerate(results[:top_k], 1):
                if rank == 1: icon = "🥇"
                elif rank == 2: icon = "🥈"
                elif rank == 3: icon = "🥉"
                else: icon = f"#{rank}"

                with st.container(border=True):
                    c1, c2 = st.columns([4, 1.3])
                    with c1:
                        st.markdown(f"### {icon} {doc}")
                        st.markdown(get_custom_progress_bar(score, max_score_val), unsafe_allow_html=True)
                        st.caption("Similarity Score (Jaccard)")
                    with c2:
                        st.write("")
                        st.write("")
                        full_path = os.path.join(folder_path, doc)
                        file_ext = os.path.splitext(doc)[1].lower()
                        
                        viewable_files = [".pdf", ".docx"]
                        if file_ext in viewable_files:
                            is_active = (st.session_state.get("opened_doc_rank") == rank)
                            if is_active:
                                if st.button("❌ Tutup", key=f"close_{rank}"):
                                    del st.session_state["opened_doc_rank"]
                                    st.rerun()
                            else:
                                btn_label = "👁️ Lihat File"
                                if st.button(btn_label, key=f"view_{rank}"):
                                    st.session_state["opened_doc_rank"] = rank
                                    st.rerun()    
                        else:
                            if os.path.exists(full_path):
                                with open(full_path, "rb") as f:
                                    st.download_button("⬇️ Unduh", f, file_name=doc, key=f"dl_{rank}")
                            else:
                                st.error("File hilang")

                if st.session_state.get("opened_doc_rank") == rank:
                    full_path = os.path.join(folder_path, doc)
                    if os.path.exists(full_path):
                        st.info(f"📂 Membuka: {doc}")
                        if file_ext == ".pdf":
                            show_pdf_embedded(full_path)
                        elif file_ext == ".docx":
                            show_docx_embedded(full_path)
                    else:
                        st.error(f"❌ File tidak ditemukan: {full_path}")