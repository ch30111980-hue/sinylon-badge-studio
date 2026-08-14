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

def get_bms_meteo():
    """
    Module officiel Bulletin Météorologique Spécial (BMS) Météo Algérie (ONM - Oran Chantier).
    """
    vent_kmh = float(os.environ.get('BMS_VENT', 24))
    temp_c = float(os.environ.get('BMS_TEMP', 32))

    bms_alert = False
    bms_message = f"CONFORME (Vent : {vent_kmh} km/h | Temp : {temp_c}°C)"
    bms_level = "Vert"

    if vent_kmh >= 60:
        bms_alert = True
        bms_message = f"🚨 BMS VENT FORT ALERTE ORANGE ({vent_kmh} km/h) — ARRÊT PERMIS HAUTEUR & LEVAGE"
        bms_level = "Orange"
    elif temp_c >= 40:
        bms_alert = True
        bms_message = f"🚨 BMS CANICULE ALERTE ORANGE ({temp_c}°C) — PAUSES HYDRATATION OBLIGATOIRES"
        bms_level = "Orange"

    return {
        'vent_kmh': vent_kmh,
        'temp_c': temp_c,
        'bms_alert': bms_alert,
        'bms_message': bms_message,
        'bms_level': bms_level
    }

@app.context_processor
def inject_globals():
    return dict(
        current_user=DummyUser(),
        now=datetime.datetime.now,
        bms=get_bms_meteo(),
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
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

class WorkerItem(dict):
    """Wrapper pour assurer la compatibilité totale avec les templates Jinja2 (attributs, méthodes)."""
    def __init__(self, d, entreprises_dict=None):
        super().__init__(d)
        self.__dict__ = self
        self.entreprises_dict = entreprises_dict or {}

    def full_name(self):
        return f"{self.get('prenom', '')} {self.get('nom', '').upper()}".strip()

    def get_photo_url(self):
        p = self.get('photo_path')
        if p and p.startswith('/static/'):
            return p
        if p:
            return f"/static/photos/{os.path.basename(p)}"
        return "/static/img/default_avatar.png"

    @property
    def photo_filename(self):
        return self.get('photo_path')

    @property
    def numero_badge(self):
        return self.get('matricule') or f"SIN-{self.get('id', 0):04d}"

    @property
    def statut(self):
        s = (self.get('status') or 'actif').lower()
        if self.get('is_blocked'):
            return 'bloque'
        return s

    @property
    def entreprise_rel(self):
        ent_id = self.get('entreprise_id')
        if ent_id and ent_id in self.entreprises_dict:
            return self.entreprises_dict[ent_id]
        return {'id': 1, 'nom': self.get('societe_affichee') or self.get('entreprise') or 'Sinylon', 'couleur': '#1d664f', 'couleur_fond': '#111828'}

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
    
    # Entreprises
    ent_rows = cursor.execute('SELECT * FROM entreprises').fetchall()
    entreprises = [dict(e) for e in ent_rows]
    ent_map = {e['id']: e for e in entreprises}

    rows = cursor.execute('SELECT * FROM workers').fetchall()
    sorted_rows = sort_workers_by_grade(rows)
    workers = [WorkerItem(w, ent_map) for w in sorted_rows]
    print_count = cursor.execute('SELECT COUNT(*) FROM print_logs').fetchone()[0]
    
    active_count = sum(1 for w in workers if w.get('status') == 'Actif')
    inactive_count = sum(1 for w in workers if w.get('status') != 'Actif')
    
    permits = cursor.execute('SELECT * FROM permits ORDER BY id DESC').fetchall()
    forms = cursor.execute('SELECT * FROM forms_generated ORDER BY id DESC').fetchall()

    conn.close()
    return render_template('index.html', workers=workers, entreprises=entreprises, active_count=active_count, inactive_count=inactive_count, print_count=print_count, permits=permits, forms=forms)

@app.route('/login', endpoint='login')
@app.route('/logout', endpoint='logout')
def auth_fallback():
    return redirect(url_for('index'))

@app.route('/api/v1/admin/pending_counts')
def api_pending_counts():
    return jsonify({'total_permis': 0, 'total_badges': 0, 'permits': [], 'badges': []})

@app.route('/favicon.ico')
def favicon():
    fiat_icon = os.path.join(os.path.dirname(__file__), 'static', 'img', 'fiat_logo.png')
    if os.path.exists(fiat_icon):
        return send_file(fiat_icon, mimetype='image/png')
    return ('', 204)

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
@app.route('/api/badge/verifier/<key>')
def verifier_public(key):
    conn = get_db()
    cursor = conn.cursor()
    
    key_str = str(key).strip()
    clean_digits = ''.join(c for c in key_str if c.isdigit())
    
    # Recherche ultra-robuste (insensible à la casse, par matricule, uuid, id, numéro seul ou nom/prénom)
    worker = cursor.execute('''
        SELECT * FROM workers 
        WHERE UPPER(TRIM(matricule)) = UPPER(?) 
           OR UPPER(TRIM(uuid)) = UPPER(?)
           OR (id = ? AND ? > 0)
    ''', (key_str, key_str, int(key_str) if key_str.isdigit() else -1, int(key_str) if key_str.isdigit() else -1)).fetchone()
    
    if not worker and clean_digits:
        worker = cursor.execute('''
            SELECT * FROM workers 
            WHERE UPPER(matricule) LIKE ? OR id = ?
        ''', (f"%{clean_digits}%", int(clean_digits))).fetchone()

    if not worker:
        worker = cursor.execute('''
            SELECT * FROM workers 
            WHERE UPPER(nom) LIKE UPPER(?) OR UPPER(prenom) LIKE UPPER(?)
        ''', (f"%{key_str}%", f"%{key_str}%")).fetchone()
        
    conn.close()

    if not worker:
        return f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="utf-8">
            <title>SINYLON FIAT STELLANTIS — Vérification Badge</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <style>
                body {{ background: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f8fafc; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
                .verify-card {{ background: #181b24; border: 1px solid #dc2626; border-radius: 20px; box-shadow: 0 25px 50px -12px rgba(220,38,38,0.25); max-width: 420px; width: 100%; overflow: hidden; }}
                .verify-header {{ background: #991b1b; padding: 20px; text-align: center; color: white; }}
            </style>
        </head>
        <body>
            <div class="verify-card text-center">
                <div class="verify-header">
                    <i class="fas fa-exclamation-triangle fa-3x mb-2"></i>
                    <h4 class="fw-bold mb-0">ACCÈS REFUSÉ</h4>
                    <small style="opacity:0.9;">SINYLON · PROJET FIAT STELLANTIS</small>
                </div>
                <div class="p-4">
                    <h5 class="fw-bold text-danger mb-2">Badge Inconnu ou Non Enregistré</h5>
                    <p class="text-secondary small mb-3">Aucune accréditation trouvée pour la référence :</p>
                    <div class="p-2 bg-dark rounded border border-danger text-danger fw-bold font-monospace mb-4">{key_str}</div>
                    
                    <div class="p-3 bg-dark rounded text-start small border border-secondary mb-3">
                        <div class="d-flex align-items-center text-warning">
                            <i class="fas fa-shield-alt fa-2x me-3"></i>
                            <div>
                                <strong class="d-block text-white">Contrôle de Sécurité Chantier</strong>
                                L'accès au site est strictement interdit aux personnes non accréditées.
                            </div>
                        </div>
                    </div>

                    <div class="p-3 rounded text-start" style="background: rgba(239, 68, 68, 0.15); border-left: 4px solid #ef4444;">
                        <small class="text-danger fw-bold d-block">URGENCE HSE CHANTIER :</small>
                        <strong class="text-white fs-6">Nouri : <a href="tel:0563765157" class="text-danger text-decoration-none">0563765157</a></strong>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """, 404

    w = dict(worker)
    is_blocked = bool(w.get('is_blocked')) or (w.get('status', '').lower() in ['bloqué', 'bloque', 'inactif'])
    is_active = not is_blocked
    
    photo = w.get('photo_path') or ''
    if not photo:
        photo = '/static/img/default_avatar.png'
    elif not photo.startswith('/') and not photo.startswith('http'):
        photo = '/' + photo
        
    fonction = (w.get('fonction') or 'Intervenant Chantier').strip()
    nom_complet = f"{w.get('prenom', '')} {w.get('nom', '').upper()}".strip()
    matricule = w.get('matricule') or f"SIN-{w.get('id', 0):04d}"
    societe = w.get('societe_affichee') or w.get('entreprise') or 'Sinylon'
    projet = w.get('projet') or 'CSPS Projet FIAT'
    date_exp = w.get('date_expiration') or '31/12/2026'
    
    s1 = bool(w.get('step_1_valide', 1))
    s2 = bool(w.get('step_2_valide', 1))
    s3 = bool(w.get('step_3_valide', 0))

    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="utf-8">
        <title>ACCRÉDITATION OFFICIELLE — {nom_complet}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{ background: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f8fafc; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
            .card-badge {{ border-radius: 24px; overflow: hidden; border: 1px solid {'#10b981' if is_active else '#ef4444'}; box-shadow: 0 25px 50px -12px {'rgba(16, 185, 129, 0.25)' if is_active else 'rgba(239, 68, 68, 0.25)'}; background: #181b24; max-width: 440px; width: 100%; }}
            .header-bar {{ background: {'linear-gradient(135deg, #064e3b 0%, #047857 100%)' if is_active else 'linear-gradient(135deg, #7f1d1d 0%, #b91c1c 100%)'}; color: white; padding: 20px; text-align: center; }}
            .photo-box {{ width: 120px; height: 140px; object-fit: cover; border-radius: 16px; border: 3px solid {'#10b981' if is_active else '#ef4444'}; background: #1f2937; }}
            .step-pill {{ width: 32px; height: 32px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; margin: 0 3px; }}
            .step-on {{ background: #10b981; color: white; }}
            .step-off {{ background: #334155; color: #94a3b8; border: 1px solid #475569; }}
        </style>
    </head>
    <body>
        <div class="card card-badge">
            <div class="header-bar">
                <div class="d-flex justify-content-between align-items-center mb-2 px-2">
                    <span style="font-family: Impact, sans-serif; font-size: 26px; letter-spacing: 1.5px;">FIAT</span>
                    <span style="font-weight: 800; font-size: 13px; letter-spacing: 1px; color: #a7f3d0;">AMCE · EL DJAZAIR</span>
                </div>
                <div style="font-size: 10px; font-weight: 800; letter-spacing: 1.5px; background: rgba(0,0,0,0.25); display: inline-block; padding: 4px 14px; border-radius: 20px;">
                    {'✓ ACCRÉDITATION CHANTIER OFFICIELLE' if is_active else '⚠️ ACCÈS CHANTIER BLOQUÉ'}
                </div>
            </div>
            
            <div class="card-body p-4 text-center">
                <div class="position-relative d-inline-block mb-3">
                    <img src="{photo}" class="photo-box shadow" alt="Photo de {nom_complet}" onerror="this.src='/static/img/default_avatar.png'">
                    <span class="position-absolute bottom-0 end-0 badge rounded-pill {'bg-success' if is_active else 'bg-danger'} p-2 border border-2 border-dark">
                        <i class="fas {'fa-check' if is_active else 'fa-ban'}"></i>
                    </span>
                </div>
                
                <h3 class="fw-bold text-white mb-1">{nom_complet}</h3>
                <div class="badge {'bg-emerald-600 text-white' if is_active else 'bg-danger'} px-3 py-2 fs-6 mb-3" style="background: {'#059669' if is_active else '#dc2626'};">
                    {fonction}
                </div>
                
                <!-- Détails Salarié -->
                <div class="rounded-3 p-3 text-start small mb-3" style="background: #0f172a; border: 1px solid #334155;">
                    <div class="d-flex justify-content-between mb-2 pb-1 border-bottom border-secondary">
                        <span class="text-secondary">Matricule ID :</span>
                        <strong class="text-info font-monospace fs-6">{matricule}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2 pb-1 border-bottom border-secondary">
                        <span class="text-secondary">Société :</span>
                        <strong class="text-white">{societe}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2 pb-1 border-bottom border-secondary">
                        <span class="text-secondary">Projet :</span>
                        <strong class="text-primary-emphasis" style="color: #60a5fa !important;">{projet}</strong>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span class="text-secondary">Date d'Expiration :</span>
                        <strong class="text-warning">{date_exp}</strong>
                    </div>
                </div>

                <!-- Validation Steps -->
                <div class="d-flex justify-content-between align-items-center rounded-3 p-2 mb-3" style="background: #0f172a; border: 1px solid #334155;">
                    <span class="text-secondary small fw-bold ps-2">Validation Chantier :</span>
                    <div>
                        <span class="step-pill {'step-on' if s1 else 'step-off'}" title="Step 1 Accueil HSE">1</span>
                        <span class="step-pill {'step-on' if s2 else 'step-off'}" title="Step 2 Visite Médicale">2</span>
                        <span class="step-pill {'step-on' if s3 else 'step-off'}" title="Step 3 Habilitations Spécifiques">3</span>
                    </div>
                </div>

                <!-- Statut Décisionnel -->
                {'<div class="alert alert-success fw-bold p-3 rounded-3 mb-3 text-start d-flex align-items-center" style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #34d399;"><i class="fas fa-check-circle fa-2x me-3"></i><div><div class="fw-bold">ACCÈS AUTORISÉ</div><small class="text-light" style="opacity:0.85;">Badge valide pour l\'ensemble des zones du site.</small></div></div>' if is_active else '<div class="alert alert-danger fw-bold p-3 rounded-3 mb-3 text-start d-flex align-items-center" style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #f87171;"><i class="fas fa-ban fa-2x me-3"></i><div><div class="fw-bold">ACCÈS REFUSÉ / BLOQUÉ</div><small class="text-light" style="opacity:0.85;">Veuillez vous présenter au bureau CSPS HSE.</small></div></div>'}

                <!-- Contact Urgence HSE -->
                <div class="p-3 rounded-3 text-start" style="background: rgba(239, 68, 68, 0.12); border-left: 4px solid #ef4444;">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-phone-volume text-danger fs-3 me-3"></i>
                        <div>
                            <div class="text-danger fw-bold small">URGENCE HSE CHANTIER</div>
                            <div class="text-white fw-bold fs-6">Nouri : <a href="tel:0563765157" class="text-danger text-decoration-none fw-bolder">0563765157</a></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card-footer text-center py-2" style="background: #0f172a; border-top: 1px solid #334155; font-size: 11px; color: #94a3b8;">
                Système CSPS NORO · FIAT Algérie © 2026
            </div>
        </div>
    </body>
    </html>
    """



DEFAULT_DOMAIN = "https://sinylon-badge-studio.onrender.com"


@app.route('/api/qr/png/<key>')
def get_qr_png(key):
    domain = os.environ.get('DOMAIN_URL', DEFAULT_DOMAIN).strip()
    key_clean = str(key).strip()
    if key_clean.startswith('PERM-') or key_clean.startswith('INSP-') or key_clean.startswith('SORTIE-'):
        url = f"{domain.rstrip('/')}/permis/verifier/{key_clean}"
    else:
        url = f"{domain.rstrip('/')}/badge/verifier/{key_clean}"

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


# ================= BADGE STUDIO & WORKERS ROUTES =================

@app.route('/badge/admin', endpoint='badge.admin_dashboard')
@app.route('/badge/studio', endpoint='badge.studio')
def badge_admin_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    ent_rows = cursor.execute('SELECT * FROM entreprises').fetchall()
    entreprises = [dict(e) for e in ent_rows]
    ent_map = {e['id']: e for e in entreprises}

    rows = cursor.execute('SELECT * FROM workers').fetchall()
    sorted_rows = sort_workers_by_grade(rows)
    workers_list = [WorkerItem(w, ent_map) for w in sorted_rows]
    conn.close()

    return render_template('badge/admin_dashboard.html', entreprises=entreprises, badges=workers_list, workers=workers_list)


@app.route('/badge/imprimer_a4', endpoint='badge.imprimer_a4')
@app.route('/badge/imprimer', endpoint='badge.imprimer')
@app.route('/badge/imprimer_selection', endpoint='badge.imprimer_selection')
def badge_imprimer_a4():
    lot_filter = request.args.get('lot', '').strip()
    ids_filter = request.args.get('ids', '').strip()
    
    conn = get_db()
    cursor = conn.cursor()
    
    ent_rows = cursor.execute('SELECT * FROM entreprises').fetchall()
    entreprises = [dict(e) for e in ent_rows]
    ent_map = {e['id']: e for e in entreprises}

    if ids_filter:
        ids_list = [int(i.strip()) for i in ids_filter.split(',') if i.strip().isdigit()]
        if ids_list:
            placeholders = ','.join('?' for _ in ids_list)
            rows = cursor.execute(f'SELECT * FROM workers WHERE id IN ({placeholders})', ids_list).fetchall()
        else:
            rows = cursor.execute('SELECT * FROM workers').fetchall()
    elif lot_filter:
        rows = cursor.execute('SELECT * FROM workers WHERE entreprise_id = ? OR entreprise LIKE ? OR societe_affichee LIKE ?', (lot_filter, f"%{lot_filter}%", f"%{lot_filter}%")).fetchall()
    else:
        rows = cursor.execute('SELECT * FROM workers').fetchall()

    sorted_rows = sort_workers_by_grade(rows)
    workers_list = [WorkerItem(w, ent_map) for w in sorted_rows]
    conn.close()

    return render_template('badge/imprimer_a4.html', badges=workers_list, lot=lot_filter)


@app.route('/badge/export_csv', endpoint='badge.export_csv')
@app.route('/api/export/excel', endpoint='api.export_excel')
def export_workers_csv():
    import csv
    import io

    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute('SELECT * FROM workers ORDER BY id ASC').fetchall()
    conn.close()

    output = io.StringIO()
    # UTF-8 BOM pour ouverture directe et propre dans Excel
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    
    writer.writerow([
        'ID', 'Matricule / N° Badge', 'Nom', 'Prénom', 'Société', 'Projet', 'Année',
        'Fonction / Poste', 'Date de Naissance', 'Groupe Sanguin', 'N° CNAS', 'N° CNI / Passeport',
        'Téléphone', 'Département', 'Statut', 'Date Émission', 'Date Expiration',
        'Step 1 Validé', 'Step 2 Validé', 'Step 3 Validé',
        'Hab. Hauteur', 'Hab. Soudure', 'Hab. Électricité', 'Hab. Espace Confiné', 'Hab. Engins', 'Hab. SST'
    ])

    for r in rows:
        w = dict(r)
        writer.writerow([
            w.get('id', ''),
            w.get('matricule', ''),
            (w.get('nom') or '').upper(),
            (w.get('prenom') or '').title(),
            w.get('societe_affichee') or w.get('entreprise') or 'Sinylon',
            w.get('projet') or 'CSPS Projet FIAT',
            w.get('annee') or '2026',
            w.get('fonction') or '',
            w.get('date_naissance') or '',
            w.get('groupe_sanguin') or '',
            w.get('cnas') or '',
            w.get('carte_id') or '',
            w.get('telephone') or '',
            w.get('departement') or '',
            w.get('status') or 'Actif',
            w.get('date_emission') or '01/01/2026',
            w.get('date_expiration') or '31/12/2026',
            'OUI' if w.get('step_1_valide') else 'NON',
            'OUI' if w.get('step_2_valide') else 'NON',
            'OUI' if w.get('step_3_valide') else 'NON',
            'OUI' if w.get('habilitation_hauteur') else 'NON',
            'OUI' if w.get('habilitation_soudure') else 'NON',
            'OUI' if w.get('habilitation_electricite') else 'NON',
            'OUI' if w.get('habilitation_confine') else 'NON',
            'OUI' if w.get('habilitation_engins') else 'NON',
            'OUI' if w.get('habilitation_sst') else 'NON'
        ])

    csv_data = output.getvalue()
    filename = f"Export_Badges_Sinylon_Fiat_{datetime.date.today().strftime('%Y%m%d')}.csv"
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    return response


@app.route('/badge/nouveau', methods=['POST'], endpoint='badge.nouveau')
@app.route('/api/workers', methods=['POST'])
def add_or_update_worker():
    edit_id = request.form.get('edit_id', '').strip()
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    matricule = (request.form.get('matricule') or request.form.get('numero_badge') or '').strip()
    fonction = (request.form.get('fonction') or request.form.get('poste') or '').strip()
    
    societe = request.form.get('societe_affichee', '').strip() or request.form.get('societe', '').strip() or 'Sinylon'
    projet = request.form.get('projet', 'CSPS Projet FIAT').strip()
    annee = request.form.get('annee', '2026').strip()
    date_naissance = request.form.get('date_naissance', '').strip()
    groupe_sanguin = request.form.get('groupe_sanguin', '').strip()
    cnas = request.form.get('cnas', '').strip()
    carte_id = request.form.get('carte_id', '').strip()
    telephone = request.form.get('telephone', '').strip()
    departement = request.form.get('departement', '').strip()
    entreprise_id = request.form.get('entreprise_id', '1').strip()
    date_emission = request.form.get('date_emission', '01/01/2026').strip()
    date_expiration = request.form.get('date_expiration', '31/12/2026').strip()
    
    step_1_valide = 1 if request.form.get('step_1_valide') in ['on', '1', 'true', True] else 0
    step_2_valide = 1 if request.form.get('step_2_valide') in ['on', '1', 'true', True] else 0
    step_3_valide = 1 if request.form.get('step_3_valide') in ['on', '1', 'true', True] else 0
    
    hab_hauteur = 1 if request.form.get('habilitation_hauteur') in ['on', '1', 'true', True] else 0
    hab_soudure = 1 if request.form.get('habilitation_soudure') in ['on', '1', 'true', True] else 0
    hab_elec = 1 if request.form.get('habilitation_electricite') in ['on', '1', 'true', True] else 0
    hab_confine = 1 if request.form.get('habilitation_confine') in ['on', '1', 'true', True] else 0
    hab_engins = 1 if request.form.get('habilitation_engins') in ['on', '1', 'true', True] else 0
    hab_sst = 1 if request.form.get('habilitation_sst') in ['on', '1', 'true', True] else 0

    status = request.form.get('status', 'Actif').strip()

    photo_path = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename != '':
            ext = os.path.splitext(file.filename)[1].lower() or '.jpg'
            safe_fname = f"worker_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, safe_fname))
            photo_path = f"/static/photos/{safe_fname}"

    conn = get_db()
    cursor = conn.cursor()

    if edit_id and edit_id.isdigit():
        # Update existing worker
        worker_id = int(edit_id)
        if photo_path:
            cursor.execute('''
                UPDATE workers 
                SET nom = ?, prenom = ?, matricule = ?, fonction = ?, entreprise = ?, societe_affichee = ?,
                    projet = ?, annee = ?, date_naissance = ?, groupe_sanguin = ?, cnas = ?, carte_id = ?,
                    telephone = ?, departement = ?, entreprise_id = ?, date_emission = ?, date_expiration = ?,
                    step_1_valide = ?, step_2_valide = ?, step_3_valide = ?,
                    habilitation_hauteur = ?, habilitation_soudure = ?, habilitation_electricite = ?,
                    habilitation_confine = ?, habilitation_engins = ?, habilitation_sst = ?,
                    status = ?, photo_path = ?
                WHERE id = ?
            ''', (nom, prenom, matricule, fonction, societe, societe, projet, annee, date_naissance, groupe_sanguin, cnas, carte_id,
                  telephone, departement, entreprise_id, date_emission, date_expiration,
                  step_1_valide, step_2_valide, step_3_valide,
                  hab_hauteur, hab_soudure, hab_elec, hab_confine, hab_engins, hab_sst,
                  status, photo_path, worker_id))
        else:
            cursor.execute('''
                UPDATE workers 
                SET nom = ?, prenom = ?, matricule = ?, fonction = ?, entreprise = ?, societe_affichee = ?,
                    projet = ?, annee = ?, date_naissance = ?, groupe_sanguin = ?, cnas = ?, carte_id = ?,
                    telephone = ?, departement = ?, entreprise_id = ?, date_emission = ?, date_expiration = ?,
                    step_1_valide = ?, step_2_valide = ?, step_3_valide = ?,
                    habilitation_hauteur = ?, habilitation_soudure = ?, habilitation_electricite = ?,
                    habilitation_confine = ?, habilitation_engins = ?, habilitation_sst = ?,
                    status = ?
                WHERE id = ?
            ''', (nom, prenom, matricule, fonction, societe, societe, projet, annee, date_naissance, groupe_sanguin, cnas, carte_id,
                  telephone, departement, entreprise_id, date_emission, date_expiration,
                  step_1_valide, step_2_valide, step_3_valide,
                  hab_hauteur, hab_soudure, hab_elec, hab_confine, hab_engins, hab_sst,
                  status, worker_id))
        conn.commit()
    else:
        # Create new worker
        if not matricule:
            last_id_row = cursor.execute('SELECT MAX(id) FROM workers').fetchone()
            next_num = (last_id_row[0] or 0) + 1
            matricule = f"SIN-{next_num:04d}"

        new_uuid = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO workers (
                uuid, matricule, nom, prenom, fonction, entreprise, societe_affichee,
                projet, annee, date_naissance, groupe_sanguin, cnas, carte_id,
                telephone, departement, entreprise_id, date_emission, date_expiration,
                step_1_valide, step_2_valide, step_3_valide,
                habilitation_hauteur, habilitation_soudure, habilitation_electricite,
                habilitation_confine, habilitation_engins, habilitation_sst,
                photo_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            new_uuid, matricule, nom, prenom, fonction, societe, societe,
            projet, annee, date_naissance, groupe_sanguin, cnas, carte_id,
            telephone, departement, entreprise_id, date_emission, date_expiration,
            step_1_valide, step_2_valide, step_3_valide,
            hab_hauteur, hab_soudure, hab_elec, hab_confine, hab_engins, hab_sst,
            photo_path, status
        ))
        conn.commit()

    conn.close()

    # Redirection vers la page appropriée
    ref = request.headers.get('Referer', '')
    if 'badge/admin' in ref or 'badge/studio' in ref:
        return redirect(url_for('badge.admin_dashboard'))
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
            ext = os.path.splitext(file.filename)[1].lower() or '.jpg'
            safe_fname = f"worker_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, safe_fname))
            photo_path = f"/static/photos/{safe_fname}"

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

    ref = request.headers.get('Referer', '')
    if 'badge/admin' in ref:
        return redirect(url_for('badge.admin_dashboard'))
    return redirect(url_for('index'))


@app.route('/api/workers/delete/<int:worker_id>', methods=['POST'])
@app.route('/badge/supprimer/<int:worker_id>', endpoint='badge.supprimer')
def delete_worker(worker_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM workers WHERE id = ?', (worker_id,))
    conn.commit()
    conn.close()
    
    ref = request.headers.get('Referer', '')
    if 'badge/admin' in ref:
        return redirect(url_for('badge.admin_dashboard'))
    return redirect(url_for('index'))


@app.route('/api/workers/toggle_block/<int:worker_id>', methods=['POST'])
@app.route('/badge/bloquer/<int:worker_id>', endpoint='badge.bloquer')
def toggle_block_worker(worker_id):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT status, is_blocked FROM workers WHERE id = ?', (worker_id,)).fetchone()
    if row:
        new_status = 'Bloqué' if row['status'] == 'Actif' else 'Actif'
        new_blocked = 1 if new_status == 'Bloqué' else 0
        cursor.execute('UPDATE workers SET status = ?, is_blocked = ? WHERE id = ?', (new_status, new_blocked, worker_id))
        conn.commit()
    conn.close()
    
    ref = request.headers.get('Referer', '')
    if 'badge/admin' in ref:
        return redirect(url_for('badge.admin_dashboard'))
    return redirect(url_for('index'))


@app.route('/badge/telecharger_pdf/<int:worker_id>', endpoint='badge.telecharger_pdf')
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


@app.route('/api/print/batch', methods=['GET', 'POST'])
def print_batch():
    download = request.values.get('download') == '1' or request.values.get('dl') == '1'
    conn = get_db()
    cursor = conn.cursor()
    
    rows = cursor.execute('SELECT * FROM workers WHERE status = "Actif"').fetchall()
    workers_list = sort_workers_by_grade(rows)
    
    if not workers_list:
        conn.close()
        return "Aucun travailleur actif à imprimer", 400

    cursor.execute('INSERT INTO print_logs (type_impression) VALUES (?)', (f'Planche A4 (Lot {len(workers_list)} Actifs)',))
    conn.commit()
    conn.close()

    filename = f"Planche_Badges_Sinylon_Actifs_{len(workers_list)}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    output_pdf = os.path.join(SCRATCH_FOLDER, filename)
    generate_batch_badges_pdf(workers_list, output_pdf)

    return send_file(
        output_pdf,
        mimetype='application/pdf',
        as_attachment=download,
        download_name=filename
    )


@app.route('/api/print/selected', methods=['GET', 'POST'])
def print_selected_batch():
    download = request.values.get('download') == '1' or request.values.get('dl') == '1'
    worker_ids = request.values.getlist('worker_ids') or request.values.getlist('badge_ids')
    if not worker_ids:
        raw_ids = request.values.get('ids', '')
        if raw_ids:
            worker_ids = [i.strip() for i in raw_ids.split(',') if i.strip()]

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

    filename = f"Planche_Badges_Selection_{len(workers_list)}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    output_pdf = os.path.join(SCRATCH_FOLDER, filename)
    generate_batch_badges_pdf(workers_list, output_pdf)

    return send_file(
        output_pdf,
        mimetype='application/pdf',
        as_attachment=download,
        download_name=filename
    )


@app.route('/badge/api_update_ent', methods=['POST'], endpoint='badge.api_update_ent')
def api_update_ent():
    data = request.get_json(silent=True) or request.form
    ent_id = data.get('id')
    couleur = data.get('couleur')
    couleur_fond = data.get('couleur_fond')
    email_notifications = data.get('email_notifications')

    if not ent_id:
        return jsonify({'success': False, 'error': 'ID requis'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE entreprises
        SET couleur = COALESCE(?, couleur),
            couleur_fond = COALESCE(?, couleur_fond),
            email_notifications = COALESCE(?, email_notifications)
        WHERE id = ?
    ''', (couleur, couleur_fond, email_notifications, ent_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/badge/api/entreprise/creer', methods=['POST'])
def api_create_entreprise():
    nom = request.form.get('nom', '').strip()
    couleur = request.form.get('couleur', '#1d664f').strip()
    couleur_fond = request.form.get('couleur_fond', '#111828').strip()

    if not nom:
        return redirect(url_for('badge.admin_dashboard'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO entreprises (nom, couleur, couleur_fond) VALUES (?, ?, ?)', (nom, couleur, couleur_fond))
    conn.commit()
    conn.close()

    return redirect(url_for('badge.admin_dashboard'))


@app.route('/badge/api/entreprise/delete/<int:ent_id>', methods=['POST'])
def api_delete_entreprise(ent_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM entreprises WHERE id = ?', (ent_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('badge.admin_dashboard'))


@app.route('/api/ai/parse_document', methods=['POST'])
def api_ai_parse_document():
    """Endpoint backend pour parser les CNI/Passeports/CNAS si besoin."""
    if 'document' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier reçu'}), 400
    
    file = request.files['document']
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'Nom de fichier vide'}), 400

    # Sauvegarde temporaire
    ext = os.path.splitext(file.filename)[1].lower() or '.jpg'
    safe_name = f"scan_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
    saved_path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(saved_path)

    # Réponse par défaut avec détection basique de nom de fichier
    res_data = {
        'success': True,
        'photo_url': f"/static/photos/{safe_name}",
        'nom': '',
        'prenom': '',
        'fonction': 'Ouvrier Spécialisé',
        'societe': 'Sinylon',
        'projet': 'CSPS Projet FIAT',
        'annee': '2026',
        'cnas': '',
        'carte_id': ''
    }
    return jsonify(res_data)

# ================= PERMIS PAPIER OFFICIELS NORO-UNIFIED =================
@app.route('/permis/papier/<type_name>', methods=['GET', 'POST'], endpoint='permis.formulaire_papier')
@app.route('/permis/nouveau', methods=['GET', 'POST'], endpoint='permis.nouveau')
@app.route('/permis/creer', methods=['GET', 'POST'], endpoint='permis.creer')
def render_permis_papier(type_name='securite_generale'):
    valid_templates = {
        'chaud': 'permis/papier/chaud.html',
        'fouille': 'permis/papier/fouille.html',
        'espace_confine': 'permis/papier/espace_confine.html',
        'hauteur': 'permis/papier/hauteur.html',
        'levage': 'permis/papier/levage.html',
        'electrique': 'permis/papier/electrique.html',
        'securite_generale': 'permis/papier/securite_generale.html',
        'revalidation': 'permis/papier/revalidation.html',
        'vehicule': 'permis/papier/vehicule.html',
        'materiel': 'permis/papier/materiel.html',
        'permis_general': 'permis/papier/securite_generale.html',
        'permis_general_recto': 'permis/papier/securite_generale.html',
        'permis_general_verso': 'permis/papier/revalidation.html'
    }

    if request.method == 'POST':
        demandeur = (request.form.get('demandeur') or request.form.get('responsable') or request.form.get('nom_demandeur') or 'Responsable Chantier').strip()
        entreprise = (request.form.get('entreprise') or 'Sinylon').strip()
        zone = (request.form.get('zone') or request.form.get('emplacement') or 'Zone Chantier').strip()
        description = (request.form.get('description') or request.form.get('nature_travaux') or f"Permis Papier {type_name.replace('_', ' ').title()}").strip()
        
        try:
            vent_kmh = float(request.form.get('vent_kmh', 0) or 0)
        except (ValueError, TypeError):
            vent_kmh = 0.0
            
        try:
            temp_celsius = float(request.form.get('temp_celsius', 0) or 0)
        except (ValueError, TypeError):
            temp_celsius = 0.0

        type_title = type_name.replace('_', ' ').title()
        ref_num = f"PERM-{type_name.upper()[:4]}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        status = "VALIDE"
        if vent_kmh > 60 or temp_celsius > 40:
            status = "ARRÊT MÉTÉO"

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO permits (ref_num, type_permis, entreprise, demandeur, zone, description, vent_kmh, temp_celsius, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ref_num, f"Permis Papier {type_title}", entreprise, demandeur, zone, description, vent_kmh, temp_celsius, status))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Erreur enregistrement permis ({type_name}): {e}")

        return redirect(url_for('index'))

    type_key = request.args.get('type_form') or type_name
    if type_key in valid_templates:
        return render_template(valid_templates[type_key])
    return render_template('permis/papier/securite_generale.html')

# ================= FICHES DU BUREAU (SORTIE MATÉRIEL & PEMP) =================
@app.route('/fiches/sortie_materiel')
def render_fiche_sortie_materiel():
    return render_template('fiches/sortie_materiel.html')

@app.route('/fiches/entree_depannage')
def render_fiche_entree_depannage():
    return render_template('fiches/entree_depannage.html')

@app.route('/inspection_nacelle/<sn>')
@app.route('/verifier/nacelle/<sn>')
def verifier_nacelle_sinylon(sn):
    clean_sn = str(sn).strip()
    nacelle_models = {
        's4726e-01-180400318': {'modele': 'Nacelle Ciseaux Électrique S4726E', 'marque': 'Sinoboom / Haulotte', 'code': 'NAC-S4726E-01'},
        'mp12h467122026': {'modele': 'Nacelle Ciseaux MP12H', 'marque': 'Magni / Dingli', 'code': 'NAC-MP12H-01'},
        'jcpt1212': {'modele': 'Nacelle Ciseaux JCPT1212', 'marque': 'Dingli JCPT', 'code': 'NAC-JCPT1212-01'},
        'mp12h': {'modele': 'Nacelle Ciseaux MP12H (Unité 2)', 'marque': 'Magni / Dingli', 'code': 'NAC-MP12H-02'},
        'si180412-4': {'modele': 'Nacelle Ciseaux SI180412-4 Heavy Duty', 'marque': 'Sinoboom Heavy', 'code': 'NAC-SI180412-04'},
        'man00000a01033498': {'modele': 'Nacelle Ciseaux Manitou 120 SE', 'marque': 'MANITOU / INNOVALIFT', 'code': 'NAC-MAN120SE-01'},
        'man00000a01033499': {'modele': 'Nacelle Ciseaux Manitou 120 SE (Unité 2)', 'marque': 'MANITOU / INNOVALIFT', 'code': 'NAC-MAN120SE-02'},
        'man00000l01033499': {'modele': 'Nacelle Ciseaux Manitou 120 SE (Unité 2)', 'marque': 'MANITOU / INNOVALIFT', 'code': 'NAC-MAN120SE-02'}
    }
    info = nacelle_models.get(clean_sn.lower(), {
        'modele': f'Nacelle à Ciseaux ({clean_sn})',
        'marque': 'PEMP Sinylon Fiat',
        'code': f'NAC-{clean_sn[:8].upper()}'
    })
    return render_template('verifier_nacelle.html', sn=clean_sn, nacelle_info=info)

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


# ══════════════════════════════════════════════════════════════
# PERMIS DE TRAVAIL QUOTIDIEN — Routes
# ══════════════════════════════════════════════════════════════

import json as _json
import hashlib as _hashlib

@app.route('/permis/scan/<path:permis_key>')
@app.route('/permis/scan/DAILY-<permis_id>')
@app.route('/permis/scan')
@app.route('/permis/travail')
def permis_travail_scan(permis_key=None, permis_id=None):
    """
    Page mobile scannée via QR Code — affiche le permis du jour.
    Gère aussi bien les filtres d'activités (hauteur, chaud, tuyauterie...) que le portail général.
    """
    today_iso = datetime.date.today().isoformat()
    today_pid = _hashlib.sha256(today_iso.encode()).hexdigest()[:8].upper()

    key_clean = (permis_key or permis_id or "all").replace("DAILY-", "").lower().strip()
    selected_slug = key_clean
    
    # Mapping des slugs d'activités
    # Dictionnaire des métadonnées pour chaque discipline
    permis_details = {
        'hauteur': {
            'nom': 'Travaux en Hauteur & Nacelles',
            'nom_cn': '高空作业与升降机安全许可证',
            'code': 'PT-HAU',
            'icone': '🪢',
            'risque': 'ÉLEVÉ (CLASSE 1)',
            'couleur_risque': '#ef4444',
            'epi': ['Harnais antichute EN361', 'Longe double avec absorbeur', 'Casque avec jugulaire', 'Chaussures sécurité S3', 'Ligne de vie certifiée'],
            'precautions': [
                'Arrêt obligatoire des travaux si vent > 45 km/h.',
                'Balisage d\'un périmètre d\'exclusion de 10 m au sol.',
                'Contrôle journalier de conformité des nacelles PEMP.',
                'Points d\'ancrage inspectés et testés avant toute montée.',
                'Interdiction formelle de travailler seul en élévation.'
            ]
        },
        'chaud': {
            'nom': 'Travaux à Chaud & Soudage (Permis Feu)',
            'nom_cn': '动火作业与焊接气割安全许可证',
            'code': 'PT-CHD',
            'icone': '🔥',
            'risque': 'ÉLEVÉ (PERMIS FEU)',
            'couleur_risque': '#ef4444',
            'epi': ['Masque soudeur cristaux liquides', 'Gants soudeur cuir croûte', 'Tablier ignifugé', 'Chaussures sécurité S3', 'Lunettes meulage'],
            'precautions': [
                'Éloignement de toutes matières combustibles dans un rayon de 10 m.',
                'Bâches ignifugées M0 déployées sous la zone de projection.',
                'Extincteur 6kg CO₂ / Poudre placé à moins de 3 mètres.',
                'Contrôle d\'atmosphère par explosimètre si proximité réseaux fluides.',
                'Ronde de surveillance obligatoire pendant 2h après l\'arrêt des feux.'
            ]
        },
        'tuyauterie': {
            'nom': 'Installation Tuyauterie Industrielle & Piping',
            'nom_cn': '工业管道与配管安装作业许可证',
            'code': 'PT-PIP',
            'icone': '🚰',
            'risque': 'MOYEN (PRESSION & FLUIDES)',
            'couleur_risque': '#f59e0b',
            'epi': ['Gants anti-coupure Niveau 5', 'Lunettes étanches', 'Casque de chantier', 'Chaussures sécurité S3', 'Protection auditive'],
            'precautions': [
                'Purge, dégazage et vérification de l\'absence de pression résiduelle.',
                'Élingage et arrimage certifié des tronçons de tuyauterie.',
                'Serrage des brides au couple prescrit avec joint neuf.',
                'Balisage strict lors des épreuves hydrostatiques sous pression.',
                'Contrôle des fixations antivibratiles et des pentes.'
            ]
        },
        'charpente': {
            'nom': 'Charpente Métallique & Levage Poutres',
            'nom_cn': '钢结构安装、吊装与高空装配许可证',
            'code': 'PT-CHA',
            'icone': '🏗️',
            'risque': 'ÉLEVÉ (LEVAGE LOURD)',
            'couleur_risque': '#ef4444',
            'epi': ['Harnais antichute EN361', 'Casque avec jugulaire', 'Gants anti-écrasement', 'Chaussures S3 montantes', 'Gilet haute visibilité'],
            'precautions': [
                'Plan de levage formellement validé avant manœuvre.',
                'Utilisation obligatoire de cordes de guidage (taglines).',
                'Interdiction formelle de stationner sous charge suspendue.',
                'Contrôle du couple de serrage de la boulonnerie HR.',
                'Arrêt immédiat du grutage si les rafales dépassent 35 km/h.'
            ]
        },
        'rails': {
            'nom': 'Rails Suspendus & Convoyeurs Aériens',
            'nom_cn': '悬挂轨道、输送线与起重机械作业许可证',
            'code': 'PT-RAI',
            'icone': '🚡',
            'risque': 'ÉLEVÉ (HAUTEUR & FIXATIONS)',
            'couleur_risque': '#ef4444',
            'epi': ['Harnais de sécurité', 'Casque de protection EN397', 'Gants renforcés', 'Chaussures de sécurité S3'],
            'precautions': [
                'Contrôle du serrage des platines d\'ancrage et suspentes au couple requis.',
                'Contrôle de l\'alignement et nivellement par laser des rails.',
                'Élingage équilibré et sécurisé pendant le hissage en hauteur.',
                'Inspection des butées mécaniques de fin de course et arrêts d\'urgence.',
                'Essais statiques et dynamiques à vide avant mise sous charge.'
            ]
        },
        'equipements': {
            'nom': 'Installation Équipements & Machinerie',
            'nom_cn': '机械设备、工业生产线与机器安装许可证',
            'code': 'PT-EQP',
            'icone': '⚙️',
            'risque': 'MOYEN (RIPAGE & MANUTENTION)',
            'couleur_risque': '#f59e0b',
            'epi': ['Chaussures renfort métatarse', 'Gants mécaniques', 'Lunettes de sécurité', 'Casque de chantier'],
            'precautions': [
                'Utilisation de rouleurs de charge et vérins hydrauliques homologués.',
                'Vérification de la portance de la dalle béton avant ripage.',
                'Calage mécanique et scellements chimiques rigoureusement contrôlés.',
                'Consignation mécanique et arrêt sécurisé des équipements adjacents.',
                'Signalement et protection des angles saillants et pièces mobiles.'
            ]
        },
        'cables': {
            'nom': 'Tirage de Câbles & Travaux Électriques',
            'nom_cn': '电缆敷设、桥架安装与电气作业安全许可证',
            'code': 'PT-CAB',
            'icone': '⚡',
            'risque': 'ÉLECTRIQUE (HABILITATION REQUISE)',
            'couleur_risque': '#f59e0b',
            'epi': ['Gants isolants 1000V', 'Écran facial anti-arc', 'Outillage isolé IEC 60900', 'Chaussures sans métal'],
            'precautions': [
                'Consignation électrique stricte LOTO (Cadenassage & Balisage armoires).',
                'Vérification d\'Absence de Tension (VAT) systématique avant travail.',
                'Dérouleurs de tourets solidement freinés et arrimés au sol.',
                'Protection des mains lors du tirage mécanique dans les caniveaux.',
                'Personnel obligatoirement détenteur de l\'habilitation B1V / B2V valide.'
            ]
        },
        'installations': {
            'nom': 'Autres Installations & Génie Civil',
            'nom_cn': '土建综合配套安装与现场通用施工作业许可证',
            'code': 'PT-DIV',
            'icone': '🛠️',
            'risque': 'MODÉRÉ (TRAVAUX GÉNÉRAUX)',
            'couleur_risque': '#10b981',
            'epi': ['Gants de protection', 'Masque anti-poussière FFP3', 'Protection auditive', 'Chaussures sécurité S3'],
            'precautions': [
                'Détection des réseaux enterrés ou encastrés avant tout carottage.',
                'Ventilation forcée lors de travaux en espace semi-confiné.',
                'Nettoyage et évacuation régulière des gravats et déblais.',
                'Signalisation et barriérage des réservations ou tranchées ouvertes.',
                'Port des lunettes étanches lors des phases de piquage / découpe béton.'
            ]
        }
    }

    context = {
        "today_iso": today_iso,
        "today_pid": today_pid,
        "selected_slug": selected_slug,
        "permis_details": permis_details
    }

    if selected_slug in permis_details:
        context["permis_info"] = permis_details[selected_slug]
        return render_template('permis/verifier_permis_travail.html', **context)

    return render_template('permis/permis_travail_scan.html', **context)




@app.route('/permis/travail/pdf')
def permis_travail_pdf():
    """Télécharge ou re-génère le PDF du permis du jour."""
    import os as _os
    today_iso = datetime.date.today().isoformat()
    pdf_name = f"PERMIS_TRAVAIL_{today_iso}.pdf"
    pdf_path = _os.path.join(_os.path.dirname(__file__), 'static', 'fiches', pdf_name)

    if not _os.path.exists(pdf_path):
        # Re-génère si absent
        from generate_permis_travail_daily import main as _gen
        _gen()

    if _os.path.exists(pdf_path):
        return send_file(pdf_path, mimetype='application/pdf',
                         download_name=pdf_name, as_attachment=False)
    return "PDF non disponible", 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"🚀 SINYLON Badge Studio Pro démarré sur http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

