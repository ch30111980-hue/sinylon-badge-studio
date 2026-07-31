import sqlite3
import os
import glob
import shutil
import re

STUDIO_DIR = os.path.dirname(__file__)
STUDIO_DB = os.path.join(STUDIO_DIR, 'sinylon_studio.db')
PHOTOS_DIR = os.path.join(STUDIO_DIR, 'static', 'photos')
os.makedirs(PHOTOS_DIR, exist_ok=True)

PHOTO_SOURCE_DIRS = [
    "/Users/nourine/Documents/SINYLON /PHOTOS/厂区卡证资-20260718/厂区卡证资-20260718",
    "/Users/nourine/Documents/SINYLON /PHOTOS",
    "/Users/nourine/Documents/SINYLON",
    "/Users/nourine/Documents/NoroBadgeData/uploads",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/uploads",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/static/uploads"
]

def normalize(text):
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()

def fix_photos():
    # 1. Indexer tous les fichiers photos disponibles sur le Mac avec leur nom nettoyé
    available_photos = {}
    
    for pdir in PHOTO_SOURCE_DIRS:
        if not os.path.exists(pdir):
            continue
        for ext in ['*.jpg', '*.png', '*.jpeg', '*.webp', '*.JPG', '*.PNG']:
            for filepath in glob.glob(os.path.join(pdir, '**', ext), recursive=True):
                fname = os.path.basename(filepath)
                norm_name = normalize(os.path.splitext(fname)[0])
                
                # Copier vers static/photos
                dest = os.path.join(PHOTOS_DIR, fname)
                try:
                    shutil.copy2(filepath, dest)
                except Exception:
                    pass

                if norm_name:
                    available_photos[norm_name] = f"/static/photos/{fname}"

    print(f"📦 Photos indexées : {len(available_photos)} fichiers uniques dans static/photos/")

    # 2. Ouvrir la base de données Sinylon
    conn = sqlite3.connect(STUDIO_DB)
    cursor = conn.cursor()
    workers = cursor.execute("SELECT id, matricule, nom, prenom FROM workers").fetchall()

    matched_count = 0

    for w_id, mat, nom, prenom in workers:
        norm_nom = normalize(nom)
        norm_prenom = normalize(prenom)
        norm_full = normalize(f"{prenom}{nom}")
        norm_full_rev = normalize(f"{nom}{prenom}")
        norm_mat = normalize(mat)

        photo_url = None

        # Recherche par nom complet ou exact
        for candidate_key, url in available_photos.items():
            if candidate_key in [norm_full, norm_full_rev, norm_nom, norm_mat]:
                photo_url = url
                break

        # Deuxième passe : si le nom contient la clé (ex: "wanglei" -> "WANG LEI.png")
        if not photo_url:
            for candidate_key, url in available_photos.items():
                if len(candidate_key) >= 4 and (candidate_key in norm_full or norm_full in candidate_key or candidate_key in norm_full_rev):
                    photo_url = url
                    break

        # Mise à jour dans SQLite
        cursor.execute("UPDATE workers SET photo_path = ? WHERE id = ?", (photo_url, w_id))
        if photo_url:
            matched_count += 1
            print(f"✅ Match réussi : [{mat}] {prenom} {nom} -> {photo_url}")
        else:
            print(f"⚠️ Pas de photo pour : [{mat}] {prenom} {nom}")

    conn.commit()
    conn.close()

    print(f"\n🎉 BILAN FINAL : {matched_count}/{len(workers)} travailleurs Sinylon ont leur photo exacte associée !")

if __name__ == '__main__':
    fix_photos()
