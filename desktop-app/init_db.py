import sqlite3
import os
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), 'sinylon_studio.db')
EXISTING_DB = "/Users/nourine/Documents/SINYLON/sinylon_workers.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            matricule TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            fonction TEXT NOT NULL,
            entreprise TEXT DEFAULT 'Sinylon',
            photo_path TEXT,
            qr_code_path TEXT,
            status TEXT DEFAULT 'Actif',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS print_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER,
            type_impression TEXT DEFAULT 'Badge Individuel',
            printed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (worker_id) REFERENCES workers (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_num TEXT UNIQUE NOT NULL,
            type_permis TEXT NOT NULL,
            entreprise TEXT DEFAULT 'Sinylon',
            demandeur TEXT NOT NULL,
            zone TEXT NOT NULL,
            description TEXT,
            vent_kmh REAL DEFAULT 0,
            temp_celsius REAL DEFAULT 0,
            status TEXT DEFAULT 'VALIDE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forms_generated (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_num TEXT NOT NULL,
            type_fiche TEXT NOT NULL,
            titre TEXT NOT NULL,
            demandeur TEXT,
            pdf_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed demo workers if table is empty
    cursor.execute("SELECT COUNT(*) FROM workers")
    count = cursor.fetchone()[0]

    if count == 0:
        demo_workers = [
            ("Shi", "Junming", "SIN-0032", "Conducteur de Travaux", "Actif"),
            ("Chen", "Wei", "SIN-0033", "Chef d'Équipe Génie Civil", "Actif"),
            ("Brahimi", "Karim", "SIN-0034", "Superviseur HSE", "Actif"),
            ("Li", "Ming", "SIN-0035", "Opérateur Grue", "Actif"),
            ("Wang", "Lei", "SIN-0036", "Ingénieur Structure", "Actif"),
            ("Benali", "Yacine", "SIN-0037", "Technicien Électricité", "Actif"),
            ("Zhang", "Wei", "SIN-0038", "Coordinateur Sécurité", "Actif"),
            ("Liu", "Yang", "SIN-0039", "Spécialiste Coffrage", "Actif")
        ]

        for nom, prenom, matricule, fonction, status in demo_workers:
            cursor.execute('''
                INSERT INTO workers (uuid, matricule, nom, prenom, fonction, entreprise, status)
                VALUES (?, ?, ?, ?, ?, 'Sinylon', ?)
            ''', (str(uuid.uuid4()), matricule, nom, prenom, fonction, status))
        
        # Add sample print log
        cursor.execute("INSERT INTO print_logs (worker_id, type_impression) VALUES (1, 'Badge Individuel')")
        cursor.execute("INSERT INTO print_logs (worker_id, type_impression) VALUES (2, 'Planche A4 (Lot)')")
        
        print(f"✅ Base de données initialisée avec {len(demo_workers)} travailleurs Sinylon.")
    else:
        print(f"ℹ️ Base de données déjà existante ({count} travailleurs).")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
