/* static/js/export_polling.js
   Polling client pour les exports async NORO
   Usage : exportAsync('/export/badges', 'Badges Excel')
*/

async function exportAsync(endpoint, label) {
  // Afficher la modale de progression
  showExportModal(label);

  try {
    // 1. Lancer le job
    const res  = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();
    if (!data.job_id) throw new Error('Job non créé');

    // 2. Polling toutes les 1.5 secondes
    const jobId = data.job_id;
    let attempts = 0;
    const maxAttempts = 60;   // timeout après 90 secondes

    const poll = setInterval(async () => {
      attempts++;
      if (attempts > maxAttempts) {
        clearInterval(poll);
        hideExportModal();
        showToast('Export timeout — réessayez.', 'error');
        return;
      }

      const r    = await fetch(`/export/status/${jobId}`);
      const job  = await r.json();

      updateModalProgress(attempts, maxAttempts);

      if (job.statut === 'done') {
        clearInterval(poll);
        hideExportModal();
        // Téléchargement automatique
        const a = document.createElement('a');
        a.href  = job.result_url;
        a.download = '';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast(`${label} exporté avec succès ✓`, 'success');
      } else if (job.statut === 'error') {
        clearInterval(poll);
        hideExportModal();
        showToast(`Erreur export : ${job.error_msg}`, 'error');
      }
    }, 1500);

  } catch (err) {
    hideExportModal();
    showToast(`Erreur : ${err.message}`, 'error');
  }
}

/* ── Modale de progression ── */
function showExportModal(label) {
  let modal = document.getElementById('export-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'export-modal';
    modal.style.cssText = `
      position: fixed; inset: 0; background: rgba(0,0,0,0.5);
      display: flex; align-items: center; justify-content: center;
      z-index: 9999;
    `;
    modal.innerHTML = `
      <div style="
        background: var(--noro-surface, #141414);
        border: 1px solid var(--noro-border, #2a2a2a);
        border-radius: 10px; padding: 28px 32px; text-align: center;
        min-width: 280px;
      ">
        <div style="font-family:'Space Mono',monospace; font-size:12px; color:#e87c2b; letter-spacing:2px; margin-bottom:14px;">
          ⬡ NORO — EXPORT EN COURS
        </div>
        <div id="export-modal-label" style="font-size:14px; margin-bottom:18px;"></div>
        <div style="background:#1a1a1a; border-radius:4px; height:4px; overflow:hidden;">
          <div id="export-progress-bar" style="
            background: #e87c2b; height:100%; width:5%;
            transition: width 1.5s ease; border-radius:4px;
          "></div>
        </div>
        <div style="font-size:11px; color:#666; margin-top:10px;">
          Génération en cours, veuillez patienter...
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }
  document.getElementById('export-modal-label').textContent = label;
  document.getElementById('export-progress-bar').style.width = '5%';
  modal.style.display = 'flex';
}

function updateModalProgress(attempts, maxAttempts) {
  const bar = document.getElementById('export-progress-bar');
  if (bar) {
    const pct = Math.min(90, Math.round((attempts / maxAttempts) * 100));
    bar.style.width = pct + '%';
  }
}

function hideExportModal() {
  const modal = document.getElementById('export-modal');
  if (modal) modal.style.display = 'none';
}

function showToast(msg, type = 'info') {
  let t = document.getElementById('noro-toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'noro-toast';
    t.style.cssText = `
      position: fixed; bottom: 24px; right: 24px;
      padding: 10px 18px; border-radius: 4px;
      font-family: 'Space Mono', monospace; font-size: 11px;
      z-index: 10000; opacity: 0; transition: opacity .3s;
      pointer-events: none;
    `;
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.background  = type === 'error'   ? '#2e1010' :
                        type === 'success' ? '#102e10' : '#1a1a1a';
  t.style.color       = type === 'error'   ? '#e05050' :
                        type === 'success' ? '#50e050' : '#e87c2b';
  t.style.border      = `1px solid ${type === 'error' ? '#4a1010' : type === 'success' ? '#104a10' : '#e87c2b'}`;
  t.style.opacity     = '1';
  setTimeout(() => { t.style.opacity = '0'; }, 3500);
}
