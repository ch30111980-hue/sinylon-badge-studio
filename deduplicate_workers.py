import sqlite3
import os
import re

STUDIO_DB = os.path.join(os.path.dirname(__file__), 'sinylon_studio.db')

def normalize_name(text):
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()

def deduplicate():
    conn = sqlite3.connect(STUDIO_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    workers = cursor.execute("SELECT * FROM workers ORDER BY id ASC").fetchall()
    print(f"📊 Total travailleurs avant déduplication : {len(workers)}")

    seen_signatures = {}
    to_delete_ids = []

    for w in workers:
        w_id = w['id']
        nom = w['nom'] or ''
        prenom = w['prenom'] or ''
        photo = w['photo_path'] or ''
        mat = w['matricule'] or ''

        # Signature basée soit sur la photo (si présente), soit sur le nom nettoyé
        norm_full = normalize_name(f"{prenom}{nom}")
        norm_rev = normalize_name(f"{nom}{prenom}")
        photo_key = os.path.basename(photo).lower() if photo else ""

        # Déterminer si ce travailleur est déjà vu
        key = None
        if photo_key:
            key = f"photo_{photo_key}"
        elif norm_full:
            key = f"name_{norm_full}"

        if not key:
            continue

        if key in seen_signatures or (f"name_{norm_rev}" in seen_signatures and not photo_key):
            # Déjà présent : marquer ce doublon pour suppression
            prev_id = seen_signatures.get(key) or seen_signatures.get(f"name_{norm_rev}")
            
            # Préférer garder la fiche qui a un prénom ET nom séparés, ou un matricule plus petit (ex: SIN-0032 vs SIN-1070)
            prev_w = cursor.execute("SELECT * FROM workers WHERE id = ?", (prev_id,)).fetchone()
            
            # Comparer la qualité
            if (len(prenom) > 0 and len(prev_w['prenom']) == 0) or (mat.startswith('SIN-00') and not prev_w['matricule'].startswith('SIN-00')):
                # Remplacer le précédent par le nouveau plus propre
                to_delete_ids.append(prev_id)
                seen_signatures[key] = w_id
                print(f"🗑️ Doublon détecté : Suppression ID {prev_id} ({prev_w['matricule']}), conservation ID {w_id} ({mat}) [{prenom} {nom}]")
            else:
                to_delete_ids.append(w_id)
                print(f"🗑️ Doublon détecté : Suppression ID {w_id} ({mat}), conservation ID {prev_id} ({prev_w['matricule']}) [{prev_w['prenom']} {prev_w['nom']}]")
        else:
            seen_signatures[key] = w_id
            if norm_rev != norm_full:
                seen_signatures[f"name_{norm_rev}"] = w_id

    # Exécuter les suppressions
    for del_id in set(to_delete_ids):
        cursor.execute("DELETE FROM workers WHERE id = ?", (del_id,))

    conn.commit()

    final_count = cursor.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    conn.close()

    print(f"\n✅ DÉDUPLICATION TERMINÉE : {len(to_delete_ids)} doublons supprimés.")
    print(f"🎯 Total travailleurs Sinylon uniques conservés : {final_count}")

if __name__ == '__main__':
    deduplicate()
