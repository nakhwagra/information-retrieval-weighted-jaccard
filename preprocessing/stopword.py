import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH_STOPWORD = os.path.join(BASE_DIR, '..', 'data', 'stopwords-id.txt')

def load_stopwords():
    """Membaca daftar kata dari file txt ke dalam set"""
    try:
        if not os.path.exists(PATH_STOPWORD):
            print(f"Peringatan: File tidak ditemukan di {PATH_STOPWORD}")
            return set()
            
        with open(PATH_STOPWORD, 'r', encoding='utf-8') as f:
            # Menggunakan set untuk pencarian yang sangat cepat O(1)
            return set(line.strip().lower() for line in f if line.strip())
    except Exception as e:
        print(f"Terjadi kesalahan saat membaca stopword: {e}")
        return set()

# Load list stopword ke memori sekali saja saat aplikasi dijalankan
STOPWORDS_SET = load_stopwords()

def remove_stopwords(tokens):
    # Mengabaikan huruf besar/kecil (case-insensitive)
    return [t for t in tokens if t.lower() not in STOPWORDS_SET]