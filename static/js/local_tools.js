let ipcRenderer = {
    send: (channel, ...args) => console.log(`[Mock IPC Send] ${channel}`, args),
    on: (channel, listener) => console.log(`[Mock IPC On] ${channel} registered`)
};
try {
    const electron = require('electron');
    ipcRenderer = electron.ipcRenderer;
} catch (e) {
    console.warn("Running in standard browser, electron ipcRenderer mocked");
}

// État de l'application
let currentPage = 'consignation';
let currentPermitId = null; 
let allPermits = {}; 
let activeTab = 'form-tab';

// Données par défaut étendues pour supporter tous les nouveaux permis et fiches
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
    'time-start': '08h00',
    'time-end': '17h30',
    'chef-nom': '',
    'moex-nom': '',
    'coord-nom': '',
    'hse-nom': '',
    'receveur-nom': '',
    
    // Annexe C (Confined space)
    'c-ventilation': false,
    'c-mesure-gaz': false,
    'c-harnais': false,
    'c-surveillant': false,
    'c-radio': false,
    'c-eclairage': false,
    
    // Annexe D (Excavation)
    'd-blindage': false,
    'd-balisage': false,
    'd-reseaux': false,
    'd-echelle': false,
    'd-sol-stable': false,
    'd-chef-nom': '',
    'd-coord-nom': '',
    'd-hse-nom': '',
    'd-receveur-nom': '',
    
    // Fiche Engins (Revision B)
    'engin-matricule': '',
    'engin-type': '',
    'engin-caces': '',
    'e-conformite': false,
    'e-ct': false,
    'e-grise': false,
    'e-entretien': false,
    'engin-obs': '',
    
    // HSE Checklist conformity states (C = Conforme, NC = Non Conforme)
    'hse-inspector': '',
    'hse-site-rep': '',
    'hse-period': '',
};

let formData = { ...defaultData };
let recognition = null;
let html5QrScanner = null;

// Initialisation de la reconnaissance vocale
if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'fr-FR';
}

// --------------------- TEMPLATES DES DOCUMENTS A4 ---------------------
function updateSidebarVisibility() {
    // Masquer toutes les sections spécifiques de saisie
    document.querySelectorAll('.form-section-specific').forEach(sec => {
        sec.style.display = 'none';
    });
    
    // Afficher uniquement la section liée au type de permis actif
    if (currentPage === 'annexeA') {
        document.getElementById('sec-hauteur').style.display = 'block';
    } else if (currentPage === 'annexeB') {
        document.getElementById('sec-chaud').style.display = 'block';
    } else if (currentPage === 'annexeC') {
        document.getElementById('sec-confine').style.display = 'block';
    } else if (currentPage.startsWith('annexeD')) {
        document.getElementById('sec-excavation').style.display = 'block';
    } else if (currentPage.startsWith('engin')) {
        document.getElementById('sec-engin').style.display = 'block';
    } else if (currentPage.startsWith('hse')) {
        document.getElementById('sec-hse').style.display = 'block';
    }
}

// --------------------- NAVIGATION & TABS ---------------------
function switchTab(tabId) {
    activeTab = tabId;
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    if (tabId === 'form-tab') {
        document.getElementById('tab-form').classList.add('active');
    } else {
        document.getElementById('tab-ai').classList.add('active');
    }
}

function switchPage(page) {
    currentPage = page;
    document.querySelectorAll('.page-btn').forEach(btn => btn.classList.remove('active'));
    
    const pageButtonId = {
        p1: 'btn-p1',
        p2: 'btn-p2',
        annexeA: 'btn-annA',
        annexeB: 'btn-annB',
        annexeC: 'btn-annC',
        annexeD_p1: 'btn-annD-p1',
        annexeD_p2: 'btn-annD-p2',
        engin_p1: 'btn-engin-p1',
        engin_p2: 'btn-engin-p2',
        hse_p1: 'btn-hse-p1',
        hse_p2: 'btn-hse-p2',
        consignation: 'btn-consignation',
        autorisation_mat: 'btn-aut-mat',
        entree_vehicule: 'btn-ent-veh',
        consignation: 'btn-consignation',
        autorisation_mat: 'btn-aut-mat',
        entree_vehicule: 'btn-ent-veh'
    }[page];
    
    if (document.getElementById(pageButtonId)) {
        document.getElementById(pageButtonId).classList.add('active');
    }
    
    updateSidebarVisibility();
    renderPage();
}

async function renderPage() {
    const container = document.getElementById('page-content');
    container.innerHTML = '<div style="padding:20px;text-align:center;">Chargement du modèle... <i class="fas fa-spinner fa-spin"></i></div>';
    
    try {
        const response = await fetch('/permis/api/template/' + currentPage);
        if (!response.ok) throw new Error('Template non trouvé');
        const html = await response.text();
        container.innerHTML = html;
        
        updateValues();
        updateCheckboxes();
        generateQRCodes();
        setupContentEditableFields();     
        setupClickableCheckboxes();       
        setupInteractivePreviewFields();  
        setupInteractivePreviewCheckboxes(); 
    } catch (err) {
        console.error("Erreur chargement template :", err);
        container.innerHTML = '<div style="color:red;padding:20px;">Erreur lors du chargement du modèle.</div>';
    }
}

function updateValues() {
    // Restaurer les valeurs annexes d abord
    if (formData.annexData) {
        for (const [id, value] of Object.entries(formData.annexData)) {
            const el = document.getElementById(id);
            if (el && el.hasAttribute("contenteditable")) {
                el.innerHTML = value;
            }
        }
    }
    
    // Mettre à jour les champs de texte (textContent ou innerText selon contenteditable)
    for (const [key, value] of Object.entries(formData)) {
        const updateEl = (el) => {
            if (!el) return;
            // Ne pas écraser si l'utilisateur est en train de taper
            if (document.activeElement === el) return;
            if (el.getAttribute('contenteditable') === 'true') {
                // Ne mettre à jour que si le contenu est différent (pour ne pas perturber le curseur)
                if (el.textContent !== (value || '')) {
                    el.textContent = value || '';
                }
            } else {
                el.textContent = value || '';
            }
        };
        
        updateEl(document.getElementById(`val-${key}`));
        updateEl(document.getElementById(`val-${key}-a`));
        updateEl(document.getElementById(`val-${key}-b`));
        updateEl(document.getElementById(`val-${key}-c`));
        updateEl(document.getElementById(`val-${key}-d`));
        updateEl(document.getElementById(`val-${key}-d-start`));
        updateEl(document.getElementById(`val-${key}-d-end`));
        updateEl(document.getElementById(`val-${key}-d-desc`));
        updateEl(document.getElementById(`val-${key}-d-ref`));
        updateEl(document.getElementById(`val-${key}-d-app`));
        updateEl(document.getElementById(`val-${key}-d-aut`));
        updateEl(document.getElementById(`val-${key}-d-aut2`));
        updateEl(document.getElementById(`val-${key}-d-acc`));
        updateEl(document.getElementById(`val-${key}-d-acc2`));
        updateEl(document.getElementById(`val-${key}-d-clos`));
        updateEl(document.getElementById(`val-${key}-e`));
        updateEl(document.getElementById(`val-${key}-e2`));
        updateEl(document.getElementById(`val-${key}-h1`));
        updateEl(document.getElementById(`val-${key}-h2`));
        updateEl(document.getElementById(`val-${key}-hse`));
        updateEl(document.getElementById(`val-${key}-hse-sign`));
        updateEl(document.getElementById(`val-${key}-2`));
    }
    saveToStorage();
}

// ========== FONCTIONS D'ÉDITION DIRECTE (contenteditable) ==========

function setupContentEditableFields() {
    document.querySelectorAll('[contenteditable="true"][data-field]').forEach(el => {
        if (el._ceSetup) return;
        el._ceSetup = true;
        
        // Charger la valeur depuis formData
        const fieldKey = el.getAttribute('data-field');
        const val = formData[fieldKey];
        if (val && el.textContent !== val) {
            el.textContent = val;
        }
        
        // Sauvegarder quand l'utilisateur tape
        el.addEventListener('input', () => {
            const newVal = el.textContent;
            formData[fieldKey] = newVal;
            
            // Mettre à jour les doublons (val-XXX-2, etc.)
            const dup2 = document.getElementById(`val-${fieldKey}-2`);
            if (dup2 && document.activeElement !== dup2) dup2.textContent = newVal;
            
            saveToStorage();
        });
        
        // Empecher le retour à la ligne sur les champs non-textarea
        el.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && el.tagName !== 'TEXTAREA') {
                e.preventDefault();
                el.blur();
            }
            if (e.key === 'Escape') el.blur();
        });
    });
}

function setupClickableCheckboxes() {
    document.querySelectorAll('.check-box-click[data-check]').forEach(cb => {
        if (cb._cbSetup) return;
        cb._cbSetup = true;
        
        const checkId = cb.getAttribute('data-check');
        
        // Restaurer l'état depuis formData
        if (formData.checkboxes && formData.checkboxes[checkId]) {
            cb.classList.add('checked');
        }
        
        cb.addEventListener('click', (e) => {
            e.stopPropagation();
            const isChecked = cb.classList.toggle('checked');
            
            // Sauvegarder dans formData
            if (!formData.checkboxes) formData.checkboxes = {};
            formData.checkboxes[checkId] = isChecked;
            
            // Aussi mettre à jour le checkbox de la sidebar
            const sidebarCb = document.querySelector(`input[data-check="${checkId}"]`);
            if (sidebarCb) sidebarCb.checked = isChecked;
            
            saveToStorage();
        });
    });
}

function updateCheckboxes() {

    // Mettre à jour l'état visuel sur le A4 à partir de l'état des cases à cocher
    document.querySelectorAll('input[type="checkbox"]').forEach(check => {
        const checkId = check.getAttribute('data-check');
        if (checkId) {
            const displayEl = document.getElementById(checkId);
            if (displayEl) {
                displayEl.textContent = check.checked ? 'X' : ' ';
            }
        }
        
        // Supporter aussi les data-field sur les checkboxes dans le formulaire
        const fieldName = check.getAttribute('data-field');
        if (fieldName) {
            if (fieldName === 'd-blindage') {
                const el1 = document.getElementById('check-d-blind');
                const el2 = document.getElementById('check-d-blind-2');
                if (el1) el1.textContent = check.checked ? 'X' : ' ';
                if (el2) el2.textContent = check.checked ? 'X' : ' ';
            } else if (fieldName === 'd-balisage') {
                const el = document.getElementById('check-d-balis');
                if (el) el.textContent = check.checked ? 'X' : ' ';
            } else {
                const fieldDisplayEl = document.getElementById(`check-${fieldName}`);
                if (fieldDisplayEl) {
                    fieldDisplayEl.textContent = check.checked ? 'X' : ' ';
                }
            }
        }
    });
}

// =================== EDITION DIRECTE SUR LE PERMIS ===================
// Un éditeur flottant apparaît directement sur le permis quand on clique

let activeInlineEditor = null;

function setupInteractivePreviewFields() {
    // Cibler les champs avec data-field ET les éléments val-*
    const allTargets = document.querySelectorAll('.interactive-preview-field, [id^="val-"]');
    
    allTargets.forEach(field => {
        // Obtenir la clé du champ : soit depuis data-field, soit depuis l'id "val-XXX"
        let dataField = field.getAttribute('data-field');
        
        if (!dataField) {
            const idAttr = field.getAttribute('id');
            if (idAttr && idAttr.startsWith('val-')) {
                const keyFromId = idAttr.replace(/^val-/, '');
                // Vérifier si cette clé existe dans formData (en gérant les suffixes -a, -b, etc.)
                const baseKey = keyFromId.replace(/-[a-z]$/, '').replace(/-[a-z0-9]+$/, '');
                if (formData.hasOwnProperty(keyFromId)) {
                    dataField = keyFromId;
                } else if (formData.hasOwnProperty(baseKey)) {
                    dataField = baseKey;
                }
            }
        }
        
        if (!dataField) return;
        
        // Éviter les doublons d'event listeners
        if (field._inlineEditorSetup) return;
        field._inlineEditorSetup = true;
        
        field.classList.add('editable-on-permit');
        field.setAttribute('title', '✏️ Cliquer pour modifier directement');
        
        field.addEventListener('click', (e) => {
            e.stopPropagation();
            openInlineEditor(field, dataField);
        });
    });
}

function openInlineEditor(targetEl, fieldKey) {
    // Fermer tout éditeur déjà ouvert
    closeInlineEditor();
    
    const currentValue = formData[fieldKey] || '';
    const rect = targetEl.getBoundingClientRect();
    const previewArea = document.querySelector('.preview-area');
    const previewRect = previewArea.getBoundingClientRect();
    
    // Créer le conteneur de l'éditeur flottant
    const editorContainer = document.createElement('div');
    editorContainer.id = 'inline-editor-popup';
    editorContainer.style.cssText = `
        position: fixed;
        z-index: 9999;
        background: #1e293b;
        border: 2px solid #3b82f6;
        border-radius: 10px;
        padding: 8px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,130,246,0.2);
        display: flex;
        flex-direction: column;
        gap: 6px;
        min-width: 220px;
        max-width: 350px;
        animation: editorFadeIn 0.15s ease-out;
    `;
    
    // Positionner en dessous du champ (ou au dessus si trop bas)
    let top = rect.bottom + 6;
    let left = rect.left;
    
    // S'assurer que le popup ne sort pas de l'écran
    if (top + 100 > window.innerHeight) top = rect.top - 110;
    if (left + 360 > window.innerWidth) left = window.innerWidth - 370;
    if (left < 10) left = 10;
    
    editorContainer.style.top = top + 'px';
    editorContainer.style.left = left + 'px';
    
    // Étiquette du champ
    const label = document.createElement('div');
    label.style.cssText = 'font-size: 12px; color: #94a3b8; font-weight: bold; letter-spacing: 0.5px; text-transform: uppercase;';
    label.textContent = '✏️ ' + (fieldKey.replace(/-/g, ' '));
    editorContainer.appendChild(label);
    
    // Input ou textarea selon la longueur du contenu
    const isLongField = ['work-desc', 'location', 'engin-obs'].includes(fieldKey);
    const inputEl = document.createElement(isLongField ? 'textarea' : 'input');
    inputEl.value = currentValue;
    inputEl.style.cssText = `
        background: rgba(0,0,0,0.4);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 6px;
        color: white;
        padding: 7px 10px;
        font-size: 15px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        outline: none;
        width: 100%;
        box-sizing: border-box;
        transition: border-color 0.2s;
    `;
    if (isLongField) {
        inputEl.rows = 3;
        inputEl.style.resize = 'vertical';
    }
    
    // Boutons d'action
    const btnRow = document.createElement('div');
    btnRow.style.cssText = 'display: flex; gap: 6px; justify-content: flex-end;';
    
    const btnMic = document.createElement('button');
    btnMic.innerHTML = '🎙️';
    btnMic.title = 'Dicter (voix)';
    btnMic.style.cssText = `
        background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 6px; color: white; padding: 5px 10px; cursor: pointer;
        font-size: 15px; transition: background 0.2s;
    `;
    btnMic.addEventListener('click', () => {
        startInlineVoice(inputEl, fieldKey);
    });
    
    const btnConfirm = document.createElement('button');
    btnConfirm.innerHTML = '✓ OK';
    btnConfirm.style.cssText = `
        background: #3b82f6; border: none; border-radius: 6px;
        color: white; padding: 5px 14px; cursor: pointer;
        font-size: 14px; font-weight: bold;
        box-shadow: 0 2px 6px rgba(59,130,246,0.4);
        transition: background 0.2s;
    `;
    btnConfirm.addEventListener('click', () => {
        applyInlineEdit(fieldKey, inputEl.value);
        closeInlineEditor();
    });
    
    const btnCancel = document.createElement('button');
    btnCancel.innerHTML = '✕';
    btnCancel.style.cssText = `
        background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3);
        border-radius: 6px; color: #f87171; padding: 5px 10px; cursor: pointer;
        font-size: 14px; transition: background 0.2s;
    `;
    btnCancel.addEventListener('click', closeInlineEditor);
    
    btnRow.appendChild(btnMic);
    btnRow.appendChild(btnCancel);
    btnRow.appendChild(btnConfirm);
    
    editorContainer.appendChild(inputEl);
    editorContainer.appendChild(btnRow);
    
    document.body.appendChild(editorContainer);
    activeInlineEditor = editorContainer;
    
    // Ajouter l'animation CSS si absente
    if (!document.getElementById('inline-editor-style')) {
        const style = document.createElement('style');
        style.id = 'inline-editor-style';
        style.textContent = `
            @keyframes editorFadeIn {
                from { opacity: 0; transform: translateY(-6px) scale(0.97); }
                to   { opacity: 1; transform: translateY(0) scale(1); }
            }
            .editable-on-permit {
                cursor: text !important;
                border-bottom: 1.5px dashed rgba(59,130,246,0.5) !important;
                transition: background 0.18s, border-color 0.18s !important;
                position: relative;
                min-width: 30px;
                min-height: 14px;
                display: inline-block;
            }
            .editable-on-permit:empty::before {
                content: '___';
                color: rgba(100,116,139,0.4);
                font-style: italic;
                font-size: 0.85em;
            }
            .editable-on-permit:hover {
                background: rgba(59,130,246,0.08) !important;
                border-bottom-color: #3b82f6 !important;
            }
            #inline-editor-popup input:focus,
            #inline-editor-popup textarea:focus {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 8px rgba(59,130,246,0.3);
            }
        `;
        document.head.appendChild(style);
    }
    
    // Focus immédiat et sélection du texte
    setTimeout(() => {
        inputEl.focus();
        inputEl.select();
    }, 50);
    
    // Confirmer avec Entrée (sauf pour textarea)
    if (!isLongField) {
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                applyInlineEdit(fieldKey, inputEl.value);
                closeInlineEditor();
            }
            if (e.key === 'Escape') closeInlineEditor();
        });
    }
    
    // Surligner le champ cible
    targetEl.style.outline = '2px solid #3b82f6';
    targetEl.style.outlineOffset = '2px';
    targetEl._wasHighlighted = true;
    
    // Fermer en cliquant ailleurs
    setTimeout(() => {
        document.addEventListener('click', handleOutsideClick, true);
    }, 100);
}

function handleOutsideClick(e) {
    if (activeInlineEditor && !activeInlineEditor.contains(e.target)) {
        closeInlineEditor();
    }
}

function closeInlineEditor() {
    if (activeInlineEditor) {
        activeInlineEditor.remove();
        activeInlineEditor = null;
    }
    // Retirer surlignage
    document.querySelectorAll('.editable-on-permit').forEach(el => {
        if (el._wasHighlighted) {
            el.style.outline = '';
            el.style.outlineOffset = '';
            el._wasHighlighted = false;
        }
    });
    document.removeEventListener('click', handleOutsideClick, true);
}

function applyInlineEdit(fieldKey, value) {
    // Mettre à jour formData
    formData[fieldKey] = value;
    
    // Mettre à jour l'input dans la sidebar pour rester synchro
    const sidebarInput = document.querySelector(`[data-field="${fieldKey}"]`);
    if (sidebarInput && sidebarInput.type !== 'checkbox') {
        sidebarInput.value = value;
    }
    
    // Mettre à jour l'affichage sur le permis (tous les val-)
    updateValues();
    
    // Petit flash vert pour confirmer
    setTimeout(() => {
        const updatedEl = document.getElementById(`val-${fieldKey}`) ||
                          document.querySelector(`[data-field="${fieldKey}"].interactive-preview-field`);
        if (updatedEl) {
            const origBg = updatedEl.style.background;
            updatedEl.style.background = 'rgba(16,185,129,0.25)';
            setTimeout(() => updatedEl.style.background = origBg, 800);
        }
    }, 50);
}

function startInlineVoice(inputEl, fieldKey) {
    if (!recognition) {
        alert("La reconnaissance vocale n'est pas supportée.");
        return;
    }
    recognition.onresult = (e) => {
        inputEl.value = e.results[0][0].transcript;
        inputEl.focus();
    };
    recognition.onend = () => {};
    recognition.onerror = () => {};
    recognition.start();
}


// Configurer les cases à cocher interactives (clic direct sur le permis)
function setupInteractivePreviewCheckboxes() {
    document.querySelectorAll('[id^="check-"]').forEach(span => {
        span.style.cursor = 'pointer';
        span.style.userSelect = 'none';
        span.title = 'Cliquer pour cocher/décocher';
        
        span.addEventListener('click', (e) => {
            e.stopPropagation();
            const spanId = e.currentTarget.id;
            let input = null;
            
            // Mappages spéciaux
            if (spanId === 'check-d-blind' || spanId === 'check-d-blind-2') {
                input = document.querySelector('input[data-field="d-blindage"]');
            } else if (spanId === 'check-d-balis') {
                input = document.querySelector('input[data-field="d-balisage"]');
            } else {
                input = document.querySelector(`input[data-check="${spanId}"]`);
                if (!input) {
                    const fieldName = spanId.replace(/^check-/, '');
                    input = document.querySelector(`input[data-field="${fieldName}"]`);
                }
            }
            
            if (input && input.type === 'checkbox') {
                input.checked = !input.checked;
                input.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Flash visuel sur la case
                span.style.color = input.checked ? '#10b981' : '#ef4444';
                setTimeout(() => span.style.color = '', 400);
            } else {
                // Si aucun input de sidebar trouvé, basculer directement le texte
                const isChecked = span.textContent.trim() === 'X';
                span.textContent = isChecked ? ' ' : 'X';
                span.style.color = !isChecked ? '#10b981' : '#ef4444';
                setTimeout(() => span.style.color = '', 400);
                
                // Sauvegarder dans formData
                const fieldName = spanId.replace(/^check-/, '');
                if (!formData.checkboxes) formData.checkboxes = {};
                formData.checkboxes[spanId] = !isChecked;
                saveToStorage();
            }
        });
    });
}


// --------------------- GESTION DU STORAGE & PERMIS ---------------------
function saveToStorage() {
    const newId = formData["permit-id"] || "Sans-ID-" + Date.now();
    
    // Si on a changé l ID du permis en cours, on supprime l ancien pour éviter les doublons
    if (currentPermitId && currentPermitId !== newId && allPermits[currentPermitId]) {
        delete allPermits[currentPermitId];
    }
    
    currentPermitId = newId;
    allPermits[newId] = { ...formData, lastModified: Date.now() };
    
    localStorage.setItem("csps_all_permits", JSON.stringify(allPermits));
    localStorage.setItem("csps_last_permit_id", newId);
    
    // Mettre à jour les QR Codes car l ID ou les données ont pu changer
    if (typeof generateQRCodes === "function") generateQRCodes();
    
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
        
        item.innerHTML = `
            <div class="permit-item-content" onclick="loadPermit('${id}')">
                <div class="permit-item-title">📄 ${id}</div>
                <div class="permit-item-subtitle">🏢 ${data.company || 'Sans entreprise'}</div>
            </div>
            <button class="permit-item-delete" onclick="deletePermit('${id}')" title="Supprimer">
                <i class="fa-solid fa-trash-can"></i>
            </button>
        `;
        listEl.appendChild(item);
    });
}

function loadPermit(id) {
    if (!allPermits[id]) return;
    currentPermitId = id;
    formData = { ...allPermits[id] };
    
    // Mettre à jour les inputs de saisie
    for (const [key, value] of Object.entries(formData)) {
        const input = document.querySelector(`[data-field="${key}"]`);
        if (input) {
            if (input.type === 'checkbox') {
                input.checked = value;
            } else {
                input.value = value || '';
            }
        }
    }
    
    // Mettre à jour les cases à cocher de danger
    document.querySelectorAll('input[data-check]').forEach(check => {
        const checkId = check.getAttribute('data-check');
        if (formData.checkboxes && formData.checkboxes[checkId] !== undefined) {
            check.checked = formData.checkboxes[checkId];
        } else {
            check.checked = false;
        }
    });

    updateCheckboxes();
}

function createNewPermit() {
    currentPermitId = 'Permis-' + Date.now();
    formData = { ...defaultData, 'permit-id': 'OR2-' + new Date().toLocaleDateString('fr-FR') };
    
    // Vider les inputs de saisie
    document.querySelectorAll('input[data-field], textarea[data-field]').forEach(input => {
        if (input.type === 'checkbox') {
            input.checked = false;
        } else {
            input.value = formData[input.getAttribute('data-field')] || '';
        }
    });
    // Vider les cases à cocher de danger
    document.querySelectorAll('input[data-check]').forEach(check => {
        check.checked = false;
    });
    
}

function deletePermit(id) {
    if (confirm(`Voulez-vous supprimer le permis ${id} ?`)) {
        delete allPermits[id];
        if (currentPermitId === id) {
            createNewPermit();
        } else {
            saveToStorage();
        }
    }
}

function resetForm() {
    if (confirm("Voulez-vous vraiment réinitialiser ce permis ?")) {
        formData = { ...defaultData };
        loadPermit(currentPermitId);
    }
}

// --------------------- RECONNAISSANCE VOCALE (DICTORIAL) ---------------------
function startSpeech(fieldId) {
    if (!recognition) {
        alert("La reconnaissance vocale n'est pas supportée par votre système.");
        return;
    }

    const input = document.querySelector(`[data-field="${fieldId}"]`);
    const button = event.currentTarget;
    
    if (button.classList.contains('listening')) {
        recognition.stop();
        return;
    }

    // Réinitialiser les boutons micro
    document.querySelectorAll('.mic-btn').forEach(b => b.classList.remove('listening'));
    button.classList.add('listening');

    recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (input) {
            if (input.tagName === 'TEXTAREA') {
                input.value = (input.value + " " + transcript).trim();
            } else {
                input.value = transcript;
            }
            // Déclencher l'event d'input pour mettre à jour l'état
            const event = new Event('input', { bubbles: true });
            input.dispatchEvent(event);
        }
    };

    recognition.onend = () => {
        button.classList.remove('listening');
    };

    recognition.onerror = () => {
        button.classList.remove('listening');
    };

    recognition.start();
}

// --------------------- GENERATEUR & SCANNER DE CODES QR ---------------------
function generateQRCodes() {
    // Synthétiser les données importantes du permis dans un bloc compact
    const qrPayload = {
        id: formData['permit-id'],
        comp: formData['company'],
        desc: formData['work-desc'].substring(0, 80),
        loc: formData['location'],
        date: formData['date-main']
    };
    const qrData = JSON.stringify(qrPayload);
    const size = 50;
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(qrData)}`;

    // Injecter dans les conteneurs correspondants s'ils existent
    const p1Container = document.getElementById('p1-qrcode');
    if (p1Container) p1Container.innerHTML = `<img src="${qrUrl}" alt="QR" style="border:1px solid #ddd;">`;
    const annAContainer = document.getElementById('annA-qrcode');
    if (annAContainer) annAContainer.innerHTML = `<img src="${qrUrl}" alt="QR" style="border:1px solid #ddd;">`;
    const annBContainer = document.getElementById('annB-qrcode');
    if (annBContainer) annBContainer.innerHTML = `<img src="${qrUrl}" alt="QR" style="border:1px solid #ddd;">`;
    const annCContainer = document.getElementById('annC-qrcode');
    if (annCContainer) annCContainer.innerHTML = `<img src="${qrUrl}" alt="QR" style="border:1px solid #ddd;">`;
    const annDContainer = document.getElementById('annD-qrcode');
    if (annDContainer) annDContainer.innerHTML = `<img src="${qrUrl}" alt="QR" style="border:1px solid #ddd;">`;
}

function startQrScanner() {
    document.getElementById('qr-modal').style.display = 'flex';
    document.getElementById('scanner-status').textContent = 'Initialisation de la caméra...';
    
    // Instancier le scanner
    html5QrScanner = new Html5Qrcode("scanner-container");
    
    const qrCodeSuccessCallback = (decodedText, decodedResult) => {
        try {
            const data = JSON.parse(decodedText);
            if (data.id) {
                // Si le permis est déjà enregistré localement, on le charge, sinon on applique les données scannées
                if (allPermits[data.id]) {
                    loadPermit(data.id);
                    alert(`Permis ${data.id} chargé avec succès.`);
                } else {
                    // Création dynamique avec les infos du QR
                    createNewPermit();
                    formData['permit-id'] = data.id;
                    formData['company'] = data.comp || '';
                    formData['work-desc'] = data.desc || '';
                    formData['location'] = data.loc || '';
                    formData['date-main'] = data.date || '';
                    loadPermit(currentPermitId);
                    alert(`Nouveau permis ${data.id} importé par QR Code.`);
                }
                closeQrScanner();
            }
        } catch (e) {
            console.log("Données QR non-standard: ", decodedText);
            // Charger la chaîne brute dans la description ou l'identifiant
            formData['permit-id'] = decodedText.substring(0, 30);
            loadPermit(currentPermitId);
            closeQrScanner();
        }
    };

    const config = { fps: 10, qrbox: { width: 200, height: 200 } };
    
    html5QrScanner.start({ facingMode: "environment" }, config, qrCodeSuccessCallback)
        .then(() => {
            document.getElementById('scanner-status').textContent = 'Caméra active. Visez un code QR.';
        })
        .catch(err => {
            document.getElementById('scanner-status').textContent = 'Erreur d\'accès caméra: ' + err;
        });
}

function closeQrScanner() {
    if (html5QrScanner) {
        html5QrScanner.stop().then(() => {
            html5QrScanner = null;
            document.getElementById('qr-modal').style.display = 'none';
        }).catch(err => {
            document.getElementById('qr-modal').style.display = 'none';
        });
    } else {
        document.getElementById('qr-modal').style.display = 'none';
    }
}


// --------------------- INTEGATION DE L'AGENT IA GEMINI (CLIENT-SIDE) ---------------------
let geminiApiKey = localStorage.getItem('gemini_api_key') || '';

// Gestionnaire d'enregistrement de clé
document.getElementById('gemini-key').value = geminiApiKey;
document.getElementById('btn-save-key').addEventListener('click', () => {
    const key = document.getElementById('gemini-key').value.trim();
    localStorage.setItem('gemini_api_key', key);
    geminiApiKey = key;
    alert("Clé API enregistrée !");
});

// Envoi de message à l'assistant
document.getElementById('chat-send-btn').addEventListener('click', sendChatMessage);
document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

async function callGeminiAPI(promptText, base64Image = null, mimeType = null) {
    if (!geminiApiKey) {
        throw new Error("Clé API manquante. Veuillez saisir votre clé API Gemini dans l'onglet paramètres.");
    }
    
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${geminiApiKey}`;
    
    let parts = [{ text: promptText }];
    if (base64Image && mimeType) {
        parts.push({
            inlineData: {
                mimeType: mimeType,
                data: base64Image
            }
        });
    }

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            contents: [{ parts: parts }],
            generationConfig: {
                responseMimeType: "application/json"
            }
        })
    });

    if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error?.message || "Erreur de communication avec l'API Gemini.");
    }

    const data = await response.json();
    return data.candidates[0].content.parts[0].text;
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const prompt = chatInput.value.trim();
    if (!prompt) return;

    appendChatMessage(prompt, 'user');
    chatInput.value = '';
    
    const loadingId = appendChatMessage('Réflexion en cours...', 'assistant-loading');
    
    try {
        const todayStr = new Date().toISOString().split('T')[0];
        const systemPrompt = `Tu es l'agent HSE du système CSPS FIAT.
        Analyse la demande de l'utilisateur : "${prompt}".
        
        Détermine si l'utilisateur souhaite :
        A) Créer ou copier un ou plusieurs BADGES de travailleurs (ex: "Crée des badges pour Ali et Omar", "Ajoute un badge pour Jean", etc.)
        B) Créer un PERMIS de travail (ex: "remplir un permis feu pour AMCE", "permis hauteur pour demain", etc.)
        
        - Si c'est le cas A (Badges) :
          Retourne un objet JSON sous cette forme :
          {
            "action_type": "bulk_badge_creation",
            "badges": [
              {
                "nom": "Nom de famille en majuscules",
                "prenom": "Prénom",
                "societe": "Nom de l'entreprise",
                "poste": "Fonction/Poste de travail",
                "cnas": "Numéro CNAS si spécifié",
                "carte_id": "Numéro CNI/Passeport si spécifié",
                "telephone": "Téléphone si spécifié"
              }
            ],
            "ai_response": "J'ai extrait les profils des travailleurs. Vous pouvez les valider ci-dessous pour lancer la création."
          }
          
        - Si c'est le cas B (Permis) :
          Détermine le type de permis parmi cette liste exacte : materiel, electrique, vehicule, chaud, fouille, espace_confine, hauteur, securite_generale, levage, revalidation.
          Retourne un objet JSON sous cette forme :
          {
            "action_type": "single_permit",
            "permit_type": "type_détecté",
            "company": "Entreprise",
            "contact": "Contact",
            "work-desc": "Description du travail",
            "location": "Lieu",
            "date-main": "${todayStr}",
            "time-start": "08h00",
            "ai_response": "Je vous redirige vers le permis de travail avec les données pré-remplies et la date mise à jour."
          }
          
        Ne renvoie aucun texte d'explication en dehors du JSON. Renvoie uniquement le JSON valide.`;

        const resultText = await callGeminiAPI(systemPrompt);
        removeMessage(loadingId);
        
        try {
            const updates = JSON.parse(resultText);
            
            if (updates.action_type === 'bulk_badge_creation') {
                // Table d'aperçu pour création en lot
                let tableHtml = `
                    <div style="background: white; color: #333; border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-top: 10px; font-size: 13px;">
                        <h5 style="margin-top: 0; color: #1e3a8a;"><i class="fa-solid fa-id-card"></i> Création de Badge(s)</h5>
                        <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 12px;">
                            <thead>
                                <tr style="border-bottom: 2px solid #eee; text-align: left;">
                                    <th style="padding: 4px;">Nom / Prénom</th>
                                    <th style="padding: 4px;">Poste</th>
                                    <th style="padding: 4px;">Société</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                updates.badges.forEach(b => {
                    tableHtml += `
                        <tr style="border-bottom: 1px solid #f3f4f6;">
                            <td style="padding: 4px; font-weight: bold;">${b.nom} ${b.prenom}</td>
                            <td style="padding: 4px;">${b.poste || 'N/A'}</td>
                            <td style="padding: 4px;">${b.societe || 'N/A'}</td>
                        </tr>
                    `;
                });
                tableHtml += `
                            </tbody>
                        </table>
                        <button id="btn-confirm-bulk-badges" class="btn btn-sm btn-success" style="background: #10b981; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%;">
                            <i class="fas fa-check-circle"></i> Valider et Enregistrer ces ${updates.badges.length} Badge(s)
                        </button>
                    </div>
                `;
                
                appendChatMessage(updates.ai_response || "Voici les badges détectés :", 'assistant');
                appendChatMessage(tableHtml, 'assistant-html');
                
                // Add event listener to confirm button
                document.getElementById('btn-confirm-bulk-badges').addEventListener('click', async () => {
                    const btn = document.getElementById('btn-confirm-bulk-badges');
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement en cours...';
                    btn.disabled = true;
                    
                    try {
                        const res = await fetch('/badge/api/creer_multiple', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ badges: updates.badges })
                        });
                        const resJson = await res.json();
                        if (resJson.success) {
                            btn.innerHTML = '<i class="fas fa-check"></i> Enregistré avec succès !';
                            btn.style.background = '#059669';
                            appendChatMessage(`🎉 Succès : ${resJson.created_count} badge(s) créé(s) et enregistré(s) avec succès ! Ils sont maintenant en attente de validation.`, 'assistant');
                        } else {
                            throw new Error(resJson.error || "Erreur lors de la création");
                        }
                    } catch (err) {
                        btn.innerHTML = '<i class="fas fa-times"></i> Échec';
                        btn.style.background = '#ef4444';
                        appendChatMessage("Erreur lors de la création des badges : " + err.message, 'assistant');
                    }
                });
                
            } else if (updates.action_type === 'single_permit' || updates.permit_type) {
                // Sauvegarder les données
                localStorage.setItem('sinylon_pending_data', JSON.stringify(updates));
                appendChatMessage(updates.ai_response || "Redirection vers le formulaire...", 'assistant');
                setTimeout(() => {
                    window.location.href = `/permis/formulaire_papier/${updates.permit_type || 'securite_generale'}`;
                }, 1500);
            } else {
                appendChatMessage(updates.ai_response || "Je n'ai pas pu déterminer l'action requise.", 'assistant');
            }
        } catch (parseErr) {
            appendChatMessage(resultText, 'assistant');
        }
    } catch (e) {
        removeMessage(loadingId);
        appendChatMessage("Erreur : " + e.message, 'assistant');
    }
}

function appendChatMessage(text, type) {
    const chatMessages = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    const id = 'msg-' + Date.now();
    msg.id = id;
    
    if (type === 'assistant-loading') {
        msg.className = 'message assistant';
        msg.innerHTML = `<div style="display:flex; align-items:center; gap:8px;">
            <div class="loading-spinner" style="width:24px; height:24px; border-width:1.5px;"></div>
            <span>${text}</span>
        </div>`;
    } else if (type === 'assistant-html') {
        msg.className = 'message assistant';
        msg.innerHTML = text;
    } else {
        msg.className = `message ${type}`;
        msg.textContent = text;
    }
    
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return id;
}

function removeMessage(id) {
    const msg = document.getElementById(id);
    if (msg) msg.remove();
}

// Reconnaissance vocale pour le Chat de l'Assistant
let chatSpeechActive = false;
function startChatSpeech() {
    if (!recognition) return;
    
    const btn = document.getElementById('chat-mic-btn');
    const input = document.getElementById('chat-input');
    
    if (chatSpeechActive) {
        recognition.stop();
        return;
    }
    
    chatSpeechActive = true;
    btn.classList.add('listening');
    
    recognition.onresult = (e) => {
        input.value = e.results[0][0].transcript;
    };
    
    recognition.onend = () => {
        btn.classList.remove('listening');
        chatSpeechActive = false;
    };
    
    recognition.start();
}

// --------------------- OCR / ANALYSE DE DOCUMENT PAR GEMINI ---------------------
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

if (dropZone && fileInput) {
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            handleMultipleFilesAnalysis(files);
        }
    });

    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            handleMultipleFilesAnalysis(files);
        }
    });
}

async function handleMultipleFilesAnalysis(files) {
    if (!geminiApiKey) {
        alert("Veuillez configurer votre clé API Gemini pour pouvoir analyser les documents.");
        return;
    }
    
    appendChatMessage(`Analyse en cours de ${files.length} document(s)...`, 'system');
    const loadingId = appendChatMessage(`Traitement des fichiers (0/${files.length})...`, 'assistant-loading');
    
    let extractedBadges = [];
    let extractedPermits = [];
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) {
            loadingEl.querySelector('span').textContent = `Lecture du fichier ${i + 1}/${files.length} : ${file.name}...`;
        }
        
        try {
            // Convert to base64
            const base64Data = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
            
            const mimeType = file.type || "image/png";
            
            // Ask Gemini to detect if it's a worker badge/ID or a permit, and extract fields
            const promptText = `Analyse cette image ou document. 
            Détermine s'il s'agit :
            A) D'un document d'identité ou photo de travailleur pour un BADGE.
            B) D'un formulaire ou scan de PERMIS de travail.
            
            Retourne un objet JSON valide contenant :
            {
              "type": "badge" ou "permis",
              "data": {
                // Si badge :
                "nom": "Nom de famille en majuscules",
                "prenom": "Prénom",
                "societe": "Société",
                "poste": "Poste/Fonction",
                "cnas": "CNAS si présent",
                "carte_id": "CNI/Passeport si présent",
                "telephone": "Téléphone si présent"
                // Si permis :
                "company": "Société",
                "work-desc": "Travaux",
                "location": "Lieu",
                "permit_type": "chaud" ou "hauteur" ou "fouille" etc.
              }
            }
            Ne renvoie que le JSON valide sans aucun formatage markdown ou bloc de code (pas de \`\`\`json).`;
            
            const resultText = await callGeminiAPI(promptText, base64Data, mimeType);
            const resObj = JSON.parse(resultText);
            
            if (resObj.type === 'badge') {
                extractedBadges.push(resObj.data);
            } else if (resObj.type === 'permis') {
                extractedPermits.push(resObj.data);
            }
        } catch (err) {
            console.error(`Erreur sur le fichier ${file.name}:`, err);
        }
    }
    
    removeMessage(loadingId);
    
    // Display results
    if (extractedBadges.length > 0) {
        let tableHtml = `
            <div style="background: white; color: #333; border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-top: 10px; font-size: 13px;">
                <h5 style="margin-top: 0; color: #1e3a8a;"><i class="fa-solid fa-id-card"></i> ${extractedBadges.length} Badge(s) extrait(s) par l'IA</h5>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 12px;">
                    <thead>
                        <tr style="border-bottom: 2px solid #eee; text-align: left;">
                            <th style="padding: 4px;">Nom / Prénom</th>
                            <th style="padding: 4px;">Poste</th>
                            <th style="padding: 4px;">Société</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        extractedBadges.forEach(b => {
            tableHtml += `
                <tr style="border-bottom: 1px solid #f3f4f6;">
                    <td style="padding: 4px; font-weight: bold;">${b.nom || ''} ${b.prenom || ''}</td>
                    <td style="padding: 4px;">${b.poste || 'N/A'}</td>
                    <td style="padding: 4px;">${b.societe || 'N/A'}</td>
                </tr>
            `;
        });
        tableHtml += `
                    </tbody>
                </table>
                <button id="btn-confirm-bulk-ocr" class="btn btn-sm btn-success" style="background: #10b981; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%;">
                    <i class="fas fa-check-circle"></i> Créer ces ${extractedBadges.length} Badge(s)
                </button>
            </div>
        `;
        
        appendChatMessage("J'ai détecté des fiches d'identité ou photos de travailleurs :", 'assistant');
        appendChatMessage(tableHtml, 'assistant-html');
        
        document.getElementById('btn-confirm-bulk-ocr').addEventListener('click', async () => {
            const btn = document.getElementById('btn-confirm-bulk-ocr');
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';
            btn.disabled = true;
            try {
                const res = await fetch('/badge/api/creer_multiple', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ badges: extractedBadges })
                });
                const resJson = await res.json();
                if (resJson.success) {
                    btn.innerHTML = '<i class="fas fa-check"></i> Enregistré !';
                    btn.style.background = '#059669';
                    appendChatMessage(`🎉 Succès : ${resJson.created_count} badge(s) créé(s) avec succès !`, 'assistant');
                } else {
                    throw new Error(resJson.error || "Erreur");
                }
            } catch (err) {
                btn.innerHTML = 'Échec';
                btn.style.background = '#ef4444';
                appendChatMessage("Erreur : " + err.message, 'assistant');
            }
        });
    }
    
    if (extractedPermits.length > 0) {
        // Rediriger ou pré-remplir pour le premier permis trouvé
        const p = extractedPermits[0];
        const todayStr = new Date().toISOString().split('T')[0];
        p['date-main'] = todayStr;
        
        localStorage.setItem('sinylon_pending_data', JSON.stringify(p));
        appendChatMessage(`Permis de travail détecté (${p.permit_type}). Redirection avec les données copiées et date mise à jour au ${todayStr}...`, 'assistant');
        setTimeout(() => {
            window.location.href = `/permis/formulaire_papier/${p.permit_type || 'securite_generale'}`;
        }, 2000);
    }
}
// --------------------- INITIALISATION DES EVENEMENTS GENERALS ---------------------
// Listener sur les champs de texte
document.querySelectorAll('input[data-field], textarea[data-field]').forEach(input => {
    const eventType = input.type === 'checkbox' ? 'change' : 'input';
    input.addEventListener(eventType, (e) => {
        const field = e.target.getAttribute('data-field');
        if (e.target.type === 'checkbox') {
            formData[field] = e.target.checked;
            updateCheckboxes();
        } else {
            formData[field] = e.target.value;
        }
        updateValues();
    });
});

// Listener sur les cases à cocher de danger
document.querySelectorAll('input[data-check]').forEach(check => {
    check.addEventListener('change', (e) => {
        if (!formData.checkboxes) formData.checkboxes = {};
        const checkId = e.target.getAttribute('data-check');
        formData.checkboxes[checkId] = e.target.checked;
        
        updateCheckboxes();
        saveToStorage();
    });
});


document.getElementById('btn-save').addEventListener('click', () => {
    ipcRenderer.send('save-pdf');
});

document.getElementById('btn-print').addEventListener('click', () => {
    ipcRenderer.send('print');
});


ipcRenderer.on('pdf-saved', (event, message) => {
    alert('PDF enregistré avec succès !');
});

