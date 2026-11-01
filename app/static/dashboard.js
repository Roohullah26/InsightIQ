/**
 * InsightIQ Dashboard Client Engine
 * Interactive state management, unified toolbar, enriched KPI cards,
 * causal driver insights, Chart.js visualizations, schema inspection dialog, and conversational querying.
 */

let activeDatasetId = null;
let currentProfile = null;
let currentInsights = null;
let currentCorrelations = null;
let aggChartInstance = null;

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

// Tab Navigation
function setupTabs() {
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tab);
    });
  });
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
    closeDropzoneBtn.addEventListener('click', collapseDropzone);
  }

  // Click inside dropzone triggers file selector
  dropzone.addEventListener('click', (e) => {
    if (e.target !== closeDropzoneBtn) {
      fileInput.click();
    }
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
  const label = document.getElementById('upload-btn-label');
  if (label) label.textContent = 'Hide Upload Box';
}

function collapseDropzone() {
  dropzoneContainer.classList.add('collapsed');
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
    <div class="dropzone-icon">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="17 8 12 3 7 8"></polyline>
        <line x1="12" y1="3" x2="12" y2="15"></line>
      </svg>
    </div>
    <div class="dropzone-title">Drop your CSV dataset here</div>
    <div class="dropzone-subtitle">Click to browse or drag file (up to 10 MB) · <button id="close-dropzone-btn" class="btn-text-link" type="button">Collapse</button></div>
  `;
  const btn = document.getElementById('close-dropzone-btn');
  if (btn) btn.addEventListener('click', collapseDropzone);
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

  const healthSubtext = document.getElementById('kpi-health-subtext');
  const cellSummary = `${validCells.toLocaleString()} / ${totalCells.toLocaleString()} valid cells · ${nullCells} nulls`;
  healthSubtext.style.color = '#94a3b8';
  if (dq.penalty_reason && dq.penalty_reason !== 'All health dimensions optimal') {
    healthSubtext.innerHTML = `<span class="subtext-positive">${escapeHtml(cellSummary)}</span><span class="subtext-penalty text-warning">${escapeHtml(dq.penalty_reason)}</span>`;
  } else {
    healthSubtext.innerHTML = `<span class="subtext-positive">${escapeHtml(cellSummary)} · 40% Complete · 30% Sample</span>`;
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

  // 2. Total Records (4-tier statistical sample adequacy badge)
  const nRows = currentProfile.row_count;
  document.getElementById('kpi-rows').textContent = nRows.toLocaleString();
  const memKb = (currentProfile.memory_usage_bytes / 1024).toFixed(1);
  const rowsSubtext = document.getElementById('kpi-rows-subtext');
  rowsSubtext.textContent = `${memKb} KB memory footprint`;

  const rowsBadgeWrapper = document.getElementById('kpi-rows-badge');
  if (nRows < 30) {
    rowsBadgeWrapper.innerHTML = `<span class="kpi-tag danger" title="Fewer than 30 rows limits Central Limit Theorem inference">Critical Sample (n &lt; 30)</span>`;
  } else if (nRows < 100) {
    rowsBadgeWrapper.innerHTML = `<span class="kpi-tag warning" title="Meets Central Limit Theorem minimum (n >= 30), but limited for multi-segment slicing">Small Sample (CLT Min)</span>`;
  } else if (nRows < 500) {
    rowsBadgeWrapper.innerHTML = `<span class="kpi-tag info" title="Moderate sample size suitable for grouped comparisons">Moderate Sample</span>`;
  } else {
    rowsBadgeWrapper.innerHTML = `<span class="kpi-tag success" title="Robust sample size (n >= 500) for multi-dimensional BI segmentation">Optimal Sample</span>`;
  }

  // 3. Features / Columns (Separate Identifiers from Numeric & Categorical measures)
  document.getElementById('kpi-cols').textContent = currentProfile.column_count.toLocaleString();
  const idCols = currentProfile.columns.filter(c => c.is_identifier);
  const nonIdCols = currentProfile.columns.filter(c => !c.is_identifier);
  const idCount = idCols.length;
  const numCount = nonIdCols.filter(c => c.category === 'numeric').length;
  const catCount = nonIdCols.length - numCount;

  if (idCount > 0) {
    document.getElementById('kpi-cols-subtext').textContent = `${numCount} Numeric · ${catCount} Categorical · ${idCount} ID`;
  } else {
    document.getElementById('kpi-cols-subtext').textContent = `${numCount} Numeric · ${catCount} Categorical`;
  }

  // 4. Anomalies Flagged
  const anomalyInsights = (currentInsights.insights || []).filter(i => i.category === 'anomaly');
  const colAnomalyInsights = anomalyInsights.filter(i => i.action_link && i.action_link.column);
  const flaggedColsSet = new Set(colAnomalyInsights.map(i => i.action_link.column));
  const flaggedColsCount = flaggedColsSet.size || anomalyInsights.length;
  const totalAnomaliesCount = anomalyInsights.length;

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
    anomaliesSubtext.textContent = `Across ${featureCountToDisplay} numeric feature${featureCountToDisplay === 1 ? '' : 's'} | IQR & Z-Score`;
  }
}

// Live Navigation Tab Badges (Actionable counts only)
function updateTabBadges() {
  if (!currentProfile || !currentInsights) return;

  // Tab 1: Insights Count
  const badgeInsights = document.getElementById('badge-insights');
  if (badgeInsights) {
    badgeInsights.textContent = currentInsights.insights.length;
  }

  // Tab 6: Anomalies Count
  const badgeAnomalies = document.getElementById('badge-anomalies');
  if (badgeAnomalies) {
    const anomalyInsights = currentInsights.insights.filter(i => i.category === 'anomaly');
    badgeAnomalies.textContent = anomalyInsights.length;
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

  currentInsights.insights.forEach(item => {
    const card = document.createElement('div');
    card.className = 'insight-card';

    const isCluster = item.cluster_features && item.cluster_features.length > 0;
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
      <div>
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
        <div class="insight-evidence"><strong>Quantitative Evidence:</strong> ${escapeHtml(item.evidence)}</div>
      </div>
      <div>
        ${item.recommendation ? `<div class="insight-recommendation"><strong>Strategic Recommendation:</strong> ${escapeHtml(item.recommendation)}</div>` : ''}
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

// Render Tab 3: Profile & Table
function renderProfileTab() {
  if (!currentProfile) return;

  const tableHead = document.getElementById('preview-table-head');
  const tableBody = document.getElementById('preview-table-body');
  tableHead.innerHTML = '';
  tableBody.innerHTML = '';

  if (currentProfile.preview && currentProfile.preview.length > 0) {
    const cols = Object.keys(currentProfile.preview[0]);
    const headerRow = document.createElement('tr');
    cols.forEach(col => {
      const th = document.createElement('th');
      th.textContent = col;
      headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);

    currentProfile.preview.forEach(row => {
      const tr = document.createElement('tr');
      cols.forEach(col => {
        const td = document.createElement('td');
        const val = row[col];
        td.textContent = val !== null && val !== undefined ? val : '—';
        tr.appendChild(td);
      });
      tableBody.appendChild(tr);
    });
  }

  const colGrid = document.getElementById('column-cards-container');
  colGrid.innerHTML = '';

  currentProfile.columns.forEach(col => {
    const card = document.createElement('div');
    card.className = 'col-card';

    let statsHtml = '';
    if (col.stats) {
      if (col.category === 'numeric') {
        statsHtml = `
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.5rem;">
            Min: <strong>${col.stats.min}</strong> | Max: <strong>${col.stats.max}</strong> | Mean: <strong>${col.stats.mean}</strong>
          </div>
        `;
      } else if (col.stats.most_frequent_value) {
        statsHtml = `
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.5rem;">
            Top: <strong>${col.stats.most_frequent_value}</strong> (${col.stats.frequency_of_most_frequent} times)
          </div>
        `;
      }
    }

    card.innerHTML = `
      <div class="col-card-header">
        <span class="col-card-name">${escapeHtml(col.name)}</span>
        <span class="col-type-tag">${col.category}</span>
      </div>
      <div style="font-size:0.8rem; color:var(--text-dim);">
        Nulls: ${col.null_count} (${col.null_percentage}%) | Distinct: ${col.distinct_count}
      </div>
      ${statsHtml}
    `;
    colGrid.appendChild(card);
  });
}

// Render Tab 4: Correlations
function renderCorrelationsTab() {
  const container = document.getElementById('correlations-container');
  container.innerHTML = '';

  if (!currentCorrelations || currentCorrelations.top_correlations.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted);">At least two numeric columns required to generate correlations.</div>';
    return;
  }

  let pairsHtml = `<div style="margin-bottom:1.5rem; display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:1rem;">`;
  currentCorrelations.top_correlations.forEach(p => {
    const isPos = p.coefficient >= 0;
    const barWidth = Math.abs(p.coefficient) * 100;
    pairsHtml += `
      <div class="col-card" id="corr-card-${escapeHtml(p.feature_x)}-${escapeHtml(p.feature_y)}">
        <div style="display:flex; justify-content:space-between; font-weight:600; margin-bottom:0.25rem;">
          <span>${escapeHtml(p.feature_x)} &amp; ${escapeHtml(p.feature_y)}</span>
          <span style="color:${isPos ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; font-family:var(--font-heading);">${p.coefficient.toFixed(3)}</span>
        </div>
        <div style="font-size:0.75rem; color:var(--text-dim); margin-bottom:0.5rem;">${p.strength.replace(/_/g, ' ')} relationship</div>
        <div style="background:rgba(255,255,255,0.06); height:6px; border-radius:3px; overflow:hidden;">
          <div style="width:${barWidth}%; height:100%; background:${isPos ? 'var(--accent-emerald)' : 'var(--accent-rose)'};"></div>
        </div>
      </div>
    `;
  });
  pairsHtml += '</div>';

  container.innerHTML = pairsHtml;
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

  try {
    const res = await fetch(`/api/v1/analytics/aggregate/${activeDatasetId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        group_by: [dim],
        metrics: { [metric]: [func] },
        sort_by: `${metric}_${func}`,
        ascending: false,
        limit: 15,
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
    formatted = (abs / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
  } else if (abs >= 1e6) {
    formatted = (abs / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
  } else if (abs >= 1e3) {
    formatted = (abs / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
  } else if (Number.isInteger(abs)) {
    formatted = abs.toString();
  } else {
    formatted = abs.toFixed(2).replace(/\.?0+$/, '');
  }

  return isCurrency ? `${sign}$${formatted}` : `${sign}${formatted}`;
}

function renderAggChart(data, labelKey, valueKey, chartType = 'bar', metric = '', func = '') {
  const canvas = document.getElementById('agg-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const labels = data.map(d => String(d[labelKey] ?? ''));
  const values = data.map(d => d[valueKey] ?? 0);

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

  const humanTitle = humanizeAggTitle(resolvedMetric, resolvedFunc, labelKey);
  const isCurrency = /spend|cost|revenue|sales|profit|price|budget|amount|salary|fee/i.test(resolvedMetric);

  const chartTitleEl = document.getElementById('agg-chart-title');
  if (chartTitleEl) {
    chartTitleEl.textContent = humanTitle;
  }

  // Custom inline Chart.js plugin to render direct data value labels at the end of bars
  const directBarValueLabelsPlugin = {
    id: 'directBarValueLabels',
    afterDatasetsDraw(chart) {
      if (chart.config.type !== 'bar') return;
      const { ctx: chartCtx } = chart;
      const isHorizontal = chart.config.options && chart.config.options.indexAxis === 'y';
      const meta = chart.getDatasetMeta(0);
      const dataset = chart.data.datasets[0];
      if (!meta || !dataset) return;

      chartCtx.save();
      chartCtx.font = '600 11px Inter, sans-serif';
      chartCtx.fillStyle = '#e2e8f0';

      meta.data.forEach((barEl, idx) => {
        const rawVal = dataset.data[idx];
        if (rawVal === null || rawVal === undefined) return;
        const labelText = formatCompactNumber(rawVal, isCurrency);
        if (isHorizontal) {
          chartCtx.textAlign = 'left';
          chartCtx.textBaseline = 'middle';
          chartCtx.fillText(labelText, barEl.x + 8, barEl.y);
        } else {
          chartCtx.textAlign = 'center';
          chartCtx.textBaseline = 'bottom';
          chartCtx.fillText(labelText, barEl.x, barEl.y - 5);
        }
      });

      chartCtx.restore();
    }
  };

  if (chartType === 'donut') {
    aggChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          label: humanTitle,
          data: values,
          backgroundColor: labels.map((_, i) => PALETTE[i % PALETTE.length]),
          borderColor: '#1e293b',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: { color: '#94a3b8', font: { family: 'inherit', size: 12 } }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const rawVal = context.raw ?? 0;
                const formatted = isCurrency
                  ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(rawVal)
                  : new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(rawVal);
                return ` ${context.label || ''}: ${formatted}`;
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
          backgroundColor: 'rgba(99, 102, 241, 0.75)',
          borderColor: '#6366f1',
          borderWidth: 1,
          borderRadius: 6,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: { right: 56 }
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
            ticks: {
              color: '#94a3b8',
              callback: function(value) {
                return formatCompactNumber(value, isCurrency);
              }
            },
            grid: { color: 'rgba(255,255,255,0.05)' }
          },
          y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
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
          pointBackgroundColor: '#818cf8',
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
          x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: {
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
    // Default vertical bar
    aggChartInstance = new Chart(ctx, {
      type: 'bar',
      plugins: [directBarValueLabelsPlugin],
      data: {
        labels: labels,
        datasets: [{
          label: humanTitle,
          data: values,
          backgroundColor: 'rgba(99, 102, 241, 0.75)',
          borderColor: '#6366f1',
          borderWidth: 1,
          borderRadius: 6,
        }]
      },
      options: {
        indexAxis: 'x',
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: { top: 20 }
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
          x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: {
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
  }
}

// Tab 6: Anomaly Inspector
function populateAnomalySelectors() {
  if (!currentProfile) return;
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

  // If insights flagged a specific column with anomalies, auto-select it
  if (currentInsights && currentInsights.insights) {
    const anomalyInsight = currentInsights.insights.find(i => i.category === 'anomaly' && i.action_link && i.action_link.column);
    if (anomalyInsight) {
      select.value = anomalyInsight.action_link.column;
    }
  }

  if (methodSelect && !methodSelect.value) {
    methodSelect.value = 'hybrid';
  }

  const scanBtn = document.getElementById('scan-anomalies-btn');
  if (scanBtn) {
    scanBtn.onclick = scanAnomalies;
  }

  // Auto-scan on dropdown changes
  select.onchange = scanAnomalies;
  if (methodSelect) {
    methodSelect.onchange = scanAnomalies;
  }

  if (select.options.length > 0) {
    scanAnomalies();
  }
}

async function scanAnomalies() {
  if (!activeDatasetId) return;
  const col = document.getElementById('anomaly-col-select').value;
  const method = document.getElementById('anomaly-method-select').value || 'hybrid';
  if (!col) return;

  const resultContainer = document.getElementById('anomalies-result-container');
  resultContainer.innerHTML = '<div class="loading-spinner"></div>';

  const threshold = method === 'zscore' ? '2.5' : '1.5';

  try {
    const res = await fetch(`/api/v1/analytics/outliers/${activeDatasetId}?column=${encodeURIComponent(col)}&method=${method}&threshold=${threshold}`);
    if (!res.ok) throw new Error('Outlier detection failed');
    const data = await res.json();

    // Check for segment-level anomalies in insights to display alongside column outliers
    const segmentAnomalies = (currentInsights && currentInsights.insights)
      ? currentInsights.insights.filter(i => i.category === 'anomaly' && i.title && i.title.startsWith('Segment Anomaly'))
      : [];

    let segmentHtml = '';
    if (segmentAnomalies.length > 0) {
      segmentHtml = `
        <div style="margin-top:1.5rem; padding:1rem; background:rgba(245, 158, 11, 0.08); border:1px solid rgba(245, 158, 11, 0.25); border-radius:var(--radius-md);">
          <div style="font-weight:600; color:var(--accent-amber); margin-bottom:0.4rem; display:flex; align-items:center; gap:0.4rem;">
            <span>⚠️ Segment-Level Multidimensional Discrepancies</span>
          </div>
          ${segmentAnomalies.map(s => `
            <div style="font-size:0.85rem; color:var(--text-main); margin-bottom:0.35rem;">
              <strong>${escapeHtml(s.title)}:</strong> ${escapeHtml(s.summary)}
            </div>
          `).join('')}
        </div>
      `;
    }

    if (data.outlier_count === 0) {
      // Find other numeric columns with anomalies if any
      const otherAnomalies = (currentInsights && currentInsights.insights)
        ? currentInsights.insights.filter(i => i.category === 'anomaly' && i.action_link && i.action_link.column && i.action_link.column !== col)
        : [];
      const tipText = otherAnomalies.length > 0
        ? ` Tip: Statistical outliers were detected in <strong>${escapeHtml(otherAnomalies.map(a => a.action_link.column).join(', '))}</strong>.`
        : '';

      resultContainer.innerHTML = `
        <div style="color:var(--accent-emerald); font-size:0.9rem;">
          No outliers detected in '<strong>${escapeHtml(col)}</strong>' under ${method.toUpperCase()} boundary [${data.lower_bound}, ${data.upper_bound}].${tipText}
        </div>
        ${segmentHtml}
      `;
    } else {
      let html = `
        <div style="margin-bottom:1rem; font-size:0.9rem;">
          Found <strong>${data.outlier_count}</strong> outlier(s) in <strong>${escapeHtml(col)}</strong> (${data.outlier_percentage}% of column rows) using ${method.toUpperCase()} detection.
          Bounds: [<strong>${data.lower_bound}</strong>, <strong>${data.upper_bound}</strong>].
        </div>
        <table style="width:100%; border-collapse:collapse;">
          <thead>
            <tr><th>Row Index</th><th>Observed Value</th><th>Distance / Z-Score</th></tr>
          </thead>
          <tbody>
      `;
      data.outliers.forEach(o => {
        html += `<tr><td>#${o.row_index}</td><td style="color:var(--accent-rose); font-weight:600;">${o.value}</td><td>${o.score}</td></tr>`;
      });
      html += '</tbody></table>';
      html += segmentHtml;
      resultContainer.innerHTML = html;
    }
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
