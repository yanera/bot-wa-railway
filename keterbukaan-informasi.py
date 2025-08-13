import os
import requests
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# ====== KONFIGURASI ======
RAILWAY_URL = "https://<NAMA-APP>.up.railway.app"  # Ganti dengan URL Railway Bot kamu
GROUP_MODE = "name"  # "id" atau "name"
GROUP_TARGET = "Info Bursa"  # Nama grup kalau GROUP_MODE="name"
GROUP_ID = "1234567890-123456@g.us"  # ID grup kalau GROUP_MODE="id"

# Keyword berita yang mau diambil
KEYWORDS = ['HMETD', 'PMTHMETD']
BLACKLIST = []

# Lokasi file dataset
DATASET_DIR = "Dataset"
DATASET_FILE = os.path.join(DATASET_DIR, "Keterbukaan Informasi.csv")

# ====== FUNGSI ======
def timestamp(date_value):
    month_mapping = {
        'Januari': '01',
        'Februari': '02',
        'Maret': '03',
        'April': '04',
        'Mei': '05',
        'Juni': '06',
        'Juli': '07',
        'Agustus': '08',
        'September': '09',
        'Oktober': '10',
        'November': '11',
        'Desember': '12'
    }
    try:
        day, month_name, year, time_str = date_value.split()
        month_number = month_mapping.get(month_name)
    except:
        first_part, time_str = date_value.split()
        year, month_number, day = first_part.split('-')

    formatted_date = f"{year}-{month_number}-{day} {time_str}"
    return pd.to_datetime(formatted_date, format="%Y-%m-%d %H:%M:%S")

def send_to_group(text):
    if GROUP_MODE == "id":
        url = f"{RAILWAY_URL}/send"
        payload = {"to": GROUP_ID, "message": text}
    else:  # name
        url = f"{RAILWAY_URL}/sendGroupByName"
        payload = {"groupName": GROUP_TARGET, "message": text}

    r = requests.post(url, json=payload)
    print("Send response:", r.json())

def check_keywords(text):
    return any(k in text for k in KEYWORDS) and not any(b in text for b in BLACKLIST)

def scrape_idx():
    print("🔍 Mengambil data keterbukaan informasi IDX...")
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = uc.Chrome(options=options)

    url = "https://www.idx.co.id/id/perusahaan-tercatat/keterbukaan-informasi/"
    driver.get(url)

    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH,
        "//*[@id='app']/div[2]/main/div/div/div[2]/div[2]/div/div[1]")))

    data = {"Date": [], "Title": [], "Link": []}

    for i in range(10):  # Ambil 10 berita di halaman pertama
        try:
            date_item = timestamp(driver.find_element(By.XPATH, f"//*[@id='app']/div[2]/main/div/div/div[2]/div[2]/div/div[{i+1}]").text.split("\n")[0])
            title_item = driver.find_element(By.XPATH, f"//*[@id='app']/div[2]/main/div/div/div[2]/div[2]/div/div[{i+1}]/h6/a").text
            link_item = driver.find_element(By.XPATH, f"//*[@id='app']/div[2]/main/div/div/div[2]/div[2]/div/div[{i+1}]/h6/a").get_attribute('href')

            data["Date"].append(date_item)
            data["Title"].append(title_item)
            data["Link"].append(link_item)
        except Exception as e:
            print("Error ambil data:", e)

    driver.quit()
    return pd.DataFrame(data)

# ====== MAIN ======
if __name__ == "__main__":
    # Pastikan folder Dataset ada
    os.makedirs(DATASET_DIR, exist_ok=True)

    # Kalau file CSV belum ada, buat file kosong
    if not os.path.exists(DATASET_FILE):
        print("📂 Membuat file dataset baru...")
        pd.DataFrame(columns=["Date", "Title", "Link"]).to_csv(DATASET_FILE, index=False)

    # Load dataset lama
    old_data = pd.read_csv(DATASET_FILE, parse_dates=["Date"])

    # Scrape data baru
    new_data = scrape_idx()

    # Filter hanya yang lebih baru dari dataset lama
    if not old_data.empty:
        latest_date = old_data["Date"].max()
        new_data = new_data[new_data["Date"] > latest_date]

    if new_data.empty:
        print("Tidak ada data baru.")
    else:
        print(f"📢 {len(new_data)} berita baru ditemukan.")
        for _, row in new_data.iterrows():
            if check_keywords(row["Title"]):
                pesan = f"📅 {row['Date']}\n📰 {row['Title']}\n🔗 {row['Link']}"
                send_to_group(pesan)

        # Simpan data terbaru ke CSV
        all_data = pd.concat([new_data, old_data], ignore_index=True)
        all_data.to_csv(DATASET_FILE, index=False, date_format='%Y-%m-%d %H:%M:%S')
        print("✅ Dataset diperbarui.")
