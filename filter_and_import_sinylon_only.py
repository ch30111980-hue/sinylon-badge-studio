import sqlite3
import os
import glob
import shutil
import uuid

STUDIO_DIR = os.path.dirname(__file__)
STUDIO_DB = os.path.join(STUDIO_DIR, 'sinylon_studio.db')
PHOTOS_DIR = os.path.join(STUDIO_DIR, 'static', 'photos')
os.makedirs(PHOTOS_DIR, exist_ok=True)

DB_SOURCES = [
    "/Users/nourine/Documents/SINYLON/sinylon_workers.db",
    "/Users/nourine/Documents/NoroBadgeData/badge.db",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/instance/noro_unified.db",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/instance/noro.db"
]

PHOTO_SEARCH_DIRS = [
    "/Users/nourine/Documents/NoroBadgeData/uploads",
    "/Users/nourine/Documents/NoroBadgeData/badges",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/uploads",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/static/uploads",
    "/Users/nourine/Documents/SINYLON"
]

def find_photo_for_worker(matricule, nom, prenom):
    """
    Recherche une photo correspondant au matricule ou au nom/prénom dans les dossiers de médias.
    """
    clean_mat = matricule.replace('-', '').lower()
    clean_nom = nom.lower().strip()
    clean_prenom = prenom.lower().strip()

    for pdir in PHOTO_SEARCH_DIRS:
        if not os.path.exists(pdir):
            continue
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.JPG', '*.PNG']:
            for filepath in glob.glob(os.path.join(pdir, '**', ext), recursive=True):
                fname = os.path.basename(filepath).lower()
                if (clean_mat and clean_mat in fname) or (clean_nom and clean_nom in fname) or (clean_prenom and clean_prenom in fname):
                    # Copier la photo vers static/photos
                    dest_filename = f"{clean_mat if clean_mat else clean_nom}_{os.path.basename(filepath)}"
                    dest_path = os.path.join(PHOTOS_DIR, dest_filename)
                    shutil.copy2(filepath, dest_path)
                    return f"/static/photos/{dest_filename}"
    return None

def filter_and_import_sinylon_only():
    conn_studio = sqlite3.connect(STUDIO_DB)
    cursor_studio = conn_studio.cursor()

    # 1. Nettoyer la base studio : Supprimer toutes les entrées non Sinylon
    cursor_studio.execute("DELETE FROM workers WHERE LOWER(entreprise) NOT LIKE '%sinylon%' AND matricule NOT LIKE 'SIN-%'")
    conn_studio.commit()

    print("🧹 Nettoyage effectué : Seules les données Sinylon ont été conservées.")

    existing_matricules = set(row[0] for row in cursor_studio.execute("SELECT matricule FROM workers").fetchall())
    sinylon_imported = 0

    # 2. Scanner les bases sources pour extraire STRICTEMENT les travailleurs Sinylon
    for db_path in DB_SOURCES:
        if not os.path.exists(db_path):
            continue

        print(f"🔍 Extraction Sinylon depuis : {db_path}...")
        try:
            conn_src = sqlite3.connect(db_path)
            conn_src.row_factory = sqlite3.Row
            cursor_src = conn_src.cursor()

            tables = [row[0] for row in cursor_src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            
            for t in ['workers', 'travailleur', 'badge', 'badges', 'users']:
                if t in tables:
                    rows = cursor_src.execute(f"SELECT * FROM {t}").fetchall()
                    for r in rows:
                        d = dict(r)
                        ent = str(d.get('entreprise') or d.get('company') or '').lower()
                        mat = str(d.get('matricule') or d.get('code') or d.get('badge_id') or '').upper()

                        # Filtre Strict Sinylon
                        if 'sinylon' in ent or mat.startswith('SIN-') or 'sin' in ent:
                            nom = str(d.get('nom') or d.get('name') or d.get('last_name') or '').strip()
                            prenom = str(d.get('prenom') or d.get('first_name') or '').strip()
                            fonction = str(d.get('fonction') or d.get('post') or d.get('role') or 'Travailleur Sinylon').strip()
                            photo_src = d.get('photo_path') or d.get('photo') or ''

                            if not nom and not prenom:
                                continue

                            if not mat or not mat.startswith('SIN-'):
                                mat = f"SIN-{1000 + len(existing_matricules) + 1}"

                            # Gérer la photo
                            final_photo = None
                            if photo_src and os.path.exists(photo_src):
                                dest_filename = f"{mat}_{os.path.basename(photo_src)}"
                                dest_path = os.path.join(PHOTOS_DIR, dest_filename)
                                shutil.copy2(photo_src, dest_path)
                                final_photo = f"/static/photos/{dest_filename}"
                            else:
                                final_photo = find_photo_for_worker(mat, nom, prenom)

                            if mat not in existing_matricules:
                                cursor_studio.execute('''
                                    INSERT INTO workers (uuid, matricule, nom, prenom, fonction, entreprise, photo_path, status)
                                    VALUES (?, ?, ?, ?, ?, 'Sinylon', ?, 'Actif')
                                ''', (str(uuid.uuid4()), mat, nom, prenom, fonction, final_photo))
                                existing_matricules.add(mat)
                                sinylon_imported += 1
                            else:
                                # Mettre à jour la photo si elle manquait
                                if final_photo:
                                    cursor_studio.execute("UPDATE workers SET photo_path = ? WHERE matricule = ? AND (photo_path IS NULL OR photo_path = '')", (final_photo, mat))

            conn_src.close()
        except Exception as e:
            print(f"⚠️ Erreur de lecture sur {db_path}: {e}")

    # 3. Mettre à jour les photos pour tous les travailleurs Sinylon existants
    workers_in_db = cursor_studio.execute("SELECT id, matricule, nom, prenom, photo_path FROM workers").fetchall()
    for w_id, mat, nom, prenom, photo in workers_in_db:
        if not photo or not os.path.exists(os.path.join(STUDIO_DIR, photo.lstrip('/'))):
            found = find_photo_for_worker(mat, nom, prenom)
            if found:
                cursor_studio.execute("UPDATE workers SET photo_path = ? WHERE id = ?", (found, w_id))

    conn_studio.commit()

    total_sinylon = cursor_studio.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    conn_studio.close()

    print(f"\n✅ RESTRUCTURATION TERMINÉE EN SUCCÈS ! Total Travailleurs 100% Sinylon : {total_sinylon}")

if __name__ == '__main__':
    filter_and_import_sinylon_only()
