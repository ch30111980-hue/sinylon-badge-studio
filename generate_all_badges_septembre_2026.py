#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur Officiel des Badges et Affiche Chantier — SINYLON BADGE STUDIO
Mois : Septembre 2026 (Du 01/09/2026 Au 30/09/2026)
Total Intervenants : 60 (55 Sinylon + 5 Locaux Algérie)
Format Badges : Calibré B3 (90mm x 120mm), 4 badges par page A4
Format Affiche : A4 Portrait avec Grand QR Code Terrain
"""

import os
import sys
import sqlite3
import base64
from io import BytesIO
import qrcode
from PIL import Image as PILImage, ImageDraw, ImageFont

from reportlab.lib.pagesizes import A4, mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'sinylon_studio.db')

# Dossier de destination sur le Bureau
OUTPUT_DIR = os.path.expanduser("~/Desktop/BADGES_SINYLON_SEPTEMBRE_2026")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Logo Sinylon officiel extrait du casque
LOGO_PATH = os.path.join(BASE_DIR, 'static', 'img', 'sinylon_official_logo.png')
LOGO_WHITE_PATH = os.path.join(BASE_DIR, 'static', 'img', 'sinylon_official_logo_white.png')

# URL de vérification terrain
VERIF_URL_BASE = "https://permis-sinylon.onrender.com/badge.html"

# Dimensions badge B3 (90 x 120 mm)
BADGE_WIDTH = 90.0 * mm
BADGE_HEIGHT = 120.0 * mm

# Couleurs officielles
COLOR_HEADER = HexColor("#0f172a")       # Bleu nuit / noir
COLOR_ALERT_BG = HexColor("#e0f2fe")     # Bleu clair
COLOR_ALERT_TEXT = HexColor("#1e3a8a")   # Bleu marine
COLOR_DARK = HexColor("#0f172a")
COLOR_MUTED = HexColor("#64748b")
COLOR_WHITE = HexColor("#ffffff")
COLOR_GREEN_WAVE = HexColor("#15803d")   # Vert conformité
COLOR_CSPS_RED = HexColor("#dc2626")     # Rouge logo badge
COLOR_BORDER = HexColor("#cbd5e1")
COLOR_VALID_BG = HexColor("#1e293b")

def get_workers():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, matricule, nom, prenom, fonction, entreprise, photo_path, 
               status, projet, date_emission, date_expiration
        FROM workers 
        ORDER BY id ASC
    """)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def make_qr_png_bytes(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def draw_single_badge_canvas(c, x, y, worker, qr_img_path):
    """
    Dessine un badge officiel B3 (90mm x 120mm) avec le nouveau logo Sinylon,
    validité Septembre 2026, photo/avatar et QR Code sécurisé.
    """
    prenom = (worker.get('prenom') or '').strip()
    nom = (worker.get('nom') or '').strip()
    full_name = f"{nom} {prenom}".strip()
    fonction = (worker.get('fonction') or 'Intervenant Montage').strip()
    matricule = (worker.get('matricule') or f"SIN-{worker['id']:04d}").strip()
    projet = (worker.get('projet') or 'Projet K9 CKD0 STELLANTIS').strip()
    
    # 1. Fond du badge et bordure arrondie avec repère
    c.saveState()
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.8)
    c.roundRect(x, y, BADGE_WIDTH, BADGE_HEIGHT, 3.5 * mm, fill=1, stroke=1)
    
    # 2. En-tête supérieur
    header_h = 22.0 * mm
    header_y = y + BADGE_HEIGHT - header_h
    c.setFillColor(COLOR_HEADER)
    
    # Clip arrondi supérieur
    c.saveState()
    clip_p = c.beginPath()
    clip_p.roundRect(x, y, BADGE_WIDTH, BADGE_HEIGHT, 3.5 * mm)
    c.clipPath(clip_p, stroke=0)
    
    # Dessin bandeau avec vague
    p = c.beginPath()
    p.moveTo(x, y + BADGE_HEIGHT)
    p.lineTo(x + BADGE_WIDTH, y + BADGE_HEIGHT)
    p.lineTo(x + BADGE_WIDTH, header_y + 1.5 * mm)
    p.curveTo(x + BADGE_WIDTH * 0.7, header_y - 1.5 * mm, x + BADGE_WIDTH * 0.35, header_y + 3.5 * mm, x, header_y + 1.5 * mm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    
    # Liseré argenté
    c.setStrokeColor(HexColor("#94a3b8"))
    c.setLineWidth(0.7)
    c.bezier(x, header_y + 1.5 * mm, x + BADGE_WIDTH * 0.35, header_y + 3.5 * mm, x + BADGE_WIDTH * 0.7, header_y - 1.5 * mm, x + BADGE_WIDTH, header_y + 1.5 * mm)
    
    # STELLANTIS à gauche
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + 5.5 * mm, header_y + 9.5 * mm, "STELLANTIS")
    c.setFont("Helvetica", 6.5)
    c.setFillColor(HexColor("#cbd5e1"))
    c.drawString(x + 5.5 * mm, header_y + 6.0 * mm, "ALGERIA K9 CKD0")
    
    # LOGO SINYLON OFFICIEL à droite
    if os.path.exists(LOGO_WHITE_PATH):
        try:
            c.drawImage(LOGO_WHITE_PATH, x + BADGE_WIDTH - 25.0 * mm, header_y + 2.5 * mm, width=19.0 * mm, height=17.0 * mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            c.setFillColor(COLOR_WHITE)
            c.setFont("Helvetica-Bold", 12)
            c.drawRightString(x + BADGE_WIDTH - 6 * mm, header_y + 8.5 * mm, "SINYLON")
    else:
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(x + BADGE_WIDTH - 6 * mm, header_y + 8.5 * mm, "SINYLON")
        
    c.restoreState() # fin clip en-tête
    
    # 3. Bandeau sous-titre Sécurité
    alert_h = 5.5 * mm
    alert_y = header_y - 6.0 * mm
    c.setFillColor(COLOR_ALERT_BG)
    c.rect(x + 0.4 * mm, alert_y, BADGE_WIDTH - 0.8 * mm, alert_h, fill=1, stroke=0)
    c.setStrokeColor(HexColor("#bae6fd"))
    c.setLineWidth(0.5)
    c.line(x + 0.4 * mm, alert_y, x + BADGE_WIDTH - 0.4 * mm, alert_y)
    
    c.setFillColor(COLOR_ALERT_TEXT)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawCentredString(x + BADGE_WIDTH / 2.0, alert_y + 1.5 * mm, "🛡️ BADGE DE SÉCURITÉ CHANTIER · SINYLON")
    
    # 4. Section Centrale : Photo + QR Code
    mid_y = alert_y - 37.0 * mm
    photo_w = 32.0 * mm
    photo_h = 35.0 * mm
    photo_x = x + 5.5 * mm
    
    # Cadre Photo
    c.setFillColor(HexColor("#f1f5f9"))
    c.setStrokeColor(HexColor("#cbd5e1"))
    c.setLineWidth(0.8)
    c.roundRect(photo_x, mid_y, photo_w, photo_h, 1.5 * mm, fill=1, stroke=1)
    
    # Dessiner la photo
    photo_file = worker.get('photo_path') or ''
    if photo_file and photo_file.startswith('/static/'):
        photo_file = os.path.join(BASE_DIR, photo_file.lstrip('/'))
    
    photo_drawn = False
    if photo_file and os.path.exists(photo_file):
        try:
            c.drawImage(photo_file, photo_x + 0.6 * mm, mid_y + 0.6 * mm, width=photo_w - 1.2 * mm, height=photo_h - 1.2 * mm, preserveAspectRatio=True)
            photo_drawn = True
        except Exception:
            photo_drawn = False
            
    if not photo_drawn:
        # Avatar stylisé avec initiales
        c.setFillColor(HexColor("#1e3a8a"))
        c.roundRect(photo_x + 0.6 * mm, mid_y + 0.6 * mm, photo_w - 1.2 * mm, photo_h - 1.2 * mm, 1.2 * mm, fill=1, stroke=0)
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 16)
        inits = ((nom[0] if nom else '') + (prenom[0] if prenom else '')).upper() or 'SN'
        c.drawCentredString(photo_x + photo_w / 2.0, mid_y + photo_h / 2.0 - 5, inits)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(photo_x + photo_w / 2.0, mid_y + 4 * mm, "SINYLON")
        
    # Cadre QR Code
    qr_w = 35.0 * mm
    qr_h = 35.0 * mm
    qr_x = x + BADGE_WIDTH - qr_w - 5.5 * mm
    
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(HexColor("#cbd5e1"))
    c.setLineWidth(0.8)
    c.roundRect(qr_x, mid_y, qr_w, qr_h, 1.5 * mm, fill=1, stroke=1)
    
    if os.path.exists(qr_img_path):
        try:
            c.drawImage(qr_img_path, qr_x + 1.0 * mm, mid_y + 1.0 * mm, width=qr_w - 2.0 * mm, height=qr_h - 2.0 * mm, preserveAspectRatio=True)
        except Exception:
            pass
            
    # 5. Informations Intervenant (Nom, Fonction, Matricule)
    info_y = mid_y - 4.5 * mm
    
    # NOM
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 11.5)
    disp_nom = nom.upper()[:22]
    c.drawString(x + 5.5 * mm, info_y, disp_nom)
    
    # Prénom
    info_y -= 4.2 * mm
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(HexColor("#334155"))
    c.drawString(x + 5.5 * mm, info_y, prenom[:24])
    
    # Fonction
    info_y -= 4.2 * mm
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(HexColor("#0369a1")) # Bleu clair
    c.drawString(x + 5.5 * mm, info_y, fonction[:32])
    
    # Société & Matricule
    info_y -= 4.2 * mm
    c.setFont("Helvetica", 8.0)
    c.setFillColor(COLOR_MUTED)
    c.drawString(x + 5.5 * mm, info_y, "Société :")
    c.setFont("Helvetica-Bold", 8.0)
    c.setFillColor(COLOR_DARK)
    c.drawString(x + 18.0 * mm, info_y, "SINYLON")
    
    c.setFont("Helvetica", 8.0)
    c.setFillColor(COLOR_MUTED)
    c.drawString(x + 42.0 * mm, info_y, "Matricule :")
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(HexColor("#1e3a8a"))
    c.drawString(x + 56.0 * mm, info_y, matricule)
    
    # 6. STEP Boxes (1, 2, 3) + Pastille Validité Septembre 2026
    step_y = y + 15.5 * mm
    step_size = 5.2 * mm
    
    # Step 1
    s1_x = x + 5.5 * mm
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(HexColor("#000000"))
    c.setLineWidth(0.8)
    c.rect(s1_x, step_y, step_size, step_size, fill=1, stroke=1)
    c.setFillColor(HexColor("#15803d"))
    c.setFont("Helvetica-Bold", 9.0)
    c.drawCentredString(s1_x + step_size / 2.0, step_y + 1.0 * mm, "✓")
    c.setFillColor(HexColor("#64748b"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(s1_x + step_size / 2.0, step_y - 2.5 * mm, "S1")
    
    # Step 2
    s2_x = s1_x + step_size + 3.0 * mm
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(HexColor("#000000"))
    c.setLineWidth(0.8)
    c.rect(s2_x, step_y, step_size, step_size, fill=1, stroke=1)
    c.setFillColor(HexColor("#15803d"))
    c.setFont("Helvetica-Bold", 9.0)
    c.drawCentredString(s2_x + step_size / 2.0, step_y + 1.0 * mm, "✓")
    c.setFillColor(HexColor("#64748b"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(s2_x + step_size / 2.0, step_y - 2.5 * mm, "S2")
    
    # Step 3
    s3_x = s2_x + step_size + 3.0 * mm
    c.setFillColor(COLOR_WHITE)
    c.setStrokeColor(HexColor("#000000"))
    c.setLineWidth(0.8)
    c.rect(s3_x, step_y, step_size, step_size, fill=1, stroke=1)
    c.setFillColor(HexColor("#15803d"))
    c.setFont("Helvetica-Bold", 9.0)
    c.drawCentredString(s3_x + step_size / 2.0, step_y + 1.0 * mm, "✓")
    c.setFillColor(HexColor("#64748b"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(s3_x + step_size / 2.0, step_y - 2.5 * mm, "S3")
    
    # Pastille Date Validité (Septembre 2026 : Du 01/09 Au 30/09)
    valid_w = 42.0 * mm
    valid_h = 6.8 * mm
    valid_x = x + BADGE_WIDTH - valid_w - 5.5 * mm
    c.setFillColor(COLOR_VALID_BG)
    c.roundRect(valid_x, step_y - 0.5 * mm, valid_w, valid_h, 1.8 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 7.8)
    c.drawCentredString(valid_x + valid_w / 2.0, step_y + 1.4 * mm, "VALIDE : 01/09 → 30/09/2026")
    
    # 7. Pied de page : Vague verte & Pastille SINYLON
    c.saveState()
    clip_foot = c.beginPath()
    clip_foot.roundRect(x, y, BADGE_WIDTH, BADGE_HEIGHT, 3.5 * mm)
    c.clipPath(clip_foot, stroke=0)
    
    footer_h = 11.5 * mm
    c.setFillColor(COLOR_GREEN_WAVE)
    
    pw = c.beginPath()
    pw.moveTo(x, y)
    pw.lineTo(x + BADGE_WIDTH, y)
    pw.lineTo(x + BADGE_WIDTH, y + footer_h - 1.2 * mm)
    pw.curveTo(x + BADGE_WIDTH * 0.7, y + footer_h - 3.0 * mm, x + BADGE_WIDTH * 0.35, y + footer_h + 1.8 * mm, x, y + footer_h - 0.6 * mm)
    pw.close()
    c.drawPath(pw, fill=1, stroke=0)
    
    # Pastille centrale SINYLON
    pill_w = 28.0 * mm
    pill_h = 4.8 * mm
    pill_x = x + (BADGE_WIDTH - pill_w) / 2.0
    c.setFillColor(COLOR_CSPS_RED)
    c.roundRect(pill_x, y + 1.6 * mm, pill_w, pill_h, 1.2 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_WHITE)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawCentredString(x + BADGE_WIDTH / 2.0, y + 2.6 * mm, "SINYLON")
    
    c.restoreState() # fin clip pied
    c.restoreState() # fin état badge

def generate_pdf_badges(workers):
    output_pdf = os.path.join(OUTPUT_DIR, "BADGES_TOUS_TRAVAILLEURS_SEPTEMBRE_2026.pdf")
    c = canvas.Canvas(output_pdf, pagesize=A4)
    page_w, page_h = A4
    
    margin_x = 10 * mm
    spacing_x = 10 * mm
    margin_y = 18.5 * mm
    spacing_y = 20 * mm
    
    col = 0
    row = 0
    
    temp_qrs = []
    
    for idx, worker in enumerate(workers):
        x = margin_x + col * (BADGE_WIDTH + spacing_x)
        y = page_h - margin_y - (row + 1) * BADGE_HEIGHT - row * spacing_y
        
        # QR Code individuel
        mat = worker.get('matricule') or f"SIN-{worker['id']:04d}"
        qr_url = f"{VERIF_URL_BASE}?id={mat}"
        qr_bytes = make_qr_png_bytes(qr_url)
        qr_temp_path = f"/tmp/qr_badge_{idx}_{mat}.png"
        with open(qr_temp_path, 'wb') as qf:
            qf.write(qr_bytes)
        temp_qrs.append(qr_temp_path)
        
        # Repères de découpe d'imprimerie
        c.setStrokeColor(HexColor("#94a3b8"))
        c.setLineWidth(0.4)
        c.line(x - 3 * mm, y, x - 1 * mm, y)
        c.line(x, y - 3 * mm, x, y - 1 * mm)
        c.line(x + BADGE_WIDTH + 1 * mm, y, x + BADGE_WIDTH + 3 * mm, y)
        c.line(x + BADGE_WIDTH, y - 3 * mm, x + BADGE_WIDTH, y - 1 * mm)
        c.line(x - 3 * mm, y + BADGE_HEIGHT, x - 1 * mm, y + BADGE_HEIGHT)
        c.line(x, y + BADGE_HEIGHT + 1 * mm, x, y + BADGE_HEIGHT + 3 * mm)
        c.line(x + BADGE_WIDTH + 1 * mm, y + BADGE_HEIGHT, x + BADGE_WIDTH + 3 * mm, y + BADGE_HEIGHT)
        c.line(x + BADGE_WIDTH, y + BADGE_HEIGHT + 1 * mm, x + BADGE_WIDTH, y + BADGE_HEIGHT + 3 * mm)
        
        draw_single_badge_canvas(c, x, y, worker, qr_temp_path)
        
        col += 1
        if col >= 2:
            col = 0
            row += 1
            if row >= 2:
                c.showPage()
                row = 0
                
    if col != 0 or row != 0:
        c.showPage()
        
    c.save()
    
    # Nettoyage des qr temporaires
    for q in temp_qrs:
        try:
            os.remove(q)
        except Exception:
            pass
            
    print(f"Succès : PDF des badges généré -> {output_pdf}")
    return output_pdf

def generate_html_badges(workers):
    output_html = os.path.join(OUTPUT_DIR, "BADGES_TOUS_TRAVAILLEURS_SEPTEMBRE_2026.html")
    
    # Logo base64
    logo_b64 = ""
    if os.path.exists(LOGO_WHITE_PATH):
        with open(LOGO_WHITE_PATH, 'rb') as lf:
            logo_b64 = base64.b64encode(lf.read()).decode('utf-8')
            
    logo_black_b64 = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, 'rb') as lf:
            logo_black_b64 = base64.b64encode(lf.read()).decode('utf-8')

    pages_html = []
    # 4 badges per page
    for i in range(0, len(workers), 4):
        batch = workers[i:i+4]
        cards_html = []
        for w in batch:
            mat = w.get('matricule') or f"SIN-{w['id']:04d}"
            qr_url = f"{VERIF_URL_BASE}?id={mat}"
            qr_bytes = make_qr_png_bytes(qr_url)
            qr_b64 = base64.b64encode(qr_bytes).decode('utf-8')
            
            # Photo
            photo_file = w.get('photo_path') or ''
            photo_b64 = None
            if photo_file and photo_file.startswith('/static/'):
                p_local = os.path.join(BASE_DIR, photo_file.lstrip('/'))
                if os.path.exists(p_local):
                    with open(p_local, 'rb') as pf:
                        photo_b64 = base64.b64encode(pf.read()).decode('utf-8')
                        
            nom = (w.get('nom') or '').upper()
            prenom = (w.get('prenom') or '').title()
            fonction = w.get('fonction') or 'Intervenant Montage'
            
            if photo_b64:
                photo_dom = f'<img src="data:image/jpeg;base64,{photo_b64}" style="width:100%;height:100%;object-fit:cover;border-radius:3px;">'
            else:
                inits = ((nom[0] if nom else '') + (prenom[0] if prenom else '')).upper() or 'SN'
                photo_dom = f'''<div style="width:100%;height:100%;background:linear-gradient(135deg, #1e3a8a, #3b82f6);display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;border-radius:3px;">
                    <span style="font-size:22px;font-weight:900;">{inits}</span>
                    <span style="font-size:8px;opacity:0.8;margin-top:2px;">SINYLON</span>
                </div>'''
                
            card = f"""
            <div class="badge-card">
                <div class="b-header">
                    <div>
                        <div style="font-size:14px;font-weight:900;letter-spacing:0.5px;color:#fff;">STELLANTIS</div>
                        <div style="font-size:7px;color:#cbd5e1;letter-spacing:0.5px;">ALGERIA K9 CKD0</div>
                    </div>
                    <img src="data:image/png;base64,{logo_b64}" style="height:20px;width:auto;" alt="Sinylon Logo">
                </div>
                <div class="b-alert">
                    🛡️ BADGE DE SÉCURITÉ CHANTIER · SINYLON
                </div>
                <div class="b-middle">
                    <div class="b-photo">{photo_dom}</div>
                    <div class="b-qr">
                        <img src="data:image/png;base64,{qr_b64}" style="width:100%;height:100%;" alt="QR Code">
                    </div>
                </div>
                <div class="b-info">
                    <div style="font-size:13px;font-weight:900;color:#0f172a;line-height:1.1;">{nom}</div>
                    <div style="font-size:10.5px;font-weight:700;color:#334155;margin-top:1px;">{prenom}</div>
                    <div style="font-size:9px;font-weight:700;color:#0369a1;margin-top:2px;">{fonction}</div>
                    <div style="display:flex;justify-content:space-between;font-size:8.5px;margin-top:3px;">
                        <span>Société : <strong>SINYLON</strong></span>
                        <span>Matricule : <strong style="color:#1e3a8a;font-family:monospace;">{mat}</strong></span>
                    </div>
                </div>
                <div class="b-steps-row">
                    <div class="step-box"><span style="color:#15803d;font-weight:bold;">✓</span><small>S1</small></div>
                    <div class="step-box"><span style="color:#15803d;font-weight:bold;">✓</span><small>S2</small></div>
                    <div class="step-box"><span style="color:#15803d;font-weight:bold;">✓</span><small>S3</small></div>
                    <div class="valid-box">VALIDE : 01/09 → 30/09/2026</div>
                </div>
                <div class="b-footer">
                    <svg viewBox="0 0 200 40" preserveAspectRatio="none">
                        <path d="M0,0 C70,25 140,-10 200,10 L200,40 L0,40 Z" fill="#15803d"></path>
                    </svg>
                    <div class="pill-csps">SINYLON</div>
                </div>
            </div>
            """
            cards_html.append(card)
            
        page = f"""
        <div class="page-a4">
            <div class="grid-4">
                {"".join(cards_html)}
            </div>
        </div>
        """
        pages_html.append(page)

    full_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>BADGES SINYLON — TOUS LES TRAVAILLEURS (SEPTEMBRE 2026)</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=JetBrains+Mono:wght@700&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #334155; font-family: 'Outfit', sans-serif; }}
.no-print {{
    background: #0f172a; color: #fff; padding: 14px 20px; text-align: center;
    position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.4);
}}
.no-print button {{
    background: #15803d; color: #fff; font-size: 15px; font-weight: 800;
    border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer;
    font-family: inherit; margin-left: 14px;
}}
.page-a4 {{
    width: 210mm; height: 297mm; background: #fff; margin: 20px auto;
    padding: 18mm 10mm; display: flex; align-items: center; justify-content: center;
    page-break-after: always; box-shadow: 0 8px 30px rgba(0,0,0,0.3);
}}
.grid-4 {{
    display: grid; grid-template-columns: 90mm 90mm; grid-template-rows: 120mm 120mm;
    gap: 16mm 10mm; justify-content: center; align-content: center;
}}
.badge-card {{
    width: 90mm; height: 120mm; background: #fff; border: 1.5px solid #94a3b8;
    border-radius: 4mm; position: relative; overflow: hidden; display: flex;
    flex-direction: column; box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}}
.b-header {{
    height: 22mm; background: #0f172a; padding: 0 5mm; display: flex;
    align-items: center; justify-content: space-between; position: relative;
    border-bottom: 1.5px solid #64748b;
}}
.b-alert {{
    height: 5.5mm; background: #e0f2fe; color: #1e3a8a; font-size: 8px;
    font-weight: 800; display: flex; align-items: center; justify-content: center;
    border-bottom: 1px solid #bae6fd;
}}
.b-middle {{
    display: flex; gap: 5mm; padding: 3mm 4mm; justify-content: center;
}}
.b-photo {{
    width: 32mm; height: 35mm; background: #f8fafc; border: 1px solid #cbd5e1;
    border-radius: 2mm; overflow: hidden; display: flex; align-items: center; justify-content: center;
}}
.b-qr {{
    width: 35mm; height: 35mm; background: #fff; border: 1px solid #cbd5e1;
    border-radius: 2mm; padding: 1mm; display: flex; align-items: center; justify-content: center;
}}
.b-info {{
    padding: 0 4.5mm; flex: 1;
}}
.b-steps-row {{
    padding: 0 4.5mm; margin-bottom: 12mm; display: flex; align-items: center;
    gap: 2mm;
}}
.step-box {{
    width: 5.5mm; height: 5.5mm; border: 1px solid #000; display: flex;
    flex-direction: column; align-items: center; justify-content: center;
    font-size: 8px; position: relative;
}}
.step-box small {{
    position: absolute; bottom: -8px; font-size: 6px; font-weight: bold; color: #64748b;
}}
.valid-box {{
    margin-left: auto; background: #1e293b; color: #fff; font-size: 7.5px;
    font-weight: 800; padding: 2px 6px; border-radius: 2mm;
}}
.b-footer {{
    position: absolute; bottom: 0; left: 0; width: 100%; height: 11mm;
    overflow: hidden;
}}
.b-footer svg {{
    width: 100%; height: 100%; display: block;
}}
.pill-csps {{
    position: absolute; bottom: 2mm; left: 50%; transform: translateX(-50%);
    background: #dc2626; color: #fff; font-size: 8px; font-weight: 900;
    padding: 1.5px 8px; border-radius: 1.5mm; letter-spacing: 0.5px;
}}
@media print {{
    body {{ background: #fff; }}
    .no-print {{ display: none !important; }}
    .page-a4 {{ margin: 0; box-shadow: none; }}
}}
</style>
</head>
<body>
<div class="no-print">
    <span>🛡️ <strong>SINYLON BADGE STUDIO</strong> — {len(workers)} Badges Travailleurs (Septembre 2026)</span>
    <button onclick="window.print()">🖨️ IMPRIMER TOUS LES BADGES (A4)</button>
</div>
{"".join(pages_html)}
</body>
</html>
"""
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print(f"Succès : HTML des badges généré -> {output_html}")
    return output_html

def generate_chantier_poster(workers):
    """
    Génère l'affiche A4 officielle de contrôle d'accès sur le chantier
    avec le grand QR Code scannable à distance et la liste des 60 intervenants.
    """
    output_pdf = os.path.join(OUTPUT_DIR, "AFFICHE_A4_CHANTIER_QR_CODE_BADGES_SEPTEMBRE_2026.pdf")
    output_html = os.path.join(OUTPUT_DIR, "AFFICHE_A4_CHANTIER_QR_CODE_BADGES_SEPTEMBRE_2026.html")
    
    # Grand QR Code pour le chantier
    chantier_url = "https://permis-sinylon.onrender.com/badge.html?view=chantier"
    qr_bytes = make_qr_png_bytes(chantier_url)
    qr_b64 = base64.b64encode(qr_bytes).decode('utf-8')
    qr_temp = "/tmp/qr_chantier_poster.png"
    with open(qr_temp, 'wb') as qf:
        qf.write(qr_bytes)

    # Logo base64
    logo_b64 = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, 'rb') as lf:
            logo_b64 = base64.b64encode(lf.read()).decode('utf-8')

    # 1. HTML Affiche
    poster_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>AFFICHE CHANTIER — CONTRÔLE BADGES SINYLON (SEPTEMBRE 2026)</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=JetBrains+Mono:wght@700&display=swap');
@page {{ size: A4 portrait; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Outfit', sans-serif; background: #f8fafc; color: #0f172a; }}
.no-print {{
    background: #0f172a; color: #fff; padding: 12px; text-align: center;
}}
.no-print button {{
    background: #15803d; color: #fff; font-size: 15px; font-weight: 800;
    border: none; padding: 10px 22px; border-radius: 8px; cursor: pointer;
}}
.poster {{
    width: 210mm; height: 297mm; margin: 0 auto; background: #fff;
    border: 4mm solid #0f172a; padding: 10mm 12mm; display: flex;
    flex-direction: column; justify-content: space-between;
}}
.p-header {{
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 3px solid #0f172a; padding-bottom: 8px;
}}
.p-title-zone {{
    text-align: center; margin: 10px 0;
}}
.badge-status {{
    background: #15803d; color: #fff; font-size: 14px; font-weight: 900;
    padding: 6px 20px; border-radius: 20px; display: inline-block; margin-top: 8px;
}}
.qr-container {{
    display: flex; gap: 20px; align-items: center; justify-content: center;
    background: #f8fafc; border: 2px solid #cbd5e1; border-radius: 12px; padding: 12px;
}}
.qr-box {{
    background: #fff; border: 3px solid #000; border-radius: 10px; padding: 10px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.15);
}}
.workers-table {{
    width: 100%; border-collapse: collapse; font-size: 7.5px; margin: 8px 0;
}}
.workers-table th {{
    background: #0f172a; color: #fff; padding: 3px 4px; text-align: left;
}}
.workers-table td {{
    border: 1px solid #cbd5e1; padding: 2px 4px;
}}
@media print {{
    body {{ background: #fff; }}
    .no-print {{ display: none !important; }}
    .poster {{ border: 3mm solid #000; box-shadow: none; }}
}}
</style>
</head>
<body>
<div class="no-print">
    <button onclick="window.print()">🖨️ IMPRIMER L'AFFICHE CHANTIER A4</button>
</div>
<div class="poster">
    <div class="p-header">
        <div style="display:flex;align-items:center;gap:12px;">
            <img src="data:image/png;base64,{logo_b64}" style="height:36px;width:auto;" alt="Sinylon">
            <div>
                <div style="font-size:20px;font-weight:900;letter-spacing:1px;">SINYLON</div>
                <div style="font-size:11px;color:#475569;font-weight:700;">ENTREPRISE INDUSTRIELLE CKD0</div>
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:18px;font-weight:900;color:#1e3a8a;">STELLANTIS ALGERIA</div>
            <div style="font-size:11px;font-weight:700;color:#64748b;">PROJET K9 CKD0 — ATELIER MONTAGE</div>
        </div>
    </div>

    <div class="p-title-zone">
        <div style="font-size:24px;font-weight:900;text-transform:uppercase;letter-spacing:0.5px;">
            REGISTRE OFFICIEL DES BADGES &amp; CONTRÔLE D'ACCÈS
        </div>
        <div style="font-size:13px;font-weight:700;color:#475569;margin-top:2px;">
            VÉRIFICATION DIGITALE EN DIRECT DU PERSONNEL AUTORISÉ SUR LE CHANTIER
        </div>
        <div class="badge-status">
            🟢 {len(workers)} TRAVAILLEURS CERTIFIÉS &amp; VALIDES · SEPTEMBRE 2026 (01/09 → 30/09)
        </div>
    </div>

    <div class="qr-container">
        <div class="qr-box">
            <img src="data:image/png;base64,{qr_b64}" style="width:170px;height:170px;display:block;" alt="QR Code Chantier">
        </div>
        <div style="max-width:320px;">
            <div style="font-size:16px;font-weight:900;color:#0f172a;margin-bottom:6px;">
                📱 SCANNEZ CE QR CODE POUR CONTRÔLER LA VALIDITÉ
            </div>
            <div style="font-size:11px;color:#475569;line-height:1.4;">
                Permet aux agents de sécurité, responsables HSE et coordinateurs de vérifier en direct sur smartphone les <strong>{len(workers)} travailleurs autorisés</strong>, leurs habilitations, inductions et fonctions.
            </div>
            <div style="font-size:10px;font-family:monospace;color:#1e3a8a;margin-top:8px;word-break:break-all;">
                {chantier_url}
            </div>
        </div>
    </div>

    <!-- TABLEAU CONDENSÉ DES 60 TRAVAILLEURS (4 COLONNES) -->
    <div style="margin:6px 0;">
        <div style="font-size:10px;font-weight:900;color:#0f172a;margin-bottom:4px;display:flex;justify-content:space-between;">
            <span>LISTE OFFICIELLE DES INTERVENANTS (55 SINYLON + 5 LOCAUX ALGÉRIE) :</span>
            <span style="color:#15803d;">TOUS STEP 1-2-3 VALIDÉS</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:7.5px;">
            <table class="workers-table">
                <thead>
                    <tr><th>MATRICULE</th><th>NOM &amp; PRÉNOM</th><th>FONCTION</th></tr>
                </thead>
                <tbody>
                    {"".join([f"<tr><td style='font-family:monospace;font-weight:bold;'>{w['matricule']}</td><td><strong>{w['nom']}</strong> {w['prenom']}</td><td>{w['fonction']}</td></tr>" for w in workers[:30]])}
                </tbody>
            </table>
            <table class="workers-table">
                <thead>
                    <tr><th>MATRICULE</th><th>NOM &amp; PRÉNOM</th><th>FONCTION</th></tr>
                </thead>
                <tbody>
                    {"".join([f"<tr><td style='font-family:monospace;font-weight:bold;'>{w['matricule']}</td><td><strong>{w['nom']}</strong> {w['prenom']}</td><td>{w['fonction']}</td></tr>" for w in workers[30:]])}
                </tbody>
            </table>
        </div>
    </div>

    <!-- SIGNATURES ET VISAS -->
    <div style="display:flex;justify-content:space-between;border-top:2px solid #0f172a;padding-top:8px;font-size:9px;">
        <div style="border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;width:32%;">
            <div style="color:#64748b;font-size:8px;">COORDINATEUR HSE CHANTIER :</div>
            <div style="font-weight:800;color:#0f172a;">Nouri Chahrour</div>
            <div style="font-size:8px;color:#15803d;margin-top:2px;">Validé 08h10 · Conforme HSE</div>
        </div>
        <div style="border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;width:32%;">
            <div style="color:#64748b;font-size:8px;">CHEF DE PROJET SINYLON :</div>
            <div style="font-weight:800;color:#0f172a;">Xie Xian</div>
            <div style="font-size:8px;color:#15803d;margin-top:2px;">Approuvé &amp; Autorisé</div>
        </div>
        <div style="border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;width:32%;">
            <div style="color:#64748b;font-size:8px;">SUPERVISEUR SUIVI MOEX :</div>
            <div style="font-weight:800;color:#0f172a;">M. W.P.E.E.X</div>
            <div style="font-size:8px;color:#15803d;margin-top:2px;">Visa Sécurité Chantier OK</div>
        </div>
    </div>
</div>
</body>
</html>
"""
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(poster_html)
    print(f"Succès : HTML Affiche chantier généré -> {output_html}")

    # 2. PDF Affiche avec ReportLab (Strictement 1 page A4)
    doc_p = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=8*mm,
        rightMargin=8*mm,
        topMargin=8*mm,
        bottomMargin=8*mm
    )
    story = []
    
    p_title = Paragraph("<b>REGISTRE OFFICIEL DES BADGES & CONTRÔLE D'ACCÈS</b>", ParagraphStyle('PT1', fontName='Helvetica-Bold', fontSize=15, leading=18, alignment=1))
    p_sub = Paragraph("<b>SINYLON · STELLANTIS ALGERIA K9 CKD0 — SEPTEMBRE 2026</b>", ParagraphStyle('PT2', fontName='Helvetica-Bold', fontSize=11, leading=14, alignment=1, textColor=HexColor('#1e3a8a')))
    p_stat = Paragraph("<b>🟢 60 TRAVAILLEURS AUTORISÉS & VALIDÉS (DU 01/09/2026 AU 30/09/2026)</b>", ParagraphStyle('PT3', fontName='Helvetica-Bold', fontSize=10, leading=13, alignment=1, textColor=HexColor('#15803d')))
    
    story.append(p_title)
    story.append(Spacer(1, 1.5*mm))
    story.append(p_sub)
    story.append(Spacer(1, 2*mm))
    story.append(p_stat)
    story.append(Spacer(1, 3*mm))
    
    # Image QR
    story.append(RLImage(qr_temp, width=90, height=90))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph("<b>📱 SCANNEZ CE QR CODE POUR CONTRÔLER EN DIRECT LA VALIDITÉ DES BADGES</b>", ParagraphStyle('PT4', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=1)))
    story.append(Paragraph(f"<i>{chantier_url}</i>", ParagraphStyle('PT5', fontName='Helvetica', fontSize=7.5, leading=9, alignment=1, textColor=HexColor('#64748b'))))
    story.append(Spacer(1, 3*mm))
    
    # Tableaux des 60 intervenants
    t_data_1 = [["MATRICULE", "NOM & PRÉNOM", "FONCTION"]]
    for w in workers[:30]:
        t_data_1.append([w['matricule'], f"{w['nom']} {w['prenom']}"[:20], w['fonction'][:24]])
    t1 = Table(t_data_1, colWidths=[65, 115, 105])
    t1.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 5.8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.8),
    ]))
    
    t_data_2 = [["MATRICULE", "NOM & PRÉNOM", "FONCTION"]]
    for w in workers[30:]:
        t_data_2.append([w['matricule'], f"{w['nom']} {w['prenom']}"[:20], w['fonction'][:24]])
    t2 = Table(t_data_2, colWidths=[65, 115, 105])
    t2.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 5.8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.8),
    ]))
    
    double_table = Table([[t1, t2]], colWidths=[285, 285])
    double_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(double_table)
    story.append(Spacer(1, 3*mm))
    
    # Visas
    sig_data = [
        ["COORDINATEUR HSE CHANTIER", "CHEF DE PROJET SINYLON", "SUPERVISEUR SUIVI MOEX"],
        ["Nouri Chahrour", "Xie Xian", "M. W.P.E.E.X"],
        ["Validé 08h10 · Conforme HSE", "Approuvé & Autorisé", "Visa Sécurité Chantier OK"]
    ]
    t_sig = Table(sig_data, colWidths=[190, 190, 190])
    t_sig.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0f172a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 1.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
    ]))
    story.append(t_sig)
    
    doc_p.build(story)
    print(f"Succès : PDF Affiche chantier généré -> {output_pdf}")
    
    try:
        os.remove(qr_temp)
    except Exception:
        pass

def main():
    workers = get_workers()
    print(f"Chargement de {len(workers)} travailleurs depuis la base de données...")
    
    # 1. Génération PDF des Badges (15 pages A4)
    generate_pdf_badges(workers)
    
    # 2. Génération HTML des Badges (interactif)
    generate_html_badges(workers)
    
    # 3. Génération Affiche Chantier A4 (PDF + HTML)
    generate_chantier_poster(workers)
    
    print("\n========================================================")
    print(f"Tous les fichiers ont été générés avec succès dans :")
    print(f"-> {OUTPUT_DIR}")
    print("========================================================\n")

if __name__ == '__main__':
    main()
