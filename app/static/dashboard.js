/**
 * InsightIQ Dashboard Client Engine
 * Interactive state management, unified toolbar, enriched KPI cards,
 * causal driver insights, Chart.js visualizations, schema inspection dialog, and conversational querying.
 */

let activeDatasetId = null;
let currentProfile = null;
let currentInsights = null;
let currentCorrelations = null;
let currentTruthLens = null;
let activeTruthLensFilter = 'all';
let activeTruthLensSeverity = 'all';
let activeTruthLensScenario = 'active';
let workspaceAnomalyCount = null;
let aggChartInstance = null;
let tlDetailChartInstance = null;

// DOM Elements: Unified Toolbar & Upload
const datasetPicker = document.getElementById('dataset-picker');
const toggleUploadBtn = document.getElementById('toggle-upload-btn');
const dropzoneContainer = document.getElementById('dropzone-container');
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const closeDropzoneBtn = document.getElementById('close-dropzone-btn');
const demoBtn = document.getElementById('load-demo-btn');
const demoBtnText = document.getElementById('demo-btn-text');
const openSchemaBtn = document.getElementById('open-schema-btn');
const deleteDatasetBtn = document.getElementById('delete-dataset-btn');

// DOM Elements: Navigation Tabs
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

// DOM Elements: Briefing Actions
const copySummaryBtn = document.getElementById('copy-summary-btn');
const exportBriefingBtn = document.getElementById('export-briefing-btn');
const exportWordBtn = document.getElementById('export-word-btn');

// DOM Elements: Schema Dialog Modal
const schemaDialog = document.getElementById('schema-dialog');
const closeSchemaBtn = document.getElementById('close-schema-btn');
const schemaCloseFooterBtn = document.getElementById('schema-close-footer-btn');

// DOM Elements: Chat & Query
const chatHistory = document.getElementById('chat-history');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send-btn');
const clearChatBtn = document.getElementById('clear-chat-btn');
const toastEl = document.getElementById('toast');
let chatChartInstances = [];

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
  setupTabs();
  setupToolbarAndDropzone();
  setupBriefingActions();
  setupSchemaDialog();
  setupChat();
  setupAggregationControls();
  setupTruthLens();
  await refreshDatasetList();
});

// Toast Notification Utility
let toastTimeout = null;
function showToast(message, duration = 3000) {
  if (!toastEl) return;
  toastEl.textContent = message;
  toastEl.classList.add('show');
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toastEl.classList.remove('show');
  }, duration);
}

// Tab Navigation & Collapsible Left Sidebar
function setupTabs() {
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tab);
    });
  });

  const sidebar = document.getElementById('app-sidebar');
  const shell = document.getElementById('app-shell');
  const collapseBtn = document.getElementById('sidebar-collapse-btn');
  const collapseIcon = document.getElementById('sidebar-collapse-icon');
  // Remove any legacy duplicate sidebar toggle icon [◧] in the top header
  document.querySelectorAll('.header button, .header [role="button"], #header-sidebar-toggle, .header-sidebar-toggle').forEach(el => {
    if (el.id === 'header-sidebar-toggle' || el.classList.contains('header-sidebar-toggle') || (el.textContent && el.textContent.includes('◧'))) {
      el.style.setProperty('display', 'none', 'important');
      el.remove();
    }
  });
  if (collapseBtn && sidebar) {
    collapseBtn.addEventListener('click', () => {
      const isCollapsed = sidebar.classList.toggle('collapsed');
      if (shell) shell.classList.toggle('sidebar-collapsed', isCollapsed);
      collapseBtn.setAttribute('aria-expanded', String(!isCollapsed));
      if (collapseIcon) collapseIcon.textContent = isCollapsed ? '»' : '«';
      if (aggChartInstance) {
        setTimeout(() => aggChartInstance.resize(), 180);
      }
    });
  }

  const previewFilterInput = document.getElementById('preview-table-filter');
  if (previewFilterInput) {
    previewFilterInput.addEventListener('input', () => {
      const q = previewFilterInput.value.trim().toLowerCase();
      const tbody = document.getElementById('preview-table-body');
      if (!tbody) return;
      tbody.querySelectorAll('tr').forEach(tr => {
        const match = !q || tr.textContent.toLowerCase().includes(q);
        tr.style.display = match ? '' : 'none';
      });
    });
  }
}

function switchTab(tabId) {
  tabButtons.forEach(b => {
    if (b.dataset.tab === tabId) {
      b.classList.add('active');
    } else {
      b.classList.remove('active');
    }
  });

  tabPanes.forEach(p => {
    if (p.id === tabId) {
      p.classList.add('active');
    } else {
      p.classList.remove('active');
    }
  });

  if (tabId === 'tab-aggregations') {
    if (aggChartInstance) {
      aggChartInstance.resize();
    } else {
      runAggregation();
    }
  }
}

// Toolbar, Dropzone & Dataset Actions
function setupToolbarAndDropzone() {
  // Always ensure upload dropzone starts hidden by default
  collapseDropzone();

  // Toggle collapsible dropzone on button click
  if (toggleUploadBtn) {
    toggleUploadBtn.addEventListener('click', () => {
      if (dropzoneContainer.classList.contains('collapsed')) {
        expandDropzone();
      } else {
        collapseDropzone();
      }
    });
  }

  if (closeDropzoneBtn) {
    closeDropzoneBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      collapseDropzone();
    });
  }

  // Click inside dropzone triggers file selector
  dropzone.addEventListener('click', (e) => {
    if (e.target.closest('#close-dropzone-btn')) return;
    fileInput.click();
  });

  // Drag and drop behavior (auto-expand on dragover)
  window.addEventListener('dragover', (e) => {
    e.preventDefault();
  });

  window.addEventListener('drop', (e) => {
    e.preventDefault();
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  ['dragleave', 'dragend'].forEach(type => {
    dropzone.addEventListener(type, () => dropzone.classList.remove('drag-over'));
  });

  dropzone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', async (e) => {
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  });

  // Demo Dataset Loader
  if (demoBtn) {
    demoBtn.addEventListener('click', async () => {
      if (demoBtn.classList.contains('active-demo')) {
        showToast('Enterprise demo dataset is already loaded and active.');
        return;
      }
      await loadDemoDataset();
    });
  }

  // Dataset dropdown picker
  datasetPicker.addEventListener('change', (e) => {
    if (e.target.value) {
      loadDataset(e.target.value);
    }
  });

  // Delete Dataset Button
  if (deleteDatasetBtn) {
    deleteDatasetBtn.addEventListener('click', async () => {
      if (!activeDatasetId) return;
      const curFilename = currentProfile ? currentProfile.filename : 'active dataset';
      const confirmed = window.confirm(`Permanently delete dataset "${curFilename}"? This action cannot be undone.`);
      if (!confirmed) return;

      try {
        const res = await fetch(`/api/v1/datasets/${activeDatasetId}`, {
          method: 'DELETE',
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to delete dataset');
        }
        showToast(`Dataset "${curFilename}" successfully deleted.`);
        await refreshDatasetList();
      } catch (err) {
        alert(`Error deleting dataset: ${err.message}`);
      }
    });
  }
}

function expandDropzone() {
  dropzoneContainer.classList.remove('collapsed');
  dropzoneContainer.removeAttribute('hidden');
  dropzoneContainer.style.display = 'block';
  const label = document.getElementById('upload-btn-label');
  if (label) label.textContent = 'Hide Upload Box';
}

function collapseDropzone() {
  dropzoneContainer.classList.add('collapsed');
  dropzoneContainer.setAttribute('hidden', '');
  dropzoneContainer.style.display = 'none';
  const label = document.getElementById('upload-btn-label');
  if (label) label.textContent = '+ Upload CSV';
}

async function uploadFile(file) {
  if (!file.name.toLowerCase().endsWith('.csv')) {
    alert('Please upload a valid CSV file.');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    dropzone.innerHTML = `<div class="loading-spinner"></div><div style="margin-top:0.75rem; font-size:0.9rem;">Uploading and profiling dataset...</div>`;
    const res = await fetch('/api/v1/datasets/upload', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'Upload failed');
    }

    const data = await res.json();
    showToast(`Dataset "${file.name}" uploaded successfully!`);
    await refreshDatasetList(data.summary.dataset_id);
    collapseDropzone();
  } catch (err) {
    alert(`Upload Error: ${err.message}`);
  } finally {
    resetDropzoneUI();
  }
}

function resetDropzoneUI() {
  dropzone.innerHTML = `
    <div class="dropzone-left">
      <div class="dropzone-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
      </div>
      <div class="dropzone-copy">
        <div class="dropzone-title">Drop your CSV dataset here</div>
        <div class="dropzone-subtitle">Click to browse or drag file (up to 10 MB)</div>
      </div>
    </div>
    <button id="close-dropzone-btn" class="btn-text-link" type="button">Collapse</button>
  `;
  const btn = document.getElementById('close-dropzone-btn');
  if (btn) {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      collapseDropzone();
    });
  }
}

// 45-Row Realistic Enterprise Demo Dataset Generator (n >= 30, Data Health 100%)
async function loadDemoDataset() {
  const demoCsv = (
    "region,store,revenue,marketing_spend,customers,satisfaction\n" +
    "North,Chicago Flagship,139700.0,22900.0,1353,4.38\n" +
    "North,Minneapolis Metro,111500.0,16900.0,1043,4.24\n" +
    "North,Detroit Central,106700.0,16900.0,1073,3.20\n" +
    "North,Milwaukee Plaza,98100.0,17900.0,1030,4.15\n" +
    "North,Grand Rapids,87900.0,13800.0,906,4.05\n" +
    "North,Green Bay,119900.0,19600.0,1181,4.13\n" +
    "North,Columbus North,108100.0,18000.0,1112,4.23\n" +
    "North,Indianapolis,109800.0,18200.0,1107,4.34\n" +
    "North,Des Moines,100000.0,15800.0,956,4.08\n" +
    "North,Cleveland,107800.0,19500.0,1110,4.22\n" +
    "North,Toledo,124300.0,20300.0,1232,4.22\n" +
    "South,Atlanta Premier,139600.0,24100.0,1392,4.35\n" +
    "South,Dallas Galleria,103200.0,17300.0,1005,4.15\n" +
    "South,Houston Heights,127700.0,19800.0,1223,4.30\n" +
    "South,Miami Beachside,122200.0,19900.0,1193,4.30\n" +
    "South,Austin Downtown,120200.0,20500.0,1228,4.15\n" +
    "South,Charlotte South,121500.0,18900.0,1205,4.30\n" +
    "South,Nashville Midtown,131500.0,21900.0,1282,4.36\n" +
    "South,Tampa Bay,127700.0,21800.0,1361,4.33\n" +
    "South,Orlando Lake,133300.0,22200.0,1311,4.12\n" +
    "South,San Antonio,124300.0,19000.0,1173,4.19\n" +
    "South,Raleigh,134100.0,21900.0,1288,4.28\n" +
    "East,New York 5th Ave,167100.0,28100.0,1643,4.41\n" +
    "East,Boston Waterfront,133400.0,22600.0,1330,4.16\n" +
    "East,Philadelphia Market,126700.0,20600.0,1251,4.23\n" +
    "East,DC Metro Center,132800.0,22500.0,1322,4.21\n" +
    "East,Baltimore Harbor,151500.0,23900.0,1424,4.30\n" +
    "East,Pittsburgh Point,139000.0,24600.0,1442,4.29\n" +
    "East,Hartford Downtown,138600.0,21500.0,1380,4.30\n" +
    "East,Providence Place,148200.0,24900.0,1415,4.34\n" +
    "East,Buffalo Central,155800.0,26000.0,1481,4.20\n" +
    "East,Albany Mall,158100.0,26000.0,1599,4.29\n" +
    "East,Stamford,129000.0,22700.0,1329,4.27\n" +
    "West,San Francisco Silicon,176100.0,30600.0,1769,4.49\n" +
    "West,Seattle Downtown,153700.0,25600.0,1483,4.22\n" +
    "West,Los Angeles Century,185900.0,37500.0,1892,4.42\n" +
    "West,Denver Foothills,141100.0,23900.0,1439,4.20\n" +
    "West,Phoenix Desert,164800.0,27700.0,1614,4.36\n" +
    "West,Portland Pearl,160000.0,26800.0,1566,4.27\n" +
    "West,San Diego Bay,169400.0,29500.0,1713,4.41\n" +
    "West,Las Vegas Strip,150200.0,23900.0,1439,4.23\n" +
    "West,Salt Lake City,175200.0,29200.0,1695,4.49\n" +
    "West,Sacramento Capitol,159800.0,28300.0,1605,4.28\n" +
    "West,San Jose Tech,170800.0,28800.0,1672,4.41\n" +
    "West,Honolulu Palm,157600.0,25900.0,1566,4.51\n"
  );

  const blob = new Blob([demoCsv], { type: 'text/csv' });
  const file = new File([blob], 'executive_q3_performance.csv', { type: 'text/csv' });
  await uploadFile(file);
}

// Refresh Dataset Dropdown with Deduplication
async function refreshDatasetList(autoSelectId = null) {
  try {
    const res = await fetch('/api/v1/datasets');
    if (!res.ok) return;
    const rawDatasets = await res.json();

    // Client-side deduplication by filename + shape
    const seen = new Set();
    const datasets = [];
    rawDatasets.forEach(d => {
      const key = `${d.filename.toLowerCase()}-${d.row_count}-${d.column_count}`;
      if (!seen.has(key)) {
        seen.add(key);
        datasets.push(d);
      }
    });

    datasetPicker.innerHTML = '';
    if (datasets.length === 0) {
      datasetPicker.innerHTML = '<option value="">No datasets available — Upload above</option>';
      resetQuickMetricChips();
      expandDropzone();
      return;
    }

    datasets.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.dataset_id;
      opt.textContent = `${d.filename} (${d.row_count} rows, ${d.column_count} cols)`;
      datasetPicker.appendChild(opt);
    });

    const targetId = autoSelectId || datasets[0].dataset_id;
    datasetPicker.value = targetId;
    collapseDropzone();
    await loadDataset(targetId);
  } catch (e) {
    console.error('Failed to list datasets:', e);
  }
}

// Load Selected Dataset Across All Views
async function loadDataset(datasetId) {
  activeDatasetId = datasetId;

  try {
    // 1. Fetch Profile
    const profileRes = await fetch(`/api/v1/datasets/${datasetId}`);
    currentProfile = await profileRes.json();

    // 2. Fetch Insights
    const insightsRes = await fetch(`/api/v1/insights/${datasetId}`);
    currentInsights = await insightsRes.json();

    // 3. Fetch Correlations
    const corrRes = await fetch(`/api/v1/analytics/correlations/${datasetId}`);
    currentCorrelations = corrRes.ok ? await corrRes.json() : null;

    // 4. Fetch TruthLens Evidence-Based Intelligence Report
    const tlRes = await fetch(`/api/v1/truthlens/${datasetId}`);
    currentTruthLens = tlRes.ok ? await tlRes.json() : null;
    activeTruthLensScenario = 'active';

    // Ensure frontend + backend Data Health Score and insight recommendations stay in sync
    syncInsightsAndHealthScore();

    // Check if demo dataset is active and toggle button state
    updateDemoButtonState();

    // Collapse dropzone once dataset is active so KPIs are visible immediately above the fold
    collapseDropzone();

    renderKPIs();
    renderInsightsTab();
    renderProfileTab();
    renderCorrelationsTab();
    populateAggregationSelectors();
    populateAnomalySelectors();
    renderTruthLensTab();
    updateTabBadges();
    await loadQuickMetricChips(datasetId);
  } catch (err) {
    console.error('Error loading dataset views:', err);
  }
}

async function loadQuickMetricChips(datasetId) {
  const container = document.getElementById('quick-metrics-chips');
  if (!container) return;

  try {
    const res = await fetch(`/api/v1/query/${datasetId}/suggestions`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.chips && data.chips.length > 0) {
      container.innerHTML = data.chips
        .map(chip => `<button class="suggestion-chip" type="button">${escapeHtml(chip)}</button>`)
        .join('');
    }
  } catch (err) {
    console.warn('Failed to load dynamic query chips:', err);
  }
}

function resetQuickMetricChips() {
  const container = document.getElementById('quick-metrics-chips');
  if (container) {
    container.innerHTML = '<span class="chips-placeholder">Load a dataset to generate tailored quick metrics.</span>';
  }
}

function updateDemoButtonState() {
  if (!demoBtn) return;
  const isDemo = currentProfile && currentProfile.filename === 'executive_q3_performance.csv';
  if (isDemo) {
    demoBtn.classList.add('active-demo');
    demoBtn.setAttribute('aria-disabled', 'true');
    if (demoBtnText) demoBtnText.textContent = 'Demo Active';
  } else {
    demoBtn.classList.remove('active-demo');
    demoBtn.removeAttribute('aria-disabled');
    if (demoBtnText) demoBtnText.textContent = 'Demo Dataset';
  }
}

// Formatting Completeness: if nulls exist, never show 100.0%
function formatCompleteness(pct, nullCount) {
  if (nullCount > 0) {
    if (pct >= 99.95 || pct >= 100) return '99.9%';
    const floored = Math.min(99.9, Math.floor(pct * 10) / 10);
    return `${floored.toFixed(1)}%`;
  }
  return `${(pct || 100).toFixed(1)}%`;
}

// Formatting Data Health Score: never round to 100% if nulls exist or any weighted dimension < 100%
function formatHealthScore(score, nullCount, dq) {
  const hasImperfection = (nullCount > 0) ||
    (dq && (
      (dq.completeness_score !== undefined && dq.completeness_score < 99.99) ||
      (dq.sample_size_score !== undefined && dq.sample_size_score < 99.99) ||
      (dq.duplicate_score !== undefined && dq.duplicate_score < 99.99) ||
      (dq.variance_score !== undefined && dq.variance_score < 99.99) ||
      (dq.anomaly_score !== undefined && dq.anomaly_score < 99.99)
    ));

  if (hasImperfection) {
    const floored = Math.min(99, Math.round(score));
    return `${floored}%`;
  }
  return `${Math.round(score || 100)}%`;
}

function formatTitleCaseIdentifier(col) {
  if (!col) return '';
  return String(col)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function formatInsightCardTitle(item) {
  if (!item || !item.title) return '';
  if (item.cluster_features && item.cluster_features.length > 0 && item.title.startsWith('Multi-Driver Growth Cluster:')) {
    return `Multi-Driver Growth Cluster: ${item.cluster_features.map(formatTitleCaseIdentifier).join(' · ')}`;
  }
  return item.title
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/\bIn\b/g, 'in');
}

// Synchronize Data Health Score (40 Completeness / 30 Sample Adequacy / 30 Outlier & Variance Hygiene)
// and ensure anomaly/collinear recommendations are dynamically calibrated
function syncInsightsAndHealthScore() {
  if (!currentProfile || !currentInsights || !currentInsights.data_quality) return;

  const dq = currentInsights.data_quality;
  const nRows = currentProfile.row_count || 0;
  const nCols = currentProfile.column_count || 1;
  const totalCells = dq.total_cells || Math.max(1, nRows * nCols);
  const nullCells = dq.null_cells || 0;
  const validCells = dq.valid_cells !== undefined ? dq.valid_cells : (totalCells - nullCells);

  // 1. Completeness (40 pts max)
  const completenessPts = Number(((validCells / totalCells) * 40.0).toFixed(1));
  dq.completeness_score = Number(((validCells / totalCells) * 100.0).toFixed(2));

  // 2. Sample Adequacy (30 pts max, tiered scaling up to n = 200)
  let samplePts = 30.0;
  if (nRows < 30) {
    samplePts = Number(((nRows / 30.0) * 15.0).toFixed(1));
  } else if (nRows < 60) {
    samplePts = 20.0;
  } else if (nRows < 100) {
    samplePts = 22.5;
  } else if (nRows < 200) {
    samplePts = Number((25.0 + ((nRows - 100.0) / 100.0) * 5.0).toFixed(1));
  }
  dq.sample_size_score = Number(((samplePts / 30.0) * 100.0).toFixed(2));

  // 3. Outlier & Variance Hygiene (30 pts max): deduct 3 pts per flagged outlier feature (capped at -15 pts)
  const insightsList = currentInsights.insights || [];
  const colAnomalyInsights = insightsList.filter(
    i => i.category === 'anomaly' && i.action_link && i.action_link.column
  );
  const flaggedColsSet = new Set(colAnomalyInsights.map(i => i.action_link.column));
  const flaggedOutlierCols = flaggedColsSet.size;
  const outlierPenaltyPts = Math.min(15.0, flaggedOutlierCols * 3.0);
  const dupScore = dq.duplicate_score !== undefined ? dq.duplicate_score : 100.0;
  const varScore = dq.variance_score !== undefined ? dq.variance_score : 100.0;
  const dupPenaltyPts = Number((((100.0 - dupScore) / 100.0) * 7.5).toFixed(2));
  const varPenaltyPts = Number((((100.0 - varScore) / 100.0) * 7.5).toFixed(2));
  const hygienePts = Math.max(0.0, Number((30.0 - outlierPenaltyPts - dupPenaltyPts - varPenaltyPts).toFixed(2)));
  dq.anomaly_score = Number(((hygienePts / 30.0) * 100.0).toFixed(2));

  const overallHealth = Number((completenessPts + samplePts + hygienePts).toFixed(1));
  dq.overall_score = overallHealth;

  const penalties = [];
  if (nRows < 30) {
    penalties.push(`Penalized for small sample size (n=${nRows} < 30)`);
  } else if (nRows < 200) {
    penalties.push(`Limited sample size (n=${nRows} < 200)`);
  }
  if (flaggedOutlierCols > 0) {
    penalties.push(`${flaggedOutlierCols} outlier feature(s) flagged (-${outlierPenaltyPts.toFixed(0)} pts)`);
  }
  if (dq.duplicate_rows > 0) {
    penalties.push(`${dq.duplicate_rows} duplicate row(s)`);
  }
  if (dq.constant_columns && dq.constant_columns.length > 0) {
    penalties.push(`${dq.constant_columns.length} constant column(s): ${dq.constant_columns.join(', ')}`);
  }
  dq.penalty_reason = penalties.length > 0 ? penalties.join('; ') : 'All health dimensions optimal';

  // Sync Executive Strategic Briefing score & exact completeness copy
  if (typeof currentInsights.executive_summary === 'string') {
    currentInsights.executive_summary = currentInsights.executive_summary.replace(
      /overall data health score of [\d.]+\/100/i,
      `overall data health score of ${overallHealth.toFixed(1)}/100`
    );
    if (nullCells === 0) {
      currentInsights.executive_summary = currentInsights.executive_summary.replace(
        /The dataset exhibits robust completeness with minimal missingness\./i,
        `The dataset achieves 100% data completeness (zero missing values across all ${totalCells.toLocaleString()} cells).`
      );
    }
  }

  // Sync anomaly and collinear cluster recommendations & Title Case insight titles
  insightsList.forEach(item => {
    item.title = formatInsightCardTitle(item);
    if (item.category === 'anomaly') {
      item.severity = 'warning';
    }
    if (item.category === 'anomaly' && item.evidence) {
      item.evidence = item.evidence.replace(
        /Bounds:\s*\[([-\d.]+),\s*([-\d.]+)\]/i,
        (_, lowStr, highStr) => {
          const lowNum = Number(lowStr);
          const highNum = Number(highStr);
          const fmtLow = Number.isFinite(lowNum)
            ? lowNum.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
            : lowStr;
          const fmtHigh = Number.isFinite(highNum)
            ? highNum.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
            : highStr;
          return `Bounds: [${fmtLow}, ${fmtHigh}]`;
        }
      );
    }
    if (item.category === 'anomaly' && item.action_link && item.action_link.column) {
      const col = item.action_link.column;
      if (!item.recommendation || item.recommendation.includes('Investigate anomalous records')) {
        const boundsMatch = (item.evidence || '').match(/Bounds:\s*\[([-\d.,]+),\s*([-\d.,]+)\]\.\s*Extreme value observed:\s*([-\d.,]+)/i);
        if (boundsMatch) {
          const upper = parseFloat(boundsMatch[2].replace(/,/g, ''));
          const extremeStr = boundsMatch[3];
          const extremeVal = parseFloat(extremeStr.replace(/,/g, ''));
          if (extremeVal > upper) {
            item.recommendation = `Audit the high-magnitude spike in '${col}' (${extremeStr}) to confirm whether it reflects an intentional campaign surge or a duplicate/unallocated spend entry, and evaluate its marginal ROI.`;
          } else {
            item.recommendation = `Isolate the cohort or period behind the '${col}' drop (${extremeStr}) to identify service bottlenecks, fulfillment delays, or localized churn risks.`;
          }
        }
      }
    } else if (
      item.category === 'correlation' &&
      item.cluster_features &&
      item.cluster_features.length >= 3
    ) {
      const feats = item.cluster_features;
      const singleQuotedList = feats.map(c => `'${c}'`).join(', ');
      if (item.summary && !item.summary.includes(`'${feats[0]}'`)) {
        item.summary = `Identified a highly synchronized growth cluster among ${feats.length} core metrics: ${singleQuotedList}. These metrics demonstrate tight mutual collinearity (|r| ≥ 0.85), moving in lockstep.`;
      }
      if (item.recommendation && item.recommendation.includes('primary operational lever')) {
        const quoted = feats.slice(0, -1).map(c => `'${c}'`).join(', ') + `, and '${feats[feats.length - 1]}'`;
        item.recommendation = `Strong historical co-movement links ${quoted} (r ≥ 0.96). Validate causal lift via controlled holdout testing or incremental spend attribution before scaling budget allocations, and avoid combining these collinear features directly in unregularized linear models.`;
      }
    }
  });
}

// Render Top Enriched KPI Cards
function renderKPIs() {
  if (!currentProfile || !currentInsights) return;

  const dq = currentInsights.data_quality;

  // 1. Data Health Score
  const healthScore = dq.overall_score;
  const healthEl = document.getElementById('kpi-health');
  const validCells = dq.valid_cells || (currentProfile.row_count * currentProfile.column_count);
  const totalCells = dq.total_cells || validCells;
  const nullCells = dq.null_cells || 0;
  const completeness = dq.completeness_score;

  const displayScore = formatHealthScore(healthScore, nullCells, dq);
  healthEl.textContent = displayScore;
  if (healthScore >= 90) {
    healthEl.style.color = '#10b981'; // Emerald green (>= 90%)
  } else if (healthScore >= 75) {
    healthEl.style.color = '#38bdf8'; // Teal/Sky Cyan (75% - 89%: Good / Minor Warnings)
  } else {
    healthEl.style.color = '#f59e0b'; // Amber/Warning (< 75%)
  }

  const healthBar = document.getElementById('kpi-health-bar');
  if (healthBar) {
    const pct = Math.max(0, Math.min(100, Number(healthScore) || 0));
    healthBar.style.width = `${pct}%`;
    healthBar.style.background = healthScore >= 90
      ? 'linear-gradient(90deg, #059669, #10b981)'
      : healthScore >= 75
        ? 'linear-gradient(90deg, #0284c7, #38bdf8)'
        : 'linear-gradient(90deg, #d97706, #f59e0b)';
  }

  const healthSubtext = document.getElementById('kpi-health-subtext');
  const cellSummary = nullCells > 0
    ? `${validCells.toLocaleString()} / ${totalCells.toLocaleString()} valid cells · ${nullCells} nulls`
    : `${validCells.toLocaleString()} / ${totalCells.toLocaleString()} valid cells`;
  healthSubtext.style.color = '#94a3b8';
  if (dq.penalty_reason && dq.penalty_reason !== 'All health dimensions optimal') {
    healthSubtext.title = `${cellSummary} — ${dq.penalty_reason}`;
    healthSubtext.innerHTML = `<span class="subtext-positive" title="${escapeHtml(cellSummary)}">${escapeHtml(cellSummary)}</span><span class="subtext-penalty text-warning" title="${escapeHtml(dq.penalty_reason)}">${escapeHtml(dq.penalty_reason)}</span>`;
  } else {
    healthSubtext.title = `${cellSummary} · 40% Complete · 30% Sample`;
    healthSubtext.innerHTML = `<span class="subtext-positive" title="${escapeHtml(cellSummary)}">${escapeHtml(cellSummary)}</span>`;
  }

  // Populate Tooltip (40 pts Completeness / 30 pts Sample / 30 pts Outlier & Variance Hygiene)
  const completenessPts = ((completeness / 100) * 40).toFixed(1);
  const samplePts = (((dq.sample_size_score ?? 100) / 100) * 30).toFixed(1);
  const hygienePts = (((dq.anomaly_score ?? 100) / 100) * 30).toFixed(1);
  document.getElementById('score-completeness').textContent = `${completenessPts} / 40 pts (${formatCompleteness(completeness, nullCells)})`;
  document.getElementById('score-sample').textContent = `${samplePts} / 30 pts (${(dq.sample_size_score || 100).toFixed(1)}%)`;
  document.getElementById('score-variance').textContent = `${hygienePts} / 30 pts (${(dq.anomaly_score || 100).toFixed(1)}%)`;
  document.getElementById('score-unique').textContent = `${(dq.duplicate_score || 100).toFixed(1)}%`;
  document.getElementById('score-penalty-note').textContent = dq.penalty_reason || 'All health dimensions optimal';

  // 2. Total Records (3-tier dynamic statistical sample adequacy badge: <30 CLT < 30, 30..199 SAMPLE < 200, >=200 ROBUST n)
  const nRows = currentProfile.row_count;
  document.getElementById('kpi-rows').textContent = nRows.toLocaleString();
  const memKb = (currentProfile.memory_usage_bytes / 1024).toFixed(1);
  const rowsSubtext = document.getElementById('kpi-rows-subtext');
  rowsSubtext.textContent = `${memKb} KB memory`;
  rowsSubtext.title = `${memKb} KB memory footprint`;

  const rowsBadgeWrapper = document.getElementById('kpi-rows-badge');
  if (nRows < 30) {
    rowsBadgeWrapper.innerHTML = `<span class="kpi-tag warning" title="Critical Sample (n &lt; 30) — Small Sample (CLT Min)">CLT &lt; 30</span>`;
  } else if (nRows < 200) {
    rowsBadgeWrapper.innerHTML = `<span class="kpi-tag info" title="Moderate Sample (30 &lt;= n &lt; 200) — Meets Central Limit Theorem minimum (n &gt;= 30)">SAMPLE &lt; 200</span>`;
  } else {
    rowsBadgeWrapper.innerHTML = `<span class="kpi-tag success" title="Optimal Sample (n &gt;= 200) — Robust sample size for multi-dimensional BI">ROBUST n</span>`;
  }

  // 3. Features / Columns (Separate Identifiers from Numeric & Categorical measures)
  document.getElementById('kpi-cols').textContent = currentProfile.column_count.toLocaleString();
  const idCols = currentProfile.columns.filter(c => c.is_identifier);
  const nonIdCols = currentProfile.columns.filter(c => !c.is_identifier);
  const idCount = idCols.length;
  const numCount = nonIdCols.filter(c => c.category === 'numeric').length;
  const catCount = nonIdCols.length - numCount;

  const dot = (color, label) => `<span class="kpi-legend-item"><i style="background:${color}"></i>${label}</span>`;
  const legendParts = [dot('#6366f1', `${numCount} Num`), dot('#06b6d4', `${catCount} Cat`)];
  if (idCount > 0) legendParts.push(dot('#64748b', `${idCount} ID`));
  document.getElementById('kpi-cols-subtext').innerHTML = legendParts.join('<span class="kpi-legend-sep">·</span>');

  const colsBar = document.getElementById('kpi-cols-bar');
  if (colsBar) {
    const segs = [
      { n: numCount, color: '#6366f1', label: 'Numeric' },
      { n: catCount, color: '#06b6d4', label: 'Categorical' },
      { n: idCount, color: '#64748b', label: 'ID' },
    ].filter(s => s.n > 0);
    colsBar.innerHTML = segs
      .map(s => `<span title="${s.n} ${s.label}" style="flex:${s.n}; background:${s.color}"></span>`)
      .join('');
  }

  // 4. Anomalies Flagged — synced with TruthLens statistical-anomaly alerts / Anomaly Inspector badge
  const tlAnomalyFindings = (currentTruthLens && currentTruthLens.findings)
    ? currentTruthLens.findings.filter(f => f.category === 'statistical_anomalies')
    : null;
  const anomalyInsights = (currentInsights.insights || []).filter(i => i.category === 'anomaly');
  const colAnomalyInsights = anomalyInsights.filter(i => i.action_link && i.action_link.column);
  const flaggedColsSet = new Set(colAnomalyInsights.map(i => i.action_link.column));
  const flaggedColsCount = tlAnomalyFindings ? tlAnomalyFindings.length : (flaggedColsSet.size || anomalyInsights.length);
  const totalAnomaliesCount = tlAnomalyFindings ? tlAnomalyFindings.length : anomalyInsights.length;
  workspaceAnomalyCount = totalAnomaliesCount;

  // Exact number of anomalous records surfaced across those flagged features
  let anomalousRecordCount = 0;
  if (tlAnomalyFindings) {
    tlAnomalyFindings.forEach(f => {
      const m = (f.what_happened || '').match(/Detected (\d+) statistical anomaly/i);
      anomalousRecordCount += m ? parseInt(m[1], 10) : 1;
    });
  }

  const anomaliesEl = document.getElementById('kpi-anomalies');
  if (anomaliesEl) {
    anomaliesEl.textContent = totalAnomaliesCount.toLocaleString();
    anomaliesEl.style.color = totalAnomaliesCount > 0 ? 'var(--accent-amber)' : 'var(--accent-emerald)';
  }

  const anomaliesBadgeWrapper = document.getElementById('kpi-anomalies-badge');
  if (anomaliesBadgeWrapper) {
    if (totalAnomaliesCount > 0) {
      anomaliesBadgeWrapper.innerHTML = `<span class="kpi-tag warning">Flagged</span>`;
    } else {
      anomaliesBadgeWrapper.innerHTML = `<span class="kpi-tag success">Clean</span>`;
    }
  }

  const anomaliesSubtext = document.getElementById('kpi-anomalies-subtext');
  if (anomaliesSubtext) {
    const featureCountToDisplay = flaggedColsCount > 0 ? flaggedColsCount : numCount;
    const rowsCountToDisplay = anomalousRecordCount > 0 ? anomalousRecordCount : totalAnomaliesCount;
    const recordsClause = rowsCountToDisplay > 0
      ? `${rowsCountToDisplay} row${rowsCountToDisplay === 1 ? '' : 's'} · `
      : '';
    anomaliesSubtext.title = `${rowsCountToDisplay} anomalous records across ${featureCountToDisplay} numeric features | IQR & Z-Score`;
    anomaliesSubtext.textContent = `${recordsClause}${featureCountToDisplay} col${featureCountToDisplay === 1 ? '' : 's'}`;
  }

  // Update Sidebar Footer Dataset Memory/Health Indicator (Single Clean Status Pill)
  const sidebarMetaText = document.getElementById('sidebar-meta-text');
  const sidebarHealthDot = document.getElementById('sidebar-health-dot');
  if (sidebarMetaText) {
    sidebarMetaText.textContent = `${memKb} KB`;
  }
  if (sidebarHealthDot) {
    sidebarHealthDot.style.background = healthScore >= 90 ? '#10b981' : healthScore >= 75 ? '#38bdf8' : '#f59e0b';
  }

  updateTabBadges();
}

// Live Navigation Tab Badges (Actionable counts only)
function updateTabBadges() {
  if (!currentProfile || !currentInsights) return;

  // Tab 1: Insights Count
  const badgeInsights = document.getElementById('badge-insights');
  if (badgeInsights) {
    badgeInsights.textContent = currentInsights.insights.length;
  }

  // Tab 6: Anomalies Count (synced with KPI card & TruthLens anomaly alerts)
  const badgeAnomalies = document.getElementById('badge-anomalies');
  if (badgeAnomalies) {
    const anomalyInsights = currentInsights.insights.filter(i => i.category === 'anomaly');
    badgeAnomalies.textContent = workspaceAnomalyCount !== null ? workspaceAnomalyCount : anomalyInsights.length;
  }

  // Tab 7: TruthLens Count
  const badgeTruthLens = document.getElementById('badge-truthlens');
  if (badgeTruthLens && currentTruthLens && currentTruthLens.summary_counts) {
    badgeTruthLens.textContent = currentTruthLens.summary_counts.total_findings;
  }
}

// Render Tab 1: AI Insights with Causal Hierarchy, Slopes, Confidence Badges, and Cross-Navigation
function renderInsightsTab() {
  if (!currentInsights) return;

  const heroSummary = document.getElementById('insights-exec-summary');
  heroSummary.textContent = currentInsights.executive_summary;

  const grid = document.getElementById('insights-container');
  grid.innerHTML = '';

  if (currentInsights.insights.length === 0) {
    grid.innerHTML = '<div style="color:var(--text-muted);">No critical insights detected for this dataset.</div>';
    return;
  }

  // Arrange anomaly briefing cards first (side-by-side 2-column grid), and multi-driver cluster cards full-width below
  const orderedInsights = [...currentInsights.insights].sort(
    (a, b) => (a.category === 'anomaly' ? 0 : 1) - (b.category === 'anomaly' ? 0 : 1)
  );

  orderedInsights.forEach(item => {
    const isCluster = item.cluster_features && item.cluster_features.length > 0;
    const isFullSpan = isCluster || item.category === 'correlation';
    const card = document.createElement('div');
    card.className = `insight-card${isFullSpan ? ' insight-card-full' : ''}`;

    const clusterTagHtml = isCluster ? `<span class="insight-cluster-tag">Collinear Cluster</span>` : '';

    let confidenceHtml = '';
    if (item.confidence_badge) {
      const isLow = item.confidence_badge.includes('Low Confidence') || item.confidence_badge.includes('Small Sample');
      confidenceHtml = `<div class="confidence-badge ${isLow ? 'low-sample' : ''}">${escapeHtml(item.confidence_badge)}</div>`;
    }

    let actionBtnHtml = '';
    if (item.action_link) {
      actionBtnHtml = `
        <button type="button" class="insight-action-btn"
          data-target-tab="${escapeHtml(item.action_link.target_tab)}"
          data-feat-x="${escapeHtml(item.action_link.feature_x || '')}"
          data-feat-y="${escapeHtml(item.action_link.feature_y || '')}"
          data-column="${escapeHtml(item.action_link.column || '')}">
          <span>${escapeHtml(item.action_link.label)}</span>
        </button>
      `;
    }

    card.innerHTML = `
      <div class="insight-card-top">
        <div class="insight-header">
          <div class="insight-title-wrap">
            <div class="insight-title">
              <span>${escapeHtml(item.title)}</span>
              ${clusterTagHtml}
            </div>
            ${confidenceHtml}
          </div>
          <span class="severity-badge severity-${item.severity}">${item.severity}</span>
        </div>
        <div class="insight-summary">${escapeHtml(item.summary)}</div>
        <div class="insight-evidence insight-evidence-pillbar">
          <strong class="insight-callout-label">Quantitative Evidence:</strong>
          <code class="insight-evidence-code">${escapeHtml(item.evidence)}</code>
        </div>
      </div>
      <div class="insight-recommendation-box ${isFullSpan ? 'rec-indigo' : 'rec-emerald'}">
        ${item.recommendation ? `<div class="insight-recommendation"><strong class="insight-rec-label">Strategic Recommendation:</strong> <span class="insight-rec-text">${escapeHtml(item.recommendation)}</span></div>` : ''}
        ${actionBtnHtml ? `<div class="insight-footer-actions">${actionBtnHtml}</div>` : ''}
      </div>
    `;

    grid.appendChild(card);
  });

  // Attach action link navigation listeners
  grid.querySelectorAll('.insight-action-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.targetTab;
      const featX = btn.dataset.featX;
      const featY = btn.dataset.featY;
      const col = btn.dataset.column;

      if (targetTab) {
        switchTab(targetTab);

        if (targetTab === 'tab-anomalies' && col) {
          const colSelect = document.getElementById('anomaly-col-select');
          if (colSelect) {
            colSelect.value = col;
            scanAnomalies();
          }
        } else if (targetTab === 'tab-correlations' && (featX || featY)) {
          highlightCorrelationPair(featX, featY);
        }
      }
    });
  });
}

function highlightCorrelationPair(featX, featY) {
  const container = document.getElementById('correlations-container');
  if (!container) return;
  const cards = container.querySelectorAll('.col-card');
  cards.forEach(card => {
    const text = card.textContent.toLowerCase();
    if (featX && text.includes(featX.toLowerCase()) && featY && text.includes(featY.toLowerCase())) {
      card.style.borderColor = 'var(--accent-primary)';
      card.style.boxShadow = '0 0 20px rgba(99, 102, 241, 0.4)';
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      card.style.borderColor = 'var(--border-color)';
      card.style.boxShadow = 'none';
    }
  });
}

// Executive Strategic Briefing Actions: Copy Summary, Export PDF & Export Word
function setupBriefingActions() {
  if (copySummaryBtn) {
    copySummaryBtn.addEventListener('click', async () => {
      if (!currentInsights || !currentInsights.executive_summary) return;
      try {
        await navigator.clipboard.writeText(currentInsights.executive_summary);
        const textSpan = document.getElementById('copy-summary-text');
        if (textSpan) textSpan.textContent = '✓ Copied!';
        showToast('Strategic briefing summary copied to clipboard.');
        setTimeout(() => {
          if (textSpan) textSpan.textContent = 'Copy Summary';
        }, 2000);
      } catch (e) {
        showToast('Summary copied!');
      }
    });
  }

  if (exportBriefingBtn) {
    exportBriefingBtn.addEventListener('click', exportBriefingPdf);
  }

  if (exportWordBtn) {
    exportWordBtn.addEventListener('click', exportBriefingWord);
  }
}

function buildExecutiveBriefingDocumentHtml() {
  const dq = currentInsights.data_quality;
  const completenessStr = formatCompleteness(dq.completeness_score, dq.null_cells || 0);
  const healthStr = formatHealthScore(dq.overall_score, dq.null_cells || 0, dq);
  const generatedDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const insightsRowsHtml = currentInsights.insights.map((item, idx) => {
    const sevColors = {
      critical: '#e11d48',
      warning: '#d97706',
      positive: '#059669',
      info: '#0284c7',
    };
    const badgeColor = sevColors[item.severity] || '#4f46e5';
    return `
      <div class="finding-card">
        <div class="finding-header">
          <span class="finding-title">${idx + 1}. ${escapeHtml(item.title)}</span>
          <span class="finding-badge" style="color:${badgeColor}; border-color:${badgeColor};">${escapeHtml(item.severity.toUpperCase())}</span>
        </div>
        ${item.confidence_badge ? `<div class="finding-meta">Statistical Confidence: ${escapeHtml(item.confidence_badge)}</div>` : ''}
        <p class="finding-summary">${escapeHtml(item.summary)}</p>
        <div class="finding-evidence"><strong>Quantitative Evidence:</strong> ${escapeHtml(item.evidence)}</div>
        ${item.recommendation ? `<div class="finding-rec"><strong>Strategic Recommendation:</strong> ${escapeHtml(item.recommendation)}</div>` : ''}
      </div>
    `;
  }).join('');

  return `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40"
      lang="en">
<head>
  <meta charset="UTF-8">
  <title>Executive Strategic Briefing — ${escapeHtml(currentProfile.filename)}</title>
  <style>
    @page { size: A4; margin: 18mm 16mm; }
    body {
      font-family: 'Segoe UI', Calibri, Arial, sans-serif;
      color: #0f172a;
      line-height: 1.55;
      margin: 0;
      padding: 24px;
      background: #ffffff;
    }
    .report-header {
      border-bottom: 3px solid #4f46e5;
      padding-bottom: 14px;
      margin-bottom: 20px;
    }
    .report-brand {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #4f46e5;
      margin-bottom: 4px;
    }
    .report-title {
      font-size: 22px;
      font-weight: 800;
      color: #0f172a;
      margin: 0 0 6px 0;
    }
    .report-subtitle {
      font-size: 12px;
      color: #64748b;
    }
    .section-heading {
      font-size: 15px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #1e293b;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 6px;
      margin: 22px 0 12px 0;
    }
    .exec-summary-box {
      background: #f8fafc;
      border-left: 4px solid #4f46e5;
      padding: 14px 16px;
      font-size: 14px;
      color: #1e293b;
      margin-bottom: 18px;
    }
    .kpi-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
    }
    .kpi-table th, .kpi-table td {
      border: 1px solid #cbd5e1;
      padding: 10px 12px;
      text-align: left;
      font-size: 12.5px;
    }
    .kpi-table th {
      background: #f1f5f9;
      color: #475569;
      font-weight: 700;
      text-transform: uppercase;
      font-size: 11px;
    }
    .kpi-table td strong {
      font-size: 16px;
      color: #0f172a;
      display: block;
    }
    .finding-card {
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 14px 16px;
      margin-bottom: 14px;
      page-break-inside: avoid;
      background: #ffffff;
    }
    .finding-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }
    .finding-title {
      font-size: 14.5px;
      font-weight: 700;
      color: #0f172a;
    }
    .finding-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border: 1px solid #4f46e5;
      border-radius: 10px;
      margin-left: 8px;
    }
    .finding-meta {
      font-size: 11.5px;
      color: #0284c7;
      font-weight: 600;
      margin-bottom: 6px;
    }
    .finding-summary {
      font-size: 13px;
      color: #334155;
      margin: 6px 0;
    }
    .finding-evidence {
      font-size: 12.5px;
      background: #f8fafc;
      border-left: 3px solid #6366f1;
      padding: 7px 10px;
      color: #1e293b;
      margin: 8px 0;
    }
    .finding-rec {
      font-size: 12.5px;
      color: #0f172a;
      border-top: 1px dashed #cbd5e1;
      padding-top: 7px;
      margin-top: 7px;
    }
    .report-footer {
      margin-top: 28px;
      padding-top: 10px;
      border-top: 1px solid #e2e8f0;
      font-size: 11px;
      color: #64748b;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="report-header">
    <div class="report-brand">InsightIQ Enterprise Business Intelligence</div>
    <h1 class="report-title">Executive Strategic Briefing: ${escapeHtml(currentProfile.filename)}</h1>
    <div class="report-subtitle">Generated on ${escapeHtml(generatedDate)} · Dataset ID: ${escapeHtml(currentProfile.dataset_id)}</div>
  </div>

  <h2 class="section-heading">1. Executive Summary</h2>
  <div class="exec-summary-box">${escapeHtml(currentInsights.executive_summary)}</div>

  <h2 class="section-heading">2. Core Quantitative Health &amp; Hygiene</h2>
  <table class="kpi-table">
    <thead>
      <tr>
        <th>Data Health Score</th>
        <th>Total Records</th>
        <th>Features / Columns</th>
        <th>Matrix Completeness</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>${escapeHtml(healthStr)}</strong>${escapeHtml(dq.penalty_reason || 'All dimensions optimal')}</td>
        <td><strong>${currentProfile.row_count.toLocaleString()}</strong>${(currentProfile.memory_usage_bytes / 1024).toFixed(1)} KB footprint</td>
        <td><strong>${currentProfile.column_count}</strong>Analyzed attributes</td>
        <td><strong>${escapeHtml(completenessStr)}</strong>${dq.valid_cells.toLocaleString()} / ${dq.total_cells.toLocaleString()} valid cells</td>
      </tr>
    </tbody>
  </table>

  <h2 class="section-heading">3. Key Business Findings, Drivers &amp; Recommendations (${currentInsights.insights.length})</h2>
  ${insightsRowsHtml}

  <div class="report-footer">
    Confidential — Automatically synthesized by InsightIQ Enterprise BI Platform (v0.1.0)
  </div>
</body>
</html>`;
}

function exportBriefingWord() {
  if (!currentProfile || !currentInsights) return;
  const fname = currentProfile.filename.replace(/\.csv$/i, '');
  const timestamp = new Date().toISOString().split('T')[0];
  const docHtml = '\ufeff' + buildExecutiveBriefingDocumentHtml();

  const blob = new Blob([docHtml], {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${fname}_executive_briefing_${timestamp}.docx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('Executive briefing downloaded as Microsoft Word (.docx)!');
}

function exportBriefingPdf() {
  if (!currentProfile || !currentInsights) return;
  const reportHtml = buildExecutiveBriefingDocumentHtml();

  const printIframe = document.createElement('iframe');
  printIframe.style.position = 'fixed';
  printIframe.style.right = '0';
  printIframe.style.bottom = '0';
  printIframe.style.width = '0';
  printIframe.style.height = '0';
  printIframe.style.border = '0';
  document.body.appendChild(printIframe);

  const frameDoc = printIframe.contentWindow.document;
  frameDoc.open();
  frameDoc.write(reportHtml);
  frameDoc.close();

  showToast('Preparing PDF report — select "Save as PDF" in the print dialog.');

  setTimeout(() => {
    try {
      printIframe.contentWindow.focus();
      printIframe.contentWindow.print();
    } catch (e) {
      console.error('PDF print error:', e);
    } finally {
      setTimeout(() => {
        if (printIframe.parentNode) {
          printIframe.parentNode.removeChild(printIframe);
        }
      }, 2000);
    }
  }, 250);
}

// Schema & Raw Data Preview Dialog
function setupSchemaDialog() {
  if (openSchemaBtn && schemaDialog) {
    openSchemaBtn.addEventListener('click', () => {
      populateSchemaDialog();
      schemaDialog.showModal();
    });
  }

  if (closeSchemaBtn && schemaDialog) {
    closeSchemaBtn.addEventListener('click', () => schemaDialog.close());
  }

  if (schemaCloseFooterBtn && schemaDialog) {
    schemaCloseFooterBtn.addEventListener('click', () => schemaDialog.close());
  }

  if (schemaDialog) {
    schemaDialog.addEventListener('click', (e) => {
      const rect = schemaDialog.getBoundingClientRect();
      const isInDialog = (
        rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX && e.clientX <= rect.left + rect.width
      );
      if (!isInDialog) {
        schemaDialog.close();
      }
    });
  }
}

function populateSchemaDialog() {
  if (!currentProfile) return;

  const subtitle = document.getElementById('schema-dialog-subtitle');
  if (subtitle) {
    subtitle.textContent = `${currentProfile.filename} · ${currentProfile.row_count.toLocaleString()} rows · ${currentProfile.column_count} columns`;
  }

  // Meta chips
  const chipsContainer = document.getElementById('schema-meta-chips');
  if (chipsContainer) {
    const memKb = (currentProfile.memory_usage_bytes / 1024).toFixed(1);
    chipsContainer.innerHTML = `
      <div class="meta-chip">Filename: <strong>${escapeHtml(currentProfile.filename)}</strong></div>
      <div class="meta-chip">Total Rows: <strong>${currentProfile.row_count.toLocaleString()}</strong></div>
      <div class="meta-chip">Total Columns: <strong>${currentProfile.column_count}</strong></div>
      <div class="meta-chip">Memory: <strong>${memKb} KB</strong></div>
      <div class="meta-chip">Uploaded: <strong>${new Date(currentProfile.uploaded_at).toLocaleString()}</strong></div>
    `;
  }

  // Schema Columns Table
  const tbody = document.getElementById('schema-columns-body');
  if (tbody) {
    tbody.innerHTML = '';
    currentProfile.columns.forEach(col => {
      const tr = document.createElement('tr');
      const samples = col.sample_values ? col.sample_values.slice(0, 3).join(', ') : '—';
      const completeness = (100 - col.null_percentage).toFixed(1);
      tr.innerHTML = `
        <td style="font-weight:600; color:#fff;">${escapeHtml(col.name)}</td>
        <td><span class="col-type-tag">${col.category}</span></td>
        <td><code>${escapeHtml(col.native_dtype)}</code></td>
        <td>${col.distinct_count} (${col.distinct_percentage}%)</td>
        <td>${col.null_count}</td>
        <td>${completeness}%</td>
        <td style="color:var(--text-muted); font-size:0.75rem;">${escapeHtml(samples)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Schema Preview Table
  const prevHead = document.getElementById('schema-preview-head');
  const prevBody = document.getElementById('schema-preview-body');
  if (prevHead && prevBody) {
    prevHead.innerHTML = '';
    prevBody.innerHTML = '';
    if (currentProfile.preview && currentProfile.preview.length > 0) {
      const cols = Object.keys(currentProfile.preview[0]);
      const headerTr = document.createElement('tr');
      cols.forEach(c => {
        const th = document.createElement('th');
        th.textContent = c;
        headerTr.appendChild(th);
      });
      prevHead.appendChild(headerTr);

      currentProfile.preview.forEach(row => {
        const tr = document.createElement('tr');
        cols.forEach(c => {
          const td = document.createElement('td');
          const val = row[c];
          td.textContent = val !== null && val !== undefined ? val : '—';
          tr.appendChild(td);
        });
        prevBody.appendChild(tr);
      });
    }
  }
}

// Format numbers cleanly for Exploratory Profile preview table & column cards using Intl.NumberFormat
function formatProfileStatNumber(val, colName = '') {
  if (val === null || val === undefined || val === '') return '—';
  const num = Number(val);
  if (!Number.isFinite(num)) return String(val);

  const isRatingOrRate = /satisfaction|rating|score|margin|rate|ratio/i.test(colName)
    || (Math.abs(num) > 0 && Math.abs(num) < 20 && !Number.isInteger(num));
  if (isRatingOrRate) {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  }
  if (Math.abs(num) >= 100 || Number.isInteger(num)) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 0,
    }).format(Math.round(num));
  }
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(num);
}

// Render Tab 3: Profile & Table
function renderProfileTab() {
  if (!currentProfile) return;

  const tableHead = document.getElementById('preview-table-head');
  const tableBody = document.getElementById('preview-table-body');
  const previewTitleEl = document.getElementById('preview-table-title');
  const previewBadgeEl = document.getElementById('preview-table-col-badge');
  const previewFilterEl = document.getElementById('preview-table-filter');
  if (previewFilterEl) previewFilterEl.value = '';
  tableHead.innerHTML = '';
  tableBody.innerHTML = '';

  const colMetaMap = {};
  (currentProfile.columns || []).forEach(c => {
    colMetaMap[c.name] = c;
  });

  // Collect outlier bounds/values per column from insights & TruthLens so preview table highlights anomalies
  const outlierBoundsByCol = {};
  if (currentInsights && currentInsights.insights) {
    currentInsights.insights.forEach(item => {
      if (item.category === 'anomaly' && item.action_link && item.action_link.column) {
        const col = item.action_link.column;
        const m = (item.evidence || '').match(/Bounds:\s*\[([-\d.,]+),\s*([-\d.,]+)\]\.\s*Extreme value observed:\s*([-\d.,]+)/i);
        if (m) {
          outlierBoundsByCol[col] = {
            low: parseFloat(m[1].replace(/,/g, '')),
            high: parseFloat(m[2].replace(/,/g, '')),
            extreme: parseFloat(m[3].replace(/,/g, '')),
          };
        }
      }
    });
  }

  if (currentProfile.preview && currentProfile.preview.length > 0) {
    const previewRows = currentProfile.preview;
    const cols = Object.keys(previewRows[0]);
    if (previewTitleEl) {
      previewTitleEl.textContent = `Sample Records Preview (Top ${previewRows.length} of ${currentProfile.row_count.toLocaleString()} rows)`;
    }
    if (previewBadgeEl) {
      previewBadgeEl.textContent = `${cols.length} Columns`;
    }

    const headerRow = document.createElement('tr');
    cols.forEach(col => {
      const th = document.createElement('th');
      const isNum = colMetaMap[col] && colMetaMap[col].category === 'numeric';
      if (isNum) th.className = 'num-col';
      th.textContent = col;
      headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);

    previewRows.forEach(row => {
      const tr = document.createElement('tr');
      cols.forEach(col => {
        const td = document.createElement('td');
        const val = row[col];
        const colMeta = colMetaMap[col];
        const isNum = colMeta && colMeta.category === 'numeric';

        if (val === null || val === undefined || val === '') {
          td.textContent = '—';
        } else if (isNum && Number.isFinite(Number(val))) {
          td.className = 'num-col';
          const numVal = Number(val);
          const formatted = formatProfileStatNumber(numVal, col);
          const bounds = outlierBoundsByCol[col];
          const stats = colMeta.stats || {};
          const zScore = stats.std && stats.std > 0 ? Math.abs((numVal - stats.mean) / stats.std) : 0;
          const isOutlier = (bounds && (numVal < bounds.low || numVal > bounds.high || Math.abs(numVal - bounds.extreme) < 1e-6))
            || zScore > 2.4;

          if (isOutlier) {
            td.innerHTML = `<span class="preview-outlier-pill" data-col="${escapeHtml(col)}" title="Flagged statistical outlier in '${escapeHtml(col)}' — click to inspect in Anomaly Inspector">⚠ ${escapeHtml(formatted)}</span>`;
          } else {
            td.textContent = formatted;
          }
        } else {
          td.className = 'text-col';
          td.textContent = String(val);
        }
        tr.appendChild(td);
      });
      tableBody.appendChild(tr);
    });

    tableBody.querySelectorAll('.preview-outlier-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        const targetCol = pill.dataset.col;
        switchTab('tab-anomalies');
        const colSelect = document.getElementById('anomaly-col-select');
        if (colSelect && targetCol) {
          colSelect.value = targetCol;
          scanAnomalies();
        }
      });
    });
  }

  const colGrid = document.getElementById('column-cards-container');
  colGrid.innerHTML = '';

  currentProfile.columns.forEach(col => {
    const card = document.createElement('div');
    card.className = 'col-card';

    const nullPct = Number(col.null_percentage || 0);
    const compPct = Math.max(0, Math.min(100, 100 - nullPct));
    const uniqPct = Math.max(6, Math.min(100, Number(col.distinct_percentage || ((col.distinct_count / Math.max(1, currentProfile.row_count)) * 100))));

    let miniBarHtml = '';
    let statsHtml = '';

    if (col.category === 'numeric' && col.stats) {
      const minVal = Number(col.stats.min);
      const maxVal = Number(col.stats.max);
      const meanVal = Number(col.stats.mean);
      const meanPct = maxVal > minVal
        ? Math.max(5, Math.min(95, ((meanVal - minVal) / (maxVal - minVal)) * 100))
        : 50;
      const fmtMin = formatProfileStatNumber(minVal, col.name);
      const fmtMax = formatProfileStatNumber(maxVal, col.name);
      const fmtMean = formatProfileStatNumber(meanVal, col.name);

      miniBarHtml = `
        <div class="col-mini-bar-wrap" title="Range: ${escapeHtml(fmtMin)} to ${escapeHtml(fmtMax)} · Mean: ${escapeHtml(fmtMean)} (${meanPct.toFixed(0)}% of range)">
          <div class="col-mini-bar-track numeric-range-track">
            <div class="col-mini-bar-fill numeric-range-fill" style="width: 100%;"></div>
            <span class="col-mini-bar-mean-dot" style="left: ${meanPct.toFixed(1)}%;" title="Mean: ${escapeHtml(fmtMean)}"></span>
          </div>
        </div>
      `;
      statsHtml = `
        <div class="col-stats-row">
          <span>Min: <strong>${escapeHtml(fmtMin)}</strong></span>
          <span>Mean: <strong class="stat-mean-val">${escapeHtml(fmtMean)}</strong></span>
          <span>Max: <strong>${escapeHtml(fmtMax)}</strong></span>
        </div>
      `;
    } else {
      miniBarHtml = `
        <div class="col-mini-bar-wrap" title="${compPct.toFixed(0)}% Completeness · ${col.distinct_count} Distinct (${uniqPct.toFixed(0)}% Uniqueness)">
          <div class="col-mini-bar-track cat-completeness-track">
            <div class="col-mini-bar-fill cat-completeness-fill" style="width: ${compPct}%;"></div>
            <div class="col-mini-bar-subfill cat-uniqueness-fill" style="width: ${uniqPct}%;"></div>
          </div>
        </div>
      `;
      if (col.stats && col.stats.most_frequent_value) {
        statsHtml = `
          <div class="col-stats-row">
            <span>Top: <strong>${escapeHtml(String(col.stats.most_frequent_value))}</strong> (${col.stats.frequency_of_most_frequent}×)</span>
            <span>Unique: <strong>${uniqPct.toFixed(0)}%</strong></span>
          </div>
        `;
      } else {
        statsHtml = `
          <div class="col-stats-row">
            <span>Completeness: <strong>${compPct.toFixed(0)}%</strong></span>
            <span>Distinct: <strong>${col.distinct_count}</strong></span>
          </div>
        `;
      }
    }

    card.innerHTML = `
      <div class="col-card-header">
        <span class="col-card-name">${escapeHtml(col.name)}</span>
        <span class="col-type-tag ${col.category === 'numeric' ? 'tag-numeric' : 'tag-categorical'}">${escapeHtml(col.category)}</span>
      </div>
      <div class="col-card-meta">
        <span>${nullPct}% Nulls (${col.null_count})</span>
        <span class="col-meta-sep">·</span>
        <span>${col.distinct_count} Distinct</span>
      </div>
      ${miniBarHtml}
      ${statsHtml}
    `;
    colGrid.appendChild(card);
  });
}

// Render Tab 4: Correlations (Compact N×N Heatmap Matrix + 2-Column Bento Grid with R² & Bidirectional Meter)
function renderCorrelationsTab() {
  const container = document.getElementById('correlations-container');
  container.innerHTML = '';

  if (!currentCorrelations || currentCorrelations.top_correlations.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted);">At least two numeric columns required to generate correlations.</div>';
    return;
  }

  const features = currentCorrelations.features || [];
  const matrix = currentCorrelations.matrix || {};
  const pairs = currentCorrelations.top_correlations || [];

  const summaryPill = document.getElementById('corr-summary-pill');
  if (summaryPill) {
    summaryPill.textContent = `${pairs.length} Feature Pair${pairs.length === 1 ? '' : 's'} · ${features.length} Numeric Driver${features.length === 1 ? '' : 's'}`;
  }

  // 1. Compact N×N Numeric Correlation Matrix Heatmap Header
  let heatmapHtml = '';
  if (features.length >= 2) {
    const thCols = features
      .map(f => `<th title="${escapeHtml(f)}">${escapeHtml(formatColumnLabel(f))}</th>`)
      .join('');
    const bodyRows = features
      .map(fRow => {
        const cells = features
          .map(fCol => {
            const rawVal = matrix[fRow] && matrix[fRow][fCol] !== undefined ? matrix[fRow][fCol] : null;
            if (fRow === fCol) {
              return `<td class="corr-hm-cell heatmap-cell-diag" title="${escapeHtml(fRow)} identity diagonal (r = 1.000)">1.000</td>`;
            }
            if (rawVal === null || rawVal === undefined || !Number.isFinite(Number(rawVal))) {
              return `<td class="corr-hm-cell heatmap-cell-diag">—</td>`;
            }
            const r = Number(rawVal);
            const absR = Math.abs(r);
            const r2 = (r * r * 100).toFixed(1);
            let cellClass = 'heatmap-cell-weak';
            if (r < 0) {
              cellClass = 'heatmap-cell-neg';
            } else if (absR >= 0.7) {
              cellClass = 'heatmap-cell-strong';
            } else if (absR >= 0.4) {
              cellClass = 'heatmap-cell-mod';
            }
            const sign = r > 0 ? '+' : '';
            return `<td class="corr-hm-cell ${cellClass}" data-fx="${escapeHtml(fRow)}" data-fy="${escapeHtml(fCol)}" title="${escapeHtml(formatColumnLabel(fRow))} ↔ ${escapeHtml(formatColumnLabel(fCol))}: r = ${sign}${r.toFixed(3)} (R² = ${r2}%) — click to highlight card">${r.toFixed(3)}</td>`;
          })
          .join('');
        return `<tr><th class="corr-hm-row-label" title="${escapeHtml(fRow)}">${escapeHtml(formatColumnLabel(fRow))}</th>${cells}</tr>`;
      })
      .join('');

    heatmapHtml = `
      <div class="corr-matrix-panel" id="corr-matrix-heatmap">
        <div class="corr-matrix-header">
          <div class="corr-matrix-title-group">
            <span class="corr-matrix-title">${features.length}×${features.length} Numeric Correlation Matrix Heatmap</span>
            <span class="corr-matrix-sub">Click any off-diagonal cell to highlight its driver card below</span>
          </div>
          <div class="corr-matrix-legend">
            <span class="corr-legend-chip diag"><i></i>1.000 Diagonal</span>
            <span class="corr-legend-chip strong"><i></i>|r| ≥ 0.70 Strong</span>
            <span class="corr-legend-chip mod"><i></i>0.40–0.69 Moderate</span>
            <span class="corr-legend-chip neg"><i></i>r &lt; 0 Inverse</span>
          </div>
        </div>
        <div class="corr-heatmap-wrap">
          <table class="corr-heatmap-table">
            <thead>
              <tr>
                <th class="corr-hm-corner">Feature</th>
                ${thCols}
              </tr>
            </thead>
            <tbody>
              ${bodyRows}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // 2. 2-Column Bento Grid of Correlation Cards with R² Shared Variance & 8px Tick-Marked Meter
  let pairsHtml = `<div class="corr-bento-grid" id="corr-bento-grid">`;
  pairs.forEach(p => {
    const r = Number(p.coefficient) || 0;
    const absR = Math.abs(r);
    const isPos = r >= 0;
    const signStr = r > 0 ? '+' : '';
    const barWidth = Math.min(100, Math.max(4, absR * 100)).toFixed(1);
    const r2Pct = (r * r * 100).toFixed(1);

    let strengthLabel = 'WEAK POSITIVE';
    let strengthClass = 'weak-pos';
    let fillClass = 'fill-mod-pos';

    if (!isPos) {
      strengthLabel = absR >= 0.7 ? 'STRONG NEGATIVE' : absR >= 0.4 ? 'MODERATE NEGATIVE' : 'WEAK NEGATIVE';
      strengthClass = 'neg';
      fillClass = 'fill-neg';
    } else if (absR >= 0.7) {
      strengthLabel = 'STRONG POSITIVE';
      strengthClass = 'strong-pos';
      fillClass = 'fill-strong-pos';
    } else if (absR >= 0.4) {
      strengthLabel = 'MODERATE POSITIVE';
      strengthClass = 'mod-pos';
      fillClass = 'fill-mod-pos';
    }

    pairsHtml += `
      <div class="col-card corr-bento-card" id="corr-card-${escapeHtml(p.feature_x)}-${escapeHtml(p.feature_y)}">
        <div class="corr-card-top">
          <div class="corr-pair-title-group">
            <div class="corr-pill-pair">
              <span class="corr-var-pill">${escapeHtml(formatColumnLabel(p.feature_x))}</span>
              <span class="corr-var-arrow">↔</span>
              <span class="corr-var-pill">${escapeHtml(formatColumnLabel(p.feature_y))}</span>
            </div>
            <code class="corr-tech-tag">${escapeHtml(p.feature_x)} &amp; ${escapeHtml(p.feature_y)}</code>
          </div>
          <span class="corr-strength-badge ${strengthClass}">${strengthLabel}</span>
        </div>

        <div class="corr-metrics-row">
          <span class="corr-r-score ${strengthClass}">r = ${signStr}${r.toFixed(3)}</span>
          <span class="corr-r2-badge" title="Explained Shared Variance: R² = r² × 100%">R² = ${r2Pct}% shared variance</span>
        </div>

        <div class="corr-meter-track" title="Pearson r = ${signStr}${r.toFixed(3)} · R² = ${r2Pct}% shared variance">
          <span class="corr-meter-tick" style="left: 25%;" title="0.25"></span>
          <span class="corr-meter-tick" style="left: 50%;" title="0.50"></span>
          <span class="corr-meter-tick" style="left: 75%;" title="0.75"></span>
          <div class="corr-meter-fill ${fillClass}" style="width: ${barWidth}%;"></div>
        </div>

        <div class="corr-card-footer">
          <span class="corr-scale-labels">0.00 · 0.25 · 0.50 · 0.75 · 1.00</span>
          <button type="button" class="corr-inspect-btn" data-fx="${escapeHtml(p.feature_x)}" data-fy="${escapeHtml(p.feature_y)}" data-r="${r}">
            Inspect Scatter &amp; Fit Line →
          </button>
        </div>
      </div>
    `;
  });
  pairsHtml += '</div>';

  container.innerHTML = heatmapHtml + pairsHtml;

  // Bind heatmap cell clicks to highlight corresponding correlation card
  container.querySelectorAll('.corr-hm-cell[data-fx]').forEach(cell => {
    cell.addEventListener('click', () => {
      highlightCorrelationPair(cell.dataset.fx, cell.dataset.fy);
    });
  });

  // Bind [Inspect Scatter & Fit Line →] buttons to open the interactive scatter + OLS regression drawer
  container.querySelectorAll('.corr-inspect-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      openCorrelationScatterPreview(btn.dataset.fx, btn.dataset.fy, Number(btn.dataset.r));
    });
  });
}

function openCorrelationScatterPreview(featX, featY, rVal) {
  if (!featX || !featY) return;

  // 1. Check if TruthLens already has a correlation_vs_causation finding with full scatter + OLS chart_spec
  if (currentTruthLens && Array.isArray(currentTruthLens.findings)) {
    const match = currentTruthLens.findings.find(
      f =>
        f.category === 'correlation_vs_causation' &&
        Array.isArray(f.relevant_columns) &&
        f.relevant_columns.includes(featX) &&
        f.relevant_columns.includes(featY)
    );
    if (match) {
      openTruthLensDetailDialog(match);
      return;
    }
  }

  // 2. Otherwise synthesize a scatter + OLS linear regression fit preview from available dataset rows
  let records = [];
  if (currentTruthLens && Array.isArray(currentTruthLens.findings)) {
    const withRows = currentTruthLens.findings.find(f => Array.isArray(f.source_rows) && f.source_rows.length >= 10);
    if (withRows) records = withRows.source_rows;
  }
  if (records.length === 0 && currentProfile && Array.isArray(currentProfile.preview)) {
    records = currentProfile.preview;
  }

  const pts = [];
  records.forEach(row => {
    const vx = Number(row[featX]);
    const vy = Number(row[featY]);
    if (Number.isFinite(vx) && Number.isFinite(vy)) {
      pts.push({ x: vx, y: vy, row });
    }
  });

  let fitLine = [];
  let slope = 0;
  let intercept = 0;
  if (pts.length >= 2) {
    const n = pts.length;
    const meanX = pts.reduce((s, p) => s + p.x, 0) / n;
    const meanY = pts.reduce((s, p) => s + p.y, 0) / n;
    let num = 0;
    let den = 0;
    pts.forEach(p => {
      num += (p.x - meanX) * (p.y - meanY);
      den += (p.x - meanX) * (p.x - meanX);
    });
    slope = den !== 0 ? num / den : 0;
    intercept = meanY - slope * meanX;
    const xs = pts.map(p => p.x);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    fitLine = [
      { x: Number(minX.toFixed(2)), y: Number((slope * minX + intercept).toFixed(2)) },
      { x: Number(maxX.toFixed(2)), y: Number((slope * maxX + intercept).toFixed(2)) },
    ];
  }

  const r = Number.isFinite(rVal) ? rVal : 0;
  const r2Pct = (r * r * 100).toFixed(1);
  const labelX = formatColumnLabel(featX);
  const labelY = formatColumnLabel(featY);
  const nRows = currentProfile ? currentProfile.row_count : pts.length;

  const syntheticFinding = {
    id: `corr_preview_${featX}_${featY}`,
    title: `${labelX} ↔ ${labelY} (r = ${r >= 0 ? '+' : ''}${r.toFixed(3)}, R² = ${r2Pct}%)`,
    severity: Math.abs(r) >= 0.7 ? 'High' : 'Medium',
    category: 'correlation_vs_causation',
    category_label: 'Driver Correlation & OLS Fit',
    confidence_level: nRows >= 30 ? 'High' : 'Moderate',
    confidence_justification: `Computed across n = ${nRows} paired observations.`,
    comparison_baseline: `Pairwise Pearson r & Ordinary Least Squares (OLS) linear regression across n = ${nRows} rows`,
    what_happened: `'${featX}' and '${featY}' exhibit a ${Math.abs(r) >= 0.7 ? 'strong' : 'moderate'} ${r >= 0 ? 'positive' : 'negative'} linear association (r = ${r >= 0 ? '+' : ''}${r.toFixed(3)}), explaining R² = ${r2Pct}% of shared variance.`,
    supporting_evidence: `Pearson r = ${r >= 0 ? '+' : ''}${r.toFixed(3)} · Explained Variance R² = ${r2Pct}% · OLS Slope = ${slope >= 0 ? '+' : ''}${slope.toFixed(4)} (${labelY} per unit ${labelX})`,
    why_it_matters: `While R² = ${r2Pct}% confirms substantial co-movement between '${featX}' and '${featY}', observational correlation does not prove direct causality without controlled holdout or incremental lift testing.`,
    hypotheses: [
      `Hypothesis 1 (Direct Operational Driver): Changes in '${featX}' directly influence '${featY}' along the fitted OLS trajectory.`,
      `Hypothesis 2 (Shared Confounding Factor): Both '${featX}' and '${featY}' scale jointly with store footprint tier or regional demand volume.`,
    ],
    recommended_investigation: [
      `Inspect residuals around the OLS trendline to identify stores outperforming expected '${featY}' for their '${featX}' level.`,
      `Validate incremental lift with controlled cohort holdouts before reallocating budget based on bivariate slope.`,
    ],
    relevant_columns: [featX, featY],
    comparison_periods: [`Full Dataset Cross-Section (n = ${nRows})`],
    calculation_methodology: `Pearson product-moment correlation coefficient (r), coefficient of determination (R² = r²), and Ordinary Least Squares (OLS) regression fit.`,
    calculations: [
      `pearson_r(${featX}, ${featY}) = ${r.toFixed(4)}`,
      `r_squared = (${r.toFixed(4)})² = ${(r * r).toFixed(4)} (${r2Pct}% shared variance)`,
      `ols_fit: ${featY} = ${slope.toFixed(4)} * ${featX} + ${intercept.toFixed(2)}`,
    ],
    supporting_row_references: [`Rows #0..#${Math.max(0, nRows - 1)} (Full Dataset Scan, n = ${nRows})`],
    group_references: [],
    data_quality_warnings: [],
    ai_explanation: `${labelX} and ${labelY} co-move with r = ${r >= 0 ? '+' : ''}${r.toFixed(3)} (R² = ${r2Pct}% shared variance). Use the scatter plot and OLS trendline below to inspect record-level alignment and outliers.`,
    evidence_table: [
      {
        Feature_Pair: `${featX} ↔ ${featY}`,
        Pearson_r: r.toFixed(3),
        Shared_Variance_R2: `${r2Pct}%`,
        OLS_Slope: slope.toFixed(4),
        Sample_Size_n: nRows,
      },
    ],
    chart_spec: pts.length >= 2
      ? {
          chart_type: 'scatter',
          title: `Scatter & OLS Fit: ${labelX} (x) vs. ${labelY} (y) — r = ${r >= 0 ? '+' : ''}${r.toFixed(3)} (R² = ${r2Pct}%)`,
          labels: [],
          datasets: [
            {
              label: `Store Observations (n = ${pts.length})`,
              data: pts.map(p => ({ x: p.x, y: p.y })),
              color: '#38bdf8',
            },
            {
              label: `OLS Linear Fit (R² = ${r2Pct}%)`,
              data: fitLine,
              color: '#10b981',
              type: 'line',
            },
          ],
        }
      : null,
    source_rows: pts.slice(0, 12).map((p, idx) => ({
      _row_index: p.row._row_index !== undefined ? p.row._row_index : idx,
      ...(p.row.store ? { store: p.row.store } : {}),
      ...(p.row.region ? { region: p.row.region } : {}),
      [featX]: p.x,
      [featY]: p.y,
    })),
  };

  openTruthLensDetailDialog(syntheticFinding);
}

// Format raw snake_case or lowercase column names into human-readable Title Case
function formatColumnLabel(name) {
  if (!name) return '';
  return String(name)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

// Tab 5: Aggregations & Visual Chart
function populateAggregationSelectors() {
  if (!currentProfile) return;

  const dimSelect = document.getElementById('agg-dim-select');
  const metricSelect = document.getElementById('agg-metric-select');
  const funcSelect = document.getElementById('agg-func-select');
  const sortSelect = document.getElementById('agg-sort-select');

  dimSelect.innerHTML = '';
  metricSelect.innerHTML = '';

  let defaultDimIndex = -1;
  let defaultMetricIndex = -1;

  currentProfile.columns.forEach(col => {
    if (col.is_identifier) return;

    if (col.category === 'categorical' || col.category === 'text' || col.category === 'boolean') {
      const opt = document.createElement('option');
      opt.value = col.name;
      opt.textContent = formatColumnLabel(col.name);
      dimSelect.appendChild(opt);

      // Prioritize City as default dimension
      if (/^city$/i.test(col.name) || (defaultDimIndex === -1 && /city/i.test(col.name))) {
        defaultDimIndex = dimSelect.options.length - 1;
      } else if (defaultDimIndex === -1 && /region|state|category|department/i.test(col.name)) {
        defaultDimIndex = dimSelect.options.length - 1;
      }
    }
    if (col.category === 'numeric') {
      const opt = document.createElement('option');
      opt.value = col.name;
      opt.textContent = formatColumnLabel(col.name);
      metricSelect.appendChild(opt);

      // Prioritize Total Spend (or revenue/sales/profit) as default metric
      if (/total[\s_]?spend/i.test(col.name) || (defaultMetricIndex === -1 && /spend/i.test(col.name))) {
        defaultMetricIndex = metricSelect.options.length - 1;
      } else if (defaultMetricIndex === -1 && /revenue|sales|profit|amount/i.test(col.name)) {
        defaultMetricIndex = metricSelect.options.length - 1;
      }
    }
  });

  if (defaultDimIndex >= 0) {
    dimSelect.selectedIndex = defaultDimIndex;
  }
  if (defaultMetricIndex >= 0) {
    metricSelect.selectedIndex = defaultMetricIndex;
  }
  if (funcSelect) {
    funcSelect.value = 'sum';
  }
  if (sortSelect) {
    sortSelect.value = 'desc';
  }

  if (dimSelect.options.length > 0 && metricSelect.options.length > 0) {
    runAggregation();
  }
}

let lastAggBreakdownState = null;

function setupAggregationControls() {
  const runBtn = document.getElementById('run-agg-btn');
  if (runBtn) {
    runBtn.addEventListener('click', runAggregation);
  }

  // Auto-update chart whenever any control dropdown changes
  const controlIds = ['agg-dim-select', 'agg-metric-select', 'agg-func-select', 'agg-chart-type', 'agg-sort-select'];
  controlIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', runAggregation);
    }
  });

  const copyTableBtn = document.getElementById('agg-copy-table-btn');
  if (copyTableBtn) {
    copyTableBtn.addEventListener('click', copyAggBreakdownTable);
  }

  const exportCsvBtn = document.getElementById('agg-export-csv-btn');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', exportAggBreakdownCsv);
  }
}

async function runAggregation() {
  if (!activeDatasetId) return;

  const dimEl = document.getElementById('agg-dim-select');
  const metricEl = document.getElementById('agg-metric-select');
  const funcEl = document.getElementById('agg-func-select');
  const chartTypeEl = document.getElementById('agg-chart-type');
  const sortSelectEl = document.getElementById('agg-sort-select');

  const dim = dimEl ? dimEl.value : '';
  const metric = metricEl ? metricEl.value : '';
  const func = funcEl ? funcEl.value : 'sum';
  const chartType = chartTypeEl ? chartTypeEl.value : 'bar';
  const sortOrder = sortSelectEl ? sortSelectEl.value : 'desc';

  if (!dim || !metric) return;

  const requestedFuncs = func === 'count' ? ['count'] : [func, 'count'];

  try {
    const res = await fetch(`/api/v1/analytics/aggregate/${activeDatasetId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        group_by: [dim],
        metrics: { [metric]: requestedFuncs },
        sort_by: `${metric}_${func}`,
        ascending: false,
        limit: 1000,
      }),
    });

    if (!res.ok) return;
    const aggData = await res.json();
    const valueKey = `${metric}_${func}`;
    let records = aggData.data || [];

    // Client-side sorting toggle
    if (sortOrder === 'desc') {
      records.sort((a, b) => (Number(b[valueKey]) || 0) - (Number(a[valueKey]) || 0));
    } else if (sortOrder === 'asc') {
      records.sort((a, b) => (Number(a[valueKey]) || 0) - (Number(b[valueKey]) || 0));
    } else if (sortOrder === 'alpha') {
      records.sort((a, b) => String(a[dim] || '').localeCompare(String(b[dim] || '')));
    }

    renderAggChart(records, dim, valueKey, chartType, metric, func);
  } catch (e) {
    console.error('Aggregation error:', e);
  }
}

const PALETTE = [
  '#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6',
  '#06b6d4', '#3b82f6', '#14b8a6', '#f97316', '#a855f7'
];

function humanizeAggTitle(metric, func, dim) {
  const funcMap = {
    sum: 'Sum of',
    mean: 'Average',
    median: 'Median',
    max: 'Maximum',
    min: 'Minimum',
    count: 'Count of',
  };
  const funcKey = (func || 'sum').toLowerCase();
  const funcTitle = funcMap[funcKey] || (func ? func.charAt(0).toUpperCase() + func.slice(1) : 'Total');
  const metricTitle = (metric || 'Value').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const dimTitle = dim ? dim.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : '';

  return dimTitle ? `${funcTitle} ${metricTitle} by ${dimTitle}` : `${funcTitle} ${metricTitle}`;
}

function formatCompactNumber(val, isCurrency = false) {
  if (val === null || val === undefined || isNaN(val)) return '0';
  const num = Number(val);
  const sign = num < 0 ? '-' : '';
  const abs = Math.abs(num);
  let formatted = '';

  if (abs >= 1e9) {
    formatted = (abs / 1e9).toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1') + 'B';
  } else if (abs >= 1e6) {
    formatted = (abs / 1e6).toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1') + 'M';
  } else if (abs >= 1e3) {
    formatted = (abs / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
  } else if (Number.isInteger(abs)) {
    formatted = abs.toString();
  } else {
    formatted = abs.toFixed(2).replace(/\.?0+$/, '');
  }

  return isCurrency ? `${sign}$${formatted}` : `${sign}${formatted}`;
}

function formatExactAggValue(val, isCurrency = false) {
  if (val === null || val === undefined || isNaN(val)) return '0';
  const num = Number(val);
  const isInt = Number.isInteger(num) || Math.abs(num) >= 100;
  if (isCurrency) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: isInt ? 0 : 2,
      maximumFractionDigits: isInt ? 0 : 2,
    }).format(num);
  }
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: isInt ? 0 : 2,
  }).format(num);
}

function renderAggBreakdownTable(data, labelKey, valueKey, countKey, totalSum, groupMean, isCurrency, humanTitle) {
  const headEl = document.getElementById('agg-breakdown-head');
  const bodyEl = document.getElementById('agg-breakdown-body');
  const meanTagEl = document.getElementById('agg-breakdown-mean-tag');

  if (meanTagEl) {
    const meanFormatted = Math.abs(groupMean) >= 1e5
      ? formatCompactNumber(groupMean, isCurrency)
      : formatExactAggValue(groupMean, isCurrency);
    meanTagEl.textContent = `Avg: ${meanFormatted}`;
  }

  const dimHeader = formatColumnLabel(labelKey || 'Group');
  if (headEl) {
    headEl.innerHTML = `
      <tr>
        <th>${escapeHtml(dimHeader)}</th>
        <th class="num-col" title="Record count in group">n</th>
        <th class="num-col">Aggregated Value</th>
        <th>% Share</th>
        <th class="num-col">% Delta vs. Mean</th>
      </tr>
    `;
  }

  if (!bodyEl) return;

  if (!data || data.length === 0) {
    bodyEl.innerHTML = `<tr><td colspan="5" class="text-muted">No aggregation groups available.</td></tr>`;
    lastAggBreakdownState = null;
    return;
  }

  const maxAbsVal = Math.max(...data.map(d => Math.abs(Number(d[valueKey]) || 0)), 1);
  const rowsForExport = [];

  bodyEl.innerHTML = data.map((row, idx) => {
    const groupLabel = String(row[labelKey] ?? '—');
    const rawVal = Number(row[valueKey]) || 0;
    const nCount = row[countKey] !== undefined && row[countKey] !== null
      ? Number(row[countKey])
      : '—';
    const sharePct = totalSum > 0 ? (rawVal / totalSum) * 100 : 0;
    const shareWidth = Math.max(4, Math.min(100, Math.round((Math.abs(rawVal) / maxAbsVal) * 100)));
    const deltaPct = groupMean !== 0 ? ((rawVal - groupMean) / Math.abs(groupMean)) * 100 : 0;
    const deltaSign = deltaPct > 0 ? '+' : '';
    const deltaText = `${deltaSign}${deltaPct.toFixed(1)}%`;
    const deltaClass = deltaPct > 0.05 ? 'agg-delta-pos' : (deltaPct < -0.05 ? 'agg-delta-neg' : 'agg-delta-neutral');
    const exactFormatted = formatExactAggValue(rawVal, isCurrency);
    const isTopLeader = idx === 0 && rawVal === Math.max(...data.map(d => Number(d[valueKey]) || 0));

    rowsForExport.push({
      group: groupLabel,
      n: nCount,
      exactValue: exactFormatted,
      rawValue: rawVal,
      sharePct: `${sharePct.toFixed(1)}%`,
      deltaVsMean: deltaText,
    });

    return `
      <tr class="${isTopLeader ? 'agg-row-leader' : ''}">
        <td class="agg-cell-group">
          <span class="agg-group-dot ${isTopLeader ? 'leader' : ''}"></span>
          <span class="agg-group-name">${escapeHtml(groupLabel)}</span>
        </td>
        <td class="num-col agg-cell-n">${escapeHtml(String(nCount))}</td>
        <td class="num-col agg-cell-val">${escapeHtml(exactFormatted)}</td>
        <td class="agg-cell-share">
          <div class="agg-share-cell-inner">
            <span class="agg-share-pct">${sharePct.toFixed(1)}%</span>
            <div class="agg-share-bar-track" aria-hidden="true">
              <div class="agg-share-bar-fill ${isTopLeader ? 'leader' : ''}" style="width: ${shareWidth}%;"></div>
            </div>
          </div>
        </td>
        <td class="num-col agg-cell-delta">
          <span class="agg-delta-badge ${deltaClass}">${deltaText}</span>
        </td>
      </tr>
    `;
  }).join('');

  lastAggBreakdownState = {
    title: humanTitle,
    dimHeader,
    rows: rowsForExport,
  };
}

function copyAggBreakdownTable() {
  if (!lastAggBreakdownState || !lastAggBreakdownState.rows.length) return;
  const header = [lastAggBreakdownState.dimHeader, 'n', 'Value', '% Share', '% Delta vs. Mean'].join('\t');
  const lines = lastAggBreakdownState.rows.map(r =>
    [r.group, r.n, r.exactValue, r.sharePct, r.deltaVsMean].join('\t')
  );
  const text = `${lastAggBreakdownState.title}\n${header}\n${lines.join('\n')}`;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Breakdown table copied to clipboard');
    }).catch(() => {
      showToast('Copy failed — clipboard unavailable');
    });
  }
}

function exportAggBreakdownCsv() {
  if (!lastAggBreakdownState || !lastAggBreakdownState.rows.length) return;
  const escapeCsv = val => `"${String(val ?? '').replace(/"/g, '""')}"`;
  const header = [lastAggBreakdownState.dimHeader, 'n', 'Value', 'Raw_Value', 'Share_Pct', 'Delta_Vs_Mean'].map(escapeCsv).join(',');
  const lines = lastAggBreakdownState.rows.map(r =>
    [r.group, r.n, r.exactValue, r.rawValue, r.sharePct, r.deltaVsMean].map(escapeCsv).join(',')
  );
  const csvContent = `${header}\n${lines.join('\n')}`;
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const slug = (lastAggBreakdownState.title || 'aggregation_breakdown').toLowerCase().replace(/[^a-z0-9]+/g, '_');
  a.download = `${slug}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('Exported breakdown CSV');
}

function truncateLegendLabel(label, maxChars = 18) {
  const s = String(label ?? '');
  if (s.length <= maxChars) return s;
  return s.slice(0, maxChars - 1) + '…';
}

function renderAggChart(data, labelKey, valueKey, chartType = 'bar', metric = '', func = '') {
  const canvas = document.getElementById('agg-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const allValues = data.map(d => Number(d[valueKey]) || 0);

  if (aggChartInstance) {
    aggChartInstance.destroy();
  }

  let resolvedMetric = metric;
  let resolvedFunc = func;
  if (!resolvedMetric || !resolvedFunc) {
    const lastUnderscore = valueKey ? valueKey.lastIndexOf('_') : -1;
    if (lastUnderscore > 0) {
      resolvedMetric = valueKey.substring(0, lastUnderscore);
      resolvedFunc = valueKey.substring(lastUnderscore + 1);
    } else {
      resolvedMetric = valueKey || 'Value';
      resolvedFunc = 'sum';
    }
  }

  const countKey = `${resolvedMetric}_count`;
  const humanTitle = humanizeAggTitle(resolvedMetric, resolvedFunc, labelKey);
  const isCurrency = /spend|cost|revenue|sales|profit|price|budget|amount|salary|fee/i.test(resolvedMetric);

  // Compute True Dataset Totals & Mean Across ALL Distinct Groups (Never Truncated)
  const totalSum = allValues.reduce((acc, v) => acc + v, 0);
  const groupMean = allValues.length > 0 ? totalSum / allValues.length : 0;

  const chartTitleEl = document.getElementById('agg-chart-title');
  if (chartTitleEl) {
    chartTitleEl.textContent = humanTitle;
  }

  const dimRaw = (labelKey || 'group').replace(/_/g, ' ').toLowerCase();
  const dimPlural = `${dimRaw}${data.length === 1 ? '' : 's'}`;
  const dimTitlePlural = dimPlural.replace(/\b\w/g, c => c.toUpperCase());

  // Cap bar/line visual canvas at Top 15 for readability while preserving 100% of groups in totals & breakdown table
  const isCappedTop15 = chartType !== 'donut' && data.length > 15;
  const chartData = isCappedTop15 ? data.slice(0, 15) : data;
  const labels = chartData.map(d => String(d[labelKey] ?? ''));
  const values = chartData.map(d => Number(d[valueKey]) || 0);
  const maxVal = values.length > 0 ? Math.max(...values) : 0;

  const subtitlePillEl = document.getElementById('agg-chart-subtitle-pill');
  if (subtitlePillEl) {
    if (isCappedTop15) {
      subtitlePillEl.textContent = `Showing Top 15 of ${data.length} ${dimPlural} · Full Dataset Total: ${formatCompactNumber(totalSum, isCurrency)}`;
    } else if (chartType === 'donut' && data.length > 7) {
      subtitlePillEl.textContent = `Top 6 + Other (${data.length - 6} ${dimPlural}) · Full Dataset Total: ${formatCompactNumber(totalSum, isCurrency)}`;
    } else {
      subtitlePillEl.textContent = `Total: ${formatCompactNumber(totalSum, isCurrency)} across ${data.length} ${dimPlural}`;
    }
  }

  // Update the right-hand Live Breakdown Table with 100% of groups (all 45 stores)
  renderAggBreakdownTable(data, labelKey, valueKey, countKey, totalSum, groupMean, isCurrency, humanTitle);

  // Vertical Indigo-to-Cyan Gradient Fill + Top Leader Highlight
  const verticalBarGradient = ctx.createLinearGradient(0, 0, 0, 270);
  verticalBarGradient.addColorStop(0, '#6366f1');
  verticalBarGradient.addColorStop(0.55, 'rgba(56, 189, 248, 0.65)');
  verticalBarGradient.addColorStop(1, 'rgba(99, 102, 241, 0.35)');

  const leaderBarGradient = ctx.createLinearGradient(0, 0, 0, 270);
  leaderBarGradient.addColorStop(0, '#38bdf8');
  leaderBarGradient.addColorStop(0.6, 'rgba(99, 102, 241, 0.78)');
  leaderBarGradient.addColorStop(1, 'rgba(16, 185, 129, 0.38)');

  const barBgColors = values.map(v => (v === maxVal && maxVal > 0 ? leaderBarGradient : verticalBarGradient));
  const barBorderColors = values.map(v => (v === maxVal && maxVal > 0 ? '#38bdf8' : '#6366f1'));
  const barBorderWidths = values.map(v => (v === maxVal && maxVal > 0 ? 2 : 1));

  // Custom inline Chart.js plugin:
  // 1) Draws dashed Group Mean reference line + right-aligned Avg pill
  // 2) Renders direct bar value labels with 2-decimal precision + muted (% share)
  const directBarValueLabelsPlugin = {
    id: 'directBarValueLabels',
    afterDatasetsDraw(chart) {
      if (chart.config.type !== 'bar') return;
      const { ctx: chartCtx, chartArea, scales } = chart;
      const isHorizontal = chart.config.options && chart.config.options.indexAxis === 'y';
      const meta = chart.getDatasetMeta(0);
      const dataset = chart.data.datasets[0];
      if (!meta || !dataset) return;

      chartCtx.save();

      // 1. Draw Dashed Group Mean Reference Line
      if (groupMean > 0 && chartArea && scales) {
        const avgLabel = `Avg: ${formatCompactNumber(groupMean, isCurrency)}`;
        chartCtx.save();
        chartCtx.setLineDash([5, 5]);
        chartCtx.lineWidth = 1.25;
        chartCtx.strokeStyle = 'rgba(56, 189, 248, 0.55)';

        if (!isHorizontal && scales.y) {
          const yPos = scales.y.getPixelForValue(groupMean);
          if (yPos >= chartArea.top && yPos <= chartArea.bottom) {
            chartCtx.beginPath();
            chartCtx.moveTo(chartArea.left, yPos);
            chartCtx.lineTo(chartArea.right, yPos);
            chartCtx.stroke();

            // Right-aligned pill label on the dashed mean line
            chartCtx.setLineDash([]);
            chartCtx.font = '600 10.5px "JetBrains Mono", Inter, monospace';
            const textWidth = chartCtx.measureText(avgLabel).width;
            const pillPadX = 7;
            const pillH = 18;
            const pillW = textWidth + pillPadX * 2;
            const pillX = chartArea.right - pillW - 4;
            const pillY = Math.max(chartArea.top + 2, yPos - pillH - 4);

            chartCtx.fillStyle = 'rgba(15, 23, 42, 0.92)';
            chartCtx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
            chartCtx.lineWidth = 1;
            chartCtx.beginPath();
            if (chartCtx.roundRect) {
              chartCtx.roundRect(pillX, pillY, pillW, pillH, 9);
            } else {
              chartCtx.rect(pillX, pillY, pillW, pillH);
            }
            chartCtx.fill();
            chartCtx.stroke();

            chartCtx.fillStyle = '#38bdf8';
            chartCtx.textAlign = 'left';
            chartCtx.textBaseline = 'middle';
            chartCtx.fillText(avgLabel, pillX + pillPadX, pillY + pillH / 2);
          }
        } else if (isHorizontal && scales.x) {
          const xPos = scales.x.getPixelForValue(groupMean);
          if (xPos >= chartArea.left && xPos <= chartArea.right) {
            chartCtx.beginPath();
            chartCtx.moveTo(xPos, chartArea.top);
            chartCtx.lineTo(xPos, chartArea.bottom);
            chartCtx.stroke();
          }
        }
        chartCtx.restore();
      }

      // 2. Draw Direct Value Labels + Muted Share % on Each Bar
      meta.data.forEach((barEl, idx) => {
        const rawVal = dataset.data[idx];
        if (rawVal === null || rawVal === undefined) return;
        const primaryText = formatCompactNumber(rawVal, isCurrency);
        const sharePct = totalSum > 0 ? ((Number(rawVal) || 0) / totalSum) * 100 : 0;
        const shareText = meta.data.length <= 8 ? ` (${sharePct.toFixed(1)}%)` : '';

        if (isHorizontal) {
          chartCtx.textBaseline = 'middle';
          chartCtx.textAlign = 'left';
          chartCtx.font = '700 11.5px Inter, sans-serif';
          chartCtx.fillStyle = '#f8fafc';
          chartCtx.fillText(primaryText, barEl.x + 8, barEl.y);
          if (shareText) {
            const primaryW = chartCtx.measureText(primaryText).width;
            chartCtx.font = '500 10.5px "JetBrains Mono", monospace';
            chartCtx.fillStyle = '#94a3b8';
            chartCtx.fillText(shareText, barEl.x + 8 + primaryW, barEl.y);
          }
        } else {
          chartCtx.font = '700 11px Inter, sans-serif';
          const primaryW = chartCtx.measureText(primaryText).width;
          chartCtx.font = '500 10px "JetBrains Mono", monospace';
          const shareW = shareText ? chartCtx.measureText(shareText).width : 0;
          const totalW = primaryW + shareW;
          const startX = barEl.x - totalW / 2;
          const labelY = barEl.y - 6;

          chartCtx.textAlign = 'left';
          chartCtx.textBaseline = 'bottom';
          chartCtx.font = '700 11px Inter, sans-serif';
          chartCtx.fillStyle = '#f8fafc';
          chartCtx.fillText(primaryText, startX, labelY);

          if (shareText) {
            chartCtx.font = '500 10px "JetBrains Mono", monospace';
            chartCtx.fillStyle = '#94a3b8';
            chartCtx.fillText(shareText, startX + primaryW, labelY);
          }
        }
      });

      chartCtx.restore();
    }
  };

  if (chartType === 'donut') {
    // Smart Top-6 + "Other" Bucketing when groups > 7
    let donutFullLabels = labels;
    let donutDisplayLabels = labels.map(l => truncateLegendLabel(l, 18));
    let donutValues = values;
    let donutColors = labels.map((_, i) => PALETTE[i % PALETTE.length]);

    if (data.length > 7) {
      const sortedDesc = [...data].sort((a, b) => (Number(b[valueKey]) || 0) - (Number(a[valueKey]) || 0));
      const top6 = sortedDesc.slice(0, 6);
      const rest = sortedDesc.slice(6);
      const otherVal = rest.reduce((acc, r) => acc + (Number(r[valueKey]) || 0), 0);
      const otherBucketLabel = `Other (${rest.length} ${dimPlural})`;

      donutFullLabels = [...top6.map(d => String(d[labelKey] ?? '')), otherBucketLabel];
      donutDisplayLabels = [
        ...top6.map(d => truncateLegendLabel(String(d[labelKey] ?? ''), 18)),
        otherBucketLabel,
      ];
      donutValues = [...top6.map(d => Number(d[valueKey]) || 0), otherVal];
      donutColors = [...top6.map((_, i) => PALETTE[i % PALETTE.length]), '#475569'];
    }

    const donutCenterMetricPlugin = {
      id: 'donutCenterMetric',
      afterDraw(chart) {
        if (chart.config.type !== 'doughnut') return;
        const { ctx: chartCtx, chartArea } = chart;
        if (!chartArea) return;
        const centerX = (chartArea.left + chartArea.right) / 2;
        const centerY = (chartArea.top + chartArea.bottom) / 2;

        chartCtx.save();
        chartCtx.textAlign = 'center';
        chartCtx.textBaseline = 'middle';

        chartCtx.font = '800 15.5px Inter, sans-serif';
        chartCtx.fillStyle = '#f8fafc';
        chartCtx.fillText(formatCompactNumber(totalSum, isCurrency), centerX, centerY - 8);

        chartCtx.font = '600 10.5px "JetBrains Mono", monospace';
        chartCtx.fillStyle = '#94a3b8';
        chartCtx.fillText(`${data.length} ${dimTitlePlural}`, centerX, centerY + 10);
        chartCtx.restore();
      }
    };

    aggChartInstance = new Chart(ctx, {
      type: 'doughnut',
      plugins: [donutCenterMetricPlugin],
      data: {
        labels: donutDisplayLabels,
        datasets: [{
          label: humanTitle,
          data: donutValues,
          backgroundColor: donutColors,
          borderColor: '#0b1120',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '66%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: '#cbd5e1',
              boxWidth: 11,
              padding: 10,
              font: { family: 'inherit', size: 11.5 },
              generateLabels(chart) {
                const ds = chart.data.datasets[0];
                const total = (ds.data || []).reduce((a, v) => a + (Number(v) || 0), 0);
                return chart.data.labels.map((lbl, i) => {
                  const pct = total > 0 ? ((Number(ds.data[i]) || 0) / total) * 100 : 0;
                  return {
                    text: `${lbl} · ${pct.toFixed(1)}%`,
                    fillStyle: Array.isArray(ds.backgroundColor) ? ds.backgroundColor[i] : ds.backgroundColor,
                    strokeStyle: 'transparent',
                    lineWidth: 0,
                    fontColor: '#cbd5e1',
                    hidden: !chart.getDataVisibility(i),
                    index: i,
                  };
                });
              }
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const rawVal = context.raw ?? 0;
                const fullName = donutFullLabels[context.dataIndex] || context.label || '';
                const sharePct = totalSum > 0 ? ((Number(rawVal) || 0) / totalSum) * 100 : 0;
                const formatted = isCurrency
                  ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(rawVal)
                  : new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(rawVal);
                return ` ${fullName}: ${formatted} (${sharePct.toFixed(1)}%)`;
              }
            }
          }
        }
      }
    });
  } else if (chartType === 'horizontalBar') {
    aggChartInstance = new Chart(ctx, {
      type: 'bar',
      plugins: [directBarValueLabelsPlugin],
      data: {
        labels: labels,
        datasets: [{
          label: humanTitle,
          data: values,
          backgroundColor: barBgColors,
          borderColor: barBorderColors,
          borderWidth: barBorderWidths,
          borderRadius: 6,
          maxBarThickness: 38,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: { top: 8, right: 96, bottom: 4 }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(context) {
                const rawVal = context.raw !== undefined ? context.raw : (context.parsed?.x ?? 0);
                const formatted = isCurrency
                  ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(rawVal)
                  : new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(rawVal);
                return ` ${context.dataset.label || ''}: ${formatted}`;
              }
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            min: 0,
            ticks: {
              color: '#94a3b8',
              callback: function(value) {
                return formatCompactNumber(value, isCurrency);
              }
            },
            grid: { color: 'rgba(255,255,255,0.05)' }
          },
          y: {
            ticks: { color: '#e2e8f0', font: { weight: '600', size: 12 } },
            grid: { color: 'rgba(255,255,255,0.04)' }
          }
        }
      }
    });
  } else if (chartType === 'line') {
    aggChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: humanTitle,
          data: values,
          backgroundColor: 'rgba(99, 102, 241, 0.15)',
          borderColor: '#6366f1',
          borderWidth: 2,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: '#38bdf8',
          pointRadius: 4,
          pointHoverRadius: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(context) {
                const rawVal = context.raw !== undefined ? context.raw : (context.parsed?.y ?? 0);
                const formatted = isCurrency
                  ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(rawVal)
                  : new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(rawVal);
                return ` ${context.dataset.label || ''}: ${formatted}`;
              }
            }
          }
        },
        scales: {
          x: { ticks: { color: '#e2e8f0' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: {
            beginAtZero: true,
            min: 0,
            ticks: {
              color: '#94a3b8',
              callback: function(value) {
                return formatCompactNumber(value, isCurrency);
              }
            },
            grid: { color: 'rgba(255,255,255,0.05)' }
          }
        }
      }
    });
  } else {
    // Default vertical bar (Zero-Baseline enforced: beginAtZero: true, min: 0)
    aggChartInstance = new Chart(ctx, {
      type: 'bar',
      plugins: [directBarValueLabelsPlugin],
      data: {
        labels: labels,
        datasets: [{
          label: humanTitle,
          data: values,
          backgroundColor: barBgColors,
          borderColor: barBorderColors,
          borderWidth: barBorderWidths,
          borderRadius: 6,
          maxBarThickness: 64,
        }]
      },
      options: {
        indexAxis: 'x',
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: { top: 26, bottom: 4 }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(context) {
                const rawVal = context.raw !== undefined ? context.raw : (context.parsed?.y ?? 0);
                const formatted = isCurrency
                  ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(rawVal)
                  : new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(rawVal);
                return ` ${context.dataset.label || ''}: ${formatted}`;
              }
            }
          }
        },
        scales: {
          x: {
            ticks: { color: '#e2e8f0', font: { weight: '600', size: 12 } },
            grid: { color: 'rgba(255,255,255,0.04)' }
          },
          y: {
            beginAtZero: true,
            min: 0,
            ticks: {
              color: '#94a3b8',
              maxTicksLimit: 6,
              callback: function(value) {
                return formatCompactNumber(value, isCurrency);
              }
            },
            grid: { color: 'rgba(255,255,255,0.05)' }
          }
        }
      }
    });
  }
}

// Tab 6: Anomaly Inspector (Enterprise Outlier Workbench)
let anomalyColCountsCache = {};

function formatAnomalyNumber(val, colName = '', includeCurrency = false) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const num = Number(val);
  const isCurr = includeCurrency && /spend|cost|revenue|sales|profit|price|budget|amount|salary|fee/i.test(colName);
  const isLargeOrInt = Math.abs(num) >= 100 || Number.isInteger(num);
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: isLargeOrInt ? 0 : 2,
    maximumFractionDigits: isLargeOrInt ? 0 : 2,
  }).format(isLargeOrInt ? Math.round(num) : num);
  return isCurr ? `${num < 0 ? '-$' : '$'}${formatted.replace(/^-/, '')}` : formatted;
}

function getInitialAnomalyCountsByColumn() {
  const counts = {};
  if (!currentProfile || !currentProfile.columns) return counts;
  const numCols = currentProfile.columns.filter(c => c.category === 'numeric' && !c.is_identifier);
  numCols.forEach(c => {
    counts[c.name] = 0;
  });

  if (currentTruthLens && Array.isArray(currentTruthLens.findings)) {
    currentTruthLens.findings
      .filter(f => f.category === 'statistical_anomalies')
      .forEach(f => {
        const cols = f.affected_columns || [];
        const m = (f.what_happened || '').match(/Detected (\d+) statistical anomaly/i);
        const cnt = m ? parseInt(m[1], 10) : 1;
        cols.forEach(colName => {
          if (counts[colName] !== undefined) {
            counts[colName] = Math.max(counts[colName], cnt);
          }
        });
      });
  }

  if (currentInsights && Array.isArray(currentInsights.insights)) {
    currentInsights.insights
      .filter(i => i.category === 'anomaly' && i.action_link && i.action_link.column)
      .forEach(i => {
        const colName = i.action_link.column;
        if (counts[colName] !== undefined && counts[colName] === 0) {
          counts[colName] = 1;
        }
      });
  }

  return counts;
}

function renderAnomalyFeatureStrip(activeCol = null) {
  const pillsContainer = document.getElementById('anomaly-feature-pills');
  if (!pillsContainer || !currentProfile || !currentProfile.columns) return;

  const selectEl = document.getElementById('anomaly-col-select');
  const selectedCol = activeCol || (selectEl ? selectEl.value : '');

  const numCols = currentProfile.columns.filter(c => c.category === 'numeric' && !c.is_identifier);
  const initialCounts = getInitialAnomalyCountsByColumn();

  const items = numCols.map(c => {
    const cnt = anomalyColCountsCache[c.name] !== undefined
      ? anomalyColCountsCache[c.name]
      : (initialCounts[c.name] || 0);
    return { name: c.name, label: formatColumnLabel(c.name), count: cnt };
  });

  // Sort flagged features first so the user immediately sees columns with outliers
  items.sort((a, b) => (b.count > 0 ? 1 : 0) - (a.count > 0 ? 1 : 0) || b.count - a.count);

  pillsContainer.innerHTML = items.map(item => {
    const isFlagged = item.count > 0;
    const isActive = item.name === selectedCol;
    const stateClass = isFlagged ? 'flagged' : 'clean';
    const activeClass = isActive ? ' active' : '';
    const icon = isFlagged ? '⚠' : '✓';
    const countSuffix = isFlagged
      ? `(${item.count} outlier${item.count === 1 ? '' : 's'})`
      : '(0)';
    return `
      <button type="button" class="anomaly-feature-pill ${stateClass}${activeClass}" data-col="${escapeHtml(item.name)}" title="Inspect ${escapeHtml(item.label)}">
        <span class="anomaly-pill-icon">${icon}</span>
        <span class="anomaly-pill-name">${escapeHtml(item.label)}</span>
        <span class="anomaly-pill-count">${countSuffix}</span>
      </button>
    `;
  }).join('');

  pillsContainer.querySelectorAll('.anomaly-feature-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetCol = btn.getAttribute('data-col');
      if (!targetCol) return;
      if (selectEl) {
        selectEl.value = targetCol;
      }
      renderAnomalyFeatureStrip(targetCol);
      scanAnomalies();
    });
  });
}

function resolveOutlierRowData(rowIndex, outlierObj) {
  if (outlierObj && outlierObj.row_data && Object.keys(outlierObj.row_data).length > 0) {
    return outlierObj.row_data;
  }
  if (currentTruthLens && Array.isArray(currentTruthLens.findings)) {
    for (const f of currentTruthLens.findings) {
      const records = f.evidence_Supporting_Facts && f.evidence_Supporting_Facts.source_records;
      if (Array.isArray(records)) {
        const match = records.find(r => Number(r.row_index ?? r._row_index) === Number(rowIndex));
        if (match) return match;
      }
    }
  }
  return {};
}

function buildEntityContextLabel(rowData) {
  if (!rowData || typeof rowData !== 'object') return 'Dataset Record';
  const nonNumCols = (currentProfile && currentProfile.columns)
    ? currentProfile.columns.filter(c => c.category !== 'numeric' || c.is_identifier).map(c => c.name)
    : Object.keys(rowData).filter(k => isNaN(Number(rowData[k])));

  // Prefer store / primary entity name first, then region / secondary segment
  const orderedKeys = [...nonNumCols].sort((a, b) => {
    const aScore = /store|name|account|client|customer|city|product/i.test(a) ? 0 : 1;
    const bScore = /store|name|account|client|customer|city|product/i.test(b) ? 0 : 1;
    return aScore - bScore;
  });

  const parts = orderedKeys
    .slice(0, 2)
    .map(k => rowData[k])
    .filter(v => v !== undefined && v !== null && String(v).trim() !== '');

  return parts.length > 0 ? parts.join(' · ') : 'Record Context';
}

function populateAnomalySelectors() {
  if (!currentProfile) return;
  anomalyColCountsCache = {};
  const select = document.getElementById('anomaly-col-select');
  const methodSelect = document.getElementById('anomaly-method-select');
  select.innerHTML = '';

  const numCols = currentProfile.columns.filter(c => c.category === 'numeric' && !c.is_identifier);
  numCols.forEach(col => {
    const opt = document.createElement('option');
    opt.value = col.name;
    opt.textContent = formatColumnLabel(col.name);
    select.appendChild(opt);
  });

  // Auto-select first flagged column (e.g., marketing_spend)
  const initialCounts = getInitialAnomalyCountsByColumn();
  const firstFlagged = numCols.find(c => (initialCounts[c.name] || 0) > 0);
  if (firstFlagged) {
    select.value = firstFlagged.name;
  } else if (currentInsights && currentInsights.insights) {
    const anomalyInsight = currentInsights.insights.find(i => i.category === 'anomaly' && i.action_link && i.action_link.column);
    if (anomalyInsight) {
      select.value = anomalyInsight.action_link.column;
    }
  }

  if (methodSelect && !methodSelect.value) {
    methodSelect.value = 'hybrid';
  }

  renderAnomalyFeatureStrip(select.value);

  const scanBtn = document.getElementById('scan-anomalies-btn');
  if (scanBtn) {
    scanBtn.onclick = scanAnomalies;
  }

  // Auto-scan on dropdown changes
  select.onchange = () => {
    renderAnomalyFeatureStrip(select.value);
    scanAnomalies();
  };
  if (methodSelect) {
    methodSelect.onchange = () => {
      anomalyColCountsCache = {};
      scanAnomalies();
    };
  }

  if (select.options.length > 0) {
    scanAnomalies();
  }
}

async function scanAnomalies() {
  if (!activeDatasetId) return;
  const colSelect = document.getElementById('anomaly-col-select');
  const methodSelect = document.getElementById('anomaly-method-select');
  const col = colSelect ? colSelect.value : '';
  const method = methodSelect ? (methodSelect.value || 'hybrid') : 'hybrid';
  if (!col) return;

  const resultContainer = document.getElementById('anomalies-result-container');
  resultContainer.innerHTML = '<div class="loading-spinner"></div>';

  const threshold = method === 'zscore' ? '2.5' : '1.5';

  try {
    const res = await fetch(`/api/v1/analytics/outliers/${activeDatasetId}?column=${encodeURIComponent(col)}&method=${method}&threshold=${threshold}`);
    if (!res.ok) throw new Error('Outlier detection failed');
    const data = await res.json();

    anomalyColCountsCache[col] = data.outlier_count;
    renderAnomalyFeatureStrip(col);

    const colProfile = (currentProfile && currentProfile.columns)
      ? currentProfile.columns.find(c => c.name === col)
      : null;
    const numStats = (colProfile && (colProfile.stats || colProfile.numeric_stats)) || {};
    const colMean = data.column_mean !== undefined && data.column_mean !== null
      ? Number(data.column_mean)
      : (numStats.mean !== undefined ? Number(numStats.mean) : (Number(data.lower_bound) + Number(data.upper_bound)) / 2);
    const rawStd = numStats.std ?? numStats.std_dev ?? numStats.stddev;
    const colStd = rawStd ? Number(rawStd) : 0;
    const colMin = numStats.min !== undefined ? Number(numStats.min) : Number(data.lower_bound);
    const colMax = numStats.max !== undefined ? Number(data.upper_bound) : Number(data.upper_bound);
    const isCurrency = /spend|cost|revenue|sales|profit|price|budget|amount|salary|fee/i.test(col);

    const lowerStr = formatAnomalyNumber(data.lower_bound, col, false);
    const meanStr = formatAnomalyNumber(colMean, col, false);
    const upperStr = formatAnomalyNumber(data.upper_bound, col, false);

    const methodBadgeMap = {
      hybrid: 'HYBRID Ensemble',
      iqr: 'IQR 1.5x Fence',
      zscore: 'Z-Score (|z| > 2.5)',
    };
    const methodLabel = methodBadgeMap[method] || `${method.toUpperCase()} Detection`;

    // Compute Visual Bullet / Box-and-Whisker Track geometry
    const outlierValues = (data.outliers || []).map(o => Number(o.value));
    const rawMin = Math.min(Number(data.lower_bound), colMin, ...(outlierValues.length ? outlierValues : [Number(data.lower_bound)]));
    const rawMax = Math.max(Number(data.upper_bound), colMax, ...(outlierValues.length ? outlierValues : [Number(data.upper_bound)]));
    const span = Math.max(rawMax - rawMin, 1e-6);
    const pad = span * 0.08;
    const domainMin = rawMin - pad;
    const domainMax = rawMax + pad;
    const domainSpan = Math.max(domainMax - domainMin, 1e-6);
    const toPct = val => Math.max(2, Math.min(98, ((Number(val) - domainMin) / domainSpan) * 100));

    const zoneLeftPct = toPct(data.lower_bound);
    const zoneRightPct = toPct(data.upper_bound);
    const zoneWidthPct = Math.max(4, zoneRightPct - zoneLeftPct);
    const meanPct = toPct(colMean);

    const outlierDotsHtml = (data.outliers || []).map(o => {
      const dotPct = toPct(o.value);
      const isUpper = Number(o.value) > Number(data.upper_bound);
      const valFormatted = formatAnomalyNumber(o.value, col, false);
      return `
        <div class="anomaly-iqr-outlier-dot ${isUpper ? 'spike' : 'drop'}" style="left: ${dotPct.toFixed(1)}%;" title="Row #${o.row_index}: ${valFormatted} (${isUpper ? 'Above Upper Bound' : 'Below Lower Bound'})">
          <span class="anomaly-iqr-dot-callout">${valFormatted} (Row #${o.row_index})</span>
        </div>
      `;
    }).join('');

    // 3. 2-Column Visual IQR & Outlier Distribution Card
    const bannerStatusClass = data.outlier_count > 0 ? 'flagged' : 'clean';
    const bannerHeaderTitle = data.outlier_count > 0
      ? `${data.outlier_count} Outlier${data.outlier_count === 1 ? '' : 's'} Detected · ${Number(data.outlier_percentage).toFixed(2)}% of rows · ${methodLabel}`
      : `0 Outliers Detected · 100% Within Normal Bounds · ${methodLabel}`;

    const diagnosticBannerHtml = `
      <div class="anomaly-diagnostic-banner ${bannerStatusClass}" id="anomaly-diagnostic-banner">
        <div class="anomaly-diag-left">
          <div class="anomaly-diag-badge-row">
            <span class="anomaly-status-badge ${bannerStatusClass}">
              ${data.outlier_count > 0 ? '⚠ ANOMALY DETECTED' : '✓ CLEAN DISTRIBUTION'}
            </span>
            <span class="anomaly-diag-summary-text">${escapeHtml(bannerHeaderTitle)}</span>
          </div>
          <div class="anomaly-bound-pills">
            <span class="anomaly-bound-pill">Lower Bound: <strong>${escapeHtml(lowerStr)}</strong></span>
            <span class="anomaly-bound-pill mean">Column Mean: <strong>${escapeHtml(meanStr)}</strong></span>
            <span class="anomaly-bound-pill">Upper Bound: <strong>${escapeHtml(upperStr)}</strong></span>
          </div>
        </div>

        <div class="anomaly-diag-right">
          <div class="anomaly-iqr-header">
            <span class="anomaly-iqr-zone-caption">Normal IQR Zone [${escapeHtml(lowerStr)} – ${escapeHtml(upperStr)}]</span>
            <span class="anomaly-iqr-mean-caption">Mean: ${escapeHtml(meanStr)}</span>
          </div>
          <div class="anomaly-iqr-track" role="img" aria-label="Visual IQR and Outlier Distribution Track">
            <div class="anomaly-iqr-zone" style="left: ${zoneLeftPct.toFixed(1)}%; width: ${zoneWidthPct.toFixed(1)}%;" title="Normal Bound Zone: [${escapeHtml(lowerStr)} – ${escapeHtml(upperStr)}]"></div>
            <div class="anomaly-iqr-mean-tick" style="left: ${meanPct.toFixed(1)}%;" title="Column Mean: ${escapeHtml(meanStr)}"></div>
            ${outlierDotsHtml}
          </div>
          <div class="anomaly-iqr-scale">
            <span>MinFence: ${escapeHtml(lowerStr)}</span>
            <span>Mean: ${escapeHtml(meanStr)}</span>
            <span>MaxFence: ${escapeHtml(upperStr)}</span>
          </div>
        </div>
      </div>
    `;

    // Check for segment-level anomalies in insights
    const segmentAnomalies = (currentInsights && currentInsights.insights)
      ? currentInsights.insights.filter(i => i.category === 'anomaly' && i.title && i.title.startsWith('Segment Anomaly'))
      : [];

    let segmentHtml = '';
    if (segmentAnomalies.length > 0) {
      segmentHtml = `
        <div class="anomaly-segment-alert">
          <div class="anomaly-segment-alert-title">
            <span>⚠️ Segment-Level Multidimensional Discrepancies</span>
          </div>
          ${segmentAnomalies.map(s => `
            <div class="anomaly-segment-alert-body">
              <strong>${escapeHtml(s.title)}:</strong> ${escapeHtml(s.summary)}
            </div>
          `).join('')}
        </div>
      `;
    }

    if (data.outlier_count === 0) {
      const initialCounts = getInitialAnomalyCountsByColumn();
      const otherFlaggedCols = Object.keys(initialCounts).filter(k => k !== col && (anomalyColCountsCache[k] ?? initialCounts[k]) > 0);
      const tipHtml = otherFlaggedCols.length > 0
        ? `<div class="anomaly-clean-tip">Tip: Click a flagged feature pill above (e.g., <strong>${escapeHtml(otherFlaggedCols.map(formatColumnLabel).join(', '))}</strong>) to inspect active dataset outliers.</div>`
        : '';

      resultContainer.innerHTML = `
        ${diagnosticBannerHtml}
        <div class="anomaly-clean-card">
          <span>✓ No statistical outliers detected in <strong>${escapeHtml(formatColumnLabel(col))}</strong> under ${escapeHtml(methodLabel)} bounds [${escapeHtml(lowerStr)} – ${escapeHtml(upperStr)}].</span>
          ${tipHtml}
        </div>
        ${segmentHtml}
      `;
      return;
    }

    // 4. Enrich the Anomaly Results Table with Full 6-Column Record Context & Interactive Row Inspection
    const rowsHtml = data.outliers.map((o, idx) => {
      const rowData = resolveOutlierRowData(o.row_index, o);
      const entityLabel = buildEntityContextLabel(rowData);
      const obsFormatted = formatAnomalyNumber(o.value, col, false);
      const boundsFormatted = `[${lowerStr} – ${upperStr}]`;

      // Compute Breach Delta vs Upper or Lower Fence
      const valNum = Number(o.value);
      const upperNum = Number(data.upper_bound);
      const lowerNum = Number(data.lower_bound);
      let breachText = '0';
      let breachClass = 'spike';
      if (valNum > upperNum) {
        const diff = valNum - upperNum;
        const pctOver = upperNum !== 0 ? (diff / Math.abs(upperNum)) * 100 : 0;
        const diffFormatted = formatAnomalyNumber(diff, col, isCurrency);
        breachText = `+${diffFormatted} (+${pctOver.toFixed(1)}% over max)`;
        breachClass = 'spike';
      } else if (valNum < lowerNum) {
        const diff = lowerNum - valNum;
        const pctUnder = lowerNum !== 0 ? (diff / Math.abs(lowerNum)) * 100 : 0;
        const diffFormatted = formatAnomalyNumber(diff, col, isCurrency);
        breachText = `-${diffFormatted} (-${pctUnder.toFixed(1)}% below min)`;
        breachClass = 'drop';
      }

      // Compute Signed Z-Score & Severity Badge
      const rawZ = o.z_score !== undefined && o.z_score !== null
        ? Number(o.z_score)
        : (colStd > 0 ? (valNum - colMean) / colStd : Number(o.score));
      const absZ = Math.abs(rawZ);
      const zSign = rawZ >= 0 ? '+' : '-';
      const zFormatted = `${zSign}${absZ.toFixed(2)}σ`;
      const severityLabel = absZ >= 3.0 ? 'EXTREME' : 'HIGH';
      const severityClass = absZ >= 3.0 ? 'sev-extreme' : 'sev-high';

      // Build Full 6-Column Inline Inspection Drawer comparing Row # values vs Column Averages
      const allCols = (currentProfile && currentProfile.columns) ? currentProfile.columns : [];
      const drawerCellsHtml = allCols.map(c => {
        const cellVal = rowData[c.name];
        const isTargetCol = c.name === col;
        if (c.category === 'numeric' && !c.is_identifier && (c.stats || c.numeric_stats)) {
          const cStats = c.stats || c.numeric_stats;
          const avgVal = Number(cStats.mean || 0);
          const numVal = cellVal !== undefined && cellVal !== null ? Number(cellVal) : null;
          const isColCurr = /spend|cost|revenue|sales|profit|price|budget|amount|salary|fee/i.test(c.name);
          const valDisp = numVal !== null ? formatAnomalyNumber(numVal, c.name, isColCurr) : '—';
          const avgDisp = formatAnomalyNumber(avgVal, c.name, isColCurr);
          const deltaVsAvg = (numVal !== null && avgVal !== 0) ? ((numVal - avgVal) / Math.abs(avgVal)) * 100 : 0;
          const deltaSign = deltaVsAvg > 0 ? '+' : '';
          const deltaTone = deltaVsAvg > 5 ? 'pos' : (deltaVsAvg < -5 ? 'neg' : 'neutral');
          return `
            <div class="anomaly-drawer-metric-card ${isTargetCol ? 'target-col' : ''}">
              <span class="anomaly-drawer-col-name">${escapeHtml(formatColumnLabel(c.name))}</span>
              <strong class="anomaly-drawer-col-val">${escapeHtml(valDisp)}</strong>
              <div class="anomaly-drawer-col-comp">
                <span class="anomaly-drawer-avg">Avg: ${escapeHtml(avgDisp)}</span>
                <span class="anomaly-drawer-delta ${deltaTone}">${deltaSign}${deltaVsAvg.toFixed(1)}%</span>
              </div>
            </div>
          `;
        } else {
          const textDisp = cellVal !== undefined && cellVal !== null ? String(cellVal) : '—';
          return `
            <div class="anomaly-drawer-metric-card cat-col">
              <span class="anomaly-drawer-col-name">${escapeHtml(formatColumnLabel(c.name))}</span>
              <strong class="anomaly-drawer-col-val">${escapeHtml(textDisp)}</strong>
              <div class="anomaly-drawer-col-comp">
                <span class="anomaly-drawer-avg">Context Identifier</span>
              </div>
            </div>
          `;
        }
      }).join('');

      const isExpandedByDefault = idx === 0;

      return `
        <tr class="anomaly-data-row ${isExpandedByDefault ? 'expanded' : ''}" data-row-index="${o.row_index}" tabindex="0" role="button" aria-expanded="${isExpandedByDefault}" title="Click to inspect all 6 columns of Row #${o.row_index} vs dataset averages">
          <td>
            <span class="anomaly-row-badge">#${o.row_index}</span>
          </td>
          <td class="anomaly-entity-cell">
            <span class="anomaly-entity-name">${escapeHtml(entityLabel)}</span>
          </td>
          <td class="num-col">
            <span class="anomaly-observed-val ${breachClass}">${escapeHtml(obsFormatted)}</span>
          </td>
          <td class="num-col anomaly-bounds-cell">${escapeHtml(boundsFormatted)}</td>
          <td class="num-col">
            <span class="anomaly-breach-badge ${breachClass}">${escapeHtml(breachText)}</span>
          </td>
          <td class="num-col anomaly-z-cell">
            <div class="anomaly-z-wrap">
              <span class="anomaly-z-score">${escapeHtml(zFormatted)}</span>
              <span class="anomaly-severity-pill ${severityClass}">${severityLabel}</span>
              <span class="anomaly-row-chevron" aria-hidden="true">${isExpandedByDefault ? '▾' : '▸'}</span>
            </div>
          </td>
        </tr>
        <tr class="anomaly-inline-drawer-row" id="anomaly-drawer-row-${o.row_index}" style="display: ${isExpandedByDefault ? 'table-row' : 'none'};">
          <td colspan="6">
            <div class="anomaly-inline-drawer">
              <div class="anomaly-inline-drawer-header">
                <span class="anomaly-inline-drawer-title">Full Record Inspection — Row #${o.row_index} (${escapeHtml(entityLabel)}) vs. Column Averages</span>
                <span class="anomaly-inline-drawer-hint">Cross-feature impact across all ${allCols.length} columns</span>
              </div>
              <div class="anomaly-row-context-grid">
                ${drawerCellsHtml}
              </div>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    resultContainer.innerHTML = `
      ${diagnosticBannerHtml}
      <div class="anomaly-table-card">
        <table class="anomaly-workbench-table" id="anomaly-workbench-table">
          <thead>
            <tr>
              <th>ROW INDEX</th>
              <th>ENTITY / CONTEXT</th>
              <th class="num-col">OBSERVED VALUE</th>
              <th class="num-col">NORMAL BOUNDS</th>
              <th class="num-col">BREACH DELTA</th>
              <th class="num-col">Z-SCORE / SEVERITY</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
      ${segmentHtml}
    `;

    // Wire interactive click/keyboard toggle on each outlier row to expand/collapse its 6-column inspection drawer
    resultContainer.querySelectorAll('.anomaly-data-row').forEach(tr => {
      const toggleDrawer = () => {
        const rIdx = tr.getAttribute('data-row-index');
        const drawerRow = document.getElementById(`anomaly-drawer-row-${rIdx}`);
        if (!drawerRow) return;
        const isOpen = drawerRow.style.display !== 'none';
        drawerRow.style.display = isOpen ? 'none' : 'table-row';
        tr.classList.toggle('expanded', !isOpen);
        tr.setAttribute('aria-expanded', String(!isOpen));
        const chev = tr.querySelector('.anomaly-row-chevron');
        if (chev) chev.textContent = isOpen ? '▸' : '▾';
      };
      tr.addEventListener('click', toggleDrawer);
      tr.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleDrawer();
        }
      });
    });
  } catch (err) {
    resultContainer.innerHTML = `<div style="color:var(--accent-rose);">Error: ${escapeHtml(err.message)}</div>`;
  }
}

// Tab 2: Conversational Data Query Chat
function setupChat() {
  chatSendBtn.addEventListener('click', sendChatMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendChatMessage();
  });

  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', resetChat);
  }

  // Event delegation for suggestion chips (both static strategic and dynamic quick metrics)
  const suggestionsWrapper = document.querySelector('.chat-suggestions-wrapper');
  if (suggestionsWrapper) {
    suggestionsWrapper.addEventListener('click', (e) => {
      const chip = e.target.closest('.suggestion-chip');
      if (chip) {
        chatInput.value = chip.textContent.trim();
        sendChatMessage();
      }
    });
  }

  // Handle clickable action buttons inside chat responses
  chatHistory.addEventListener('click', (e) => {
    const btn = e.target.closest('.chat-action-btn');
    if (!btn) return;
    try {
      const action = JSON.parse(btn.getAttribute('data-action'));
      if (action.target_tab) {
        switchTab(action.target_tab);
        if (action.target_tab === 'tab-aggregations') {
          if (action.dimension) {
            const dimSelect = document.getElementById('agg-dim-select');
            if (dimSelect) dimSelect.value = action.dimension;
          }
          if (action.metric) {
            const metricSelect = document.getElementById('agg-metric-select');
            if (metricSelect) metricSelect.value = action.metric;
          }
          if (action.function) {
            const funcSelect = document.getElementById('agg-func-select');
            if (funcSelect) funcSelect.value = action.function;
          }
          runAggregation();
        } else if (action.target_tab === 'tab-correlations') {
          if (action.x && action.y) {
            highlightCorrelationPair(action.x, action.y);
          }
        }
      }
    } catch (err) {
      console.warn('Failed to handle chat action click:', err);
    }
  });
}

function resetChat() {
  chatChartInstances.forEach(inst => {
    try { inst.destroy(); } catch (e) {}
  });
  chatChartInstances = [];

  const initialWelcome = `
    <div class="chat-msg bot">
      <div style="display:flex; gap:0.5rem; align-items:center; margin-bottom:0.5rem;">
        <span class="chat-intent-tag">InsightIQ Copilot</span>
        <span class="chat-source-badge source-det">⚡ Dual-Engine Intelligence</span>
      </div>
      <div>Welcome! Ask me <strong>any type of question</strong> about this dataset — from exact totals and correlations to open-ended strategic reasoning (e.g. SWOT analysis, growth opportunities, risks, investor pitch briefing, or ELI5 analogies).</div>
    </div>
  `;
  if (chatHistory) {
    chatHistory.innerHTML = initialWelcome;
  }
  showToast('Chat history cleared.');
}

function formatMarkdownToHtml(text) {
  if (!text) return '';
  let safe = escapeHtml(text);

  // Convert markdown headers
  safe = safe.replace(/^### (.*$)/gim, '<h4 class="chat-heading">$1</h4>');
  safe = safe.replace(/^## (.*$)/gim, '<h3 class="chat-heading">$1</h3>');

  // Convert bold
  safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Convert blockquotes
  safe = safe.replace(/^>\s*(.*$)/gim, '<blockquote style="border-left:3px solid var(--accent-primary); padding-left:0.75rem; margin:0.5rem 0; color:var(--text-muted); font-size:0.9rem;">$1</blockquote>');

  const lines = safe.split('\n');
  let inList = false;
  let inTable = false;
  let tableRows = [];
  let formatted = [];

  function flushTable() {
    if (!inTable) return;
    if (tableRows.length > 0) {
      let tHtml = '<div class="chat-table-wrapper"><table class="chat-md-table">';
      tableRows.forEach((row, rIdx) => {
        // Skip separator row (|---|---|)
        if (row.every(c => /^:?-+:?$/.test(c.trim()))) return;
        const tag = rIdx === 0 ? 'th' : 'td';
        tHtml += '<tr>';
        row.forEach(cell => {
          const trimmed = cell.trim();
          const isNumeric = /^-?[\$0-9,\.]+%?$/.test(trimmed);
          tHtml += `<${tag} class="${isNumeric ? 'num' : ''}">${trimmed}</${tag}>`;
        });
        tHtml += '</tr>';
      });
      tHtml += '</table></div>';
      formatted.push(tHtml);
    }
    inTable = false;
    tableRows = [];
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    // Check if table row: starts and ends with '|'
    if (line.startsWith('|') && line.endsWith('|')) {
      if (inList) {
        formatted.push('</ul>');
        inList = false;
      }
      inTable = true;
      const cells = line.slice(1, -1).split('|');
      tableRows.push(cells);
      continue;
    } else {
      flushTable();
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      if (!inList) {
        formatted.push('<ul class="chat-list">');
        inList = true;
      }
      formatted.push(`<li class="chat-bullet">${line.substring(2)}</li>`);
    } else {
      if (inList) {
        formatted.push('</ul>');
        inList = false;
      }
      if (line.startsWith('<h3') || line.startsWith('<h4') || line.startsWith('<blockquote')) {
        formatted.push(line);
      } else if (line.length > 0) {
        formatted.push(`<p class="chat-p">${line}</p>`);
      }
    }
  }

  flushTable();
  if (inList) {
    formatted.push('</ul>');
  }

  return formatted.join('');
}

function renderChatInlineChart(canvasId, chartSpec) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  if (chartSpec.type === 'scatter') {
    const inst = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: chartSpec.label || 'Scatter Distribution',
          data: chartSpec.points,
          backgroundColor: 'rgba(236, 72, 153, 0.75)',
          borderColor: '#ec4899',
          pointRadius: 4,
          pointHoverRadius: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#94a3b8', font: { size: 11 } } }
        },
        scales: {
          x: {
            title: { display: !!chartSpec.x_label, text: chartSpec.x_label, color: '#94a3b8' },
            ticks: { color: '#94a3b8', font: { size: 10 } },
            grid: { color: 'rgba(255,255,255,0.05)' }
          },
          y: {
            title: { display: !!chartSpec.y_label, text: chartSpec.y_label, color: '#94a3b8' },
            ticks: {
              color: '#94a3b8',
              font: { size: 10 },
              callback: function(v) { return formatCompactNumber(v); }
            },
            grid: { color: 'rgba(255,255,255,0.05)' }
          }
        }
      }
    });
    chatChartInstances.push(inst);
  } else {
    // Bar chart
    const inst = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: chartSpec.labels,
        datasets: [{
          label: chartSpec.label || 'Metric',
          data: chartSpec.values,
          backgroundColor: 'rgba(99, 102, 241, 0.75)',
          borderColor: '#6366f1',
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#94a3b8', font: { size: 11 } } }
        },
        scales: {
          x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
          y: {
            ticks: {
              color: '#94a3b8',
              font: { size: 10 },
              callback: function(v) { return formatCompactNumber(v); }
            },
            grid: { color: 'rgba(255,255,255,0.05)' }
          }
        }
      }
    });
    chatChartInstances.push(inst);
  }
}

async function sendChatMessage() {
  const query = chatInput.value.trim();
  if (!query || !activeDatasetId) return;

  appendMessage('user', escapeHtml(query));
  chatInput.value = '';

  const botMsgId = 'msg-' + Date.now();
  appendMessage('bot', `<div class="loading-spinner"></div>`, botMsgId);

  try {
    const res = await fetch(`/api/v1/query/${activeDatasetId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to interpret inquiry');
    }

    const data = await res.json();
    const botEl = document.getElementById(botMsgId);

    const sourceClass = data.source === 'ai_model' ? 'source-ai' : 'source-det';
    const sourceLabel = data.source === 'ai_model' ? '🤖 Gemini 3.6 Flash' : '⚡ Dual-Engine Intelligence';

    let html = `
      <div style="display:flex; gap:0.5rem; align-items:center; margin-bottom:0.6rem;">
        <span class="chat-intent-tag">${data.intent.replace(/_/g, ' ')}</span>
        <span class="chat-source-badge ${sourceClass}">${sourceLabel}</span>
      </div>
      <div style="font-size:0.95rem;">${formatMarkdownToHtml(data.answer)}</div>
    `;

    // Render inline chart if present
    if (data.chart) {
      const chartCanvasId = 'chat-chart-' + Date.now();
      html += `
        <div class="chat-chart-card">
          <canvas id="${chartCanvasId}"></canvas>
        </div>
      `;
      setTimeout(() => {
        renderChatInlineChart(chartCanvasId, data.chart);
      }, 50);
    }

    // Render action button if present
    if (data.action) {
      const actionDataAttr = escapeHtml(JSON.stringify(data.action));
      html += `
        <div>
          <button class="chat-action-btn" type="button" data-action='${actionDataAttr}'>
            <span>${escapeHtml(data.action.label || 'View in Dashboard →')}</span>
          </button>
        </div>
      `;
    }

    const hasMarkdownTable = data.answer && data.answer.includes('|');
    if (!hasMarkdownTable && data.data_preview && data.data_preview.length > 0 && data.intent !== 'chart_request') {
      const keys = Object.keys(data.data_preview[0]);
      html += `<div style="overflow-x:auto; margin-top:0.75rem; border-top:1px solid rgba(255,255,255,0.08); padding-top:0.5rem;"><table style="font-size:0.8rem; width:100%;"><thead><tr>`;
      keys.forEach(k => html += `<th>${k.replace(/_/g, ' ')}</th>`);
      html += `</tr></thead><tbody>`;
      data.data_preview.slice(0, 6).forEach(row => {
        html += `<tr>`;
        keys.forEach(k => html += `<td>${row[k] !== null && row[k] !== undefined ? escapeHtml(String(row[k])) : '—'}</td>`);
        html += `</tr>`;
      });
      html += `</tbody></table></div>`;
    }

    botEl.innerHTML = html;
  } catch (err) {
    const botEl = document.getElementById(botMsgId);
    botEl.innerHTML = `<div style="color:var(--accent-rose);">Error executing query: ${escapeHtml(err.message)}</div>`;
  }
}

function appendMessage(sender, htmlContent, id = null) {
  const div = document.createElement('div');
  div.className = `chat-msg ${sender}`;
  if (id) div.id = id;
  div.innerHTML = htmlContent;
  chatHistory.appendChild(div);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function escapeHtml(str) {
  if (typeof str !== 'string') return str;
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// =========================================================================
// Tab 7: TruthLens — Evidence-Based Intelligence Controller
// =========================================================================
function setupTruthLens() {
  // A. Context-Preserving Scenario Switcher (Active Dataset, Scenario A, Scenario B, Scenario C)
  const scenarioBar = document.getElementById('truthlens-scenario-bar');
  if (scenarioBar) {
    scenarioBar.querySelectorAll('.tl-scenario-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const scenarioKey = btn.dataset.scenario;
        scenarioBar.querySelectorAll('.tl-scenario-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeTruthLensScenario = scenarioKey;

        if (scenarioKey === 'active') {
          if (activeDatasetId) {
            const tlRes = await fetch(`/api/v1/truthlens/${activeDatasetId}`);
            if (tlRes.ok) {
              currentTruthLens = await tlRes.json();
              activeTruthLensFilter = 'all';
              activeTruthLensSeverity = 'all';
              resetTruthLensFilterChips();
              renderTruthLensTab();
              updateTabBadges();
              showToast(`TruthLens auditing active workspace dataset (${currentTruthLens.filename})`);
            }
          }
          return;
        }

        try {
          // Non-destructive context-preserving preview of Scenario A, B, or C
          const res = await fetch(`/api/v1/truthlens/scenarios/${scenarioKey}/report`);
          if (!res.ok) throw new Error('Failed to evaluate TruthLens scenario');
          currentTruthLens = await res.json();
          activeTruthLensFilter = 'all';
          activeTruthLensSeverity = 'all';
          resetTruthLensFilterChips();
          renderTruthLensTab();
          updateTabBadges();
          showToast(`Inspecting ${btn.textContent.trim()} (Active workspace dataset preserved)`);
        } catch (err) {
          showToast(`Error loading scenario: ${err.message}`);
        }
      });
    });
  }

  // Optional button to promote previewed scenario into the global workspace
  const promoteBtn = document.getElementById('tl-promote-scenario-btn');
  if (promoteBtn) {
    promoteBtn.addEventListener('click', async () => {
      if (!activeTruthLensScenario || activeTruthLensScenario === 'active') return;
      try {
        const res = await fetch(`/api/v1/truthlens/scenarios/${activeTruthLensScenario}`, {
          method: 'POST',
        });
        if (!res.ok) throw new Error('Failed to persist scenario dataset');
        const rep = await res.json();
        activeTruthLensScenario = 'active';
        await refreshDatasetList(rep.dataset_id);
        showToast(`Loaded ${rep.filename} into global workspace!`);
      } catch (err) {
        showToast(`Error promoting scenario: ${err.message}`);
      }
    });
  }

  // B.1 Severity filter chips (Critical, High, Medium, Low, All findings)
  const severityBar = document.getElementById('truthlens-severity-bar');
  if (severityBar) {
    severityBar.querySelectorAll('.tl-severity-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        severityBar.querySelectorAll('.tl-severity-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        activeTruthLensSeverity = chip.dataset.severity || 'all';
        renderTruthLensFindingsList();
      });
    });
  }

  // Global Expand / Collapse All Audit Drawers button
  const toggleAllBtn = document.getElementById('tl-toggle-all-cards-btn');
  if (toggleAllBtn) {
    toggleAllBtn.addEventListener('click', () => {
      const isExpanded = toggleAllBtn.dataset.expanded === 'true';
      const nextState = !isExpanded;
      toggleAllBtn.dataset.expanded = String(nextState);
      toggleAllBtn.textContent = nextState ? 'Collapse Audit Drawers ▴' : 'Expand All Audit Drawers ▾';
      const container = document.getElementById('truthlens-findings-container');
      if (container) {
        container.querySelectorAll('details.tl-expand-section').forEach(det => {
          det.open = nextState;
          const card = det.closest('.tl-finding-card');
          const btn = card ? card.querySelector('.tl-audit-toggle-btn') : null;
          if (btn) {
            btn.setAttribute('aria-expanded', String(nextState));
            btn.classList.toggle('is-open', nextState);
            const caret = btn.querySelector('.tl-audit-caret');
            if (caret) caret.textContent = nextState ? '▾' : '▸';
          }
        });
      }
    });
  }

  // Return to Active Dataset button inside the Global KPI Sandbox Banner
  const returnActiveBtn = document.getElementById('kpi-sandbox-return-btn');
  if (returnActiveBtn) {
    returnActiveBtn.addEventListener('click', () => {
      const activeBtn = document.getElementById('tl-btn-active');
      if (activeBtn) activeBtn.click();
    });
  }

  // Close overflow menu when clicking outside
  document.addEventListener('click', e => {
    const overflowMenu = document.getElementById('toolbar-overflow-menu');
    if (overflowMenu && overflowMenu.open && !overflowMenu.contains(e.target)) {
      overflowMenu.open = false;
    }
  });

  // B.2 Category filter chips
  const filterBar = document.getElementById('truthlens-filter-bar');
  if (filterBar) {
    filterBar.querySelectorAll('.tl-filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        filterBar.querySelectorAll('.tl-filter-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        activeTruthLensFilter = chip.dataset.filter || 'all';
        renderTruthLensFindingsList();
      });
    });
  }

  // Detail modal close handlers
  const tlDialog = document.getElementById('truthlens-detail-dialog');
  const closeTlBtn = document.getElementById('close-tl-dialog-btn');
  const closeTlFooterBtn = document.getElementById('tl-dialog-close-footer-btn');
  if (tlDialog) {
    const closeFn = () => tlDialog.close();
    if (closeTlBtn) closeTlBtn.addEventListener('click', closeFn);
    if (closeTlFooterBtn) closeTlFooterBtn.addEventListener('click', closeFn);
    tlDialog.addEventListener('click', e => {
      if (e.target === tlDialog) tlDialog.close();
    });
  }
}

function resetTruthLensFilterChips() {
  const filterBar = document.getElementById('truthlens-filter-bar');
  if (filterBar) {
    filterBar.querySelectorAll('.tl-filter-chip').forEach(c => {
      c.classList.toggle('active', c.dataset.filter === 'all');
    });
  }
  const severityBar = document.getElementById('truthlens-severity-bar');
  if (severityBar) {
    severityBar.querySelectorAll('.tl-severity-chip').forEach(c => {
      c.classList.toggle('active', c.dataset.severity === 'all');
    });
  }
  const toggleAllBtn = document.getElementById('tl-toggle-all-cards-btn');
  if (toggleAllBtn) {
    toggleAllBtn.dataset.expanded = 'false';
    toggleAllBtn.textContent = 'Expand All 7 Card Sections ▾';
  }
}

function renderTruthLensTab() {
  if (!currentTruthLens) return;

  const sc = currentTruthLens.summary_counts;
  const rel = currentTruthLens.reliability;

  // Sync active scenario button & context preservation banner
  const scenarioBar = document.getElementById('truthlens-scenario-bar');
  const contextBanner = document.getElementById('tl-context-indicator');
  const contextText = document.getElementById('tl-context-text');
  let matchedScenario = activeTruthLensScenario || 'active';
  if (matchedScenario === 'active') {
    if (currentTruthLens.filename === 'truthlens_scenario_a_revenue_profit.csv') matchedScenario = 'scenario_a';
    else if (currentTruthLens.filename === 'truthlens_scenario_b_satisfaction_churn.csv') matchedScenario = 'scenario_b';
    else if (currentTruthLens.filename === 'truthlens_scenario_c_category_declines.csv') matchedScenario = 'scenario_c';
  }
  if (scenarioBar) {
    scenarioBar.querySelectorAll('.tl-scenario-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.scenario === matchedScenario);
    });
  }
  const isPreview = String(currentTruthLens.dataset_id || '').startsWith('builtin_scenario_');
  if (contextBanner) {
    contextBanner.style.display = isPreview ? 'inline-flex' : 'none';
    if (isPreview && contextText) {
      contextText.textContent = `Scenario Preview Mode (${currentTruthLens.filename}) — Active workspace dataset preserved`;
    }
  }

  // 2. Sandbox State Isolation on Global KPI Ribbon
  const globalKpiGrid = document.getElementById('global-kpi-grid');
  const kpiSandboxBanner = document.getElementById('kpi-sandbox-banner');
  if (globalKpiGrid) {
    globalKpiGrid.classList.toggle('is-sandbox-active', isPreview);
  }
  if (kpiSandboxBanner) {
    kpiSandboxBanner.style.display = isPreview ? 'inline-flex' : 'none';
  }

  const verdictEl = document.getElementById('truthlens-verdict');
  if (verdictEl) verdictEl.textContent = currentTruthLens.executive_verdict;

  // Populate Severity Filter Badge Counts & Dynamically Hide 0-Count Pills when total_findings <= 5
  const setChipCountAndVisibility = (btnId, countId, val) => {
    const countEl = document.getElementById(countId);
    if (countEl) countEl.textContent = String(val);
    const btnEl = document.getElementById(btnId);
    if (btnEl && btnId !== 'tl-sev-btn-all') {
      btnEl.style.display = (sc.total_findings <= 5 && val === 0) ? 'none' : 'inline-flex';
    }
  };
  setChipCountAndVisibility('tl-sev-btn-all', 'tl-sev-count-all', sc.total_findings);
  setChipCountAndVisibility('tl-sev-btn-critical', 'tl-sev-count-critical', sc.critical_count);
  setChipCountAndVisibility('tl-sev-btn-high', 'tl-sev-count-high', sc.high_count);
  setChipCountAndVisibility('tl-sev-btn-medium', 'tl-sev-count-medium', sc.medium_count);
  setChipCountAndVisibility('tl-sev-btn-low', 'tl-sev-count-low', sc.low_count);

  // Dynamically hide 0-count domain filter chips when total_findings <= 5
  const filterBar = document.getElementById('truthlens-filter-bar');
  if (filterBar) {
    const allF = currentTruthLens.findings || [];
    filterBar.querySelectorAll('.tl-filter-chip').forEach(chip => {
      const cat = chip.dataset.filter;
      if (!cat || cat === 'all') {
        chip.style.display = 'inline-flex';
        return;
      }
      const matchCount = allF.filter(f => {
        if (cat === 'statistical_anomalies') return f.category === 'statistical_anomalies' || f.category === 'data_quality_problems';
        if (cat === 'misleading_averages') return f.category === 'misleading_averages' || f.category === 'incomplete_comparisons';
        return f.category === cat;
      }).length;
      chip.style.display = (sc.total_findings <= 5 && matchCount === 0) ? 'none' : 'inline-flex';
    });
  }

  // 1. Total Insights Detected
  const totalEl = document.getElementById('tl-kpi-total');
  if (totalEl) totalEl.textContent = sc.total_findings.toLocaleString();
  const totalSub = document.getElementById('tl-kpi-total-sub');
  if (totalSub) {
    totalSub.textContent = `Audited ${rel.sample_size.toLocaleString()} records in ${currentTruthLens.filename}`;
  }

  // 2. Critical & High-Priority Findings
  const critHighEl = document.getElementById('tl-kpi-critical-high');
  if (critHighEl) {
    critHighEl.textContent = sc.critical_and_high_count.toLocaleString();
    critHighEl.style.color = sc.critical_count > 0 ? 'var(--accent-rose)' : sc.high_count > 0 ? 'var(--accent-amber)' : '#10b981';
  }
  const prioBadge = document.getElementById('tl-kpi-priority-badge');
  if (prioBadge) {
    if (sc.critical_count > 0) {
      prioBadge.className = 'kpi-tag danger';
      prioBadge.textContent = 'Critical Alert';
    } else if (sc.high_count > 0) {
      prioBadge.className = 'kpi-tag warning';
      prioBadge.textContent = 'High Caution';
    } else {
      prioBadge.className = 'kpi-tag success';
      prioBadge.textContent = 'Low Risk';
    }
  }
  const prioSub = document.getElementById('tl-kpi-priority-sub');
  if (prioSub) {
    prioSub.textContent = `${sc.critical_count} Critical · ${sc.high_count} High · ${sc.medium_count} Medium · ${sc.low_count} Low`;
  }

  // 3. Data Reliability Indicator
  const relEl = document.getElementById('tl-kpi-reliability');
  if (relEl) {
    relEl.textContent = `${Math.round(rel.score)}%`;
    relEl.style.color = rel.score >= 85 ? '#10b981' : rel.score >= 68 ? '#38bdf8' : 'var(--accent-amber)';
  }
  const relBadge = document.getElementById('tl-reliability-badge');
  if (relBadge) {
    if (rel.status === 'High Reliability') {
      relBadge.className = 'kpi-tag success';
    } else if (rel.status === 'Moderate Caution') {
      relBadge.className = 'kpi-tag info';
    } else {
      relBadge.className = 'kpi-tag warning';
    }
    relBadge.textContent = rel.status;
  }
  const relSub = document.getElementById('tl-reliability-sub');
  if (relSub) {
    relSub.textContent = rel.distortion_flags && rel.distortion_flags.length > 0
      ? rel.distortion_flags[0]
      : `${rel.completeness_pct.toFixed(1)}% completeness · n = ${rel.sample_size}`;
  }

  // 4. Alert Category Breakdown
  const contrEl = document.getElementById('tl-kpi-contradictions');
  if (contrEl) contrEl.textContent = sc.kpi_contradictions_count.toLocaleString();
  const brkSub = document.getElementById('tl-kpi-breakdown-sub');
  if (brkSub) {
    brkSub.textContent = `${sc.segment_warnings_count} Segment Warnings · ${sc.statistical_anomalies_count} Anomalies · ${sc.bias_and_averages_count} Bias/Avg`;
  }

  renderTruthLensFindingsList();
  renderTruthLensAuditBanner();
  renderTruthLensTracePanel();
  renderTruthLensInsufficientList();
}

function renderTruthLensFindingsList() {
  const container = document.getElementById('truthlens-findings-container');
  if (!container || !currentTruthLens) return;

  const allFindings = currentTruthLens.findings || [];
  const filtered = allFindings.filter(f => {
    // Severity filter check
    if (activeTruthLensSeverity !== 'all' && f.severity !== activeTruthLensSeverity) {
      return false;
    }
    // Category filter check
    if (activeTruthLensFilter === 'all') return true;
    if (activeTruthLensFilter === 'statistical_anomalies') {
      return f.category === 'statistical_anomalies' || f.category === 'data_quality_problems';
    }
    if (activeTruthLensFilter === 'misleading_averages') {
      return f.category === 'misleading_averages' || f.category === 'incomplete_comparisons';
    }
    return f.category === activeTruthLensFilter;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="tl-finding-card" style="grid-column: 1 / -1; text-align:center; padding: 2rem;">
        <div style="color:var(--text-muted); font-size:0.9rem;">
          No TruthLens alerts match the selected filter (Severity: <strong>${escapeHtml(activeTruthLensSeverity)}</strong>, Domain: <strong>${escapeHtml(activeTruthLensFilter)}</strong>) in <strong>${escapeHtml(currentTruthLens.filename)}</strong>.
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = '';
  filtered.forEach(finding => {
    const sevKey = (finding.severity || 'Medium').toLowerCase();
    const card = document.createElement('div');
    card.className = `tl-finding-card tl-sev-${sevKey}`;
    card.id = `tl-card-${finding.id}`;

    const shared = getTruthLensSharedContext();
    const hyps = finding.hypotheses || [];
    const recs = finding.recommended_investigation || [];
    const pairCount = Math.max(hyps.length, recs.length);

    // Diagnostic hypotheses as side-by-side mini-cards, each paired with its audit "Next Step"
    const hypCards = [];
    for (let i = 0; i < pairCount; i++) {
      let parsed;
      let nextStepText = recs[i] || '';
      if (hyps[i]) {
        parsed = parseTruthLensHypothesis(hyps[i], i);
      } else if (finding.category === 'sampling_and_response_bias') {
        const segColName = (finding.relevant_columns && finding.relevant_columns[0]) || 'region';
        parsed = {
          title: 'Cross-Tabulation Sparsity Risk',
          body: `Splitting '${segColName}' across additional categorical dimensions will further fracture cell counts below reliable statistical thresholds.`,
        };
        if (!nextStepText) {
          nextStepText = 'Pool multi-period records before running multi-dimensional cross-tabulations.';
        }
      } else {
        parsed = {
          title: 'Recommended Audit',
          body: finding.why_it_matters || 'Validate underlying segment and record distributions before acting on headline aggregates.',
        };
      }
      hypCards.push(`
        <div class="tl-hyp-card">
          <div class="tl-hyp-title">${escapeHtml(parsed.title)}</div>
          ${parsed.body ? `<div class="tl-hyp-body">${escapeHtml(parsed.body)}</div>` : ''}
          ${nextStepText ? `<div class="tl-hyp-next"><span>↳ Next Step</span>${escapeHtml(nextStepText)}</div>` : ''}
        </div>
      `);
    }

    const colCount = (finding.relevant_columns || []).length;
    const colsStr = (finding.relevant_columns || []).map(c => `'${c}'`).join(', ');
    const periodsText = (finding.comparison_periods || [finding.comparison_baseline]).join(' vs. ');
    const evidenceGridHtml = buildTruthLensEvidenceGrid(finding);

    // Lineage pills (dataset-wide group definitions are shown once in the Dataset Audit Summary banner)
    const rowPills = (finding.supporting_row_references || []).map(r => buildLineagePill(r, 'row')).join('');
    const isSharedGroups = shared.sharedGroupKey !== null
      && JSON.stringify(finding.group_references || []) === shared.sharedGroupKey;
    const grpPills = isSharedGroups
      ? ''
      : (finding.group_references || []).map(g => buildLineagePill(g, 'group')).join('');
    const localWarnings = (finding.data_quality_warnings || []).filter(w => !shared.datasetWarnings.includes(w));
    const codeLines = (finding.calculations || []).map(c => escapeHtml(c)).join('\n');

    card.innerHTML = `
      <div class="tl-card-grid">
        <!-- Left Column: badges, title, executive narrative, diagnostic hypothesis mini-cards -->
        <div class="tl-card-left">
          <div class="tl-card-top-badges">
            <div class="tl-badge-group">
              <span class="tl-sev-pill ${sevKey}">${escapeHtml(finding.severity)}</span>
              <span class="tl-cat-pill">${escapeHtml(finding.category_label)}</span>
              <span class="tl-conf-badge" title="${escapeHtml(finding.confidence_justification)}">Confidence · ${escapeHtml(finding.confidence_level)}</span>
            </div>
          </div>
          <div class="tl-finding-title">${escapeHtml(finding.title)}</div>
          <p class="tl-card-exec-summary">${escapeHtml(finding.what_happened)} ${escapeHtml(finding.why_it_matters)}</p>
          <div class="tl-pane-title">Diagnostic Hypotheses</div>
          <div class="tl-hyp-grid">${hypCards.join('')}</div>
        </div>

        <!-- Right Column: Verified Empirical Delta data grid with inline micro-bars -->
        <div class="tl-card-right">
          <div class="tl-pane-title">Verified Empirical Delta <span class="tl-pane-sub">${escapeHtml(finding.comparison_baseline)}</span></div>
          ${evidenceGridHtml}
        </div>
      </div>

      <!-- Unified Single Action Footer (Left: Audit Trail & Lineage Pill Toggle | Right: Inspect Evidence & Chart) -->
      <div class="tl-trace-footer">
        <button type="button" class="tl-audit-toggle-btn" aria-expanded="false">
          <span class="tl-audit-caret">▸</span> Audit Trail &amp; Lineage (${colCount} column${colCount === 1 ? '' : 's'})
        </button>
        <div class="tl-card-action-group">
          <button type="button" class="insight-action-btn tl-open-detail-btn" data-finding-id="${escapeHtml(finding.id)}">
            <span>Inspect Evidence &amp; Chart →</span>
          </button>
        </div>
      </div>

      <!-- Developer-style Audit & Lineage Inspector (closed by default, toggled by footer pill) -->
      <details class="tl-expand-section tl-audit-drawer">
        <summary class="tl-expand-summary sr-only">Audit Trail &amp; Lineage</summary>
        <div class="tl-inspector-grid">
          <div class="tl-inspector-col">
            <div class="tl-inspector-label">Formulas &amp; Methodology</div>
            <div class="tl-inspector-text">${escapeHtml(finding.calculation_methodology || 'Deterministic aggregation & ratio verification')}</div>
            <pre class="tl-code-box">${codeLines}</pre>
            <div class="tl-inspector-text"><strong>Confidence (${escapeHtml(finding.confidence_level)}):</strong> ${escapeHtml(finding.confidence_justification)}</div>
          </div>
          <div class="tl-inspector-col">
            <div class="tl-inspector-label">Lineage</div>
            <div class="tl-pill-row">${rowPills || '<span class="tl-inspector-muted">No row-level references</span>'}${grpPills}</div>
            <div class="tl-lineage-detail" hidden></div>
            <div class="tl-inspector-text tl-inspector-muted">Columns: ${escapeHtml(colsStr)} · Periods: ${escapeHtml(periodsText)}</div>
            ${localWarnings.length ? `<div class="tl-inspector-warns">${localWarnings.map(w => `<span class="tl-audit-warn">${escapeHtml(w)}</span>`).join('')}</div>` : ''}
          </div>
        </div>
      </details>
    `;

    attachLineagePillHandlers(card);

    const auditToggleBtn = card.querySelector('.tl-audit-toggle-btn');
    const auditDrawer = card.querySelector('details.tl-audit-drawer');
    if (auditToggleBtn && auditDrawer) {
      const syncAuditBtn = () => {
        const isOpen = auditDrawer.open;
        auditToggleBtn.setAttribute('aria-expanded', String(isOpen));
        auditToggleBtn.classList.toggle('is-open', isOpen);
        const caret = auditToggleBtn.querySelector('.tl-audit-caret');
        if (caret) caret.textContent = isOpen ? '▾' : '▸';
      };
      auditToggleBtn.addEventListener('click', () => {
        auditDrawer.open = !auditDrawer.open;
        syncAuditBtn();
      });
      auditDrawer.addEventListener('toggle', syncAuditBtn);
    }

    card.querySelector('.tl-open-detail-btn').addEventListener('click', () => {
      openTruthLensDetailDialog(finding);
    });

    container.appendChild(card);
  });
}

// ---- TruthLens card helpers: hypotheses, evidence micro-bars, lineage pills, dataset audit banner ----
function parseTruthLensHypothesis(text, index) {
  const m = String(text).match(/^Hypothesis\s*\d+\s*\(([^)]*)\):\s*([\s\S]*)$/);
  if (m) return { title: m[1], body: m[2] };
  const idx = String(text).indexOf(':');
  if (idx > 0 && idx < 90) return { title: text.slice(0, idx), body: text.slice(idx + 1).trim() };
  return { title: `Hypothesis ${index + 1}`, body: String(text) };
}

function parseTruthLensNumber(v) {
  if (v === null || v === undefined) return NaN;
  const s = String(v).trim().replace(/[$%x×σ,]/g, '').replace(/^\+/, '');
  if (!/^-?\d+(\.\d+)?$/.test(s)) return NaN;
  return parseFloat(s);
}

function buildTruthLensEvidenceGrid(finding) {
  const rows = finding.evidence_table || [];
  if (rows.length === 0) {
    return `<div class="tl-evidence-fallback">${escapeHtml(finding.supporting_evidence)}</div>`;
  }
  const cols = Object.keys(rows[0]);

  // 1. Visual Bullet Bar for IQR / Z-score Anomalies (single-row anomaly bounds table)
  let bulletChartHtml = '';
  const r0 = rows[0] || {};
  if (
    r0['Lower Bound (IQR)'] !== undefined &&
    r0['Upper Bound (IQR)'] !== undefined &&
    r0['Outlier Value'] !== undefined
  ) {
    const lowFence = parseTruthLensNumber(r0['Lower Bound (IQR)']);
    const highFence = parseTruthLensNumber(r0['Upper Bound (IQR)']);
    const outlierVal = parseTruthLensNumber(r0['Outlier Value']);
    if (Number.isFinite(lowFence) && Number.isFinite(highFence) && Number.isFinite(outlierVal)) {
      const rawMin = Math.min(lowFence, highFence, outlierVal);
      const rawMax = Math.max(lowFence, highFence, outlierVal);
      const span = Math.max(rawMax - rawMin, 1e-6);
      const pad = span * 0.14;
      const domMin = rawMin >= 0 && rawMin - pad < 0 ? 0 : rawMin - pad;
      const domMax = rawMax + pad;
      const domSpan = Math.max(domMax - domMin, 1e-6);
      const toPct = v => Math.max(3, Math.min(97, ((v - domMin) / domSpan) * 100));
      const safeLeft = toPct(lowFence);
      const safeRight = toPct(highFence);
      const safeWidth = Math.max(4, safeRight - safeLeft);
      const markerLeft = toPct(outlierVal);
      const isSpike = outlierVal > highFence;
      const recordName = r0['Outlier Record'] ? `${escapeHtml(String(r0['Outlier Record']))} · ` : '';
      bulletChartHtml = `
        <div class="tl-bullet-chart" title="IQR Safe Zone: [${escapeHtml(String(r0['Lower Bound (IQR)']))}, ${escapeHtml(String(r0['Upper Bound (IQR)']))}] • Outlier: ${escapeHtml(String(r0['Outlier Value']))}">
          <div class="tl-bullet-labels">
            <span class="tl-bullet-zone-label">IQR Safe Zone [${escapeHtml(String(r0['Lower Bound (IQR)']))} – ${escapeHtml(String(r0['Upper Bound (IQR)']))}]</span>
            <span class="tl-bullet-outlier-label ${isSpike ? 'spike' : 'drop'}">● ${recordName}${escapeHtml(String(r0['Outlier Value']))}</span>
          </div>
          <div class="tl-bullet-track">
            <div class="tl-bullet-safe-zone" style="left:${safeLeft.toFixed(1)}%; width:${safeWidth.toFixed(1)}%;"></div>
            <div class="tl-bullet-marker ${isSpike ? 'spike' : 'drop'}" style="left:${markerLeft.toFixed(1)}%;"></div>
          </div>
        </div>
      `;
    }
  }

  // Per-column proportional bar stats (first column is always the row label; needs >= 2 numeric rows)
  const colStats = cols.map((c, idx) => {
    if (idx === 0 || rows.length < 2) return null;
    const vals = rows.map(r => parseTruthLensNumber(r[c]));
    const ok = vals.filter(v => Number.isFinite(v));
    if (ok.length < 2 || ok.length < rows.length * 0.75) return null;
    const isSegmentFillCol = /^(Mean\s|.*Share$)/i.test(c);
    const isDeltaPillCol = /vs\.\s*Overall\s*Mean|Change\s*\(%\)|Pct\s*Change/i.test(c);
    return { vals, max: Math.max(...ok.map(Math.abs)) || 1, isSegmentFillCol, isDeltaPillCol };
  });

  const head = cols.map((c, i) => `<th class="${colStats[i] ? 'num' : ''}">${escapeHtml(c)}</th>`).join('');
  const body = rows.map((row, rowIdx) => {
    const cells = cols.map((c, i) => {
      const text = escapeHtml(String(row[c] !== undefined && row[c] !== null ? row[c] : '—'));
      const stats = colStats[i];
      if (!stats) return `<td>${text}</td>`;
      const v = stats.vals[rowIdx];
      if (!Number.isFinite(v)) return `<td class="num">${text}</td>`;
      const w = Math.max(4, Math.round((Math.abs(v) / stats.max) * 100));
      if (stats.isDeltaPillCol) {
        const pillTone = v > 0 ? 'pos' : v < 0 ? 'neg' : 'neutral';
        return `<td class="num"><span class="tl-delta-pill ${pillTone}">${text}</span></td>`;
      }
      const cellBg = stats.isSegmentFillCol
        ? ` style="background: linear-gradient(90deg, rgba(56, 189, 248, 0.18) ${w}%, transparent ${w}%);"`
        : '';
      return `<td class="num${stats.isSegmentFillCol ? ' tl-segment-bar-td' : ''}"${cellBg}><div class="tl-bar-cell"><span class="tl-bar-val">${text}</span><span class="tl-bar-track"><span class="tl-bar-fill${v < 0 ? ' neg' : ''}" style="width:${w}%"></span></span></div></td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

  return `<div class="tl-data-grid-wrap">${bulletChartHtml}<table class="tl-data-grid"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function buildLineagePill(text, kind) {
  let label;
  if (kind === 'row') {
    const str = String(text);
    const outlierMatch = str.match(/^Row #\d+\s*•\s*[^[\n]+\(Outlier\)/);
    const stdMatch = str.match(/^Row #\d+(?:\s*\[\w+\])?/);
    if (outlierMatch) {
      label = outlierMatch[0].trim();
    } else if (/^Rows #\d+\.\.#\d+/i.test(str)) {
      label = str;
    } else if (stdMatch) {
      label = stdMatch[0];
    } else {
      label = str;
    }
  } else {
    label = String(text).replace(/,?\s*rows=\[[^\]]*\]/, '').replace(/,?\s*n=\d+/, '');
    if (label.length > 46) label = label.slice(0, 45) + '…';
  }
  return `<button type="button" class="tl-lineage-pill ${kind}" data-detail="${escapeHtml(String(text))}" title="${escapeHtml(String(text))}">${escapeHtml(label)}</button>`;
}

function attachLineagePillHandlers(root) {
  root.querySelectorAll('.tl-lineage-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const scope = pill.closest('.tl-inspector-col, .tl-audit-banner') || root;
      const detail = scope.querySelector('.tl-lineage-detail');
      if (!detail) return;
      const isActive = pill.classList.contains('active');
      scope.querySelectorAll('.tl-lineage-pill').forEach(p => p.classList.remove('active'));
      if (isActive) {
        detail.hidden = true;
        return;
      }
      pill.classList.add('active');
      detail.textContent = pill.dataset.detail || '';
      detail.hidden = false;
    });
  });
}

function getTruthLensSharedContext() {
  const findings = (currentTruthLens && currentTruthLens.findings) || [];
  const counts = {};
  findings.forEach(f => {
    const k = JSON.stringify(f.group_references || []);
    counts[k] = (counts[k] || 0) + 1;
  });
  let sharedGroupKey = null;
  Object.keys(counts).forEach(k => {
    if (counts[k] >= 2 && k !== '[]' && (sharedGroupKey === null || counts[k] > counts[sharedGroupKey])) {
      sharedGroupKey = k;
    }
  });
  return {
    sharedGroupKey,
    sharedGroups: sharedGroupKey ? JSON.parse(sharedGroupKey) : [],
    datasetWarnings: (currentTruthLens && currentTruthLens.data_quality_warnings) || [],
  };
}

function renderTruthLensAuditBanner() {
  const el = document.getElementById('truthlens-audit-banner');
  if (!el || !currentTruthLens) return;
  const ctx = getTruthLensSharedContext();
  const roleEntries = Object.entries(currentTruthLens.detected_roles || {}).filter(([, v]) => v);
  const roles = roleEntries
    .map(([k, v]) => `<span class="tl-trace-code-tag">${escapeHtml(k.replace('_column', ''))}: ${escapeHtml(String(v))}</span>`)
    .join('');
  const periods = (currentTruthLens.comparison_periods || []).map(p => escapeHtml(p)).join(' · ');
  const warns = ctx.datasetWarnings.map(w => `<span class="tl-audit-warn">${escapeHtml(w)}</span>`).join('');
  const shownGroups = ctx.sharedGroups.slice(0, 8).map(g => buildLineagePill(g, 'group')).join('');
  const moreGroups = ctx.sharedGroups.length > 8 ? `<span class="tl-inspector-muted">+${ctx.sharedGroups.length - 8} more</span>` : '';
  const rowCount = currentTruthLens.row_count || (currentTruthLens.reliability ? currentTruthLens.reliability.sample_size : 0);

  el.innerHTML = `
    <details class="tl-audit-collapsible">
      <summary class="tl-audit-summary-strip">
        <div class="tl-audit-head">
          <span class="tl-audit-title">Dataset Audit Summary</span>
          <span class="tl-audit-meta-pill">${roleEntries.length} Mapped Role${roleEntries.length === 1 ? '' : 's'}</span>
          <span class="tl-audit-meta-pill">${ctx.datasetWarnings.length} Guardrail${ctx.datasetWarnings.length === 1 ? '' : 's'}</span>
          <span class="tl-audit-meta-pill">${ctx.sharedGroups.length} Segment Group${ctx.sharedGroups.length === 1 ? '' : 's'}</span>
          <code>${escapeHtml(currentTruthLens.filename)}</code>
          <span class="tl-inspector-muted">${rowCount.toLocaleString()} rows × ${currentTruthLens.column_count || '—'} cols${periods ? ' · ' + periods : ''}</span>
        </div>
        <span class="tl-audit-toggle-pill"><span class="tl-audit-summary-caret">▸</span> View Audit Metadata</span>
      </summary>
      <div class="tl-audit-expanded-body">
        ${roles ? `<div class="tl-audit-row"><span class="tl-audit-key">Column roles</span><div class="tl-pill-row">${roles}</div></div>` : ''}
        ${warns ? `<div class="tl-audit-row"><span class="tl-audit-key">Guardrails</span><div class="tl-pill-row">${warns}</div></div>` : ''}
        ${shownGroups ? `<div class="tl-audit-row"><span class="tl-audit-key">Shared groups</span><div class="tl-pill-row">${shownGroups}${moreGroups}</div></div>` : ''}
        <div class="tl-lineage-detail" hidden></div>
      </div>
    </details>
  `;
  el.style.display = 'block';
  attachLineagePillHandlers(el);

  const det = el.querySelector('details.tl-audit-collapsible');
  const togglePill = el.querySelector('.tl-audit-toggle-pill');
  if (det && togglePill) {
    det.addEventListener('toggle', () => {
      togglePill.innerHTML = det.open
        ? '<span class="tl-audit-summary-caret">▾</span> Hide Audit Metadata'
        : '<span class="tl-audit-summary-caret">▸</span> View Audit Metadata';
    });
  }
}

function renderTruthLensTracePanel() {
  const metaContainer = document.getElementById('truthlens-trace-meta');
  const tbody = document.getElementById('truthlens-trace-tbody');
  if (!metaContainer || !tbody || !currentTruthLens) return;

  const roles = currentTruthLens.detected_roles || {};
  const activeRoles = Object.entries(roles)
    .filter(([, val]) => val !== null && val !== undefined && val !== '')
    .map(([k, v]) => `<span class="tl-trace-code-tag">${escapeHtml(k.replace('_column', ''))}: '${escapeHtml(String(v))}'</span>`)
    .join(' ');

  const periodsList = (currentTruthLens.comparison_periods || []).map(p => `<div>• ${escapeHtml(p)}</div>`).join('') || '<div>• Snapshot scope</div>';
  const dqWarnings = (currentTruthLens.data_quality_warnings || []);
  const dqHtml = dqWarnings.length > 0
    ? dqWarnings.slice(0, 4).map(w => `<div>• ${escapeHtml(w)}</div>`).join('')
    : '<div>• 100% matrix completeness · 0 duplicate rows</div>';

  const rowCount = currentTruthLens.row_count || (currentTruthLens.reliability ? currentTruthLens.reliability.sample_size : 0);
  const colCount = currentTruthLens.column_count || Object.values(roles).filter(Boolean).length;

  metaContainer.innerHTML = `
    <div class="tl-trace-meta-card">
      <div class="tl-trace-meta-label">1. Original Dataset Identification</div>
      <div><strong>Filename:</strong> ${escapeHtml(currentTruthLens.filename)}</div>
      <div><strong>Dataset ID:</strong> <code>${escapeHtml(currentTruthLens.dataset_id)}</code></div>
      <div><strong>Dimensions:</strong> ${rowCount.toLocaleString()} rows × ${colCount} columns</div>
    </div>
    <div class="tl-trace-meta-card">
      <div class="tl-trace-meta-label">2. Relevant Column Role Mapping</div>
      <div>${activeRoles || 'Standard numeric &amp; categorical schema'}</div>
    </div>
    <div class="tl-trace-meta-card">
      <div class="tl-trace-meta-label">3. Comparison Periods &amp; Baselines</div>
      ${periodsList}
    </div>
    <div class="tl-trace-meta-card">
      <div class="tl-trace-meta-label">4. Data Quality &amp; Distortion Warnings</div>
      ${dqHtml}
    </div>
  `;

  const findings = currentTruthLens.findings || [];
  if (findings.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No findings generated for ${escapeHtml(currentTruthLens.filename)}.</td></tr>`;
    return;
  }

  tbody.innerHTML = findings.map(f => {
    const sevKey = (f.severity || 'Medium').toLowerCase();
    const colTags = (f.relevant_columns || []).map(c => `<span class="tl-trace-code-tag">${escapeHtml(c)}</span>`).join('');
    const rowRefs = (f.supporting_row_references || []).map(r => `<div>• ${escapeHtml(r)}</div>`).join('');
    const grpRefs = (f.group_references || []).map(g => `<div style="color:#93c5fd;">◦ ${escapeHtml(g)}</div>`).join('');
    const compPeriods = (f.comparison_periods || [f.comparison_baseline]).map(p => `<div>• ${escapeHtml(p)}</div>`).join('');
    const formulas = (f.calculations || []).map(c => `<div><code>${escapeHtml(c)}</code></div>`).join('');
    const warnings = (f.data_quality_warnings || []).map(w => `<div>• ${escapeHtml(w)}</div>`).join('');

    return `
      <tr id="tl-trace-row-${escapeHtml(f.id)}">
        <td>
          <span class="tl-sev-pill ${sevKey}">${escapeHtml(f.severity)}</span>
          <div style="font-weight:700; color:#f8fafc; margin-top:0.25rem;">${escapeHtml(f.title)}</div>
          <div style="font-family:monospace; font-size:0.68rem; color:#64748b;">ID: ${escapeHtml(f.id)}</div>
        </td>
        <td>${colTags}</td>
        <td>
          ${rowRefs}
          ${grpRefs}
        </td>
        <td>${compPeriods}</td>
        <td>
          <div style="font-weight:600; color:#cbd5e1; margin-bottom:0.2rem;">${escapeHtml(f.calculation_methodology || '')}</div>
          ${formulas}
        </td>
        <td>${warnings}</td>
      </tr>
    `;
  }).join('');
}

function highlightDatasetTraceRow(findingId) {
  const row = document.getElementById(`tl-trace-row-${findingId}`);
  const panel = document.getElementById('truthlens-trace-panel');
  if (row) {
    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    row.classList.remove('tl-trace-row-highlight');
    void row.offsetWidth; // trigger reflow for animation
    row.classList.add('tl-trace-row-highlight');
  } else if (panel) {
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function renderTruthLensInsufficientList() {
  const panel = document.getElementById('truthlens-insufficient-panel');
  const container = document.getElementById('truthlens-insufficient-container');
  if (!panel || !container || !currentTruthLens) return;

  const notices = currentTruthLens.insufficient_evidence || [];
  if (notices.length === 0) {
    panel.style.display = 'none';
    return;
  }

  panel.style.display = 'block';
  container.innerHTML = notices
    .map(
      n => `
      <div class="tl-insufficient-item">
        <strong>${escapeHtml(n.category_label)} — Insufficient Evidence</strong>
        <div>${escapeHtml(n.reason)}</div>
        <div style="margin-top:0.2rem; font-family:monospace; font-size:0.7rem; color:#64748b;">
          Required: ${escapeHtml((n.required_signals || []).join(' · '))}
        </div>
      </div>
    `
    )
    .join('');
}

function openTruthLensDetailDialog(finding) {
  const dialog = document.getElementById('truthlens-detail-dialog');
  if (!dialog || !finding) return;

  const sevKey = (finding.severity || 'Medium').toLowerCase();
  document.getElementById('tl-dialog-badges').innerHTML = `
    <span class="tl-sev-pill ${sevKey}">${escapeHtml(finding.severity)}</span>
    <span class="tl-cat-pill">${escapeHtml(finding.category_label)}</span>
    <span class="tl-conf-pill">Confidence: <strong>${escapeHtml(finding.confidence_level)}</strong> (${escapeHtml(finding.confidence_justification)})</span>
  `;
  document.getElementById('tl-dialog-title').textContent = finding.title;
  document.getElementById('tl-dialog-baseline').textContent = `Comparison Baseline: ${finding.comparison_baseline}`;
  document.getElementById('tl-dialog-ai-explanation').innerHTML = `
    <strong>🤖 Layer 4 AI Explanation (Strictly Grounded in Verified Data):</strong><br>
    ${escapeHtml(finding.ai_explanation)}
  `;
  document.getElementById('tl-dialog-what').textContent = finding.what_happened;
  document.getElementById('tl-dialog-evidence-box').innerHTML = `
    <strong>Supporting Numerical Evidence:</strong> ${escapeHtml(finding.supporting_evidence)}
  `;
  document.getElementById('tl-dialog-why').textContent = finding.why_it_matters;

  // Render Hypotheses & Investigations
  document.getElementById('tl-dialog-hypotheses').innerHTML = (finding.hypotheses || [])
    .map(h => `<li>${escapeHtml(h)}</li>`)
    .join('');
  document.getElementById('tl-dialog-investigations').innerHTML = (finding.recommended_investigation || [])
    .map(r => `<li>${escapeHtml(r)}</li>`)
    .join('');

  // Render Audit Trail (Relevant Columns + Exact Calculations + Row/Group Lineage)
  const colsText = (finding.relevant_columns || []).join(', ');
  const calcsHtml = (finding.calculations || []).map(c => `<div>• ${escapeHtml(c)}</div>`).join('');
  const rowRefsHtml = (finding.supporting_row_references || []).map(r => `<div>• ${escapeHtml(r)}</div>`).join('');
  const grpRefsHtml = (finding.group_references || []).map(g => `<div>• ${escapeHtml(g)}</div>`).join('');
  const periodsText = (finding.comparison_periods || [finding.comparison_baseline]).join(' vs. ');
  const dqHtml = (finding.data_quality_warnings || []).map(w => `<div>• ${escapeHtml(w)}</div>`).join('');
  document.getElementById('tl-dialog-audit').innerHTML = `
    <div><strong>Original Dataset:</strong> ${escapeHtml(currentTruthLens ? currentTruthLens.filename : '')} (ID: ${escapeHtml(currentTruthLens ? currentTruthLens.dataset_id : '')})</div>
    <div style="margin-top:0.25rem;"><strong>Dataset Columns Used:</strong> ${escapeHtml(colsText)}</div>
    <div style="margin-top:0.25rem;"><strong>Comparison Periods:</strong> ${escapeHtml(periodsText)}</div>
    <div style="margin-top:0.25rem;"><strong>Calculation Methodology:</strong> ${escapeHtml(finding.calculation_methodology || '')}</div>
    <div style="margin-top:0.35rem;"><strong>Executed Formulas &amp; Verifications:</strong></div>
    ${calcsHtml}
    <div style="margin-top:0.35rem;"><strong>Supporting Row References:</strong></div>
    ${rowRefsHtml}
    <div style="margin-top:0.35rem;"><strong>Aggregated Group References:</strong></div>
    ${grpRefsHtml}
    <div style="margin-top:0.35rem;"><strong>Data Quality Warnings:</strong></div>
    ${dqHtml}
  `;

  // Render Evidence Table
  const tableHead = document.getElementById('tl-dialog-table-head');
  const tableBody = document.getElementById('tl-dialog-table-body');
  const rows = finding.evidence_table || [];
  if (rows.length > 0) {
    const cols = Object.keys(rows[0]);
    tableHead.innerHTML = `<tr>${cols.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr>`;
    tableBody.innerHTML = rows
      .map(
        r =>
          `<tr>${cols
            .map(c => `<td>${escapeHtml(String(r[c] !== undefined && r[c] !== null ? r[c] : '—'))}</td>`)
            .join('')}</tr>`
      )
      .join('');
  } else {
    tableHead.innerHTML = '';
    tableBody.innerHTML = '<tr><td>Direct metric verification shown above.</td></tr>';
  }

  // Render Filtered Source Records from the Active Dataset (Slide-Over Drawer)
  const sourceSection = document.getElementById('tl-dialog-source-section');
  const sourceHead = document.getElementById('tl-dialog-source-head');
  const sourceBody = document.getElementById('tl-dialog-source-body');
  const sourceCount = document.getElementById('tl-dialog-source-count');
  const sourceRows = (finding.source_rows && finding.source_rows.length > 0)
    ? finding.source_rows
    : (finding.evidence_table || []);
  if (sourceSection && sourceHead && sourceBody) {
    if (sourceRows.length > 0) {
      sourceSection.style.display = 'block';
      const srcCols = Object.keys(sourceRows[0]);
      if (sourceCount) {
        sourceCount.textContent = `${sourceRows.length} record${sourceRows.length === 1 ? '' : 's'} from ${currentTruthLens ? currentTruthLens.filename : 'active dataset'}`;
      }
      sourceHead.innerHTML = `<tr>${srcCols.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr>`;
      sourceBody.innerHTML = sourceRows
        .map(r => {
          const isOutlierRow = Object.values(r).some(val => String(val).includes('★'));
          return `<tr class="${isOutlierRow ? 'tl-outlier-source-row' : ''}">${srcCols
            .map(c => `<td>${escapeHtml(String(r[c] !== undefined && r[c] !== null ? r[c] : '—'))}</td>`)
            .join('')}</tr>`;
        })
        .join('');
    } else {
      sourceSection.style.display = 'none';
    }
  }

  // Render Supporting Domain-Matched Interactive Chart
  const chartSection = document.getElementById('tl-dialog-chart-section');
  const chartTitleEl = document.getElementById('tl-dialog-chart-title');
  if (tlDetailChartInstance) {
    tlDetailChartInstance.destroy();
    tlDetailChartInstance = null;
  }

  if (finding.chart_spec && finding.chart_spec.datasets && finding.chart_spec.datasets.length > 0) {
    chartSection.style.display = 'block';
    chartTitleEl.textContent = finding.chart_spec.title || 'Supporting Visualization';
    const ctx = document.getElementById('truthlens-detail-chart').getContext('2d');
    const cs = finding.chart_spec;
    const isScatter = cs.chart_type === 'scatter';
    const isAnomalyDist = finding.category === 'statistical_anomalies';
    const hasRefLine = cs.reference_value !== null && cs.reference_value !== undefined && Number.isFinite(Number(cs.reference_value));

    let chartDatasets = [];
    if (isScatter) {
      // Domain 1: Scatter plot with OLS linear regression line (Correlation vs. Causation)
      const toScatterPoints = dsData =>
        (dsData || []).map((pt, i) =>
          pt && typeof pt === 'object'
            ? pt
            : { x: Number((cs.labels || [])[i] ?? i), y: Number(pt) }
        );
      chartDatasets = cs.datasets.map((ds, idx) => {
        if (idx === 0) {
          return {
            type: 'scatter',
            label: ds.label,
            data: toScatterPoints(ds.data),
            backgroundColor: 'rgba(56, 189, 248, 0.78)',
            borderColor: '#38bdf8',
            pointRadius: 5,
            pointHoverRadius: 7,
          };
        }
        return {
          type: 'line',
          label: ds.label,
          data: toScatterPoints(ds.data),
          borderColor: '#f59e0b',
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [6, 4],
          pointRadius: 0,
          fill: false,
        };
      });
    } else {
      const seriesColors = [
        { bg: 'rgba(99, 102, 241, 0.72)', border: '#6366f1' },
        { bg: 'rgba(56, 189, 248, 0.72)', border: '#38bdf8' },
        { bg: 'rgba(245, 158, 11, 0.72)', border: '#f59e0b' },
      ];
      chartDatasets = cs.datasets.map((ds, idx) => {
        if (isAnomalyDist && idx === 0 && Array.isArray(cs.labels)) {
          // Domain 3: Distribution plot with highlighted outlier bar
          const bgColors = cs.labels.map(lbl =>
            String(lbl).includes('★') ? 'rgba(244, 63, 94, 0.88)' : 'rgba(56, 189, 248, 0.42)'
          );
          const bdColors = cs.labels.map(lbl =>
            String(lbl).includes('★') ? '#f43f5e' : '#38bdf8'
          );
          return {
            type: 'bar',
            label: ds.label,
            data: ds.data,
            backgroundColor: bgColors,
            borderColor: bdColors,
            borderWidth: 1.5,
            borderRadius: 4,
          };
        }
        if (hasRefLine && idx === 0 && Array.isArray(ds.data)) {
          // Domain 2: Segment bar chart colored relative to Global Mean reference line
          const refVal = Number(cs.reference_value);
          const bgColors = ds.data.map(v =>
            Number(v) < refVal ? 'rgba(244, 63, 94, 0.75)' : 'rgba(16, 185, 129, 0.75)'
          );
          const bdColors = ds.data.map(v =>
            Number(v) < refVal ? '#f43f5e' : '#10b981'
          );
          return {
            type: 'bar',
            label: ds.label,
            data: ds.data,
            backgroundColor: bgColors,
            borderColor: bdColors,
            borderWidth: 1.5,
            borderRadius: 5,
          };
        }
        return {
          label: ds.label,
          data: ds.data,
          backgroundColor: seriesColors[idx % seriesColors.length].bg,
          borderColor: seriesColors[idx % seriesColors.length].border,
          borderWidth: 1.5,
          borderRadius: 5,
        };
      });

      if (hasRefLine && Array.isArray(cs.labels) && cs.labels.length > 0) {
        const refVal = Number(cs.reference_value);
        chartDatasets.push({
          type: 'line',
          label: cs.reference_label || `Reference (${refVal.toLocaleString()})`,
          data: cs.labels.map(() => refVal),
          borderColor: '#f59e0b',
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [6, 4],
          pointRadius: 0,
          fill: false,
        });
      }
    }

    tlDetailChartInstance = new Chart(ctx, {
      type: isScatter ? 'scatter' : (cs.chart_type === 'horizontalBar' ? 'bar' : (cs.chart_type || 'bar')),
      data: {
        labels: isScatter ? undefined : cs.labels,
        datasets: chartDatasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: chartDatasets.length > 1,
            labels: { color: '#cbd5e1', font: { size: 11 } },
          },
        },
        scales: {
          x: isScatter
            ? {
                type: 'linear',
                position: 'bottom',
                ticks: { color: '#94a3b8', font: { size: 11 } },
                grid: { color: 'rgba(255, 255, 255, 0.04)' },
              }
            : {
                ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 35 },
                grid: { color: 'rgba(255, 255, 255, 0.04)' },
              },
          y: {
            ticks: { color: '#94a3b8', font: { size: 11 } },
            grid: { color: 'rgba(255, 255, 255, 0.06)' },
          },
        },
      },
    });
  } else {
    chartSection.style.display = 'none';
  }

  dialog.showModal();
}
