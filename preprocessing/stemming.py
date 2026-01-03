
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH_KAMUS = os.path.join(BASE_DIR, '..', 'data', 'kata-dasar.txt')

def load_kamus():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Sesuaikan jumlah '..' sesuai struktur folder Anda (naik 1 tingkat ke root, lalu ke data)
    path_ke_data = os.path.join(current_dir, "..", "data", "kata-dasar.txt")
    
    try:
        with open(path_ke_data, 'r', encoding='utf-8') as f:
            isi_kamus = set(line.strip().lower() for line in f if line.strip())
            print(f"✅ Kamus berhasil dimuat: {len(isi_kamus)} kata.") # Untuk debug di terminal
            return isi_kamus
    except FileNotFoundError:
        print(f"❌ GAGAL: Kamus tidak ditemukan di {path_ke_data}")
        return set()

KAMUS_DASAR = load_kamus()

def cek_kamus(kata):
    return kata in KAMUS_DASAR

def hapus_inflection(kata):
    # -lah, -kah, -tah, -pun, -ku, -mu, -nya
    return re.sub(r'(lah|kah|tah|pun|ku|mu|nya)$', '', kata)

def hapus_derivational_suffix(kata):
    # Prioritas pemotongan dengan pengecekan kamus
    if kata.endswith('kan'):
        if cek_kamus(kata[:-3]): return kata[:-3] 
        if cek_kamus(kata[:-2]): return kata[:-2] 
        return kata[:-2]
        
    if kata.endswith('an'):
        if cek_kamus(kata[:-2]): return kata[:-2]
        return kata[:-2]
        
    if kata.endswith('i'):
        if cek_kamus(kata[:-1]): return kata[:-1]
        return kata[:-1]
        
    return kata

def hapus_derivational_prefix(kata):
    if cek_kamus(kata): return kata

    # 1. Aturan meN- dan peN-
    if kata.startswith(('me', 'pe')):
        # meny- / peny- -> s
        if re.match(r'^(peny|meny)', kata):
            calon = 's' + kata[4:]
            if cek_kamus(calon): return calon
            return calon

        # pen- / men- -> t
        if re.match(r'^(pen|men)', kata):
            calon_luluh = 't' + kata[3:]
            if cek_kamus(calon_luluh): return calon_luluh
            return kata[3:]

        # pem- / mem- -> p
        if re.match(r'^(pem|mem)', kata):
            calon_luluh = 'p' + kata[3:]
            if cek_kamus(calon_luluh): return calon_luluh
            return kata[3:]

        # peng- / meng- (Pencegahan "gguna")
        if re.match(r'^(peng|meng)', kata):
            # Cek peluruhan k (mengukur -> ukur)
            calon_k = 'k' + kata[4:]
            if cek_kamus(calon_k): return calon_k
            
            # Cek potong murni (pengguna -> guna)
            calon_biasa = kata[4:]
            if cek_kamus(calon_biasa): return calon_biasa
            
            # PERBAIKAN KHUSUS: Jika sisa 'gguna', hapus g tambahan
            if len(calon_biasa) > 1 and calon_biasa[0] == 'g' and calon_biasa[1] == 'g':
                if cek_kamus(calon_biasa[1:]): return calon_biasa[1:]
                return calon_biasa[1:] # Paksa potong g jika double g di awal
            
            return calon_biasa

        # Awalan sederhana pe- / me-
        calon_dua = kata[2:]
        if cek_kamus(calon_dua): return calon_dua
        return calon_dua

    # 2. Awalan ber-, ter-, per-, be-, te-
    if re.match(r'^(ber|ter|per)', kata):
        calon = kata[3:]
        if cek_kamus(calon): return calon
        return calon
    
    if re.match(r'^(be|te|pe)', kata):
        if kata == "belajar": return "ajar"
        calon = kata[2:]
        if cek_kamus(calon): return calon
        return calon
    
    # 3. Awalan di-, ke-, se-
    if re.match(r'^(di|ke|se)', kata):
        return kata[2:]

    return kata

def stemming_nazief_adriani(kata):
    kata = kata.lower().strip()
    if not kata or cek_kamus(kata): return kata
    
    original = kata

    # Langkah 1 & 2: Suffix
    kata = hapus_inflection(kata)
    kata = hapus_derivational_suffix(kata)
    if cek_kamus(kata): return kata
    
    # Langkah 3: Prefix (Loop 3x)
    for _ in range(3):
        if cek_kamus(kata): break
        sebelum = kata
        kata = hapus_derivational_prefix(kata)
        if cek_kamus(kata): break
        if kata == sebelum: break
    
    # Langkah 4: Pembersihan Akhir (Koreksi untuk kata yang gagal stem sempurna)
    if not cek_kamus(kata):
        # Bersihkan double konsonan di awal (gguna -> guna)
        if len(kata) > 2 and kata[0] == kata[1]:
            if cek_kamus(kata[1:]): return kata[1:]
        
        # Bersihkan sisa 'k' di akhir (dasark -> dasar)
        if kata.endswith('k') and cek_kamus(kata[:-1]):
            return kata[:-1]

    return kata if len(kata) > 2 else original

def stemming(tokens):
    return [stemming_nazief_adriani(t) for t in tokens]