/**
 * InsightIQ Dashboard Client Engine
 * Interactive state management, API synchronization, Chart.js visualizations, and conversational querying.
 */

let activeDatasetId = null;
let currentProfile = null;
let currentInsights = null;
let currentCorrelations = null;
let aggChartInstance = null;

// DOM Elements
const datasetPicker = document.getElementById('dataset-picker');
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const demoBtn = document.getElementById('load-demo-btn');
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

// Chat DOM
const chatHistory = document.getElementById('chat-history');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send-btn');
const suggestionChips = document.querySelectorAll('.suggestion-chip');

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
  setupTabs();
  setupDropzone();
  setupChat();
  setupAggregationControls();
  await refreshDatasetList();
});

// Tab Navigation
function setupTabs() {
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add('active');
    });
  });
}

// Drag & Drop File Upload
function setupDropzone() {
  dropzone.addEventListener('click', () => fileInput.click());

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

  if (demoBtn) {
    demoBtn.addEventListener('click', loadDemoDataset);
  }

  datasetPicker.addEventListener('change', (e) => {
    if (e.target.value) {
      loadDataset(e.target.value);
    }
  });
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
    await refreshDatasetList(data.summary.dataset_id);
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
    <div class="dropzone-subtitle">Click to browse or drag file (up to 10 MB)</div>
  `;
}

// Load Demo Dataset
async function loadDemoDataset() {
  const demoCsv = (
    "region,store,revenue,marketing_spend,customers,satisfaction\n" +
    "North,Northgate Flagship,145000,28000,1450,4.8\n" +
    "North,Metro Galleria,120000,24000,1200,4.6\n" +
    "South,Bayside Center,95000,19000,950,4.5\n" +
    "South,Sun Valley Mall,82000,16500,820,4.2\n" +
    "East,Harbor Square,65000,13000,650,4.1\n" +
    "East,Midtown Plaza,58000,11500,580,4.0\n" +
    "West,Pacific Pavilion,320000,64000,3200,4.9\n" +
    "West,Silicon Hub,290000,58000,2900,4.7\n"
  );

  const blob = new Blob([demoCsv], { type: 'text/csv' });
  const file = new File([blob], 'executive_q3_performance.csv', { type: 'text/csv' });
  await uploadFile(file);
}

// Refresh Dataset Dropdown
async function refreshDatasetList(autoSelectId = null) {
  try {
    const res = await fetch('/api/v1/datasets');
    if (!res.ok) return;
    const datasets = await res.json();

    datasetPicker.innerHTML = '';
    if (datasets.length === 0) {
      datasetPicker.innerHTML = '<option value="">No datasets available — Upload above</option>';
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

    renderKPIs();
    renderInsightsTab();
    renderProfileTab();
    renderCorrelationsTab();
    populateAggregationSelectors();
    populateAnomalySelectors();
  } catch (err) {
    console.error('Error loading dataset views:', err);
  }
}

// Render Top KPI Cards
function renderKPIs() {
  if (!currentProfile || !currentInsights) return;

  document.getElementById('kpi-rows').textContent = currentProfile.row_count.toLocaleString();
  document.getElementById('kpi-cols').textContent = currentProfile.column_count.toLocaleString();

  const healthScore = currentInsights.data_quality.overall_score;
  const healthEl = document.getElementById('kpi-health');
  healthEl.textContent = `${healthScore.toFixed(0)}%`;
  healthEl.style.color = healthScore >= 80 ? 'var(--accent-emerald)' : healthScore >= 60 ? 'var(--accent-amber)' : 'var(--accent-rose)';

  const completeness = currentInsights.data_quality.completeness_score;
  document.getElementById('kpi-completeness').textContent = `${completeness.toFixed(1)}%`;
}

// Render Tab 1: AI Insights
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
    card.innerHTML = `
      <div>
        <div class="insight-header">
          <div class="insight-title">${escapeHtml(item.title)}</div>
          <span class="severity-badge severity-${item.severity}">${item.severity}</span>
        </div>
        <div class="insight-summary">${escapeHtml(item.summary)}</div>
        <div class="insight-evidence"><strong>Data Evidence:</strong> ${escapeHtml(item.evidence)}</div>
      </div>
      ${item.recommendation ? `<div class="insight-recommendation"><strong>Recommendation:</strong> ${escapeHtml(item.recommendation)}</div>` : ''}
    `;
    grid.appendChild(card);
  });
}

// Render Tab 2: Profile & Table
function renderProfileTab() {
  if (!currentProfile) return;

  // Render Preview Table
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

  // Render Column Metric Cards
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

// Render Tab 3: Correlations
function renderCorrelationsTab() {
  const container = document.getElementById('correlations-container');
  container.innerHTML = '';

  if (!currentCorrelations || currentCorrelations.top_correlations.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted);">At least two numeric columns required to generate correlations.</div>';
    return;
  }

  // Render Top Pairs List
  let pairsHtml = `<div style="margin-bottom:1.5rem; display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:1rem;">`;
  currentCorrelations.top_correlations.forEach(p => {
    const isPos = p.coefficient >= 0;
    const barWidth = Math.abs(p.coefficient) * 100;
    pairsHtml += `
      <div class="col-card">
        <div style="display:flex; justify-content:space-between; font-weight:600; margin-bottom:0.25rem;">
          <span>${escapeHtml(p.feature_x)} &amp; ${escapeHtml(p.feature_y)}</span>
          <span style="color:${isPos ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">${p.coefficient.toFixed(3)}</span>
        </div>
        <div style="font-size:0.75rem; color:var(--text-dim); margin-bottom:0.5rem;">${p.strength.replace('_', ' ')}</div>
        <div style="background:rgba(255,255,255,0.06); height:6px; border-radius:3px; overflow:hidden;">
          <div style="width:${barWidth}%; height:100%; background:${isPos ? 'var(--accent-emerald)' : 'var(--accent-rose)'};"></div>
        </div>
      </div>
    `;
  });
  pairsHtml += '</div>';

  container.innerHTML = pairsHtml;
}

// Tab 4: Aggregations & Visual Chart
function populateAggregationSelectors() {
  if (!currentProfile) return;

  const dimSelect = document.getElementById('agg-dim-select');
  const metricSelect = document.getElementById('agg-metric-select');

  dimSelect.innerHTML = '';
  metricSelect.innerHTML = '';

  currentProfile.columns.forEach(col => {
    if (col.category === 'categorical' || col.category === 'text' || col.category === 'boolean') {
      const opt = document.createElement('option');
      opt.value = col.name;
      opt.textContent = col.name;
      dimSelect.appendChild(opt);
    }
    if (col.category === 'numeric') {
      const opt = document.createElement('option');
      opt.value = col.name;
      opt.textContent = col.name;
      metricSelect.appendChild(opt);
    }
  });

  if (dimSelect.options.length > 0 && metricSelect.options.length > 0) {
    runAggregation();
  }
}

function setupAggregationControls() {
  const runBtn = document.getElementById('run-agg-btn');
  if (runBtn) {
    runBtn.addEventListener('click', runAggregation);
  }
}

async function runAggregation() {
  if (!activeDatasetId) return;

  const dim = document.getElementById('agg-dim-select').value;
  const metric = document.getElementById('agg-metric-select').value;
  const func = document.getElementById('agg-func-select').value;

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
        limit: 10,
      }),
    });

    if (!res.ok) return;
    const aggData = await res.json();
    renderAggChart(aggData.data, dim, `${metric}_${func}`);
  } catch (e) {
    console.error('Aggregation error:', e);
  }
}

function renderAggChart(data, labelKey, valueKey) {
  const ctx = document.getElementById('agg-chart').getContext('2d');
  const labels = data.map(d => String(d[labelKey]));
  const values = data.map(d => d[valueKey]);

  if (aggChartInstance) {
    aggChartInstance.destroy();
  }

  aggChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: valueKey,
        data: values,
        backgroundColor: 'rgba(99, 102, 241, 0.75)',
        borderColor: '#6366f1',
        borderWidth: 1,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94a3b8' } }
      },
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
      }
    }
  });
}

// Tab 5: Anomaly Inspector
function populateAnomalySelectors() {
  if (!currentProfile) return;
  const select = document.getElementById('anomaly-col-select');
  select.innerHTML = '';

  currentProfile.columns.filter(c => c.category === 'numeric').forEach(col => {
    const opt = document.createElement('option');
    opt.value = col.name;
    opt.textContent = col.name;
    select.appendChild(opt);
  });

  const scanBtn = document.getElementById('scan-anomalies-btn');
  if (scanBtn) {
    scanBtn.onclick = scanAnomalies;
  }

  if (select.options.length > 0) {
    scanAnomalies();
  }
}

async function scanAnomalies() {
  if (!activeDatasetId) return;
  const col = document.getElementById('anomaly-col-select').value;
  const method = document.getElementById('anomaly-method-select').value;
  if (!col) return;

  const resultContainer = document.getElementById('anomalies-result-container');
  resultContainer.innerHTML = '<div class="loading-spinner"></div>';

  try {
    const res = await fetch(`/api/v1/analytics/outliers/${activeDatasetId}?column=${encodeURIComponent(col)}&method=${method}&threshold=1.5`);
    if (!res.ok) throw new Error('Outlier detection failed');
    const data = await res.json();

    if (data.outlier_count === 0) {
      resultContainer.innerHTML = `<div style="color:var(--accent-emerald);">No outliers detected in '${col}' under ${method.toUpperCase()} boundary [${data.lower_bound}, ${data.upper_bound}].</div>`;
    } else {
      let html = `
        <div style="margin-bottom:1rem; font-size:0.9rem;">
          Found <strong>${data.outlier_count}</strong> outlier(s) in <strong>${col}</strong> (${data.outlier_percentage}% of column rows).
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
      resultContainer.innerHTML = html;
    }
  } catch (err) {
    resultContainer.innerHTML = `<div style="color:var(--accent-rose);">Error: ${err.message}</div>`;
  }
}

// Tab 6: Conversational Data Query Chat
function setupChat() {
  chatSendBtn.addEventListener('click', sendChatMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendChatMessage();
  });

  suggestionChips.forEach(chip => {
    chip.addEventListener('click', () => {
      chatInput.value = chip.textContent;
      sendChatMessage();
    });
  });
}

async function sendChatMessage() {
  const query = chatInput.value.trim();
  if (!query || !activeDatasetId) return;

  appendMessage('user', query);
  chatInput.value = '';

  const botMsgId = 'msg-' + Date.now();
  appendMessage('bot', `<div class="loading-spinner"></div>`, botMsgId);

  try {
    const res = await fetch(`/api/v1/query/${activeDatasetId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query }),
    });

    const data = await res.json();
    const botEl = document.getElementById(botMsgId);

    let html = `
      <span class="chat-intent-tag">${data.intent.replace('_', ' ')}</span>
      <div style="font-weight:500; margin-bottom:0.5rem;">${escapeHtml(data.answer)}</div>
    `;

    if (data.data_preview && data.data_preview.length > 0) {
      const keys = Object.keys(data.data_preview[0]);
      html += `<div style="overflow-x:auto; margin-top:0.5rem;"><table style="font-size:0.75rem;"><thead><tr>`;
      keys.forEach(k => html += `<th>${k}</th>`);
      html += `</tr></thead><tbody>`;
      data.data_preview.slice(0, 5).forEach(row => {
        html += `<tr>`;
        keys.forEach(k => html += `<td>${row[k] !== null ? row[k] : '—'}</td>`);
        html += `</tr>`;
      });
      html += `</tbody></table></div>`;
    }

    botEl.innerHTML = html;
  } catch (err) {
    const botEl = document.getElementById(botMsgId);
    botEl.innerHTML = `<div style="color:var(--accent-rose);">Error executing query: ${err.message}</div>`;
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
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
