import os
import datetime
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image as PILImage, ImageDraw, ImageFont
import math
from services.qr_service import generate_qr_code

# Dimensions standards badge CR80 Portrait (60mm x 86mm calibré)
BADGE_WIDTH = 60.0 * mm
BADGE_HEIGHT = 86.0 * mm

# Palette Couleurs Officielles Badges
COLOR_HEADER = HexColor("#1F1F21")       # Noir En-tête FIAT
COLOR_PROV_HEADER = HexColor("#991B1B")  # Rouge En-tête Provisoire
COLOR_ALERT_BG = HexColor("#E0F2FE")     # Bleu très clair sous-titre
COLOR_ALERT_PROV_BG = HexColor("#FEF2F2")# Rouge très clair
COLOR_ALERT_TEXT = HexColor("#EF4444")   # Rouge SAFETY FIRST
COLOR_DARK = HexColor("#0F172A")         # Anthracite texte
COLOR_MUTED = HexColor("#64748B")        # Gris labels
COLOR_BLUE_PROJ = HexColor("#1E4ED8")    # Bleu Projet
COLOR_WHITE = HexColor("#FFFFFF")
COLOR_GREEN_WAVE = HexColor("#1D664F")   # Vert Footer Vague
COLOR_CSPS_RED = HexColor("#DC2626")     # Rouge Pastille CSPS
COLOR_BORDER = HexColor("#CBD5E1")       # Bordure gris clair
COLOR_VALID_BG = HexColor("#1E293B")     # Fond Date Validité

def draw_single_badge(c, x, y, worker, qr_path):
    """
    Dessine le badge officiel vertical (CR80 Portrait 60mm x 86mm)
    conforme à la charte FIAT / CSPS / SINYLON / AMCE.
    """
    prenom = (worker.get('prenom') or '').strip()
    nom = (worker.get('nom') or '').strip()
    fonction = (worker.get('fonction') or 'Intervenant Chantier').strip()
    matricule = (worker.get('matricule') or worker.get('carte_id') or 'SIN-0000').strip()
    societe = (worker.get('societe_affichee') or worker.get('entreprise') or 'AMCE CONSTRUCTION').strip()
    projet = (worker.get('projet') or 'CSPS Projet FIAT').strip()
    status = (worker.get('status') or 'Actif').strip()
    
    # Indicateurs
    is_provisoire = (status.lower() == 'provisoire' or matricule.upper().startswith('PROV'))
    is_blocked = (status.lower() == 'bloqué' or status.lower() == 'bloque' or bool(worker.get('is_blocked')))
    
    # 1. Fond du badge et bordure arrondie
    c.saveState()
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(COLOR_CSPS_RED if (is_provisoire or is_blocked) else COLOR_BORDER)
    c.setLineWidth(1.0 if (is_provisoire or is_blocked) else 0.6)
    c.roundRect(x, y, BADGE_WIDTH, BADGE_HEIGHT, 3.5 * mm, fill=1, stroke=1)
    
    # 2. En-tête Supérieur (Bandeau Sombre avec vague)
    header_h = 16.0 * mm
    header_y = y + BADGE_HEIGHT - header_h
    c.setFillColor(COLOR_PROV_HEADER if is_provisoire else COLOR_HEADER)
    
    # Clip path pour respecter l'arrondi supérieur du badge
    c.saveState()
    clip_p = c.beginPath()
    clip_p.roundRect(x, y, BADGE_WIDTH, BADGE_HEIGHT, 3.5 * mm)
    c.clipPath(clip_p, stroke=0)

    # Fond noir d'en-tête avec vague inférieure
    p = c.beginPath()
    p.moveTo(x, y + BADGE_HEIGHT)
    p.lineTo(x + BADGE_WIDTH, y + BADGE_HEIGHT)
    p.lineTo(x + BADGE_WIDTH, header_y + 1.5 * mm)
    p.curveTo(x + BADGE_WIDTH * 0.7, header_y - 0.5 * mm, x + BADGE_WIDTH * 0.35, header_y + 3.0 * mm, x, header_y + 1.5 * mm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Double liseré décoratif argenté
    c.setStrokeColor(HexColor("#E5E7EB"))
    c.setLineWidth(0.6)
    c.bezier(x, header_y + 1.5 * mm, x + BADGE_WIDTH * 0.35, header_y + 3.0 * mm, x + BADGE_WIDTH * 0.7, header_y - 0.5 * mm, x + BADGE_WIDTH, header_y + 1.5 * mm)
    
    # Logo FIAT (gauche)
    base_dir = os.path.dirname(os.path.dirname(__file__))
    fiat_logo = os.path.join(base_dir, 'static', 'img', 'fiat_logo.png')
    fiat_drawn = False
    if os.path.exists(fiat_logo):
        try:
            c.drawImage(fiat_logo, x + 3.5 * mm, header_y + 3.5 * mm, width=15 * mm, height=8.5 * mm, preserveAspectRatio=True, mask='auto')
            fiat_drawn = True
        except Exception:
            pass
    if not fiat_drawn:
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + 4 * mm, header_y + 6 * mm, "FIAT")

    # Logo Société / Entreprise (droite)
    amce_logo = os.path.join(base_dir, 'static', 'img', 'amce_logo.png')
    amce_drawn = False
    if os.path.exists(amce_logo):
        try:
            c.drawImage(amce_logo, x + BADGE_WIDTH - 20 * mm, header_y + 3.5 * mm, width=16.5 * mm, height=8.5 * mm, preserveAspectRatio=True, mask='auto')
            amce_drawn = True
        except Exception:
            pass
    if not amce_drawn:
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(x + BADGE_WIDTH - 4 * mm, header_y + 6.5 * mm, (societe[:14] if societe else "SINYLON"))

    c.restoreState() # fin du clip en-tête

    # 3. Bandeau Alerte / SAFETY FIRST
    alert_h = 4.2 * mm
    alert_y = header_y - 4.5 * mm
    c.setFillColor(COLOR_ALERT_PROV_BG if is_provisoire else COLOR_ALERT_BG)
    c.rect(x + 0.3 * mm, alert_y, BADGE_WIDTH - 0.6 * mm, alert_h, fill=1, stroke=0)
    c.setStrokeColor(HexColor("#BAE6FD") if not is_provisoire else HexColor("#FCA5A5"))
    c.setLineWidth(0.5)
    c.line(x + 0.3 * mm, alert_y, x + BADGE_WIDTH - 0.3 * mm, alert_y)

    c.setFillColor(COLOR_ALERT_TEXT)
    c.setFont("Helvetica-Bold", 6.5)
    alert_msg = "⚠️ BADGE PROVISOIRE · 10 JOURS" if is_provisoire else "SAFETY FIRST"
    c.drawCentredString(x + BADGE_WIDTH / 2.0, alert_y + 1.2 * mm, alert_msg)

    # 4. Section Centrale : Photo + QR Code
    mid_y = alert_y - 25.5 * mm
    photo_w = 22.0 * mm
    photo_h = 24.5 * mm
    photo_x = x + 4.0 * mm

    # Cadre Photo
    c.setFillColor(HexColor("#F1F5F9"))
    c.setStrokeColor(HexColor("#CBD5E1") if not is_provisoire else COLOR_CSPS_RED)
    c.setLineWidth(0.8)
    c.roundRect(photo_x, mid_y, photo_w, photo_h, 1.5 * mm, fill=1, stroke=1)

    photo_file = worker.get('photo_path') or ''
    if photo_file and photo_file.startswith('/static/'):
        photo_file = os.path.join(base_dir, photo_file.lstrip('/'))

    photo_drawn = False
    if photo_file and os.path.exists(photo_file):
        try:
            c.drawImage(photo_file, photo_x + 0.5 * mm, mid_y + 0.5 * mm, width=photo_w - 1.0 * mm, height=photo_h - 1.0 * mm, preserveAspectRatio=True)
            photo_drawn = True
        except Exception:
            pass
    if not photo_drawn:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(photo_x + photo_w / 2.0, mid_y + photo_h / 2.0 - 2, "PHOTO")

    # Cadre QR Code
    qr_w = 26.5 * mm
    qr_h = 24.5 * mm
    qr_x = x + BADGE_WIDTH - qr_w - 4.0 * mm
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(HexColor("#CBD5E1") if not is_provisoire else COLOR_CSPS_RED)
    c.roundRect(qr_x, mid_y, qr_w, qr_h, 1.5 * mm, fill=1, stroke=1)

    if qr_path and os.path.exists(qr_path):
        try:
            c.drawImage(qr_path, qr_x + 1.0 * mm, mid_y + 0.5 * mm, width=qr_w - 2.0 * mm, height=qr_h - 1.0 * mm, preserveAspectRatio=True)
        except Exception:
            pass

    # 5. Données d'identité & Emploi (Alignement exact selon la photo)
    info_y = mid_y - 3.5 * mm
    line_h = 3.5 * mm

    # Nom
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 4.0 * mm, info_y, "Nom :")
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 15.0 * mm, info_y, nom.upper()[:24])

    # Prénom
    info_y -= line_h
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 4.0 * mm, info_y, "Prénom :")
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 15.0 * mm, info_y, prenom.title()[:24])

    # Société
    info_y -= line_h
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 4.0 * mm, info_y, "Société :")
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 7.0)
    c.drawString(x + 15.0 * mm, info_y, societe[:24])

    # Projet
    info_y -= line_h
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 4.0 * mm, info_y, "Projet :")
    c.setFillColor(COLOR_BLUE_PROJ)
    c.setFont("Helvetica-Bold", 7.0)
    c.drawString(x + 15.0 * mm, info_y, projet[:24])

    # ID Badge
    info_y -= line_h
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 4.0 * mm, info_y, "ID Badge :")
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 7.0)
    c.drawString(x + 15.0 * mm, info_y, f"N. {matricule}"[:24])

    # 6. Zone Inférieure : STEP 1, 2, 3 + Validité + Vague
    step_y = y + 13.0 * mm
    step_size = 4.0 * mm

    # Step 1
    s1_x = x + 4.0 * mm
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(HexColor("#000000"))
    c.setLineWidth(0.6)
    c.rect(s1_x, step_y, step_size, step_size, fill=1, stroke=1)
    c.setFillColor(HexColor("#5A6080"))
    c.setFont("Helvetica-Bold", 5.0)
    c.drawCentredString(s1_x + step_size / 2.0, step_y - 2.0 * mm, "1")
    if worker.get('step_1_valide', 1):
        c.setFillColor(COLOR_GREEN_WAVE)
        c.setFont("Helvetica-Bold", 7.0)
        c.drawCentredString(s1_x + step_size / 2.0, step_y + 0.8 * mm, "✓")

    # Step 2
    s2_x = s1_x + step_size + 2.0 * mm
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(HexColor("#000000"))
    c.rect(s2_x, step_y, step_size, step_size, fill=1, stroke=1)
    c.setFillColor(HexColor("#5A6080"))
    c.setFont("Helvetica-Bold", 5.0)
    c.drawCentredString(s2_x + step_size / 2.0, step_y - 2.0 * mm, "2")
    if worker.get('step_2_valide', 1):
        c.setFillColor(COLOR_GREEN_WAVE)
        c.setFont("Helvetica-Bold", 7.0)
        c.drawCentredString(s2_x + step_size / 2.0, step_y + 0.8 * mm, "✓")

    # Step 3
    s3_x = s2_x + step_size + 2.0 * mm
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(HexColor("#000000"))
    c.rect(s3_x, step_y, step_size, step_size, fill=1, stroke=1)
    c.setFillColor(HexColor("#5A6080"))
    c.setFont("Helvetica-Bold", 5.0)
    c.drawCentredString(s3_x + step_size / 2.0, step_y - 2.0 * mm, "3")
    if worker.get('step_3_valide', 0):
        c.setFillColor(COLOR_GREEN_WAVE)
        c.setFont("Helvetica-Bold", 7.0)
        c.drawCentredString(s3_x + step_size / 2.0, step_y + 0.8 * mm, "✓")

    # Pastille Date Validité (droite)
    valid_w = 17.5 * mm
    valid_h = 4.8 * mm
    valid_x = x + BADGE_WIDTH - valid_w - 4.0 * mm
    c.setFillColor(COLOR_PROV_HEADER if is_provisoire else COLOR_VALID_BG)
    c.roundRect(valid_x, step_y - 0.5 * mm, valid_w, valid_h, 1.2 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 6.5)
    exp_date = worker.get('date_expiration') or '31/12/2026'
    if '-' in str(exp_date) and len(str(exp_date).split('-')) == 3:
        p_date = str(exp_date).split('-')
        exp_formatted = f"{p_date[2]}/{p_date[1]}/{p_date[0]}"
    else:
        exp_formatted = str(exp_date)
    c.drawCentredString(valid_x + valid_w / 2.0, step_y + 0.8 * mm, exp_formatted)

    # 7. Pied de Page / Vague Verte & Pastille CSPS
    c.saveState()
    clip_foot = c.beginPath()
    clip_foot.roundRect(x, y, BADGE_WIDTH, BADGE_HEIGHT, 3.5 * mm)
    c.clipPath(clip_foot, stroke=0)

    footer_h = 9.5 * mm
    c.setFillColor(HexColor("#991B1B") if is_provisoire else COLOR_GREEN_WAVE)
    
    # Dessin de la vague de pied
    pw = c.beginPath()
    pw.moveTo(x, y)
    pw.lineTo(x + BADGE_WIDTH, y)
    pw.lineTo(x + BADGE_WIDTH, y + footer_h - 1.0 * mm)
    pw.curveTo(x + BADGE_WIDTH * 0.7, y + footer_h - 2.5 * mm, x + BADGE_WIDTH * 0.35, y + footer_h + 1.5 * mm, x, y + footer_h - 0.5 * mm)
    pw.close()
    c.drawPath(pw, fill=1, stroke=0)

    # Textes du Footer
    c.setFillColor(HexColor("#FFFFFF") if is_provisoire else HexColor("#EF4444"))
    c.setFont("Helvetica-Bold", 5.2)
    c.drawCentredString(x + BADGE_WIDTH / 2.0, y + 5.2 * mm, "SAFETY FIRST")

    # Pastille centrale CSPS / SINYLON
    pill_w = 14.0 * mm
    pill_h = 3.6 * mm
    pill_x = x + (BADGE_WIDTH - pill_w) / 2.0
    c.setFillColor(COLOR_CSPS_RED if not is_provisoire else HexColor("#7F1D1D"))
    c.roundRect(pill_x, y + 1.2 * mm, pill_w, pill_h, 0.8 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 6.0)
    c.drawCentredString(x + BADGE_WIDTH / 2.0, y + 2.0 * mm, "CSPS")

    c.restoreState() # fin du clip pied de page
    c.restoreState() # fin de l'état du badge


import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

DEFAULT_DOMAIN = "https://sinylon-badge-studio.onrender.com"

def get_qr_url(worker):
    domain = os.environ.get('DOMAIN_URL', DEFAULT_DOMAIN).strip()
    matricule = worker.get('matricule') or worker.get('uuid') or str(worker.get('id', ''))
    return f"{domain.rstrip('/')}/badge/verifier/{matricule}"

def get_permit_qr_url(ref_num):
    domain = os.environ.get('DOMAIN_URL', DEFAULT_DOMAIN).strip()
    return f"{domain.rstrip('/')}/permis/verifier/{ref_num}"


def generate_single_badge_pdf(worker, output_pdf_path):
    """Génère le PDF d'un seul badge vertical (CR80 Portrait 60mm x 86mm)."""
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    qr_path = output_pdf_path.replace('.pdf', '_qr.png')
    qr_url = get_qr_url(worker)
    generate_qr_code(qr_url, qr_path)

    c = canvas.Canvas(output_pdf_path, pagesize=(BADGE_WIDTH, BADGE_HEIGHT))
    draw_single_badge(c, 0, 0, worker, qr_path)
    c.save()

    if os.path.exists(qr_path):
        try:
            os.remove(qr_path)
        except Exception:
            pass

    return output_pdf_path


def generate_batch_badges_pdf(workers_list, output_pdf_path):
    """
    Génère une planche A4 d'impression officielle avec 4 badges verticaux par page (2x2),
    calibrés avec traits de coupe et repères d'alignement.
    """
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    
    page_w, page_h = A4
    
    # 4 badges verticaux par page (2 colonnes x 2 lignes)
    # Badge: 60mm x 86mm
    # A4: 210mm x 297mm
    # Espace restant horizontal: 210 - (2 * 60) = 90mm => Marges 30mm, espacement 30mm
    # Espace restant vertical: 297 - (2 * 86) = 125mm => Marges 35mm, espacement 55mm
    
    margin_x = 30 * mm
    spacing_x = 30 * mm
    margin_y = 35 * mm
    spacing_y = 55 * mm

    col = 0
    row = 0

    for idx, worker in enumerate(workers_list):
        x = margin_x + col * (BADGE_WIDTH + spacing_x)
        y = page_h - margin_y - (row + 1) * BADGE_HEIGHT - row * spacing_y

        qr_path = output_pdf_path.replace('.pdf', f'_qr_{idx}.png')
        qr_url = get_qr_url(worker)
        generate_qr_code(qr_url, qr_path)

        # Repères de coupe
        c.setStrokeColor(HexColor("#94A3B8"))
        c.setLineWidth(0.4)
        c.line(x - 3 * mm, y, x - 1 * mm, y)
        c.line(x, y - 3 * mm, x, y - 1 * mm)
        c.line(x + BADGE_WIDTH + 1 * mm, y, x + BADGE_WIDTH + 3 * mm, y)
        c.line(x + BADGE_WIDTH, y - 3 * mm, x + BADGE_WIDTH, y - 1 * mm)
        c.line(x - 3 * mm, y + BADGE_HEIGHT, x - 1 * mm, y + BADGE_HEIGHT)
        c.line(x, y + BADGE_HEIGHT + 1 * mm, x, y + BADGE_HEIGHT + 3 * mm)
        c.line(x + BADGE_WIDTH + 1 * mm, y + BADGE_HEIGHT, x + BADGE_WIDTH + 3 * mm, y + BADGE_HEIGHT)
        c.line(x + BADGE_WIDTH, y + BADGE_HEIGHT + 1 * mm, x + BADGE_WIDTH, y + BADGE_HEIGHT + 3 * mm)

        draw_single_badge(c, x, y, worker, qr_path)

        if os.path.exists(qr_path):
            try:
                os.remove(qr_path)
            except Exception:
                pass

        col += 1
        if col >= 2:
            col = 0
            row += 1
            if row >= 2:
                c.showPage()
                row = 0

    c.save()
    return output_pdf_path


def generate_permit_pdf(permit_data, output_pdf_path):
    """Génère le document PDF officiel du Permis de Travail HSE SINYLON FIAT avec QR Code Fixe Terrain."""
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    page_w, page_h = A4

    ref_num = permit_data.get('ref_num', 'PERM-001')
    qr_path = output_pdf_path.replace('.pdf', '_permit_qr.png')
    qr_url = get_permit_qr_url(ref_num)
    generate_qr_code(qr_url, qr_path)

    # En-tête SINYLON FIAT STELLANTIS
    c.setFillColor(HexColor("#1D4ED8"))
    c.rect(0, page_h - 25 * mm, page_w, 25 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(15 * mm, page_h - 15 * mm, "SINYLON FIAT STELLANTIS - PERMIS DE TRAVAIL HSE")
    c.setFont("Helvetica", 10)
    c.drawRightString(page_w - 15 * mm, page_h - 15 * mm, f"RÉF : {ref_num}")

    # Dessin du QR Code Fixe Terrain en haut à droite
    if os.path.exists(qr_path):
        c.drawImage(qr_path, page_w - 48 * mm, page_h - 68 * mm, width=32 * mm, height=32 * mm, preserveAspectRatio=True)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(COLOR_DARK)
        c.drawCentredString(page_w - 32 * mm, page_h - 71 * mm, "SCAN QR CHANTIER TERRAIN")
        try:
            os.remove(qr_path)
        except Exception:
            pass

    # Corps du Permis
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, page_h - 40 * mm, f"1. INFORMATIONS — {permit_data.get('type_permis', '').upper()}")

    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, page_h - 50 * mm, f"Entreprise Intervenante : {permit_data.get('entreprise', 'SINYLON FIAT STELLANTIS')}")
    c.drawString(15 * mm, page_h - 58 * mm, f"Responsable / Demandeur : {permit_data.get('demandeur', 'N/A')}")
    c.drawString(15 * mm, page_h - 66 * mm, f"Zone / Emplacement Chantier : {permit_data.get('zone', 'Zone A')}")
    c.drawString(15 * mm, page_h - 74 * mm, f"Description des Travaux : {permit_data.get('description', 'N/A')}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, page_h - 90 * mm, "2. MATRICE DE SÉCURITÉ & VALIDATION FIAT")
    
    vent = permit_data.get('vent_kmh', 0)
    temp = permit_data.get('temp_celsius', 0)
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, page_h - 100 * mm, f"Vent mesuré : {vent} km/h (Seuil alerte : 60 km/h)")
    c.drawString(15 * mm, page_h - 108 * mm, f"Température : {temp} °C (Seuil canicule : 40 °C)")
    c.drawString(15 * mm, page_h - 116 * mm, f"Validation Responsable : VALIDATION FIAT - CONFORME")

    # Statut
    status = permit_data.get('status', 'VALIDE')
    if status == 'VALIDE' or status == 'CONFORME':
        c.setFillColor(HexColor("#16A34A"))
        stat_txt = "✓ PERMIS AUTORISÉ & VALIDE PAR FIAT STELLANTIS"
    else:
        c.setFillColor(COLOR_CSPS_RED)
        stat_txt = "⚠️ PERMIS SUSPENDU / ARRÊT SÉCURITÉ FIAT STELLANTIS"

    c.rect(15 * mm, page_h - 135 * mm, page_w - 30 * mm, 12 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_w / 2, page_h - 127 * mm, stat_txt)

    # Pavé Urgence HSE Nouri
    c.setStrokeColor(COLOR_CSPS_RED)
    c.setFillColor(COLOR_WHITE)
    c.rect(15 * mm, page_h - 165 * mm, page_w - 30 * mm, 18 * mm, fill=0, stroke=1)
    c.setFillColor(COLOR_CSPS_RED)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, page_h - 154 * mm, "CONTACT URGENCE HSE CHANTIER FIAT STELLANTIS :")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, page_h - 160 * mm, "NOURI : 0563765157 (DISPONIBILITÉ 24/7)")

    c.save()
    return output_pdf_path


def generate_sortie_materiel_pdf(form_data, output_pdf_path):
    """Génère le PDF de la Fiche d'Autorisation de Sortie de Matériel Sinylon Fiat Stellantis avec QR Code."""
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    page_w, page_h = A4

    ref_num = form_data.get('ref_num', f"SORTIE-{datetime.date.today().strftime('%Y%m%d')}")
    qr_path = output_pdf_path.replace('.pdf', '_sortie_qr.png')
    qr_url = get_permit_qr_url(ref_num)
    generate_qr_code(qr_url, qr_path)

    # Bandeau En-tête Sinylon Fiat Stellantis
    c.setFillColor(HexColor("#1D4ED8"))
    c.rect(0, page_h - 30 * mm, page_w, 30 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(15 * mm, page_h - 15 * mm, "SINYLON FIAT STELLANTIS - AUTORISATION DE SORTIE DE MATÉRIEL")
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, page_h - 23 * mm, f"Date : {form_data.get('date_sortie', datetime.date.today().strftime('%d/%m/%Y'))}  |  Réf : {ref_num}")

    # QR Code officiel imprimé sur la fiche papier
    if os.path.exists(qr_path):
        c.drawImage(qr_path, page_w - 45 * mm, page_h - 75 * mm, width=32 * mm, height=32 * mm, preserveAspectRatio=True)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(COLOR_DARK)
        c.drawCentredString(page_w - 29 * mm, page_h - 78 * mm, "SCAN VERIFICATION ONLINE")
        try:
            os.remove(qr_path)
        except Exception:
            pass

    # Contenu de la fiche
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, page_h - 45 * mm, "INFORMATIONS DU TRANSFERT DE MATÉRIEL")

    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, page_h - 55 * mm, f"Demandeur / Transporteur : {form_data.get('demandeur', 'N/A')}")
    c.drawString(15 * mm, page_h - 63 * mm, f"Destination / Destinataire : {form_data.get('destination', 'N/A')}")
    c.drawString(15 * mm, page_h - 71 * mm, f"Véhicule / Immatriculation : {form_data.get('vehicule', 'N/A')}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, page_h - 85 * mm, "DÉSIGNATION ET LISTE DES ÉQUIPEMENTS")
    c.setFont("Helvetica", 10)
    materiels = form_data.get('materiels', 'N/A')
    y_pos = page_h - 95 * mm
    for line in materiels.split('\n'):
        c.drawString(15 * mm, y_pos, f"• {line}")
        y_pos -= 6 * mm

    # Pavé Urgence HSE Nouri
    c.setStrokeColor(COLOR_CSPS_RED)
    c.rect(15 * mm, 20 * mm, page_w - 30 * mm, 18 * mm, fill=0, stroke=1)
    c.setFillColor(COLOR_CSPS_RED)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, 31 * mm, "CONTACT URGENCE HSE CHANTIER FIAT STELLANTIS :")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, 25 * mm, "NOURI : 0563765157 (DISPONIBILITÉ 24/7)")

    c.save()
    return output_pdf_path


def generate_inspection_pemp_pdf(form_data, output_pdf_path):
    """Génère le PDF du Rapport d'Inspection Mensuelle PEMP / Nacelles Sinylon Fiat avec QR Code Fixe Nacelle."""
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    page_w, page_h = A4

    nacelle_num = form_data.get('nacelle_num', 'NAC-01')
    ref_num = form_data.get('ref_num', f"INSP-PEMP-{nacelle_num}")
    qr_path = output_pdf_path.replace('.pdf', '_pemp_qr.png')
    qr_url = get_permit_qr_url(ref_num)
    generate_qr_code(qr_url, qr_path)

    # En-tête Sinylon Fiat
    c.setFillColor(HexColor("#1D4ED8"))
    c.rect(0, page_h - 30 * mm, page_w, 30 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(15 * mm, page_h - 15 * mm, "SINYLON FIAT - INSPECTION MENSUELLE PEMP / NACELLES")
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, page_h - 23 * mm, f"Nacelle N° : {nacelle_num}  |  Réf : {ref_num}")

    # QR Code officiel imprimé sur le rapport d'inspection
    if os.path.exists(qr_path):
        c.drawImage(qr_path, page_w - 45 * mm, page_h - 75 * mm, width=32 * mm, height=32 * mm, preserveAspectRatio=True)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(COLOR_DARK)
        c.drawCentredString(page_w - 29 * mm, page_h - 78 * mm, "SCAN ÉTIQUETTE NACELLE")
        try:
            os.remove(qr_path)
        except Exception:
            pass

    # Corps
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, page_h - 45 * mm, "1. DÉTAILS DE L'ÉQUIPEMENT & INSPECTEUR")
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, page_h - 55 * mm, f"Inspecteur HSE : {form_data.get('inspecteur', 'N/A')}")
    c.drawString(15 * mm, page_h - 63 * mm, f"Marque / Modèle : {form_data.get('modele', 'N/A')}")
    
    res = form_data.get('resultat', 'CONFORME')
    c.setFont("Helvetica-Bold", 11)
    if res == 'CONFORME':
        c.setFillColor(HexColor("#16A34A"))
        c.drawString(15 * mm, page_h - 71 * mm, f"Résultat Contrôle Technique : ✓ CONFORME (ACCRÉDITÉ CHANTIER)")
    else:
        c.setFillColor(COLOR_CSPS_RED)
        c.drawString(15 * mm, page_h - 71 * mm, f"Résultat Contrôle Technique : ⚠️ NON CONFORME (IMMOBILISÉ)")

    # Pavé Urgence HSE Nouri
    c.setStrokeColor(COLOR_CSPS_RED)
    c.rect(15 * mm, 20 * mm, page_w - 30 * mm, 18 * mm, fill=0, stroke=1)
    c.setFillColor(COLOR_CSPS_RED)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, 31 * mm, "CONTACT URGENCE HSE CHANTIER FIAT STELLANTIS :")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, 25 * mm, "NOURI : 0563765157 (DISPONIBILITÉ 24/7)")

    c.save()
    return output_pdf_path
