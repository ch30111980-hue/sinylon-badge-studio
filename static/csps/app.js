// ╔══════════════════════════════════════════╗
// ║    🌪️  SINYLON CSPS  — Chahrour Nouri       ║
// ║       Tous droits réservés © 2026        ║
// ╚══════════════════════════════════════════╝

// const { ipcRenderer } = require('electron');

// État de l'application
let currentPage = 'p1';
let currentPermitId = null; 
let allPermits = {}; 

const defaultData = {
    'permit-id': '',
    'company': '',
    'contact': '',
    'work-desc': '',
    'location': '',
    'ouvrage': '',
    'zone': '',
    'tel': '',
    'date-main': new Date().toISOString().split('T')[0],
    'time-start': '8h00',
    'time-end': '17h30',
    'moc-ref': '/',
    'chef-nom': '',
    'moex-nom': '',
    'coord-nom': '',
    'hse-nom': '',
    'receveur-nom': '',
};

let formData = { ...defaultData };

// Templates de pages
const templates = {
    p1: `
        <div class="fiat-header">
            <div class="permit-title">Permis de Travail de Sécurité Générale <br><small>(à afficher sur le site de travail)</small></div>
            <div class="fiat-logo-box">CSPS<span class="black-box">FIAT</span></div>
            <div style="border: 1px solid black; padding: 5px; font-size: 10px;">
                Identifiant du permis: <br>
                <strong id="val-permit-id"></strong>
            </div>
        </div>
        
        <div class="yellow-header">Brève description du travail</div>
        <div class="field-box" style="height: 40px; border: 1px solid black; margin-bottom: 5px;">
            <div class="field-value" id="val-work-desc"></div>
        </div>
        
        <div style="border: 1px solid black; padding: 5px; font-size: 9px; margin-bottom: 5px;">
            <strong>Entreprise Intervenante:</strong> <span id="val-company"></span> <br>
            <strong>Avant de commencer le travail, veuillez contacter:</strong> <strong id="val-contact"></strong>
            <span style="float:right;">Plan d'urgence du site attaché: [ ] Y [ ] N</span>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; border: 1px solid black; margin-bottom: 5px;">
            <div style="padding: 5px; border-right: 1px solid black;">
                <div class="field-label">Endroit de travail:</div>
                <div class="field-value" id="val-location"></div>
            </div>
            <div style="padding: 5px;">
                <div class="field-label">Equipement / Machinerie / Zone:</div>
                <div class="field-value">
                    <span id="val-ouvrage"></span> - <span id="val-zone"></span>
                </div>
            </div>
        </div>

        <div style="border: 1px solid black; padding: 5px; font-size: 9px; margin-bottom: 5px;">
            <strong>Ouvrage:</strong> <span id="val-ouvrage-2"></span> | 
            <strong>ZONE:</strong> <span id="val-zone-2"></span> | 
            <strong>Tél:</strong> <span id="val-tel"></span>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px; font-size: 8px;">
            <div style="border: 1px solid black; padding: 3px;">
                <div>Travail en hauteur <span style="float:right;">[<span id="check-a"> </span>] Y [ ] N <strong>A</strong></span></div>
                <div>Travail dans un espace confiné <span style="float:right;">[<span id="check-b-conf"> </span>] Y [ ] N <strong>B</strong></span></div>
                <div>Travail sur un système électrique <span style="float:right;">[<span id="check-c-elec"> </span>] Y [ ] N <strong>C</strong></span></div>
                <div>Ouvrir un système / ligne rupture <span style="float:right;">[<span id="check-d-rup"> </span>] Y [ ] N <strong>D</strong></span></div>
                <div>Autre travaux dangereux <span style="float:right;">[<span id="check-e-oth"> </span>] Y [ ] N <strong>E</strong></span></div>
            </div>
            <div style="border: 1px solid black; padding: 3px;">
                <div>Travail à chaud <span style="float:right;">[<span id="check-b-hot"> </span>] Y [ ] N <strong>B</strong></span></div>
                <div>Excavation <span style="float:right;">[<span id="check-d-exc"> </span>] Y [ ] N <strong>D</strong></span></div>
                <div>Travail sur équipement sous tension <span style="float:right;">[<span id="check-e-tens"> </span>] Y [ ] N <strong>E</strong></span></div>
                <div>Exposition / Cond. Atmos. <span style="float:right;">[<span id="check-f-atm"> </span>] Y [ ] N <strong>F</strong></span></div>
                <div style="background: #eee;">Déclaration de méthode requis <span style="float:right;">[<span id="check-g-meth"> </span>] Y [ ] N <strong>G</strong></span></div>
            </div>
        </div>

        <div style="border: 1px solid black; padding: 5px; font-size: 9px; margin-top: 5px;">
            Est ce travail, une modification couverte par MOC ? [<span id="check-moc"> </span>] Y [ ] N
            <span style="float:right;">MOC Ref. Nr. / Id. : <strong id="val-moc-ref"></strong></span>
        </div>

        <div class="yellow-header">validité du permis et signatures</div>
        <table class="table-fiat">
            <tr>
                <th>Date du permis</th>
                <th>heure de début</th>
                <th>heure de fin</th>
            </tr>
            <tr>
                <td id="val-date-main"></td>
                <td id="val-time-start"></td>
                <td id="val-time-end"></td>
            </tr>
        </table>

        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 5px; margin-top: 10px;">
            <div class="field-box" style="border: 1px solid black; height: 60px; position: relative;">
                <div class="field-label" style="background:#dee2e6;">Chef de Projet Entreprise</div>
                <div style="text-align:center; font-weight:bold; margin-top:2px; font-size: 10px;" id="val-chef-nom"></div>
                <div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #1e3a8a; font-size: 13px; transform: rotate(-3deg); text-align: center; margin-top: 1px; line-height: 1;" id="sig-chef-nom"></div>
            </div>
            <div class="field-box" style="border: 1px solid black; height: 60px; position: relative;">
                <div class="field-label" style="background:#dee2e6;">MOEX - Ingénieur de Suivi</div>
                <div style="text-align:center; font-weight:bold; margin-top:2px; font-size: 10px;" id="val-moex-nom"></div>
                <div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #1e3a8a; font-size: 13px; transform: rotate(-3deg); text-align: center; margin-top: 1px; line-height: 1;" id="sig-moex-nom"></div>
            </div>
            <div class="field-box" style="border: 1px solid black; height: 60px; position: relative;">
                <div class="field-label" style="background:#dee2e6;">Coordonnateur CSPS</div>
                <div style="text-align:center; font-weight:bold; margin-top:2px; font-size: 10px;" id="val-coord-nom"></div>
                <div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #1e3a8a; font-size: 13px; transform: rotate(-3deg); text-align: center; margin-top: 1px; line-height: 1;" id="sig-coord-nom"></div>
            </div>
            <div class="field-box" style="border: 1px solid black; height: 60px; position: relative;">
                <div class="field-label" style="background:#dee2e6;">HSE Entreprise</div>
                <div style="text-align:center; font-weight:bold; margin-top:2px; font-size: 10px;" id="val-hse-nom"></div>
                <div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #1e3a8a; font-size: 13px; transform: rotate(-3deg); text-align: center; margin-top: 1px; line-height: 1;" id="sig-hse-nom"></div>
            </div>
            <div class="field-box" style="border: 1px solid black; height: 60px; position: relative;">
                <div class="field-label" style="background:#dee2e6;">Receveur du permis</div>
                <div style="text-align:center; font-weight:bold; margin-top:2px; font-size: 10px;" id="val-receveur-nom"></div>
                <div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #1e3a8a; font-size: 13px; transform: rotate(-3deg); text-align: center; margin-top: 1px; line-height: 1;" id="sig-receveur-nom"></div>
            </div>
        </div>

        <div class="yellow-header">Permit Hand-Back <small>(renvoyer à l'emetteur du permis après signature)</small></div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; border: 1px solid black; font-size: 8px; padding: 5px;">
            <div>
                Etat de travail: <br>
                [<span id="back-acheve"> </span>] Achevé <br>
                [ ] Inachevé (veuillez spécifier ci-dessous)
            </div>
            <div>
                Etat de la surface/installation/équipement: <br>
                [<span id="back-pret"> </span>] Pret pour l'opération normale <br>
                [ ] Pas pret (veuillez spécifier ci-dessous)
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px; border: 1px solid black; border-top: none;">
            <div style="border-right: 1px solid black; height: 30px; font-size: 7px; padding: 2px;">Receveur du permis (Nom et signature)</div>
            <div style="height: 30px; font-size: 7px; padding: 2px;">MOEX - Ingénieur de Suivi</div>
            <div style="border-right: 1px solid black; height: 30px; font-size: 7px; padding: 2px;">Chef de Projet Entreprise</div>
            <div style="height: 30px; font-size: 7px; padding: 2px;">HSE Entreprise</div>
        </div>
        <div style="position: absolute; bottom: 20px; width: calc(100% - 20mm); font-size: 10px; text-align: right;">Page 1/2</div>
    `,
    p2: `
        <div class="fiat-header">
            <div class="permit-title">Permis de Travail de Sécurité Générale</div>
            <div class="fiat-logo-box">CSPS<span class="black-box">FIAT</span></div>
        </div>
        <div class="yellow-header">REVALIDATION DU PERMIS</div>
        <table class="table-fiat" style="font-size: 8px;">
            <tr>
                <th rowspan="2">JOUR</th>
                <th rowspan="2">DATE</th>
                <th colspan="3">MOEX - Ingénieur de Suivi</th>
                <th colspan="3">Responsable d'exécution</th>
            </tr>
            <tr>
                <th>Nom</th><th>Fonction</th><th>Signature</th>
                <th>Nom</th><th>Fonction</th><th>Signature</th>
            </tr>
            ${Array(6).fill(0).map((_, i) => `<tr><td style="height:25px;">${i+2}</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>`).join('')}
        </table>

        <div class="yellow-header" style="margin-top: 20px;">REVALIDATION DU PERMIS PAR CSPS</div>
        <table class="table-fiat" style="font-size: 8px;">
            <tr>
                <th>JOUR</th>
                <th>DATE</th>
                <th>Nom</th>
                <th>Fonction</th>
                <th>Signature</th>
            </tr>
            ${Array(6).fill(0).map((_, i) => `<tr><td style="height:25px;">${i+2}</td><td></td><td></td><td></td><td></td></tr>`).join('')}
        </table>
        <div style="position: absolute; bottom: 20px; width: calc(100% - 20mm); font-size: 10px; text-align: right;">Page 2/2</div>
    `,
    annexeA: `
        <div class="border-annexe-a" style="height: 100%; padding: 30px; position: relative; font-size: 14px; line-height: 1.6; color: black; background: white;">
            <div class="annexe-tag" style="width: 70px; height: 70px; font-size: 45px;">A</div>
            <div class="fiat-header" style="margin-left: 90px; border-bottom: 5px solid var(--csps-blue); padding-bottom: 20px;">
                <div class="permit-title" style="font-size: 32px;">Travail en hauteur</div>
                <div class="fiat-logo-box" style="font-size: 42px;">CSPS<span class="black-box">FIAT</span></div>
                <div style="border: 2px solid black; padding: 10px; font-size: 12px; min-width: 180px; background: white; text-align: center;">Identifiant du permis: <br><strong id="val-permit-id-a" style="font-size: 20px;"></strong></div>
            </div>
            
            <p style="text-align: center; font-weight: bold; margin: 25px 0; font-size: 16px; text-transform: uppercase; text-decoration: underline;">Cette liste de vérification doit être toujours accompagnée par le permis de travail de sécurité générale</p>
            
            <div style="border: 3px solid black; padding: 20px; margin-bottom: 25px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px;">
                    <div style="border-right: 2px solid #000; padding-right: 25px;">
                        <strong style="font-size: 16px;">Usage de (si "oui" continuer à droite):</strong><br>
                        - Echaffaudage fixe <span style="float:right;">[<span id="check-a-fixe"> </span>] .Y .N</span><br>
                        - Echaffaudage mobile <span style="float:right;">[<span id="check-a-mob"> </span>] .Y .N</span><br>
                        - Elevateur plateforme <span style="float:right;">[<span id="check-a-elev"> </span>] .Y .N</span><br>
                        - Echelle <span style="float:right;">[<span id="check-a-ech"> </span>] Y N</span><br>
                        - Equipement arrêt chute <span style="float:right;">[<span id="check-a-arret"> </span>] Y .N</span>
                    </div>
                    <div style="font-size: 14px;">
                        • Approuvé par personnel qualifié <span style="float:right;">[.Y] [.N]</span><br>
                        • Opérateur entraîné <span style="float:right;">[.Y] [.N]</span><br>
                        • Port du harnais vérifié <span style="float:right;">[.Y] [.N]</span><br>
                        • Order given in written <span style="float:right;">[.Y] [.N]</span><br>
                        • Danger minimum <span style="float:right;">[ Y] [ N]</span>
                    </div>
                </div>
            </div>

            <div class="yellow-header" style="background:#b0c4de; border: 3px solid var(--csps-blue); color: black; font-size: 18px; padding: 10px;">TRAVAIL SUR TOIT <span style="float:right;">[.Y] [.N]</span></div>
            <div style="border: 3px solid var(--csps-blue); padding: 20px; margin-bottom: 25px;">
                Capacité de Charge suffisante ? [<span id="check-a-charge"> </span>] .Y .N<br>
                Toiture fragile à proximité ? [<span id="check-a-frag"> </span>] .Y .N <span style="float:right;">Coordonné fermé [<span id="check-a-coord"> </span>] .Y .N</span><br>
                Protection de bord existante ? [<span id="check-a-bord"> </span>] .Y .N<br>
                Mesures : ____________________________________________________________________
            </div>

            <div class="yellow-header" style="background:#b0c4de; font-size:18px; padding:10px;">CONDITIONS AMBIANTES</div>
            <table class="table-fiat" style="font-size: 16px; margin-top: 15px;">
                <tr>
                    <td style="padding: 15px;">Visibilité: Claire[Y] Amoindrit[.Y] Sombre[Y] Obscure[.Y]</td>
                    <td style="padding: 15px;">Pluie: Aucune[Y] Légère[.Y] Forte[.Y]</td>
                </tr>
                <tr>
                    <td style="padding: 15px;">Surface: Sec[Y] Mouillé[.Y] Glissante[.Y]</td>
                    <td style="padding: 15px;">Vent: Aucun[Y] Léger[.Y] Fort[.Y]</td>
                </tr>
            </table>

            <div style="border:4px solid black; padding:20px; margin-top:30px; font-weight: bold; background: #fffde7; font-size: 16px;">
                MESURES OBLIGATOIRES: Porter Casques anti-choc et Ceinture de Sécurité
            </div>

            <div style="margin-top: 40px; display: grid; grid-template-columns: 1.5fr 1.5fr 1fr; gap: 30px;">
                <div class="field-box" style="border: 2px solid black; height: 80px; position: relative;"><div class="field-label" style="background:#b0c4de; padding: 8px;">CHEF DE PROJET</div><div style="text-align:center; font-weight: bold; font-size: 13px; padding-top: 2px;" id="val-chef-nom-a"></div><div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #1e3a8a; font-size: 15px; transform: rotate(-3deg); text-align: center; margin-top: 2px; line-height: 1;" id="sig-chef-nom-a"></div></div>
                <div class="field-box" style="border: 2px solid black; height: 80px; position: relative;"><div class="field-label" style="background:#b0c4de; padding: 8px;">HSE ENTREPRISE</div><div style="text-align:center; font-weight: bold; font-size: 13px; padding-top: 2px;" id="val-hse-nom-a"></div><div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #1e3a8a; font-size: 15px; transform: rotate(-3deg); text-align: center; margin-top: 2px; line-height: 1;" id="sig-hse-nom-a"></div></div>
                <div style="font-size:16px; padding-top: 20px;">Date: ___________<br>Heure: ___________</div>
            </div>
        </div>
    `,
    annexeB: `
        <div class="border-annexe-b" style="height: 100%; padding: 30px; position: relative; font-size: 14px; line-height: 1.6; color: black; background: white;">
            <div class="annexe-tag" style="width: 70px; height: 70px; font-size: 45px; background: var(--csps-red);">B</div>
            <div class="fiat-header" style="margin-left: 90px; border-bottom: 5px solid var(--csps-red); padding-bottom: 20px;">
                <div class="permit-title" style="font-size: 32px; color: var(--csps-red);">Travail chaud</div>
                <div class="fiat-logo-box" style="font-size: 42px;">CSPS<span class="black-box">FIAT</span></div>
                <div style="border: 2px solid black; padding: 10px; font-size: 12px; min-width: 180px; background: white; text-align: center;">Permit Identifier: <br><strong id="val-permit-id-b" style="font-size: 20px;"></strong></div>
            </div>
            
            <p style="text-align: center; font-weight: bold; margin: 25px 0; font-size: 16px; text-transform: uppercase; text-decoration: underline;">La liste de vérification doit être toujours accompagnée par le permis de travail de sécurité générale</p>
            
            <div style="border: 3px solid var(--csps-red); padding: 20px; margin-bottom: 25px;">
                <div style="display:grid; grid-template-rows: auto; gap: 10px; font-size: 14px;">
                    <div>• Produits inflammables dégagés à 10 m (min. 10 m) <span style="float:right;">[ Y] [.N]</span></div>
                    <div>• Débris, poussière et saleté enlevés de la zone <span style="float:right;">[ Y] [.N]</span></div>
                    <div>• Bâches ignifugées si déplacement impossible <span style="float:right;">[ Y] [.N]</span></div>
                    <div>• Fermeture des vannes, égouts et couvercles <span style="float:right;">[.Y] [ N]</span></div>
                    <div>• Ventilation suffisante (naturelle / technique) <span style="float:right;">[.Y] [ N]</span></div>
                    <div>• Appareils électriques et câbles protégés <span style="float:right;">[.Y] [ N]</span></div>
                    <div>• Surveillance Gaz nécessaire avant l'entame <span style="float:right;">[.Y] [ N]</span></div>
                </div>
            </div>

            <div class="yellow-header" style="background: var(--csps-red); color: white; font-size: 18px; padding: 10px;">ÉQUIPEMENT LUTTE ANTI-FEU</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; border: 3px solid black; padding: 25px; margin-bottom: 25px;">
                <div>
                    <strong>Extincteur:</strong> Water[Y] Poudre[Y] CO2[Y]<br>
                    <strong>Protection:</strong> Couvertures [Y] Gourde [Y]<br>
                    <strong>Présence:</strong> Surveillant [Y] Instruction [Y]
                </div>
                <div style="border-left: 2px solid black; padding-left: 25px; font-size: 14px; font-style: italic;">
                    Le surveillant d'incendie doit être présent durant le travail à chaud et 30 minutes après.
                </div>
            </div>

            <div style="border: 3px solid black; padding: 20px; margin-bottom: 25px; background: #fffde7; border-left: 15px solid var(--csps-red);">
                <strong>Urgence :</strong> Alarme la plus proche : <strong style="font-size: 22px;">BLOC SÉCURITÉ</strong><br>
                Mise hors service des détecteurs [<span id="check-b-det"> </span>] .Y .N <br>
                Notification Dept Incendie [.Y] [.N] | Notification Assurance [.Y] [.N]
            </div>

            <div style="margin-top: 40px; display: grid; grid-template-columns: 1.5fr 1.5fr 1fr; gap: 30px;">
                <div class="field-box" style="border: 2px solid black; height: 80px; position: relative;"><div class="field-label" style="background:#f87171; color:white; padding: 8px;">CHEF DE PROJET</div><div style="text-align:center; font-weight: bold; font-size: 13px; padding-top: 2px;" id="val-chef-nom-b"></div><div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #991b1b; font-size: 15px; transform: rotate(-3deg); text-align: center; margin-top: 2px; line-height: 1;" id="sig-chef-nom-b"></div></div>
                <div class="field-box" style="border: 2px solid black; height: 80px; position: relative;"><div class="field-label" style="background:#f87171; color:white; padding: 8px;">HSE ENTREPRISE</div><div style="text-align:center; font-weight: bold; font-size: 13px; padding-top: 2px;" id="val-hse-nom-b"></div><div style="font-family: 'Dancing Script', 'Snell Roundhand', 'Brush Script MT', 'Lucida Handwriting', cursive; color: #991b1b; font-size: 15px; transform: rotate(-3deg); text-align: center; margin-top: 2px; line-height: 1;" id="sig-hse-nom-b"></div></div>
                <div style="font-size:16px; padding-top: 20px;">Date: ___________<br>Heure: ___________</div>
            </div>
        </div>
    `
};

// Fonctions de navigation
function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
}

function switchPage(page) {
    currentPage = page;
    document.querySelectorAll('.page-btn').forEach(btn => btn.classList.remove('active'));
    if(page === 'p1') document.getElementById('btn-p1').classList.add('active');
    if(page === 'p2') document.getElementById('btn-p2').classList.add('active');
    if(page === 'annexeA') document.getElementById('btn-annA').classList.add('active');
    if(page === 'annexeB') document.getElementById('btn-annB').classList.add('active');
    
    renderPage();
}

function renderPage() {
    const container = document.getElementById('page-content');
    container.innerHTML = templates[currentPage];
    updateValues();
    updateCheckboxes();
}

let saveTimeout = null;
function debouncedSave() {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        saveToStorage();
    }, 500);
}

function updateValues() {
    for (const [key, value] of Object.entries(formData)) {
        const el = document.getElementById(`val-${key}`);
        if (el) el.textContent = value;
        const elA = document.getElementById(`val-${key}-a`);
        if (elA) elA.textContent = value;
        const elB = document.getElementById(`val-${key}-b`);
        if (elB) elB.textContent = value;
        const el2 = document.getElementById(`val-${key}-2`);
        if (el2) el2.textContent = value;
        
        // Mettre à jour les signatures cursives
        const sig = document.getElementById(`sig-${key}`);
        if (sig) sig.textContent = value;
        const sigA = document.getElementById(`sig-${key}-a`);
        if (sigA) sigA.textContent = value;
        const sigB = document.getElementById(`sig-${key}-b`);
        if (sigB) sigB.textContent = value;
    }
}

function updateCheckboxes() {
    document.querySelectorAll('input[type="checkbox"]').forEach(check => {
        const checkId = check.getAttribute('data-check');
        const displayEl = document.getElementById(checkId);
        if (displayEl) {
            displayEl.textContent = check.checked ? 'X' : ' ';
        }
    });
}

function saveToStorage() {
    // Si on a un identifiant, on l'utilise pour stocker dans la liste globale
    const id = formData['permit-id'] || 'Sans-ID-' + Date.now();
    allPermits[id] = { ...formData, lastModified: Date.now() };
    localStorage.setItem('csps_all_permits', JSON.stringify(allPermits));
    localStorage.setItem('csps_last_permit_id', id);
    renderPermitList();
}

function loadFromStorage() {
    const saved = localStorage.getItem('csps_all_permits');
    if (saved) {
        allPermits = JSON.parse(saved);
        const lastId = localStorage.getItem('csps_last_permit_id');
        if (lastId && allPermits[lastId]) {
            loadPermit(lastId);
        } else {
            renderPermitList();
        }
    } else {
        createNewPermit();
    }
}

function renderPermitList() {
    const listEl = document.getElementById('permit-list');
    if (!listEl) return;
    
    listEl.innerHTML = '';
    
    // Trier par date de modification (plus récent en haut)
    const sortedIds = Object.keys(allPermits).sort((a, b) => 
        (allPermits[b].lastModified || 0) - (allPermits[a].lastModified || 0)
    );

    sortedIds.forEach(id => {
        const data = allPermits[id];
        const item = document.createElement('div');
        item.className = `permit-item ${id === currentPermitId ? 'active' : ''}`;
        item.style = `
            padding: 8px; 
            background: ${id === currentPermitId ? '#1e293b' : '#334155'}; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 11px; 
            color: white; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            border: 1px solid ${id === currentPermitId ? '#3b82f6' : 'transparent'};
        `;
        
        item.innerHTML = `
            <div onclick="loadPermit('${id}')" style="flex-grow:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                <strong>${id}</strong><br>
                <small style="color:#94a3b8">${data.company || 'Sans entreprise'}</small>
            </div>
            <button onclick="deletePermit('${id}')" style="background:none; border:none; color:#ef4444; cursor:pointer; padding:5px;">✕</button>
        `;
        listEl.appendChild(item);
    });

    // Mise à jour du compteur SINYLON CSPS
    const countEl = document.getElementById('total-permits-count');
    if (countEl) countEl.innerText = Object.keys(allPermits).length;
}

function loadPermit(id) {
    if (!allPermits[id]) return;
    currentPermitId = id;
    formData = { ...allPermits[id] };
    
    // Mettre à jour les inputs
    for (const [key, value] of Object.entries(formData)) {
        const input = document.querySelector(`[data-field="${key}"]`);
        if (input) input.value = value;
    }
    
    // Mettre à jour les checkboxes
    document.querySelectorAll('input[data-check]').forEach(check => {
        const checkId = check.getAttribute('data-check');
        if (formData.checkboxes && formData.checkboxes[checkId] !== undefined) {
            check.checked = formData.checkboxes[checkId];
        } else {
            check.checked = false;
        }
    });

    updateCheckboxes();
    renderPage();
}

function createNewPermit() {
    currentPermitId = 'Permis-' + Date.now();
    formData = { ...defaultData, 'permit-id': '' };
    
    // Vider les inputs
    document.querySelectorAll('input[data-field], textarea[data-field]').forEach(input => {
        input.value = '';
    });
    // Vider les checkboxes
    document.querySelectorAll('input[data-check]').forEach(check => {
        check.checked = false;
    });
    
    renderPage();
    renderPermitList();
}

function deletePermit(id) {
    if (confirm(`Supprimer le permis ${id} ?`)) {
        delete allPermits[id];
        if (currentPermitId === id) {
            createNewPermit();
        } else {
            saveToStorage();
        }
    }
}

function resetForm() {
    if(confirm("Voulez-vous vraiment effacer tout le formulaire ?")) {
        localStorage.removeItem('fiat_form_data');
        location.reload();
    }
}

document.querySelectorAll('input[data-field], textarea[data-field]').forEach(input => {
    input.addEventListener('input', (e) => {
        const field = e.target.getAttribute('data-field');
        formData[field] = e.target.value;
        updateValues();
        debouncedSave();
    });
});

document.querySelectorAll('input[data-check]').forEach(check => {
    check.addEventListener('change', (e) => {
        if (!formData.checkboxes) formData.checkboxes = {};
        const checkId = e.target.getAttribute('data-check');
        formData.checkboxes[checkId] = e.target.checked;
        
        updateCheckboxes();
        saveToStorage();
    });
});

// Retrait de la dépendance Electron pour la version Web
// const { ipcRenderer } = require('electron');

// ... (Le reste du code reste identique jusqu'aux événements de boutons)

document.getElementById('btn-new-permit').addEventListener('click', createNewPermit);

document.getElementById('btn-save').addEventListener('click', () => {
    // Sur le Web, la sauvegarde PDF se fait via l'impression
    window.print();
});

document.getElementById('btn-print').addEventListener('click', () => {
    window.print();
});

window.onload = () => {
    loadFromStorage();
    switchPage('p1');
};
