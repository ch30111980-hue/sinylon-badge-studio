import sqlite3
import os
import glob
import uuid
import csv

STUDIO_DB = os.path.join(os.path.dirname(__file__), 'sinylon_studio.db')

DB_SOURCES = [
    "/Users/nourine/Documents/SINYLON/sinylon_workers.db",
    "/Users/nourine/Documents/NoroBadgeData/badge.db",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/instance/noro_unified.db",
    "/Users/nourine/.gemini/antigravity/scratch/noro_unified/instance/noro.db"
]

CSV_SOURCES = [
    "/Users/nourine/Documents/Documents_Noro_Admin/export_badges_noro.csv",
    "/Users/nourine/Documents/Documents_Noro_Admin/export_badges_noro-2.csv"
]

def merge_databases():
    conn_studio = sqlite3.connect(STUDIO_DB)
    cursor_studio = conn_studio.cursor()

    imported_count = 0
    existing_matricules = set(row[0] for row in cursor_studio.execute("SELECT matricule FROM workers").fetchall())

    for db_path in DB_SOURCES:
        if not os.path.exists(db_path):
            continue

        print(f"🔍 Examination de la base : {db_path}...")
        try:
            conn_src = sqlite3.connect(db_path)
            conn_src.row_factory = sqlite3.Row
            cursor_src = conn_src.cursor()

            # Lister toutes les tables
            tables = [row[0] for row in cursor_src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            
            for t in ['workers', 'travailleur', 'badge', 'badges', 'users']:
                if t in tables:
                    rows = cursor_src.execute(f"SELECT * FROM {t}").fetchall()
                    for r in rows:
                        d = dict(r)
                        nom = d.get('nom') or d.get('name') or d.get('last_name') or ''
                        prenom = d.get('prenom') or d.get('first_name') or ''
                        matricule = d.get('matricule') or d.get('code') or d.get('badge_id') or ''
                        fonction = d.get('fonction') or d.get('post') or d.get('role') or 'Travailleur'
                        entreprise = d.get('entreprise') or d.get('company') or 'Sinylon'
                        photo = d.get('photo_path') or d.get('photo') or ''

                        if not nom and not prenom:
                            continue

                        if not matricule:
                            matricule = f"SIN-{1000 + imported_count + len(existing_matricules)}"

                        if matricule not in existing_matricules:
                            cursor_studio.execute('''
                                INSERT INTO workers (uuid, matricule, nom, prenom, fonction, entreprise, photo_path, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 'Actif')
                            ''', (str(uuid.uuid4()), matricule, str(nom).strip(), str(prenom).strip(), str(fonction).strip(), str(entreprise).strip(), photo))
                            existing_matricules.add(matricule)
                            imported_count += 1

            conn_src.close()
        except Exception as e:
            print(f"⚠️ Avertissement lors de la lecture de {db_path}: {e}")

    # Importer les CSV s'ils existent
    for csv_path in CSV_SOURCES:
        if os.path.exists(csv_path):
            print(f"📄 Lecture du fichier CSV : {csv_path}...")
            try:
                with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for d in reader:
                        nom = d.get('nom') or d.get('Nom') or ''
                        prenom = d.get('prenom') or d.get('Prenom') or ''
                        matricule = d.get('matricule') or d.get('Matricule') or ''
                        fonction = d.get('fonction') or d.get('Fonction') or 'Travailleur'
                        entreprise = d.get('entreprise') or d.get('Entreprise') or 'Sinylon'

                        if not nom and not prenom:
                            continue

                        if not matricule:
                            matricule = f"SIN-{1000 + imported_count + len(existing_matricules)}"

                        if matricule not in existing_matricules:
                            cursor_studio.execute('''
                                INSERT INTO workers (uuid, matricule, nom, prenom, fonction, entreprise, status)
                                VALUES (?, ?, ?, ?, ?, ?, 'Actif')
                            ''', (str(uuid.uuid4()), matricule, str(nom).strip(), str(prenom).strip(), str(fonction).strip(), str(entreprise).strip()))
                            existing_matricules.add(matricule)
                            imported_count += 1
            except Exception as e:
                print(f"⚠️ Erreur lors de la lecture de {csv_path}: {e}")

    conn_studio.commit()
    conn_studio.close()
    print(f"✅ Fusion terminée ! {imported_count} nouveaux travailleurs importés (Total : {len(existing_matricules)}).")

if __name__ == '__main__':
    merge_databases()
