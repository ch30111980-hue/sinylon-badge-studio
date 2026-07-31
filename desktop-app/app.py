import os
import sqlite3
import uuid
import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, make_response
from services.pdf_service import (
    generate_single_badge_pdf, generate_batch_badges_pdf,
    generate_permit_pdf, generate_sortie_materiel_pdf, generate_inspection_pemp_pdf,
    get_local_ip
)
from services.qr_service import generate_qr_code
from init_db import init_db, DB_PATH

app = Flask(__name__)
app.secret_key = 'sinylon_super_secret_key_2026'

def handle_url_error(error, endpoint, values):
    return f"/#nav-{endpoint.replace('.', '-')}"

app.url_build_error_handlers.append(handle_url_error)

if not os.path.exists(DB_PATH):
    init_db()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'photos')
SCRATCH_FOLDER = os.path.join(os.path.dirname(__file__), 'scratch')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SCRATCH_FOLDER, exist_ok=True)

class DummyUser:
    id = 1
    is_authenticated = True
    is_admin = True
    role = 'csps'
    nom = 'Nouri'
    prenom = 'Chahrour'
    entreprise = 'Sinylon'

    def full_name(self):
        return "Chahrour Nouri"

    def get_photo_url(self):
        return None

    def is_csps(self):
        return True

    def is_entreprise_admin(self):
        return True

    def get_unread_notifications_count(self):
        return 0

    def has_perm(self, perm):
        return True

    def __getattr__(self, name):
        return lambda *args, **kwargs: ""

@app.context_processor
def inject_globals():
    return dict(
        current_user=DummyUser(),
        now=datetime.datetime.now,
        _=lambda text: text,
        get_flashed_messages=lambda **kwargs: []
    )

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

GRADE_RANKS = [
    'directeur', 'director', 'manager', 'chef', 'responsable', 'head',
    'ingénieur', 'ingenieur', 'engineer', 'cadre', 'supervisor', 'superviseur',
    'technicien', 'technician', 'inspecteur', 'hse', 'qse', 'spécialiste', 'specialiste',
    'soudeur', 'welder', 'électricien', 'electricien', 'mécanicien', 'mecanicien', 'conducteur', 'maçon', 'macon', 'tuyauteur',
    'ouvrier', 'worker', 'manoeuvre', 'manœuvre', 'agent'
]

def get_grade_rank(fonction):
    fonction_lower = (fonction or '').lower()
    for idx, key in enumerate(GRADE_RANKS):
        if key in fonction_lower:
            return idx
    return 999

def sort_workers_by_grade(workers_rows):
    workers_list = [dict(w) for w in workers_rows]
    workers_list.sort(key=lambda w: (get_grade_rank(w.get('fonction', '')), (w.get('nom') or '').lower(), (w.get('matricule') or '')))
    for i, w in enumerate(workers_list, start=1):
        w['seq_id'] = i
    return workers_list

@app.route('/')
@app.route('/dashboard', endpoint='dashboard')
def index():
    conn = get_db()
    cursor = conn.cursor()
    
    rows = cursor.execute('SELECT * FROM workers').fetchall()
    workers = sort_workers_by_grade(rows)
    print_count = cursor.execute('SELECT COUNT(*) FROM print_logs').fetchone()[0]
    
    permits = cursor.execute('SELECT * FROM permits ORDER BY id DESC').fetchall()
    forms = cursor.execute('SELECT * FROM forms_generated ORDER BY id DESC').fetchall()

    conn.close()
    return render_template('index.html', workers=workers, print_count=print_count, permits=permits, forms=forms)

@app.route('/login', endpoint='login')
@app.route('/logout', endpoint='logout')
def auth_fallback():
    return redirect(url_for('index'))

@app.route('/badge/caisse', endpoint='badge.caisse')
@app.route('/caisse', endpoint='caisse')
def render_caisse():
    return render_template('badge/caisse.html')

@app.route('/badge/api/check_qr', methods=['POST'])
@app.route('/api/check_qr', methods=['POST'])
def check_qr_api():
    data = request.get_json(silent=True) or request.form
    raw_text = (data.get('text') or data.get('code') or '').strip()
    
    if not raw_text:
        return jsonify({'success': False, 'message': 'Aucun code fourni'}), 400

    matricule = None
    worker_uuid = None
    
    if '/verifier/' in raw_text:
        parts = raw_text.rstrip('/').split('/')
        last_part = parts[-1].strip()
        matricule = last_part
        worker_uuid = last_part
    elif raw_text.startswith('SINYLON_FIAT:'):
        parts = raw_text.split(':')
        if len(parts) >= 2 and parts[1].strip():
            matricule = parts[1].strip()
        if len(parts) >= 3 and parts[2].strip() and parts[2].strip() != 'None':
            worker_uuid = parts[2].strip()
    else:
        matricule = raw_text
        worker_uuid = raw_text

    conn = get_db()
    cursor = conn.cursor()
    
    worker = None
    if worker_uuid:
        worker = cursor.execute('SELECT * FROM workers WHERE uuid = ?', (worker_uuid,)).fetchone()
    if not worker and matricule:
        worker = cursor.execute('SELECT * FROM workers WHERE matricule = ?', (matricule,)).fetchone()
    if not worker and raw_text:
        worker = cursor.execute('SELECT * FROM workers WHERE nom LIKE ? OR id = ?', (f"%{raw_text}%", raw_text if raw_text.isdigit() else -1)).fetchone()
        
    conn.close()

    if not worker:
        return jsonify({'success': False, 'message': f'Badge/QR Inconnu ({raw_text})'}), 404

    w = dict(worker)
    is_blocked = (w.get('status') != 'Actif')
    
    photo = w.get('photo_path')
    if not photo or not os.path.exists(os.path.join(os.path.dirname(__file__), photo.lstrip('/'))):
        photo = '/static/img/default_avatar.png'

    badge_data = {
        'id': w['id'],
        'nom': w['nom'],
        'prenom': w['prenom'],
        'societe': w.get('entreprise') or 'Sinylon',
        'fonction': w['fonction'],
        'numero_badge': w['matricule'],
        'date_expiration': '31/12/2026',
        'photo_url': photo,
        'zones_acces': 'OR02.1, OR15, OR08, OR05, CSPS',
        'habilitations': {
            'hauteur': True,
            'soudure': True,
            'electricite': True,
            'confine': True,
            'engins': True,
            'sst': True
        },
        'is_blocked': is_blocked,
        'statut': 'bloque' if is_blocked else 'actif',
        'motif_blocage': 'Accès bloqué par la sécurité' if is_blocked else None
    }

    return jsonify({'success': True, 'badge': badge_data})


@app.route('/badge/verifier/<key>', endpoint='badge.verifier_public')
@app.route('/verifier/<key>')
def verifier_public(key):
    conn = get_db()
    cursor = conn.cursor()
    
    key_str = str(key).strip()
    worker = cursor.execute('SELECT * FROM workers WHERE id = ? OR uuid = ? OR matricule = ?', (key_str if key_str.isdigit() else -1, key_str, key_str)).fetchone()
    if not worker:
        worker = cursor.execute('SELECT * FROM workers WHERE nom LIKE ? OR prenom LIKE ?', (f"%{key_str}%", f"%{key_str}%")).fetchone()
    conn.close()

    if not worker:
        return f"""
        <!DOCTYPE html>
        <html><head><title>SINYLON FIAT STELLANTIS - Vérification Badge</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head><body class="bg-light d-flex align-items-center justify-content-center min-vh-100 p-3">
            <div class="card shadow-lg text-center p-4" style="max-width: 400px; border-radius: 16px;">
                <div class="display-1 text-danger mb-3">❌</div>
                <h4 class="fw-bold text-dark mb-2">Badge Inconnu</h4>
                <p class="text-muted">Aucune accréditation trouvée pour la référence : <strong>{key_str}</strong></p>
                <div class="badge bg-danger p-2 text-wrap">ACCÈS REFUSÉ — SINYLON FIAT STELLANTIS</div>
            </div>
        </body></html>
        """, 404

    w = dict(worker)
    is_active = (w.get('status') == 'Actif')
    photo = w.get('photo_path') or '/static/img/default_avatar.png'
    fonction = (w.get('fonction') or 'Intervenant Chantier').strip()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SINYLON FIAT STELLANTIS — Accréditation Chantier</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{ background: #0f172a; font-family: system-ui, -apple-system, sans-serif; }}
            .card-badge {{ border-radius: 20px; overflow: hidden; border: none; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }}
            .header-bar {{ background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%); color: white; padding: 20px; text-align: center; }}
            .photo-box {{ width: 110px; height: 135px; object-fit: cover; border-radius: 12px; border: 3px solid #1d4ed8; }}
        </style>
    </head>
    <body class="d-flex align-items-center justify-content-center min-vh-100 p-3">
        <div class="card card-badge w-100" style="max-width: 420px; background: white;">
            <div class="header-bar">
                <div style="font-family: Impact, sans-serif; font-size: 24px; letter-spacing: 1px; line-height: 1;">SINYLON</div>
                <div style="font-size: 11px; font-weight: 800; letter-spacing: 2px; color: #93c5fd; margin-top: 2px;">FIAT STELLANTIS</div>
                <div style="font-size: 9px; font-weight: 700; background: rgba(255,255,255,0.2); display: inline-block; padding: 2px 10px; border-radius: 20px; margin-top: 8px;">ACCRÉDITATION CHANTIER OFFICIELLE</div>
            </div>
            <div class="card-body p-4 text-center">
                <img src="{photo}" class="photo-box shadow-sm mb-3" alt="Photo">
                <h3 class="fw-bold text-dark mb-1">{w.get('prenom', '')} {w.get('nom', '').upper()}</h3>
                <h6 class="text-primary fw-bold mb-3"><i class="fas fa-briefcase me-1"></i> {fonction}</h6>
                
                <div class="bg-light p-3 rounded-3 mb-3 text-start small">
                    <div class="d-flex justify-content-between mb-1"><span class="text-muted">Fonction / Poste:</span> <strong class="text-primary">{fonction}</strong></div>
                    <div class="d-flex justify-content-between mb-1"><span class="text-muted">Matricule:</span> <strong class="text-dark">{w.get('matricule', '')}</strong></div>
                    <div class="d-flex justify-content-between mb-1"><span class="text-muted">Entreprise:</span> <strong>{w.get('entreprise') or 'SINYLON FIAT STELLANTIS'}</strong></div>
                    <div class="d-flex justify-content-between"><span class="text-muted">Projet:</span> <strong>FIAT STEP02</strong></div>
                </div>

                {'<div class="alert alert-success fw-bold p-3 rounded-3 mb-3" style="border-left: 5px solid #16a34a;"><i class="fas fa-check-circle me-2"></i>✓ ACCRÉDITÉ — ACCÈS AUTORISÉ</div>' if is_active else '<div class="alert alert-danger fw-bold p-3 rounded-3 mb-3" style="border-left: 5px solid #dc2626;"><i class="fas fa-ban me-2"></i>⚠️ ACCÈS REFUSÉ — ACCRÉDITATION BLOQUÉE</div>'}

                <div class="alert alert-danger bg-danger-subtle border-danger text-start p-3 rounded-3 mb-0" style="border-left: 5px solid #dc2626;">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-phone-volume text-danger fs-4 me-3"></i>
                        <div>
                            <div class="fw-bold text-danger-emphasis small">URGENCE HSE CHANTIER</div>
                            <div class="fw-bold text-dark fs-6">Nouri : <a href="tel:0563765157" class="text-danger text-decoration-none fw-extrabold">0563765157</a></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="card-footer bg-light text-center text-muted small py-2">
                Système NORO UNIFIED — Contrôle de Sécurité Chantier
            </div>
        </div>
    </body>
    </html>
    """


@app.route('/api/qr/png/<key>')
def get_qr_png(key):
    domain = os.environ.get('DOMAIN_URL', '').strip()
    key_clean = str(key).strip()
    if key_clean.startswith('PERM-') or key_clean.startswith('INSP-'):
        if domain:
            url = f"{domain.rstrip('/')}/permis/verifier/{key_clean}"
        else:
            ip = get_local_ip()
            url = f"http://{ip}:5050/permis/verifier/{key_clean}"
    else:
        if domain:
            url = f"{domain.rstrip('/')}/badge/verifier/{key_clean}"
        else:
            ip = get_local_ip()
            url = f"http://{ip}:5050/badge/verifier/{key_clean}"

    qr_path = os.path.join(SCRATCH_FOLDER, f"temp_qr_{key_clean}.png")
    generate_qr_code(url, qr_path)
    return send_file(qr_path, mimetype='image/png')


@app.route('/permis/verifier/<ref_num>')
@app.route('/verifier_permis/<ref_num>')
def verifier_permis_public(ref_num):
    conn = get_db()
    cursor = conn.cursor()
    ref_clean = str(ref_num).strip()
    permit = cursor.execute('SELECT * FROM permits WHERE ref_num = ? OR id = ?', (ref_clean, ref_clean if ref_clean.isdigit() else -1)).fetchone()
    conn.close()

    if not permit:
        return f"""
        <!DOCTYPE html>
        <html><head><title>SINYLON FIAT — Contrôle Permis</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head><body class="bg-dark text-white d-flex align-items-center justify-content-center min-vh-100 p-3">
            <div class="card bg-secondary text-white text-center p-4" style="max-width: 420px; border-radius: 16px;">
                <div class="display-1 text-warning mb-3">❓</div>
                <h4 class="fw-bold">Permis Inconnu ou Non Enregistré</h4>
                <p class="small text-white-50">Référence : {ref_clean}</p>
            </div>
        </body></html>
        """, 404

    p = dict(permit)
    is_valid = (p.get('status') == 'Valide' or p.get('status') == 'CONFORME')

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SINYLON FIAT — Permis de Travail HSE Dynamique</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{ background: #0b0f19; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }}
            .card-permis {{ border-radius: 24px; border: 1px solid rgba(255,255,255,0.1); background: #111827; box-shadow: 0 25px 50px rgba(0,0,0,0.6); overflow: hidden; }}
            .header-bar {{ background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%); padding: 24px; text-align: center; color: white; }}
        </style>
    </head>
    <body class="d-flex align-items-center justify-content-center min-vh-100 p-3">
        <div class="card card-permis w-100" style="max-width: 460px;">
            <div class="header-bar">
                <div class="fw-black fs-4 tracking-wider">SINYLON FIAT STELLANTIS</div>
                <div class="small fw-bold text-info mt-1">PERMIS DE TRAVAIL DYNAMIQUE (QR PERMANENT)</div>
                <div class="badge bg-white text-primary mt-2 px-3 py-1 rounded-pill">{p.get('ref_num')}</div>
            </div>
            <div class="card-body p-4">
                <h4 class="fw-bold text-center mb-1">{p.get('type_permis')}</h4>
                <p class="text-center text-muted small mb-4"><i class="fas fa-map-marker-alt text-danger me-1"></i> Zone : <strong>{p.get('zone', 'Chantier Step 02')}</strong></p>

                <div class="bg-dark p-3 rounded-3 mb-4 small border border-secondary">
                    <div class="d-flex justify-content-between mb-2"><span class="text-muted">Demandeur :</span> <strong>{p.get('demandeur')}</strong></div>
                    <div class="d-flex justify-content-between mb-2"><span class="text-muted">Entreprise :</span> <strong>{p.get('entreprise', 'Sinylon')}</strong></div>
                    <div class="d-flex justify-content-between mb-2"><span class="text-muted">Vent Météo :</span> <strong class="text-info">{p.get('vent_kmh', 15)} km/h</strong></div>
                    <div class="d-flex justify-content-between"><span class="text-muted">Dernière mise à jour PC :</span> <strong class="text-warning">{p.get('created_at', 'Aujourd\'hui')}</strong></div>
                </div>

                {'<div class="alert alert-success fw-bold text-center p-3 rounded-3 mb-4"><i class="fas fa-check-circle me-2 fs-5"></i>✓ PERMIS AUTORISÉ & EN VIGUEUR</div>' if is_valid else '<div class="alert alert-danger fw-bold text-center p-3 rounded-3 mb-4"><i class="fas fa-ban me-2 fs-5"></i>⚠️ PERMIS SUSPENDU OU EXPIRÉ</div>'}

                <div class="alert alert-danger bg-danger-subtle border-danger text-start p-3 rounded-3 mb-0">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <div class="fw-bold text-danger small">URGENCE HSE CHANTIER</div>
                            <div class="fw-bold text-dark fs-6">Nouri : <a href="tel:0563765157" class="text-danger text-decoration-none fw-extrabold">0563765157</a></div>
                        </div>
                        <span class="badge bg-danger text-white px-2 py-1">24/7</span>
                    </div>
                </div>
            </div>
            <div class="card-footer text-center text-muted small py-2 bg-dark border-top border-secondary">
                QR Code Fixe sur Terrain — Données en Direct du PC (NORO UNIFIED)
            </div>
        </div>
    </body>
    </html>
    """


@app.route('/api/workers', methods=['POST'])
def add_worker():
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    matricule = request.form.get('matricule', '').strip()
    fonction = request.form.get('fonction', '').strip()

    photo_path = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename != '':
            filename = f"{matricule}_{file.filename}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            photo_path = f"/static/photos/{filename}"

    if nom and prenom and matricule:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO workers (uuid, matricule, nom, prenom, fonction, entreprise, photo_path, status)
                VALUES (?, ?, ?, ?, ?, 'Sinylon', ?, 'Actif')
            ''', (str(uuid.uuid4()), matricule, nom, prenom, fonction, photo_path))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    return redirect(url_for('index'))

@app.route('/api/workers/edit/<int:worker_id>', methods=['POST'])
def edit_worker(worker_id):
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    matricule = request.form.get('matricule', '').strip()
    fonction = request.form.get('fonction', '').strip()
    status = request.form.get('status', 'Actif').strip()

    conn = get_db()
    cursor = conn.cursor()

    photo_path = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename != '':
            filename = f"{matricule}_{file.filename}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            photo_path = f"/static/photos/{filename}"

    if photo_path:
        cursor.execute('''
            UPDATE workers 
            SET nom = ?, prenom = ?, matricule = ?, fonction = ?, status = ?, photo_path = ?
            WHERE id = ?
        ''', (nom, prenom, matricule, fonction, status, photo_path, worker_id))
    else:
        cursor.execute('''
            UPDATE workers 
            SET nom = ?, prenom = ?, matricule = ?, fonction = ?, status = ?
            WHERE id = ?
        ''', (nom, prenom, matricule, fonction, status, worker_id))

    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/api/workers/delete/<int:worker_id>', methods=['POST'])
def delete_worker(worker_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM workers WHERE id = ?', (worker_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/api/workers/toggle_block/<int:worker_id>', methods=['POST'])
def toggle_block_worker(worker_id):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT status FROM workers WHERE id = ?', (worker_id,)).fetchone()
    if row:
        new_status = 'Bloqué' if row['status'] == 'Actif' else 'Actif'
        cursor.execute('UPDATE workers SET status = ? WHERE id = ?', (new_status, worker_id))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/api/print/single/<int:worker_id>')
def print_single(worker_id):
    conn = get_db()
    cursor = conn.cursor()
    
    worker = cursor.execute('SELECT * FROM workers WHERE id = ?', (worker_id,)).fetchone()
    if not worker:
        conn.close()
        return "Travailleur introuvable", 404

    worker_dict = dict(worker)
    
    cursor.execute('INSERT INTO print_logs (worker_id, type_impression) VALUES (?, ?)', (worker_id, 'Badge Individuel'))
    conn.commit()
    conn.close()

    output_pdf = os.path.join(SCRATCH_FOLDER, f"Badge_{worker_dict['matricule']}.pdf")
    generate_single_badge_pdf(worker_dict, output_pdf)

    response = make_response(send_file(output_pdf, mimetype='application/pdf'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/print/batch')
def print_batch():
    conn = get_db()
    cursor = conn.cursor()
    
    rows = cursor.execute('SELECT * FROM workers WHERE status = "Actif"').fetchall()
    workers_list = sort_workers_by_grade(rows)
    
    if not workers_list:
        conn.close()
        return "Aucun travailleur actif à imprimer", 400

    cursor.execute('INSERT INTO print_logs (type_impression) VALUES (?)', ('Planche A4 (Lot)',))
    conn.commit()
    conn.close()

    output_pdf = os.path.join(SCRATCH_FOLDER, "Planche_Badges_Sinylon_A4.pdf")
    generate_batch_badges_pdf(workers_list, output_pdf)

    return send_file(output_pdf, mimetype='application/pdf')

@app.route('/api/print/selected', methods=['POST'])
def print_selected_batch():
    worker_ids = request.form.getlist('worker_ids')
    if not worker_ids:
        return "Aucun travailleur sélectionné", 400

    conn = get_db()
    cursor = conn.cursor()
    
    placeholders = ','.join('?' for _ in worker_ids)
    rows = cursor.execute(f'SELECT * FROM workers WHERE id IN ({placeholders})', worker_ids).fetchall()
    workers_list = sort_workers_by_grade(rows)

    cursor.execute('INSERT INTO print_logs (type_impression) VALUES (?)', (f'Planche Sélectionnée ({len(workers_list)} badges)',))
    conn.commit()
    conn.close()

    output_pdf = os.path.join(SCRATCH_FOLDER, "Planche_Badges_Selectionnees_A4.pdf")
    generate_batch_badges_pdf(workers_list, output_pdf)

    return send_file(output_pdf, mimetype='application/pdf')

# ================= PERMIS PAPIER OFFICIELS NORO-UNIFIED =================
@app.route('/permis/papier/<type_name>')
def render_permis_papier(type_name):
    valid_templates = {
        'chaud': 'permis/papier/chaud.html',
        'fouille': 'permis/papier/fouille.html',
        'espace_confine': 'permis/papier/espace_confine.html',
        'hauteur': 'permis/papier/hauteur.html',
        'levage': 'permis/papier/levage.html',
        'electrique': 'permis/papier/electrique.html',
        'securite_generale': 'permis/papier/securite_generale.html'
    }
    if type_name in valid_templates:
        return render_template(valid_templates[type_name])
    return "Modèle de permis non trouvé", 404

# ================= FICHES DU BUREAU (SORTIE MATÉRIEL & PEMP) =================
@app.route('/fiches/sortie_materiel')
def render_fiche_sortie_materiel():
    return render_template('fiches/sortie_materiel.html')

@app.route('/fiches/inspection_pemp')
def render_fiche_inspection_pemp():
    pdf_path = os.path.join(os.path.dirname(__file__), 'templates', 'fiches', 'inspection_pemp.pdf')
    if os.path.exists(pdf_path):
        return send_file(pdf_path, mimetype='application/pdf')
    return "Fiche PEMP non trouvée", 404

# PERMIS DE TRAVAIL HSE
@app.route('/api/permis/nouveau', methods=['POST'])
def create_permit():
    type_permis = request.form.get('type_permis', 'Travaux à Chaud').strip()
    demandeur = request.form.get('demandeur', '').strip()
    zone = request.form.get('zone', '').strip()
    description = request.form.get('description', '').strip()
    vent_kmh = float(request.form.get('vent_kmh', 0) or 0)
    temp_celsius = float(request.form.get('temp_celsius', 0) or 0)

    ref_num = f"PERM-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    status = "VALIDE"
    if vent_kmh > 60 or temp_celsius > 40:
        status = "ARRÊT MÉTÉO"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO permits (ref_num, type_permis, entreprise, demandeur, zone, description, vent_kmh, temp_celsius, status)
        VALUES (?, ?, 'Sinylon', ?, ?, ?, ?, ?, ?)
    ''', (ref_num, type_permis, demandeur, zone, description, vent_kmh, temp_celsius, status))
    permit_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/api/permis/pdf/<int:permit_id>')
def print_permit(permit_id):
    conn = get_db()
    cursor = conn.cursor()
    permit = cursor.execute('SELECT * FROM permits WHERE id = ?', (permit_id,)).fetchone()
    conn.close()

    if not permit:
        return "Permis introuvable", 404

    permit_dict = dict(permit)
    output_pdf = os.path.join(SCRATCH_FOLDER, f"Permis_{permit_dict['ref_num']}.pdf")
    generate_permit_pdf(permit_dict, output_pdf)

    return send_file(output_pdf, mimetype='application/pdf')

# FICHES REMPLISSABLES
@app.route('/api/fiches/sortie_materiel', methods=['POST'])
def create_sortie_materiel():
    demandeur = request.form.get('demandeur', '').strip()
    destination = request.form.get('destination', '').strip()
    vehicule = request.form.get('vehicule', '').strip()
    materiels = request.form.get('materiels', '').strip()

    ref_num = f"SORTIE-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    form_data = {
        'ref_num': ref_num,
        'date_sortie': datetime.date.today().strftime('%d/%m/%Y'),
        'demandeur': demandeur,
        'destination': destination,
        'vehicule': vehicule,
        'materiels': materiels
    }

    output_pdf = os.path.join(SCRATCH_FOLDER, f"{ref_num}.pdf")
    generate_sortie_materiel_pdf(form_data, output_pdf)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forms_generated (ref_num, type_fiche, titre, demandeur, pdf_path)
        VALUES (?, 'Autorisation Sortie Matériel', ?, ?, ?)
    ''', (ref_num, f"Sortie Matériel - {destination}", demandeur, output_pdf))
    conn.commit()
    conn.close()

    return send_file(output_pdf, mimetype='application/pdf')

@app.route('/api/fiches/inspection_pemp', methods=['POST'])
def create_inspection_pemp():
    inspecteur = request.form.get('inspecteur', '').strip()
    nacelle_num = request.form.get('nacelle_num', '').strip()
    modele = request.form.get('modele', '').strip()
    resultat = request.form.get('resultat', 'CONFORME').strip()

    ref_num = f"INSP-PEMP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    form_data = {
        'ref_num': ref_num,
        'inspecteur': inspecteur,
        'nacelle_num': nacelle_num,
        'modele': modele,
        'resultat': resultat
    }

    output_pdf = os.path.join(SCRATCH_FOLDER, f"{ref_num}.pdf")
    generate_inspection_pemp_pdf(form_data, output_pdf)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forms_generated (ref_num, type_fiche, titre, demandeur, pdf_path)
        VALUES (?, 'Inspection Mensuelle PEMP', ?, ?, ?)
    ''', (ref_num, f"Inspection Nacelle {nacelle_num}", inspecteur, output_pdf))
    conn.commit()
    conn.close()

    return send_file(output_pdf, mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"🚀 SINYLON Badge Studio Pro démarré sur http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
