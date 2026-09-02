#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur des Listes Officielles du Personnel — SINYLON / STELLANTIS
Mois : Septembre 2026 (Du 01/09/2026 Au 30/09/2026 — Renouvelable mensuellement)

Effectif Actif : 54 Chinois Sinylon + 5 Locaux Algériens (3 Hommes & 2 Femmes) = 59 Personnes

1. Document 1 : Liste Unique Officielle pour le Chef de la Sécurité Stellantis (Tableau continu de 1 à 54 + Section Algériens collée)
2. Document 2 : Affiche A4 Chantier avec grand QR Code et registre complet
"""

import os
import sys
import sqlite3
import base64
from io import BytesIO
import qrcode
from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4, mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'sinylon_studio.db')

DESKTOP_DIR = os.path.expanduser("~/Desktop")
OUTPUT_DIR = os.path.join(DESKTOP_DIR, "LISTES_PERSONNEL_SINYLON_SEPTEMBRE_2026")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOGO_PATH = os.path.join(BASE_DIR, 'static', 'img', 'sinylon_official_logo.png')
LOGO_WHITE_PATH = os.path.join(BASE_DIR, 'static', 'img', 'sinylon_official_logo_white.png')

VERIF_URL = "https://permis-sinylon.onrender.com/badge.html"

def make_qr(url, size=10):
    qr = qrcode.QRCode(version=1, box_size=size, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def get_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 54 Chinois actifs (exclut les algériens et l'intérimaire inactif SIN-1038)
    cursor.execute("""
        SELECT matricule, nom, prenom, fonction 
        FROM workers 
        WHERE matricule NOT IN ('SIN-1158', 'SIN-1160', 'SIN-1162', 'SIN-1164', 'SIN-1166', 'SIN-1038')
        ORDER BY id ASC
    """)
    chinese_rows = cursor.fetchall()
    conn.close()

    chinese = [{'mat': r[0], 'nom': r[1], 'prenom': r[2], 'fonction': r[3]} for r in chinese_rows]

    # 5 Locaux Algériens (3 Hommes & 2 Femmes)
    algerians = [
        {'mat': 'SIN-1162', 'nom': 'CHAHROUR', 'prenom': 'Nouri', 'fonction': 'HSE', 'genre': 'Homme'},
        {'mat': 'SIN-1158', 'nom': 'DJOUHRI', 'prenom': 'Abdelkader', 'fonction': 'Installation', 'genre': 'Homme'},
        {'mat': 'SIN-1160', 'nom': 'ABDELWAHED', 'prenom': 'Najib', 'fonction': 'Installation', 'genre': 'Homme'},
        {'mat': 'SIN-1164', 'nom': 'ABDERRAHMANI', 'prenom': 'Melissa', 'fonction': 'Traductrice', 'genre': 'Femme'},
        {'mat': 'SIN-1166', 'nom': 'ZOHRA', 'prenom': 'Fatima Zohra', 'fonction': 'Assistante Chef de Projet', 'genre': 'Femme'}
    ]

    return chinese, algerians

# =========================================================================
# 1. LISTE OFFICIELLE CHEF DE LA SÉCURITÉ (UNE SEULE LISTE CONTINUE)
# =========================================================================

def generate_securite_doc(chinese, algerians):
    pdf_path = os.path.join(OUTPUT_DIR, "LISTE_OFFICIELLE_CHEF_SECURITE_SEPTEMBRE_2026.pdf")
    html_path = os.path.join(OUTPUT_DIR, "LISTE_OFFICIELLE_CHEF_SECURITE_SEPTEMBRE_2026.html")

    qr_bytes = make_qr(VERIF_URL, size=6)
    qr_b64 = base64.b64encode(qr_bytes).decode('utf-8')
    qr_temp = "/tmp/qr_sec_temp.png"
    with open(qr_temp, 'wb') as qf:
        qf.write(qr_bytes)

    logo_b64 = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, 'rb') as lf:
            logo_b64 = base64.b64encode(lf.read()).decode('utf-8')

    # --- REPORTLAB PDF (2 Pages A4 structurées et aérées) ---
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=8*mm,
        bottomMargin=8*mm
    )
    story = []

    # --- PAGE 1 ---
    # En-tête sans trait
    header_data_p1 = [
        [RLImage(LOGO_PATH, width=44, height=38) if os.path.exists(LOGO_PATH) else "SINYLON",
         Paragraph("<b>SINYLON ENTREPRISE INDUSTRIELLE</b><br/><font size=8.5 color='#475569'>Projet Assemblage Véhicules K9 CKD0 · Usine Stellantis Tafraoui</font><br/><b>Fiche Officielle des Effectifs Autorisés sur Site — Septembre 2026</b>", ParagraphStyle('HDesc', fontName='Helvetica', fontSize=10, leading=13)),
         RLImage(qr_temp, width=48, height=48)]
    ]
    t_head1 = Table(header_data_p1, colWidths=[60, 420, 60])
    t_head1.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('ALIGN', (2,0), (2,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_head1)
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph("<b>SINYLON — LISTE DU PERSONNEL AUTORISÉ SUR SITE</b>", ParagraphStyle('ST1', fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=1)))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph("<b>TRANSMISSION OFFICIELLE AU CHEF DE LA SÉCURITÉ STELLANTIS</b> — CONTRÔLE D'ACCÈS &amp; POINTAGE", ParagraphStyle('ST2', fontName='Helvetica-Bold', fontSize=9.5, leading=12, alignment=1, textColor=HexColor('#1e3a8a'))))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(f"<b>📅 PÉRIODE ACTIVE : DU 01/09/2026 AU 30/09/2026</b> (Renouvelable chaque mois du 1er au 30) — Total : <b>{len(chinese) + len(algerians)} Intervenants</b>", ParagraphStyle('ST3', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=1, textColor=HexColor('#15803d'))))
    story.append(Spacer(1, 3*mm))

    # SECTION 1 (Partie 1 : 1 à 27)
    story.append(Paragraph(f"<b>1. ÉQUIPE CHANTIER SINYLON ({len(chinese)} INTERVENANTS) — 1ÈRE PARTIE (N° 01 À 27) :</b>", ParagraphStyle('Sec1', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=HexColor('#0f172a'))))
    story.append(Spacer(1, 1.5*mm))

    t1_data = [["N°", "MATRICULE", "NOM & PRÉNOM", "FONCTION OFFICIELLE", "ENTREPRISE", "STATUT CHANTIER"]]
    for idx, w in enumerate(chinese[:27]):
        t1_data.append([
            f"{idx+1:02d}", w['mat'], f"{w['nom']} {w['prenom']}", w['fonction'], "SINYLON", "🟢 AUTORISÉ"
        ])
    t_c1 = Table(t1_data, colWidths=[28, 75, 175, 145, 60, 60])
    t_c1.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.2),
        ('ALIGN', (0,0), (1,-1), 'CENTER'),
        ('ALIGN', (4,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
    ]))
    story.append(t_c1)

    story.append(PageBreak())

    # --- PAGE 2 ---
    header_data_p2 = [
        [RLImage(LOGO_PATH, width=38, height=33) if os.path.exists(LOGO_PATH) else "SINYLON",
         Paragraph("<b>SINYLON — SUITE DE LA LISTE OFFICIELLE DU PERSONNEL (SEPTEMBRE 2026)</b><br/><font size=8 color='#64748b'>Document de Transmission Sécurité · Usine Stellantis Tafraoui</font>", ParagraphStyle('HDesc2', fontName='Helvetica', fontSize=9, leading=12)),
         RLImage(qr_temp, width=38, height=38)]
    ]
    t_head2 = Table(header_data_p2, colWidths=[55, 435, 55])
    t_head2.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('ALIGN', (2,0), (2,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_head2)
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph(f"<b>ÉQUIPE CHANTIER SINYLON — 2ÈME PARTIE (N° 28 À {len(chinese)}) :</b>", ParagraphStyle('Sec2', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=HexColor('#0f172a'))))
    story.append(Spacer(1, 1.5*mm))

    t2_data = [["N°", "MATRICULE", "NOM & PRÉNOM", "FONCTION OFFICIELLE", "ENTREPRISE", "STATUT CHANTIER"]]
    for idx, w in enumerate(chinese[27:]):
        t2_data.append([
            f"{idx+28:02d}", w['mat'], f"{w['nom']} {w['prenom']}", w['fonction'], "SINYLON", "🟢 AUTORISÉ"
        ])
    t_c2 = Table(t2_data, colWidths=[28, 75, 175, 145, 60, 60])
    t_c2.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.2),
        ('ALIGN', (0,0), (1,-1), 'CENTER'),
        ('ALIGN', (4,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
    ]))
    story.append(t_c2)
    story.append(Spacer(1, 3*mm))

    # SECTION 2 COLLÉE : PERSONNEL LOCAL ALGÉRIEN (3 Hommes & 2 Femmes)
    story.append(Paragraph("<b>2. PERSONNEL LOCAL ALGÉRIEN AUTORISÉ — 5 PERSONNES (3 HOMMES & 2 FEMMES) :</b>", ParagraphStyle('SecAlg', fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=HexColor('#15803d'))))
    story.append(Spacer(1, 1.5*mm))

    alg_data = [
        ["N°", "MATRICULE", "NOM & PRÉNOM", "FONCTION OFFICIELLE", "GENRE", "ENTREPRISE", "STATUT CHANTIER"]
    ]
    for idx, a in enumerate(algerians):
        icon = "👨 Homme" if a['genre'] == 'Homme' else "👩 Femme"
        alg_data.append([
            f"{idx+1:02d}", a['mat'], f"{a['nom']} {a['prenom']}", a['fonction'], icon, "SINYLON", "🟢 ACTIF & VALIDÉ"
        ])
    t_alg = Table(alg_data, colWidths=[28, 75, 150, 130, 55, 50, 55])
    t_alg.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.8, colors.HexColor('#15803d')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#15803d')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f0fdf4')),
        ('ALIGN', (0,0), (1,-1), 'CENTER'),
        ('ALIGN', (4,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
    ]))
    story.append(t_alg)
    story.append(Spacer(1, 4*mm))

    # VISAS ET ACCUSÉ DE RÉCEPTION SÉCURITÉ
    visa_data = [
        ["ÉMIS PAR (HSE SINYLON)", "APPROUVÉ PAR (CHEF PROJET)", "ACCUSÉ DE RÉCEPTION — CHEF DE LA SÉCURITÉ STELLANTIS"],
        ["Nom : Nouri Chahrour\nFonction : HSE Sinylon\nDate : 01/09/2026 · 08h10\n\nSignature :",
         "Nom : Xie Xian\nFonction : Chef de Projet Sinylon\nDate : 01/09/2026\n\nSignature :",
         "Reçu le : ...... / 09 / 2026 à ...... h ......\nNom de l'Officier de Sécurité : ........................................\nSignature & Cachet Sécurité :"]
    ]
    t_visa = Table(visa_data, colWidths=[175, 175, 194])
    t_visa.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0f172a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7.5),
        ('FONTSIZE', (0,1), (-1,1), 7),
        ('BACKGROUND', (2,0), (2,0), colors.HexColor('#dc2626')),
        ('BACKGROUND', (2,1), (2,1), colors.HexColor('#fef2f2')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_visa)

    doc.build(story)
    print(f"Succès : PDF Sécurité généré (2 Pages A4) -> {pdf_path}")

    # --- HTML SÉCURITÉ (UNE SEULE LISTE UNIFIÉE SUR 2 PAGES IMPRIMABLES) ---
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>LISTE OFFICIELLE DU PERSONNEL SINYLON (54 CHINOIS + 5 ALGÉRIENS) — TRANSMISSION SÉCURITÉ</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=JetBrains+Mono:wght@700&display=swap');
@page {{ size: A4 portrait; margin: 8mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Outfit', sans-serif; background: #e2e8f0; color: #0f172a; }}
.no-print {{
    background: #0f172a; color: #fff; padding: 12px; text-align: center;
    position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}}
.no-print button {{
    background: #15803d; color: #fff; font-size: 15px; font-weight: 800;
    border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer;
}}
.page-a4 {{
    width: 210mm; min-height: 297mm; background: #fff; margin: 15px auto;
    padding: 10mm 12mm; border: 1.5px solid #cbd5e1; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    display: flex; flex-direction: column; justify-content: space-between; page-break-after: always;
}}
.header-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding-bottom: 6px; margin-bottom: 6px;
}}
.logo-left {{
    display: flex; align-items: center; gap: 12px;
}}
.logo-left img {{
    height: 42px; width: auto;
}}
.title-block {{
    text-align: center; margin-bottom: 8px;
}}
.title-block h1 {{
    font-size: 15px; font-weight: 900; text-transform: uppercase; color: #0f172a;
}}
.title-block h2 {{
    font-size: 11px; font-weight: 800; color: #1e3a8a; margin-top: 2px;
}}
.period-badge {{
    display: inline-block; background: #15803d; color: #fff; font-size: 9.5px;
    font-weight: 800; padding: 3px 12px; border-radius: 12px; margin-top: 4px;
}}
table.worker-table {{
    width: 100%; border-collapse: collapse; font-size: 8.5px; margin-bottom: 6px;
}}
table.worker-table th {{
    background: #1e3a8a; color: #fff; padding: 4px 6px; text-align: left;
    font-size: 8px; font-weight: 800;
}}
table.worker-table td {{
    border: 1px solid #cbd5e1; padding: 3px 6px;
}}
table.worker-table tr:nth-child(even) {{ background: #f8fafc; }}

/* Section Locaux Algériens */
.algerian-section {{
    border: 2px solid #15803d; border-radius: 6px; padding: 6px 8px;
    background: #f0fdf4; margin-top: 4px; margin-bottom: 6px;
}}
.algerian-header {{
    font-size: 10px; font-weight: 900; color: #15803d; display: flex;
    justify-content: space-between; margin-bottom: 4px; border-bottom: 1px solid #86efac;
    padding-bottom: 3px;
}}
table.alg-table {{
    width: 100%; border-collapse: collapse; font-size: 8.5px;
}}
table.alg-table th {{
    background: #15803d; color: #fff; padding: 4px 6px; text-align: left; font-size: 8px;
}}
table.alg-table td {{
    border: 1px solid #86efac; padding: 3.5px 6px; font-weight: 700; background: #fff;
}}

.signatures-box {{
    display: grid; grid-template-columns: 1fr 1fr 1.3fr; gap: 8px;
    border-top: 1.5px solid #0f172a; padding-top: 6px; font-size: 8px;
}}
.sig-card {{
    border: 1px solid #cbd5e1; border-radius: 4px; padding: 5px 6px; background: #f8fafc;
}}
.sig-card.security {{
    border: 1.5px solid #dc2626; background: #fef2f2;
}}
.sig-card strong {{ display: block; margin-bottom: 3px; font-size: 8.5px; }}

@media print {{
    body {{ background: #fff; }}
    .no-print {{ display: none !important; }}
    .page-a4 {{ margin: 0; border: none; box-shadow: none; min-height: 297mm; height: 297mm; padding: 8mm 10mm; }}
}}
</style>
</head>
<body>
<div class="no-print">
    <button onclick="window.print()">🖨️ IMPRIMER LA LISTE OFFICIELLE (UNE SEULE LISTE — 2 PAGES A4)</button>
</div>

<!-- PAGE 1 / 2 -->
<div class="page-a4">
    <div>
        <div class="header-row">
            <div class="logo-left">
                <img src="data:image/png;base64,{logo_b64}" alt="Sinylon">
                <div>
                    <div style="font-size:18px;font-weight:900;letter-spacing:0.5px;">SINYLON</div>
                    <div style="font-size:8.5px;color:#475569;font-weight:700;">PROJET CKD0 ALGERIA</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:15px;font-weight:900;color:#1e3a8a;">STELLANTIS TAFRAOUI</div>
                <div style="font-size:8.5px;color:#64748b;font-weight:700;">USINE AUTOMOBILE ORAN</div>
            </div>
            <img src="data:image/png;base64,{qr_b64}" style="width:46px;height:46px;" alt="QR Code">
        </div>

        <div class="title-block">
            <h1>SINYLON — LISTE DU PERSONNEL AUTORISÉ SUR SITE</h1>
            <h2>TRANSMISSION OFFICIELLE AU CHEF DE LA SÉCURITÉ STELLANTIS</h2>
            <div class="period-badge">
                📅 PÉRIODE : DU 01/09/2026 AU 30/09/2026 (RENOUVELABLE CHAQUE MOIS DU 1ER AU 30) — TOTAL : {len(chinese)+len(algerians)} PERSONNES
            </div>
        </div>

        <!-- 54 INTERVENANTS SINYLON : PARTIE 1 (1 À 27) -->
        <div style="font-size:9.5px;font-weight:900;color:#0f172a;margin-bottom:4px;display:flex;justify-content:space-between;">
            <span>1. ÉQUIPE CHANTIER SINYLON ({len(chinese)} INTERVENANTS) — 1ÈRE PARTIE (N° 01 À 27) :</span>
            <span style="color:#1e3a8a;">HABILITATIONS SÉCURITÉ CONFORMES</span>
        </div>

        <table class="worker-table">
            <thead>
                <tr>
                    <th style="width:30px;text-align:center;">N°</th>
                    <th style="width:85px;">MATRICULE</th>
                    <th>NOM &amp; PRÉNOM</th>
                    <th>FONCTION OFFICIELLE</th>
                    <th style="width:75px;text-align:center;">ENTREPRISE</th>
                    <th style="width:75px;text-align:center;">STATUT</th>
                </tr>
            </thead>
            <tbody>
                {"".join([f"<tr><td style='text-align:center;font-weight:bold;'>{i+1:02d}</td><td style='font-family:monospace;font-weight:bold;color:#1e3a8a;'>{w['mat']}</td><td><strong>{w['nom']}</strong> {w['prenom']}</td><td>{w['fonction']}</td><td style='text-align:center;'>SINYLON</td><td style='text-align:center;color:#15803d;font-weight:bold;'>🟢 AUTORISÉ</td></tr>" for i, w in enumerate(chinese[:27])])}
            </tbody>
        </table>
    </div>

    <div style="text-align:center;font-size:8px;color:#64748b;border-top:1px solid #cbd5e1;padding-top:4px;">
        Page 1 / 2 — Suite de la liste et section personnel local algérien en Page 2
    </div>
</div>

<!-- PAGE 2 / 2 -->
<div class="page-a4">
    <div>
        <div class="header-row">
            <div class="logo-left">
                <img src="data:image/png;base64,{logo_b64}" alt="Sinylon">
                <div>
                    <div style="font-size:16px;font-weight:900;">SINYLON — SUITE DE LA LISTE OFFICIELLE</div>
                    <div style="font-size:8.5px;color:#475569;font-weight:700;">PROJET K9 CKD0 STELLANTIS (SEPTEMBRE 2026)</div>
                </div>
            </div>
            <img src="data:image/png;base64,{qr_b64}" style="width:40px;height:40px;" alt="QR Code">
        </div>

        <!-- 54 INTERVENANTS SINYLON : PARTIE 2 (28 À 54) -->
        <div style="font-size:9.5px;font-weight:900;color:#0f172a;margin-bottom:4px;">
            ÉQUIPE CHANTIER SINYLON — 2ÈME PARTIE (N° 28 À {len(chinese)}) :
        </div>

        <table class="worker-table">
            <thead>
                <tr>
                    <th style="width:30px;text-align:center;">N°</th>
                    <th style="width:85px;">MATRICULE</th>
                    <th>NOM &amp; PRÉNOM</th>
                    <th>FONCTION OFFICIELLE</th>
                    <th style="width:75px;text-align:center;">ENTREPRISE</th>
                    <th style="width:75px;text-align:center;">STATUT</th>
                </tr>
            </thead>
            <tbody>
                {"".join([f"<tr><td style='text-align:center;font-weight:bold;'>{i+28:02d}</td><td style='font-family:monospace;font-weight:bold;color:#1e3a8a;'>{w['mat']}</td><td><strong>{w['nom']}</strong> {w['prenom']}</td><td>{w['fonction']}</td><td style='text-align:center;'>SINYLON</td><td style='text-align:center;color:#15803d;font-weight:bold;'>🟢 AUTORISÉ</td></tr>" for i, w in enumerate(chinese[27:])])}
            </tbody>
        </table>

        <!-- SECTION LOCAUX ALGÉRIENS COLLÉE -->
        <div class="algerian-section">
            <div class="algerian-header">
                <span>🇩🇿 2. PERSONNEL LOCAL ALGÉRIEN AUTORISÉ — 5 PERSONNES (3 HOMMES &amp; 2 FEMMES) :</span>
                <span>CONTRATS &amp; VISITES MÉDICALES CONFORMES</span>
            </div>
            <table class="alg-table">
                <thead>
                    <tr>
                        <th style="width:30px;text-align:center;">N°</th>
                        <th style="width:85px;">MATRICULE</th>
                        <th>NOM &amp; PRÉNOM</th>
                        <th>FONCTION OFFICIELLE</th>
                        <th style="width:80px;text-align:center;">CATÉGORIE</th>
                        <th style="width:75px;text-align:center;">ENTREPRISE</th>
                        <th style="width:75px;text-align:center;">STATUT</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f"<tr><td style='text-align:center;font-weight:bold;'>{i+1:02d}</td><td style='font-family:monospace;color:#1e3a8a;font-weight:bold;'>{a['mat']}</td><td><strong>{a['nom']}</strong> {a['prenom']}</td><td style='color:#0f172a;'>{a['fonction']}</td><td style='text-align:center;'>{'👨 Homme' if a['genre']=='Homme' else '👩 Femme'}</td><td style='text-align:center;'>SINYLON</td><td style='text-align:center;color:#15803d;font-weight:bold;'>🟢 AUTORISÉ</td></tr>" for i, a in enumerate(algerians)])}
                </tbody>
            </table>
        </div>
    </div>

    <!-- SIGNATURES -->
    <div>
        <div class="signatures-box">
            <div class="sig-card">
                <strong style="color:#0f172a;">COORDINATEUR HSE SINYLON :</strong>
                <div>Nouri Chahrour</div>
                <div style="color:#64748b;font-size:7.5px;">Tél : 0563765157</div>
                <div style="margin-top:6px;border-bottom:1px dashed #94a3b8;height:12px;"></div>
            </div>
            <div class="sig-card">
                <strong style="color:#0f172a;">CHEF DE PROJET SINYLON :</strong>
                <div>Xie Xian</div>
                <div style="color:#64748b;font-size:7.5px;">Directeur Chantier</div>
                <div style="margin-top:6px;border-bottom:1px dashed #94a3b8;height:12px;"></div>
            </div>
            <div class="sig-card security">
                <strong style="color:#dc2626;">ACCUSÉ DE RÉCEPTION — CHEF DE LA SÉCURITÉ STELLANTIS :</strong>
                <div>Reçu le : ...... / 09 / 2026 à ...... h ......</div>
                <div style="color:#64748b;font-size:7.5px;">Nom de l'Officier Sécurité : ........................................</div>
                <div style="margin-top:3px;font-size:7.5px;color:#dc2626;">Visa, Signature &amp; Cachet Poste de Garde :</div>
            </div>
        </div>
        <div style="text-align:center;font-size:8px;color:#64748b;margin-top:4px;">
            Page 2 / 2 — Registre officiel Sinylon Stellantis K9 CKD0
        </div>
    </div>
</div>
</body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Succès : HTML Sécurité généré (Une seule liste unifiée) -> {html_path}")

# =========================================================================
# 2. AFFICHAGE CHANTIER (1 PAGE A4 STRICTEMENT)
# =========================================================================

def generate_chantier_doc(chinese, algerians):
    pdf_path = os.path.join(OUTPUT_DIR, "AFFICHAGE_CHANTIER_PERSONNEL_AUTORISE_SEPTEMBRE_2026.pdf")
    html_path = os.path.join(OUTPUT_DIR, "AFFICHAGE_CHANTIER_PERSONNEL_AUTORISE_SEPTEMBRE_2026.html")

    chantier_url = "https://permis-sinylon.onrender.com/badge.html?view=chantier"
    qr_bytes = make_qr(chantier_url, size=8)
    qr_b64 = base64.b64encode(qr_bytes).decode('utf-8')
    qr_temp = "/tmp/qr_cha_temp.png"
    with open(qr_temp, 'wb') as qf:
        qf.write(qr_bytes)

    logo_b64 = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, 'rb') as lf:
            logo_b64 = base64.b64encode(lf.read()).decode('utf-8')

    # --- REPORTLAB AFFICHE CHANTIER (1 PAGE A4) ---
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=8*mm,
        rightMargin=8*mm,
        topMargin=6*mm,
        bottomMargin=6*mm
    )
    story = []

    # En-tête sans trait
    head_data = [
        [RLImage(LOGO_PATH, width=46, height=40) if os.path.exists(LOGO_PATH) else "SINYLON",
         Paragraph("<b>AFFICHAGE CHANTIER — PERSONNEL AUTORISÉ</b><br/><font size=11 color='#1e3a8a'><b>SINYLON · PROJET STELLANTIS K9 CKD0</b></font><br/><font size=8.5 color='#15803d'><b>🟢 MOIS DE SEPTEMBRE 2026 (DU 01/09/2026 AU 30/09/2026 — RENOUVELABLE)</b></font>", ParagraphStyle('PH', fontName='Helvetica', alignment=1, leading=14)),
         RLImage(qr_temp, width=50, height=50)]
    ]
    t_h = Table(head_data, colWidths=[65, 410, 65])
    t_h.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('ALIGN', (2,0), (2,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 1.5*mm))

    # Grand QR Code
    qr_info_data = [
        [RLImage(qr_temp, width=80, height=80),
         Paragraph(f"<b>📱 SCANNEZ CE QR CODE POUR CONTRÔLER LES {len(chinese)+len(algerians)} INTERVENANTS</b><br/><font size=8 color='#334155'>Vérification instantanée sur smartphone : validité, photos et habilitations de sécurité certifiées.</font><br/><font size=7.5 color='#1e3a8a'><i>{chantier_url}</i></font><br/><font size=8 color='#dc2626'><b>Badges &amp; EPI obligatoires · Urgence HSE Sinylon : 0563765157</b></font>", ParagraphStyle('QRT', fontName='Helvetica', fontSize=9, leading=12))]
    ]
    t_qr = Table(qr_info_data, colWidths=[90, 450])
    t_qr.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_qr)
    story.append(Spacer(1, 2*mm))

    # SECTION LOCAUX ALGÉRIENS
    story.append(Paragraph("<b>🇩🇿 PERSONNEL LOCAL ALGÉRIEN AUTORISÉ (3 HOMMES &amp; 2 FEMMES) :</b>", ParagraphStyle('SA', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=HexColor('#15803d'))))
    story.append(Spacer(1, 1*mm))

    alg_rows = [["MATRICULE", "NOM & PRÉNOM", "FONCTION OFFICIELLE", "CATÉGORIE", "STATUT"]]
    for a in algerians:
        cat = "👨 Homme" if a['genre'] == 'Homme' else "👩 Femme"
        alg_rows.append([a['mat'], f"{a['nom']} {a['prenom']}", a['fonction'], cat, "🟢 VALIDÉ"])
    t_alg_cha = Table(alg_rows, colWidths=[75, 175, 150, 70, 70])
    t_alg_cha.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.8, colors.HexColor('#15803d')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#15803d')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f0fdf4')),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (3,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
    ]))
    story.append(t_alg_cha)
    story.append(Spacer(1, 2*mm))

    # 54 TRAVAILLEURS CHINOIS (2 COLONNES ÉQUILIBRÉES DE 27)
    story.append(Paragraph(f"<b>ÉQUIPE CHANTIER SINYLON ({len(chinese)} INTERVENANTS) :</b>", ParagraphStyle('SC', fontName='Helvetica-Bold', fontSize=8.5, leading=10, textColor=HexColor('#0f172a'))))
    story.append(Spacer(1, 1*mm))

    half = len(chinese) // 2
    t_data_c1 = [["MATRICULE", "NOM & PRÉNOM", "FONCTION"]]
    for w in chinese[:half]:
        t_data_c1.append([w['mat'], f"{w['nom']} {w['prenom']}"[:19], w['fonction'][:22]])
    tc1 = Table(t_data_c1, colWidths=[65, 115, 90])
    tc1.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 5.8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0.7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.7),
    ]))

    t_data_c2 = [["MATRICULE", "NOM & PRÉNOM", "FONCTION"]]
    for w in chinese[half:]:
        t_data_c2.append([w['mat'], f"{w['nom']} {w['prenom']}"[:19], w['fonction'][:22]])
    tc2 = Table(t_data_c2, colWidths=[65, 115, 90])
    tc2.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#0f172a')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 5.8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0.7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.7),
    ]))

    t_double = Table([[tc1, tc2]], colWidths=[270, 270])
    t_double.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_double)
    story.append(Spacer(1, 2*mm))

    foot_data = [
        ["SUPERVISEUR HSE : Nouri Chahrour (0563765157)", "CHEF DE PROJET : Xie Xian", "ACCÈS CHANTIER STRICTEMENT CONTRÔLÉ"]
    ]
    t_foot = Table(foot_data, colWidths=[200, 170, 170])
    t_foot.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0f172a')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_foot)

    doc.build(story)
    print(f"Succès : PDF Chantier généré -> {pdf_path}")

    # --- HTML CHANTIER ---
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>AFFICHAGE CHANTIER — PERSONNEL AUTORISÉ SINYLON (SEPTEMBRE 2026)</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=JetBrains+Mono:wght@700&display=swap');
@page {{ size: A4 portrait; margin: 6mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Outfit', sans-serif; background: #e2e8f0; color: #0f172a; }}
.no-print {{
    background: #0f172a; color: #fff; padding: 12px; text-align: center;
    position: sticky; top: 0; z-index: 100;
}}
.no-print button {{
    background: #15803d; color: #fff; font-size: 15px; font-weight: 800;
    border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer;
}}
.poster-a4 {{
    width: 210mm; height: 297mm; background: #fff; margin: 15px auto;
    padding: 8mm 10mm; border: 2.5mm solid #0f172a; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;
}}
.p-header {{
    display: flex; justify-content: space-between; align-items: center;
    padding-bottom: 4px;
}}
.p-title {{
    text-align: center; margin: 3px 0;
}}
.p-title h1 {{
    font-size: 17px; font-weight: 900; text-transform: uppercase; color: #0f172a;
}}
.p-title h2 {{
    font-size: 12px; font-weight: 800; color: #1e3a8a;
}}
.status-pill {{
    background: #15803d; color: #fff; font-size: 10px; font-weight: 800;
    padding: 3px 14px; border-radius: 12px; display: inline-block; margin-top: 2px;
}}
.qr-row {{
    display: flex; gap: 14px; align-items: center; background: #f8fafc;
    border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 5px 10px; margin: 3px 0;
}}
.alg-box {{
    border: 2px solid #15803d; border-radius: 6px; padding: 4px 8px;
    background: #f0fdf4; margin: 3px 0;
}}
table.alg-table {{
    width: 100%; border-collapse: collapse; font-size: 8.5px;
}}
table.alg-table th {{
    background: #15803d; color: #fff; padding: 2.5px 6px; text-align: left;
}}
table.alg-table td {{
    border: 1px solid #86efac; padding: 2.5px 6px; font-weight: 700; background: #fff;
}}
.grid-2 {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 3px 0;
}}
table.worker-table {{
    width: 100%; border-collapse: collapse; font-size: 7.5px;
}}
table.worker-table th {{
    background: #0f172a; color: #fff; padding: 2px 4px; text-align: left; font-size: 7px;
}}
table.worker-table td {{
    border: 1px solid #cbd5e1; padding: 1.5px 4px;
}}
table.worker-table tr:nth-child(even) {{ background: #f8fafc; }}

.p-footer {{
    border-top: 1.5px solid #0f172a; padding-top: 4px; display: flex;
    justify-content: space-between; font-size: 8px; font-weight: 700;
}}
@media print {{
    body {{ background: #fff; }}
    .no-print {{ display: none !important; }}
    .poster-a4 {{ margin: 0; border: 2.5mm solid #000; box-shadow: none; height: 297mm; }}
}}
</style>
</head>
<body>
<div class="no-print">
    <button onclick="window.print()">🖨️ IMPRIMER L'AFFICHE CHANTIER A4</button>
</div>

<div class="poster-a4">
    <div>
        <div class="p-header">
            <div style="display:flex;align-items:center;gap:10px;">
                <img src="data:image/png;base64,{logo_b64}" style="height:44px;width:auto;" alt="Logo Sinylon">
                <div>
                    <div style="font-size:18px;font-weight:900;letter-spacing:1px;">SINYLON</div>
                    <div style="font-size:9px;color:#475569;font-weight:700;">PROJET K9 CKD0 STELLANTIS</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:15px;font-weight:900;color:#1e3a8a;">STELLANTIS ALGERIA</div>
                <div style="font-size:9px;font-weight:700;color:#64748b;">USINE D'ASSEMBLAGE TAFRAOUI</div>
            </div>
        </div>

        <div class="p-title">
            <h1>AFFICHAGE CHANTIER — PERSONNEL AUTORISÉ</h1>
            <h2>CONTRÔLE D'ACCÈS &amp; VÉRIFICATION SÉCURITÉ DES ÉQUIPES</h2>
            <div class="status-pill">
                🟢 VALIDITÉ DU 01/09/2026 AU 30/09/2026 (RENOUVELABLE CHAQUE MOIS DU 1ER AU 30)
            </div>
        </div>

        <div class="qr-row">
            <img src="data:image/png;base64,{qr_b64}" style="width:75px;height:75px;" alt="QR Code Chantier">
            <div style="font-size:10px;line-height:1.3;">
                <strong style="font-size:12px;color:#0f172a;display:block;margin-bottom:2px;">
                    📱 SCANNEZ CE QR CODE POUR CONTRÔLER LES {len(chinese)+len(algerians)} INTERVENANTS
                </strong>
                Chaque agent de sécurité ou superviseur HSE peut vérifier en direct sur son smartphone les photos, fiches et habilitations certifiées.
                <div style="font-family:monospace;color:#1e3a8a;font-size:8.5px;margin-top:3px;">
                    {chantier_url}
                </div>
            </div>
        </div>

        <!-- SECTION LOCAUX ALGÉRIENS -->
        <div class="alg-box">
            <div style="font-size:10px;font-weight:900;color:#15803d;margin-bottom:3px;display:flex;justify-content:space-between;">
                <span>🇩🇿 PERSONNEL LOCAL ALGÉRIEN AUTORISÉ (3 HOMMES &amp; 2 FEMMES) :</span>
                <span>TOUS CONFORMES HSE &amp; SÉCURITÉ</span>
            </div>
            <table class="alg-table">
                <thead>
                    <tr>
                        <th style="width:75px;">MATRICULE</th>
                        <th>NOM &amp; PRÉNOM</th>
                        <th>FONCTION OFFICIELLE</th>
                        <th style="width:85px;">CATÉGORIE</th>
                        <th style="width:75px;">STATUT</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f"<tr><td style='font-family:monospace;color:#1e3a8a;'>{a['mat']}</td><td><strong>{a['nom']}</strong> {a['prenom']}</td><td>{a['fonction']}</td><td>{'👨 Homme' if a['genre']=='Homme' else '👩 Femme'}</td><td style='color:#15803d;'>🟢 AUTORISÉ</td></tr>" for a in algerians])}
                </tbody>
            </table>
        </div>

        <!-- 54 CHINOIS SINYLON -->
        <div style="font-size:8.5px;font-weight:900;color:#0f172a;margin:3px 0 2px 0;">
            ÉQUIPE CHANTIER SINYLON ({len(chinese)} INTERVENANTS) :
        </div>
        <div class="grid-2">
            <table class="worker-table">
                <thead><tr><th>MATRICULE</th><th>NOM &amp; PRÉNOM</th><th>FONCTION</th></tr></thead>
                <tbody>
                    {"".join([f"<tr><td style='font-family:monospace;font-weight:bold;'>{w['mat']}</td><td><strong>{w['nom']}</strong> {w['prenom']}</td><td>{w['fonction']}</td></tr>" for w in chinese[:27]])}
                </tbody>
            </table>
            <table class="worker-table">
                <thead><tr><th>MATRICULE</th><th>NOM &amp; PRÉNOM</th><th>FONCTION</th></tr></thead>
                <tbody>
                    {"".join([f"<tr><td style='font-family:monospace;font-weight:bold;'>{w['mat']}</td><td><strong>{w['nom']}</strong> {w['prenom']}</td><td>{w['fonction']}</td></tr>" for w in chinese[27:]])}
                </tbody>
            </table>
        </div>
    </div>

    <div class="p-footer">
        <div>Superviseur HSE Sinylon : <strong>Nouri Chahrour (0563765157)</strong></div>
        <div>Chef de Projet Sinylon : <strong>Xie Xian</strong></div>
        <div>Accès Chantier : <strong>Badges &amp; EPI Obligatoires</strong></div>
    </div>
</div>
</body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Succès : HTML Chantier généré -> {html_path}")

def main():
    chinese, algerians = get_data()
    print(f"Chargement : {len(chinese)} intervenants Sinylon + {len(algerians)} locaux algériens (Total {len(chinese)+len(algerians)}).")
    
    # 1. Document Chef de la Sécurité (Une seule liste unifiée)
    generate_securite_doc(chinese, algerians)

    # 2. Affiche Chantier
    generate_chantier_doc(chinese, algerians)

    print("\n========================================================")
    print(f"Les listes officielles sont disponibles dans :")
    print(f"-> {OUTPUT_DIR}")
    print("========================================================\n")

if __name__ == '__main__':
    main()
