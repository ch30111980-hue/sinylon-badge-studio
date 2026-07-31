import sqlite3
import os
import glob
import shutil
import re

STUDIO_DIR = os.path.dirname(__file__)
STUDIO_DB = os.path.join(STUDIO_DIR, 'sinylon_studio.db')
PHOTOS_DIR = os.path.join(STUDIO_DIR, 'static', 'photos')
os.makedirs(PHOTOS_DIR, exist_ok=True)

PHOTO_SOURCES = [
    "/Users/nourine/Documents/SINYLON /PHOTOS/厂区卡证资-20260718/厂区卡证资-20260718",
    "/Users/nourine/Documents/SINYLON /PHOTOS",
    "/Users/nourine/Documents/SINYLON",
    "/Users/nourine/Documents/NoroBadgeData/uploads",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/uploads",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/static/uploads"
]

def clean_str(s):
    if not s:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(s)).lower()

def process_photos():
    # 1. Copier TOUTES les photos sources vers static/photos
    copied_files = {}
    for src_dir in PHOTO_SOURCES:
        if not os.path.exists(src_dir):
            continue
        for ext in ['*.jpg', '*.png', '*.jpeg', '*.webp', '*.JPG', '*.PNG']:
            for filepath in glob.glob(os.path.join(src_dir, ext)):
                fname = os.path.basename(filepath)
                dest_path = os.path.join(PHOTOS_DIR, fname)
                shutil.copy2(filepath, dest_path)
                
                # Indexer la photo sous sa forme nettoyée
                clean_name = clean_str(os.path.splitext(fname)[0])
                copied_files[clean_name] = f"/static/photos/{fname}"

    print(f"🖼️ {len(copied_files)} fichiers photos copiés et indexés dans static/photos/")

    # 2. Lier les photos aux travailleurs Sinylon dans la base SQLite
    conn = sqlite3.connect(STUDIO_DB)
    cursor = conn.cursor()
    workers = cursor.execute("SELECT id, matricule, nom, prenom, photo_path FROM workers").fetchall()

    updated_count = 0
    for w_id, mat, nom, prenom, current_photo in workers:
        clean_nom = clean_str(nom)
        clean_prenom = clean_str(prenom)
        clean_mat = clean_str(mat)
        full_name_clean = clean_prenom + clean_nom
        full_name_clean_rev = clean_nom + clean_prenom

        found_photo = None

        # Recherche de correspondance exacte ou partielle
        for key, web_path in copied_files.items():
            if key and (key == clean_mat or key == clean_nom or key == clean_prenom or key == full_name_clean or key == full_name_clean_rev or key in full_name_clean or key in full_name_clean_rev or clean_nom in key or clean_prenom in key):
                found_photo = web_path
                break

        if found_photo:
            cursor.execute("UPDATE workers SET photo_path = ? WHERE id = ?", (found_photo, w_id))
            updated_count += 1
        elif current_photo and current_photo.startswith('/Users/'):
            # Convertir le chemin local absolu en chemin web relatif /static/photos/
            basename = os.path.basename(current_photo)
            dest_path = os.path.join(PHOTOS_DIR, basename)
            if os.path.exists(current_photo):
                shutil.copy2(current_photo, dest_path)
                cursor.execute("UPDATE workers SET photo_path = ? WHERE id = ?", (f"/static/photos/{basename}", w_id))
                updated_count += 1

    conn.commit()

    # Vérification du nombre de travailleurs avec photo
    with_photo = cursor.execute("SELECT COUNT(*) FROM workers WHERE photo_path IS NOT NULL AND photo_path != ''").fetchone()[0]
    total = cursor.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    conn.close()

    print(f"✅ Association terminée ! {with_photo}/{total} travailleurs Sinylon ont désormais leur photo d'identité affichée.")

if __name__ == '__main__':
    process_photos()
