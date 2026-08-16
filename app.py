import streamlit as st
import requests
import time
import base64

# Mengatur tampilan halaman
st.set_page_config(page_title="Galeri Cosplay", layout="wide")
# Menyembunyikan menu bawaan, toolbar GitHub (Fork), dan footer profil Streamlit
hide_streamlit_style = """
<style>
    /* Memusnahkan Header, Toolbar, dan Menu atas secara absolut */
    header {visibility: hidden !important; display: none !important;}
    header[data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    #MainMenu {visibility: hidden !important; display: none !important;}

    /* Memusnahkan Footer secara absolut */
    footer {visibility: hidden !important; display: none !important;}
    footer[data-testid="stFooter"] {display: none !important;}
    
    /* Memusnahkan segala jenis tombol Deploy / Profil / GitHub Icon */
    .stDeployButton {display: none !important;}
    [data-testid="stAppDeployButton"] {display: none !important;}
    .viewerBadge_container__1QSob {display: none !important;}

    /* Mengatur ulang jarak atas agar tidak ada ruang kosong yang tersisa */
    .stApp > header {background-color: transparent !important;}
    .block-container {padding-top: 1.5rem !important;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ---------------------------------------------------------
# FUNGSI MEMBACA BYTE GAMBAR & MENGUBAHNYA KE BASE64
# ---------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_image_b64(url):
    try:
        response = requests.get(url, timeout=10)
        # Mengubah data mentah (bytes) menjadi format teks Base64
        b64 = base64.b64encode(response.content).decode()
        return b64
    except Exception:
        return None

# ---------------------------------------------------------
# FUNGSI MODAL/POP-UP UNTUK ZOOM GAMBAR & DOWNLOAD (HTML MURNI)
# ---------------------------------------------------------
@st.dialog("Preview Gambar", width="large")
def zoom_gambar(url, filename):
    st.image(url, use_container_width=True)
    col_nama, col_download = st.columns([3, 1])
    
    with col_nama:
        st.write(f"`{filename}`")
        
    with col_download:
        b64_data = fetch_image_b64(url)
        
        if b64_data:
            # ---------------------------------------------------------
            # SOLUSI FINAL: HTML CUSTOM DOWNLOAD BUTTON
            # Menggunakan atribut 'download' pada tag <a> untuk memaksa browser
            # mengunduh file, bukan memicu bug rerun Streamlit.
            # ---------------------------------------------------------
            html_button = f"""
                <a href="data:image/jpeg;base64,{b64_data}" download="{filename}" 
                   style="display: inline-block; width: 100%; padding: 0.5rem 1rem; 
                          background-color: #FF4B4B; color: white; text-align: center; 
                          text-decoration: none; border-radius: 0.5rem; 
                          font-family: sans-serif; font-weight: 600; font-size: 14px;">
                   ⬇️ Download
                </a>
            """
            # Menyuntikkan HTML ke dalam Streamlit
            st.markdown(html_button, unsafe_allow_html=True)
        else:
            st.error("Gagal menyiapkan unduhan")

st.title("Cosplay Gallery")

# --- TAMBAHKAN DESKRIPSI DI SINI ---
st.markdown("""
This gallery only contains some collection from /CG/, if you curious about the full collection, you can go to the original thread on 4chan /CG/ board or go to [rentry](https://rentry.co/coslibraryv3). This gallery is just for personal use. All images are sourced from /CG/ threads
""")
# -----------------------------------

# 1. MENGAMBIL TOKEN DAN ID DARI SECRETS
TOKEN = st.secrets["DISCORD_TOKEN"]
CHANNEL_ID = st.secrets["CHANNEL_ID"]
HEADERS = {"Authorization": f"Bot {TOKEN}"}

# 2. SINKRONISASI OTOMATIS DARI DISCORD
@st.cache_data(ttl=3600, show_spinner="Syncronizing......")
def get_database_from_discord():
    all_data = []
    last_id = None
    
    while True:
        url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=100"
        if last_id:
            url += f"&before={last_id}"
            
        resp = requests.get(url, headers=HEADERS)
        
        if resp.status_code == 429:
            waktu_tunggu = resp.json().get("retry_after", 1.5)
            time.sleep(waktu_tunggu)
            continue
            
        if resp.status_code != 200:
            break
            
        messages = resp.json()
        if not messages:
            break
            
        for msg in messages:
            if msg.get("attachments"):
                teks_caption = msg.get("content", "").split('\n')[0]
                nama_album_full = teks_caption.replace('**', '').replace('**', '').split(' (Part')[0].strip()
                if not nama_album_full:
                    nama_album_full = "Lainnya"
                
                for att in msg["attachments"]:
                    all_data.append({
                        "album": nama_album_full,
                        "filename": att["filename"],
                        "url": att["url"]
                    })
        
        last_id = messages[-1]["id"]
        time.sleep(0.1)
        
    return all_data

database_gambar = get_database_from_discord()

if not database_gambar:
    st.warning("No Image Found")
    st.stop()

# ---------------------------------------------------------
# 3. MEMPROSES DATA & EXCLUDE COSPLAYER (BLACKLIST)
# ---------------------------------------------------------
# TULIS NAMA COSPLAYER YANG INGIN DISEMBUNYIKAN DI SINI
EXCLUDED_COSPLAYERS = ["evenink"] 

filtered_database = []
koleksi_cosplayer = {}

for item in database_gambar:
    nama_album_full = item["album"]
    
    # Mengekstrak nama cosplayer (tahan banting terhadap ketiadaan spasi)
    if "-" in nama_album_full:
        nama_cosplayer = nama_album_full.split("-", 1)[0].strip()
    else:
        nama_cosplayer = "Lainnya"
        
    # --- LOGIKA EXCLUDE SUPER KETAT ---
    is_excluded = False
    for ex in EXCLUDED_COSPLAYERS:
        # Jika kata kunci exclude (misal 'evenink') ADA DI DALAM nama_cosplayer
        if ex.lower() in nama_cosplayer.lower():
            is_excluded = True
            break # Hentikan pengecekan, orang ini sudah positif diblokir
            
    if is_excluded:
        continue # Buang dari website!
        
    # Jika aman (tidak mengandung kata yang dilarang), masukkan ke database bersih
    filtered_database.append(item)
        
    if nama_cosplayer not in koleksi_cosplayer:
        koleksi_cosplayer[nama_cosplayer] = set()
        
    koleksi_cosplayer[nama_cosplayer].add(nama_album_full)

# Menimpa database lama dengan database yang sudah difilter/dibersihkan
database_gambar = filtered_database

# Jika setelah difilter ternyata datanya kosong, hentikan website
if not database_gambar:
    st.warning("No Image Found")
    st.stop()

daftar_cosplayer = sorted(list(koleksi_cosplayer.keys()))

# Angka ini sekarang HANYA akan menghitung jumlah yang aman
st.write(f"Total database: **{len(daftar_cosplayer)} Cosplayer** | **{len(set(item['album'] for item in database_gambar))} Album** | **{len(database_gambar)} Images**")
st.markdown("---")

# ---------------------------------------------------------
# 4. SISTEM URL ROUTING & DROPDOWN DEFAULT
# ---------------------------------------------------------
query_album = st.query_params.get("album", None)
default_cosplayer = daftar_cosplayer[0]
default_album = None

if query_album:
    if " - " in query_album:
        calon_cosplayer = query_album.split(" - ", 1)[0].strip()
        if calon_cosplayer in daftar_cosplayer:
            default_cosplayer = calon_cosplayer
            default_album = query_album
    elif query_album in koleksi_cosplayer.get("Lainnya", []):
        default_cosplayer = "Lainnya"
        default_album = query_album

# ---------------------------------------------------------
# 5. DROPDOWN BERTINGKAT (COSPLAYER -> ALBUM)
# ---------------------------------------------------------
col_drop1, col_drop2 = st.columns(2)

with col_drop1:
    idx_cosplayer = daftar_cosplayer.index(default_cosplayer) if default_cosplayer in daftar_cosplayer else 0
    selected_cosplayer = st.selectbox("Cosplayer:", daftar_cosplayer, index=idx_cosplayer)

with col_drop2:
    if selected_cosplayer:
        daftar_album = sorted(list(koleksi_cosplayer[selected_cosplayer]))
        idx_album = daftar_album.index(default_album) if default_album in daftar_album else 0
        selected_album = st.selectbox(
            "Album:", 
            daftar_album, 
            index=idx_album,
            format_func=lambda x: x.split(" - ", 1)[1].strip() if " - " in x else x
        )

st.markdown("---")

# ---------------------------------------------------------
# 6. MENAMPILKAN GAMBAR DARI ALBUM YANG DIPILIH
# ---------------------------------------------------------
if selected_album:
    st.query_params["album"] = selected_album
    
    album_items = [item for item in database_gambar if item["album"] == selected_album]
    album_items = sorted(album_items, key=lambda x: x["filename"].lower())

    # --- BAGIAN YANG DIUBAH (Menjadi 3 Kolom) ---
    col_judul, col_info, col_tombol = st.columns([5, 1, 1])
    
    with col_judul:
        judul_rapi = selected_album.split(" - ", 1)[1].strip() if " - " in selected_album else selected_album
        st.subheader(f"Album: {judul_rapi}")
        
    with col_info:
        # Menambahkan sedikit jarak ke bawah agar teks sejajar dengan tombol
        st.write("") 
        st.write(f"**{len(album_items)} Images**")
        
    with col_tombol:
        # Menambahkan use_container_width=True agar tombolnya penuh dan rapi
        if st.button("🔄 Refresh Album", use_container_width=True):
            get_database_from_discord.clear()
            st.rerun()
    # -------------------------------------------

    with st.container():
        cols = st.columns(4) 
        
        for index, item in enumerate(album_items):
            col = cols[index % 4]
            filename = item["filename"]
            url_segar = item["url"] 
            
            with col:
                st.image(url_segar, use_container_width=True)
                
                if st.button(f"{filename}", key=f"zoom_{filename}", type="tertiary", help="Klik untuk memperbesar gambar"):
                    zoom_gambar(url_segar, filename)
