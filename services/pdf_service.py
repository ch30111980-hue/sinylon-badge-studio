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

# Dimensions standards badge ID (85.6mm x 53.9mm)
BADGE_WIDTH = 85.6 * mm
BADGE_HEIGHT = 53.9 * mm

# Couleurs Officielles Sinylon Fiat
COLOR_PRIMARY = HexColor("#1D4ED8")     # Bleu Sinylon Royal
COLOR_DARK = HexColor("#0F172A")        # Anthracite / Slate
COLOR_LIGHT_BG = HexColor("#F8FAFC")    # Gris clair fond
COLOR_WHITE = HexColor("#FFFFFF")
COLOR_SUBTITLE = HexColor("#475569")
COLOR_GREEN = HexColor("#16A34A")       # Vert validation
COLOR_RED = HexColor("#DC2626")         # Rouge alerte / bloqué

def draw_single_badge(c, x, y, worker, qr_path):
    """
    Dessine le badge professionnel officiel certifié SINYLON FIAT (85.6mm x 53.9mm).
    """
    prenom = (worker.get('prenom') or '').strip()
    nom = (worker.get('nom') or '').strip()
    fonction = (worker.get('fonction') or 'Intervenant Chantier').strip()
    matricule = (worker.get('matricule') or 'SIN-0000').strip()
    entreprise = (worker.get('entreprise') or 'Sinylon Fiat').strip()
    status = (worker.get('status') or 'Actif').strip()

    # 1. Fond du Badge & Bordure arrondie
    c.setStrokeColor(HexColor("#CBD5E1"))
    c.setFillColor(COLOR_WHITE)
    c.roundRect(x, y, BADGE_WIDTH, BADGE_HEIGHT, 4 * mm, fill=1, stroke=1)

    # 2. Bandeau Supérieur Officiel Sinylon Fiat (Bleu)
    c.setFillColor(COLOR_PRIMARY)
    c.roundRect(x, y + BADGE_HEIGHT - 12 * mm, BADGE_WIDTH, 12 * mm, 4 * mm, fill=1, stroke=0)
    c.rect(x, y + BADGE_HEIGHT - 12 * mm, BADGE_WIDTH, 6 * mm, fill=1, stroke=0)

    # Titre En-tête : SINYLON FIAT STELLANTIS
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 6 * mm, y + BADGE_HEIGHT - 8 * mm, "SINYLON FIAT STELLANTIS")
    
    c.setFont("Helvetica-Bold", 6.5)
    c.drawRightString(x + BADGE_WIDTH - 6 * mm, y + BADGE_HEIGHT - 8 * mm, "ACCRÉDITATION CHANTIER")

    # 3. Emplacement Photo
    photo_x = x + 6 * mm
    photo_y = y + 10 * mm
    photo_w = 24 * mm
    photo_h = 30 * mm

    c.setFillColor(COLOR_LIGHT_BG)
    c.setStrokeColor(HexColor("#94A3B8"))
    c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)

    photo_file = worker.get('photo_path') or ''
    if photo_file and photo_file.startswith('/static/'):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        photo_file = os.path.join(base_dir, photo_file.lstrip('/'))

    photo_drawn = False
    if photo_file and os.path.exists(photo_file):
        try:
            c.drawImage(photo_file, photo_x, photo_y, width=photo_w, height=photo_h, preserveAspectRatio=True)
            photo_drawn = True
        except Exception as e:
            print(f"⚠️ Erreur photo {photo_file}: {e}")

    if not photo_drawn:
        initials = ((prenom[0] if prenom else '') + (nom[0] if nom else '')).upper() or 'S'
        c.setFillColor(COLOR_SUBTITLE)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(photo_x + photo_w/2, photo_y + photo_h/2 - 5, initials)

    # 4. Informations Travailleur
    info_x = x + 34 * mm
    
    # Nom & Prénom
    c.setFillColor(COLOR_DARK)
    full_name = f"{prenom} {nom.upper()}".strip()
    name_font = 9.5 if len(full_name) <= 18 else (8.0 if len(full_name) <= 25 else 7.0)
    c.setFont("Helvetica-Bold", name_font)
    c.drawString(info_x, y + 33 * mm, full_name[:35])

    # Fonction (affichage dynamique pour éviter toute coupure)
    c.setFillColor(COLOR_PRIMARY)
    fonction_font = 8.0 if len(fonction) <= 20 else (7.0 if len(fonction) <= 28 else 6.0)
    c.setFont("Helvetica-Bold", fonction_font)
    c.drawString(info_x, y + 27 * mm, fonction[:45])

    # Matricule
    c.setFillColor(COLOR_SUBTITLE)
    c.setFont("Helvetica", 7)
    c.drawString(info_x, y + 21 * mm, "MATRICULE :")
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(info_x + 18 * mm, y + 21 * mm, matricule)

    # Entreprise
    c.setFillColor(COLOR_SUBTITLE)
    c.setFont("Helvetica", 7)
    c.drawString(info_x, y + 16 * mm, "ENTREPRISE :")
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 7.5)
    ent_name = worker.get('entreprise') or 'SINYLON FIAT STELLANTIS'
    c.drawString(info_x + 18 * mm, y + 16 * mm, ent_name[:22])

    # Urgence HSE
    c.setFillColor(COLOR_RED)
    c.setFont("Helvetica-Bold", 6.2)
    c.drawString(info_x, y + 11 * mm, "URGENCE HSE : NOURI 0563765157")

    # 5. Dessin du QR Code Officiel de Contrôle
    if qr_path and os.path.exists(qr_path):
        qr_size = 15 * mm
        c.drawImage(qr_path, x + BADGE_WIDTH - qr_size - 3.5 * mm, y + 3.5 * mm, width=qr_size, height=qr_size)

    # 6. Bandeau Bas / Statut Accréditation
    if status.upper() == 'BLOQUÉ' or status.upper() == 'INACTIF':
        c.setFillColor(COLOR_RED)
        stat_text = "⚠️ ACCÈS CHANTIER BLOQUÉ / INACTIF"
    else:
        c.setFillColor(COLOR_GREEN)
        stat_text = "✓ ACCRÉDITÉ - SINYLON FIAT STELLANTIS"

    c.rect(x + 6 * mm, y + 4 * mm, 40 * mm, 4.5 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 5.8)
    c.drawCentredString(x + 26 * mm, y + 5.2 * mm, stat_text)


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

def get_qr_url(worker):
    domain = os.environ.get('DOMAIN_URL', '').strip()
    matricule = worker.get('matricule') or worker.get('uuid') or str(worker.get('id', ''))
    if domain:
        return f"{domain.rstrip('/')}/badge/verifier/{matricule}"
    ip = get_local_ip()
    return f"http://{ip}:5050/badge/verifier/{matricule}"

def get_permit_qr_url(ref_num):
    domain = os.environ.get('DOMAIN_URL', '').strip()
    if domain:
        return f"{domain.rstrip('/')}/permis/verifier/{ref_num}"
    ip = get_local_ip()
    return f"http://{ip}:5050/permis/verifier/{ref_num}"


def generate_single_badge_pdf(worker, output_pdf_path):
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
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    
    page_w, page_h = A4
    margin_x = 15 * mm
    margin_y = 15 * mm
    spacing_x = 10 * mm
    spacing_y = 8 * mm

    col = 0
    row = 0

    for idx, worker in enumerate(workers_list):
        x = margin_x + col * (BADGE_WIDTH + spacing_x)
        y = page_h - margin_y - (row + 1) * BADGE_HEIGHT - row * spacing_y

        qr_path = output_pdf_path.replace('.pdf', f'_qr_{idx}.png')
        qr_url = get_qr_url(worker)
        generate_qr_code(qr_url, qr_path)

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
            if row >= 4:
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
    c.setFillColor(COLOR_PRIMARY)
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
    c.drawString(15 * mm, page_h - 50 * mm, f"Entreprise Intervenante : SINYLON FIAT STELLANTIS")
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
        c.setFillColor(COLOR_GREEN)
        stat_txt = "✓ PERMIS AUTORISÉ & VALIDE PAR FIAT STELLANTIS"
    else:
        c.setFillColor(COLOR_RED)
        stat_txt = "⚠️ PERMIS SUSPENDU / ARRÊT SÉCURITÉ FIAT STELLANTIS"

    c.rect(15 * mm, page_h - 135 * mm, page_w - 30 * mm, 12 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_w / 2, page_h - 127 * mm, stat_txt)

    # Pavé Urgence HSE Nouri
    c.setStrokeColor(COLOR_RED)
    c.setFillColor(COLOR_WHITE)
    c.rect(15 * mm, page_h - 165 * mm, page_w - 30 * mm, 18 * mm, fill=0, stroke=1)
    c.setFillColor(COLOR_RED)
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
    c.setFillColor(COLOR_PRIMARY)
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
    c.setStrokeColor(COLOR_RED)
    c.rect(15 * mm, 20 * mm, page_w - 30 * mm, 18 * mm, fill=0, stroke=1)
    c.setFillColor(COLOR_RED)
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
    c.setFillColor(COLOR_PRIMARY)
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
        c.setFillColor(COLOR_GREEN)
        c.drawString(15 * mm, page_h - 71 * mm, f"Résultat Contrôle Technique : ✓ CONFORME (ACCRÉDITÉ CHANTIER)")
    else:
        c.setFillColor(COLOR_RED)
        c.drawString(15 * mm, page_h - 71 * mm, f"Résultat Contrôle Technique : ⚠️ NON CONFORME (IMMOBILISÉ)")

    # Pavé Urgence HSE Nouri
    c.setStrokeColor(COLOR_RED)
    c.rect(15 * mm, 20 * mm, page_w - 30 * mm, 18 * mm, fill=0, stroke=1)
    c.setFillColor(COLOR_RED)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, 31 * mm, "CONTACT URGENCE HSE CHANTIER FIAT STELLANTIS :")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, 25 * mm, "NOURI : 0563765157 (DISPONIBILITÉ 24/7)")

    c.save()
    return output_pdf_path
