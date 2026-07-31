import openpyxl
import sqlite3
import os
import re

EXCEL_PATH = "/Users/nourine/Documents/SINYLON /PHOTOS/厂区卡证资-20260718/厂区卡证资-20260718/现场签证人员信息统计表 JUN.xlsx"
STUDIO_DB = os.path.join(os.path.dirname(__file__), 'sinylon_studio.db')

def normalize(text):
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()

def update_functions():
    if not os.path.exists(EXCEL_PATH):
        print(f"❌ Fichier Excel introuvable: {EXCEL_PATH}")
        return

    wb = openpyxl.load_workbook(EXCEL_PATH)
    sheet = wb.active

    excel_workers = {}
    for row in sheet.iter_rows(values_only=True):
        if not row or len(row) < 3:
            continue
        
        name_cell = str(row[1] or '').strip()
        prof_cell = str(row[2] or '').strip()

        if name_cell and prof_cell and name_cell.lower() != 'nom prenom':
            norm_name = normalize(name_cell)
            if norm_name:
                # Formater joliment la profession en Français/Titre propre
                prof_formatted = prof_cell.capitalize()
                excel_workers[norm_name] = prof_formatted

    print(f"📦 {len(excel_workers)} professions extraites du fichier Excel Sinylon.")

    conn = sqlite3.connect(STUDIO_DB)
    cursor = conn.cursor()

    workers = cursor.execute("SELECT id, matricule, nom, prenom, fonction FROM workers").fetchall()
    updated_count = 0

    for w_id, mat, nom, prenom, old_func in workers:
        norm_full1 = normalize(f"{prenom}{nom}")
        norm_full2 = normalize(f"{nom}{prenom}")
        norm_nom = normalize(nom)

        matched_prof = None
        for key, prof in excel_workers.items():
            if key in [norm_full1, norm_full2, norm_nom] or (len(key) >= 4 and key in norm_full1) or (len(norm_full1) >= 4 and norm_full1 in key):
                matched_prof = prof
                break

        if matched_prof:
            cursor.execute("UPDATE workers SET fonction = ? WHERE id = ?", (matched_prof, w_id))
            updated_count += 1
            print(f"✅ Mis à jour : [{mat}] {prenom} {nom} ➔ {matched_prof}")

    conn.commit()
    conn.close()

    print(f"\n🎉 FONCTIONS MISES À JOUR : {updated_count}/{len(workers)} travailleurs Sinylon ont leur fonction officielle !")

if __name__ == '__main__':
    update_functions()
