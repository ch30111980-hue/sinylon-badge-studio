#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AFFICHE A4 — GRAND QR CODE EXCLUSIF
Logo Sinylon en haut (sans trait) + Titre 'LISTE DU PERSONNEL' + Période + Grand QR Code
"""

import os
import sys
import base64
from io import BytesIO
import qrcode
from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4, mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_DIR = os.path.expanduser("~/Desktop")
OUTPUT_DIR = os.path.join(DESKTOP_DIR, "LISTES_PERSONNEL_SINYLON_SEPTEMBRE_2026")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOGO_PATH = os.path.join(BASE_DIR, 'static', 'img', 'sinylon_official_logo.png')
VERIF_URL = "https://permis-sinylon.onrender.com/badge.html?view=chantier"

def make_big_qr(url):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=16,
        border=2
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def main():
    pdf_path = os.path.join(OUTPUT_DIR, "AFFICHE_A4_QR_CODE_LISTE_PERSONNEL.pdf")
    html_path = os.path.join(OUTPUT_DIR, "AFFICHE_A4_QR_CODE_LISTE_PERSONNEL.html")

    qr_bytes = make_big_qr(VERIF_URL)
    qr_b64 = base64.b64encode(qr_bytes).decode('utf-8')
    qr_temp = "/tmp/big_qr_temp.png"
    with open(qr_temp, 'wb') as qf:
        qf.write(qr_bytes)

    logo_b64 = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, 'rb') as lf:
            logo_b64 = base64.b64encode(lf.read()).decode('utf-8')

    # =========================================================================
    # 1. REPORTLAB PDF (STRICTEMENT 1 PAGE A4)
    # =========================================================================
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=14*mm,
        rightMargin=14*mm,
        topMargin=12*mm,
        bottomMargin=12*mm
    )
    story = []

    # En-tête avec Logo en haut (sans trait)
    header_data = [
        [RLImage(LOGO_PATH, width=65, height=57) if os.path.exists(LOGO_PATH) else "SINYLON",
         Paragraph("<b>SINYLON ENTREPRISE INDUSTRIELLE</b><br/><font size=10 color='#475569'>Projet Assemblage Véhicules K9 CKD0</font><br/><font size=9.5 color='#1e3a8a'><b>USINE AUTOMOBILE STELLANTIS TAFRAOUI</b></font>", ParagraphStyle('HDesc', fontName='Helvetica', fontSize=12, leading=16)),
         Paragraph("<b>CONTRÔLE D'ACCÈS</b><br/><font size=8.5 color='#15803d'><b>SÉCURITÉ CHANTIER</b></font>", ParagraphStyle('HRight', fontName='Helvetica', fontSize=10, leading=13, alignment=2))]
    ]
    t_head = Table(header_data, colWidths=[75, 330, 110])
    t_head.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_head)
    story.append(Spacer(1, 6*mm))

    # Titre officiel
    p_title = Paragraph("<b>LISTE DU PERSONNEL</b>", ParagraphStyle('PTitle', fontName='Helvetica-Bold', fontSize=26, leading=30, alignment=1, textColor=HexColor('#0f172a')))
    story.append(p_title)
    story.append(Spacer(1, 3*mm))

    p_sub = Paragraph("<b>EFFECTIFS OFFICIELS AUTORISÉS SUR SITE</b>", ParagraphStyle('PSub', fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=1, textColor=HexColor('#1e3a8a')))
    story.append(p_sub)
    story.append(Spacer(1, 4*mm))

    # Période
    p_period = Paragraph("<b>📅 PÉRIODE : DU 01/09/2026 AU 30/09/2026</b><br/><font size=9 color='#15803d'>(RENOUVELABLE CHAQUE MOIS DU 1ER AU 30)</font>", ParagraphStyle('PPeriod', fontName='Helvetica-Bold', fontSize=12, leading=16, alignment=1, textColor=HexColor('#15803d')))
    story.append(p_period)
    story.append(Spacer(1, 8*mm))

    # GRAND QR CODE AU CENTRE
    story.append(RLImage(qr_temp, width=220, height=220))
    story.append(Spacer(1, 6*mm))

    # Texte explicatif sous le QR Code
    p_scan = Paragraph("<b>📱 SCANNEZ CE QR CODE AVEC VOTRE SMARTPHONE</b>", ParagraphStyle('PScan', fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=1, textColor=HexColor('#0f172a')))
    story.append(p_scan)
    story.append(Spacer(1, 2*mm))

    p_desc = Paragraph("Accédez instantanément au registre officiel en direct des <b>59 travailleurs autorisés</b><br/>(54 Spécialistes Sinylon + 5 Membres du Personnel Local Algérien)", ParagraphStyle('PDesc', fontName='Helvetica', fontSize=10, leading=14, alignment=1, textColor=HexColor('#334155')))
    story.append(p_desc)
    story.append(Spacer(1, 2*mm))

    p_url = Paragraph(f"<i>{VERIF_URL}</i>", ParagraphStyle('PUrl', fontName='Helvetica', fontSize=8, leading=10, alignment=1, textColor=HexColor('#64748b')))
    story.append(p_url)
    story.append(Spacer(1, 8*mm))

    # Pied de page sécurité
    foot_data = [
        ["SUPERVISEUR HSE SINYLON : Nouri Chahrour (0563765157)", "CHEF DE PROJET : Xie Xian", "PORT DES EPI OBLIGATOIRE"]
    ]
    t_foot = Table(foot_data, colWidths=[205, 155, 155])
    t_foot.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.2, colors.HexColor('#0f172a')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_foot)

    doc.build(story)
    print(f"Succès : PDF Grand QR Code généré (1 page A4) -> {pdf_path}")

    # =========================================================================
    # 2. HTML GRAND QR CODE (AFFICHE CHANTIER A4)
    # =========================================================================
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>LISTE DU PERSONNEL — AFFICHE A4 GRAND QR CODE (SEPTEMBRE 2026)</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=JetBrains+Mono:wght@700&display=swap');
@page {{ size: A4 portrait; margin: 8mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Outfit', sans-serif; background: #e2e8f0; color: #0f172a; }}
.no-print {{
    background: #0f172a; color: #fff; padding: 14px; text-align: center;
    position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}}
.no-print button {{
    background: #15803d; color: #fff; font-size: 16px; font-weight: 800;
    border: none; padding: 12px 28px; border-radius: 8px; cursor: pointer;
}}
.poster-a4 {{
    width: 210mm; height: 297mm; background: #fff; margin: 20px auto;
    padding: 12mm 16mm; border: 3.5mm solid #0f172a; box-shadow: 0 8px 30px rgba(0,0,0,0.2);
    display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;
    text-align: center;
}}
.header-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding-bottom: 8px;
}}
.logo-block {{
    display: flex; align-items: center; gap: 14px; text-align: left;
}}
.logo-block img {{
    height: 55px; width: auto;
}}
.title-block {{
    margin: 10px 0 6px 0;
}}
.title-block h1 {{
    font-size: 32px; font-weight: 900; text-transform: uppercase; color: #0f172a;
    letter-spacing: 1.5px;
}}
.title-block h2 {{
    font-size: 16px; font-weight: 800; color: #1e3a8a; margin-top: 4px;
    letter-spacing: 0.5px;
}}
.period-badge {{
    display: inline-block; background: #15803d; color: #fff; font-size: 13px;
    font-weight: 800; padding: 6px 20px; border-radius: 20px; margin-top: 8px;
    box-shadow: 0 2px 8px rgba(21,128,61,0.3);
}}
.qr-container {{
    margin: 14px auto; padding: 16px; background: #fff;
    border: 3px solid #0f172a; border-radius: 16px; display: inline-block;
    box-shadow: 0 6px 25px rgba(0,0,0,0.08);
}}
.qr-container img {{
    width: 230mm; max-width: 260px; height: auto; display: block;
}}
.instructions {{
    margin-top: 6px;
}}
.instructions h3 {{
    font-size: 16px; font-weight: 900; color: #0f172a; margin-bottom: 4px;
}}
.instructions p {{
    font-size: 12px; color: #475569; font-weight: 600; line-height: 1.4;
}}
.url-text {{
    font-family: 'JetBrains Mono', monospace; font-size: 9.5px; color: #1e3a8a;
    margin-top: 5px;
}}
.footer-row {{
    border-top: 2px solid #0f172a; padding-top: 10px; display: flex;
    justify-content: space-between; font-size: 10px; font-weight: 800; color: #334155;
}}
@media print {{
    body {{ background: #fff; }}
    .no-print {{ display: none !important; }}
    .poster-a4 {{ margin: 0; border: 3mm solid #000; box-shadow: none; height: 297mm; }}
}}
</style>
</head>
<body>
<div class="no-print">
    <button onclick="window.print()">🖨️ IMPRIMER L'AFFICHE A4 DU QR CODE CHANTIER</button>
</div>

<div class="poster-a4">
    <div>
        <!-- EN-TÊTE SANS TRAIT -->
        <div class="header-row">
            <div class="logo-block">
                <img src="data:image/png;base64,{logo_b64}" alt="Sinylon">
                <div>
                    <div style="font-size:22px;font-weight:900;letter-spacing:1px;color:#0f172a;">SINYLON</div>
                    <div style="font-size:10.5px;color:#475569;font-weight:700;">PROJET K9 CKD0 STELLANTIS</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:18px;font-weight:900;color:#1e3a8a;">STELLANTIS ALGERIA</div>
                <div style="font-size:10.5px;font-weight:700;color:#64748b;">USINE D'ASSEMBLAGE TAFRAOUI</div>
            </div>
        </div>

        <!-- TITRE OFFICIEL -->
        <div class="title-block">
            <h1>LISTE DU PERSONNEL</h1>
            <h2>EFFECTIFS OFFICIELS AUTORISÉS SUR SITE</h2>
            <div class="period-badge">
                📅 PÉRIODE : DU 01/09/2026 AU 30/09/2026 (RENOUVELABLE CHAQUE MOIS DU 1ER AU 30)
            </div>
        </div>

        <!-- GRAND QR CODE AU CENTRE -->
        <div class="qr-container">
            <img src="data:image/png;base64,{qr_b64}" alt="Grand QR Code Chantier">
        </div>

        <!-- INSTRUCTIONS DE SCAN -->
        <div class="instructions">
            <h3>📱 SCANNEZ CE QR CODE AVEC UN SMARTPHONE</h3>
            <p>
                Contrôle d'accès numérique direct : affiche la liste officielle, les photos et les validations de sécurité<br/>
                des <strong>59 travailleurs autorisés</strong> (54 Spécialistes Sinylon + 5 Membres du Personnel Local Algérien).
            </p>
            <div class="url-text">
                {VERIF_URL}
            </div>
        </div>
    </div>

    <!-- PIED DE PAGE -->
    <div class="footer-row">
        <div>Superviseur HSE Sinylon : <strong>Nouri Chahrour (0563765157)</strong></div>
        <div>Chef de Projet : <strong>Xie Xian</strong></div>
        <div>Sécurité Chantier : <strong>Badges &amp; EPI Obligatoires</strong></div>
    </div>
</div>
</body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Succès : HTML Grand QR Code généré -> {html_path}")

    try:
        os.remove(qr_temp)
    except Exception:
        pass

if __name__ == '__main__':
    main()
