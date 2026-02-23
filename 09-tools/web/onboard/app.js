async function runPreview(payload) {
  const response = await fetch("/api/v1/onboard/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return response.json();
}

async function runApply(payload) {
  const response = await fetch("/api/v1/onboard/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return response.json();
}

async function loadDefaults() {
  const response = await fetch("/api/v1/defaults");
  return response.json();
}

function getSelectedIdes() {
  const checkboxes = document.querySelectorAll('input[name="ide"]:checked');
  return Array.from(checkboxes).map(cb => cb.value);
}

function getKeys() {
  return {
    PERPLEXITY_API_KEY: document.querySelector('input[name="PERPLEXITY_API_KEY"]').value,
    FIRECRAWL_API_KEY: document.querySelector('input[name="FIRECRAWL_API_KEY"]').value,
  };
}

function showDiffPanel(content) {
  const panel = document.getElementById('diff-panel');
  const contentDiv = document.getElementById('diff-content');
  contentDiv.textContent = content;
  panel.classList.remove('hidden');
}

function showSummary(content) {
  const panel = document.getElementById('summary-panel');
  const contentPre = document.getElementById('summary-content');
  contentPre.textContent = content;
  panel.classList.remove('hidden');
}

let lastPreviewReport = null;

document.addEventListener('DOMContentLoaded', async () => {
  const previewBtn = document.getElementById('preview-btn');
  const applyBtn = document.getElementById('apply-btn');

  previewBtn.addEventListener('click', async () => {
    const ides = getSelectedIdes();
    if (ides.length === 0) {
      alert('Please select at least one IDE');
      return;
    }

    previewBtn.disabled = true;
    previewBtn.textContent = 'Loading...';

    try {
      const defaults = await loadDefaults();
      const payload = {
        ides,
        shellFile: defaults.defaults?.shell_file || '',
        applyKeys: false,
        keys: getKeys(),
      };

      const result = await runPreview(payload);
      lastPreviewReport = result.report;

      if (result.ok) {
        showDiffPanel(JSON.stringify(result.report, null, 2));
        showSummary(result.summary || '');
        applyBtn.disabled = false;
      } else {
        alert('Preview failed: ' + (result.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      previewBtn.disabled = false;
      previewBtn.textContent = 'Preview';
    }
  });

  applyBtn.addEventListener('click', async () => {
    if (!lastPreviewReport) {
      alert('Please run preview first');
      return;
    }

    const ides = getSelectedIdes();
    const decisions = {};
    ides.forEach(ide => {
      decisions[ide] = 'apply';
    });

    applyBtn.disabled = true;
    applyBtn.textContent = 'Applying...';

    try {
      const defaults = await loadDefaults();
      const payload = {
        ides,
        decisions,
        shellFile: defaults.defaults?.shell_file || '',
        applyKeys: confirm('Apply premium keys to shell profile?'),
        keys: getKeys(),
      };

      const result = await runApply(payload);

      if (result.ok) {
        showDiffPanel(JSON.stringify(result.report, null, 2));
        showSummary(result.summary || '');
        alert('Changes applied successfully!');
      } else {
        alert('Apply failed: ' + (result.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      applyBtn.disabled = false;
      applyBtn.textContent = 'Apply';
    }
  });

  loadDefaults().then(result => {
    if (result.ok && result.defaults?.shell_file) {
      console.log('Shell file detected:', result.defaults.shell_file);
    }
  });
});
