// GPU Hunter - Interactive Client Application

let allListings = [];
let currentConfig = null;
let activeFilters = {
  vram: 'all',
  condition: 'all',
  platform: 'all',
  maxPrice: 5000,
  search: '',
  outliersOnly: false
};

const formatBRL = (val) => {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
};

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  setupEventListeners();
  await loadConfig();
  await loadData();
  checkScanStatus();
});

// Setup event listeners
function setupEventListeners() {
  // Search input
  const searchInput = document.getElementById('filter-search');
  searchInput.addEventListener('input', (e) => {
    activeFilters.search = e.target.value.toLowerCase().trim();
    renderFiltered();
  });

  // VRAM buttons
  document.querySelectorAll('.vram-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.vram-filter-btn').forEach(b => {
        b.classList.remove('bg-indigo-600', 'text-white');
        b.classList.add('text-slate-400');
      });
      btn.classList.add('bg-indigo-600', 'text-white');
      btn.classList.remove('text-slate-400');
      activeFilters.vram = btn.dataset.vram;
      renderFiltered();
    });
  });

  // Condition buttons
  document.querySelectorAll('.cond-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cond-filter-btn').forEach(b => {
        b.classList.remove('bg-indigo-600', 'text-white');
      });
      btn.classList.add('bg-indigo-600', 'text-white');
      activeFilters.condition = btn.dataset.cond;
      renderFiltered();
    });
  });

  // Platform buttons
  document.querySelectorAll('.platform-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.platform-filter-btn').forEach(b => {
        b.classList.remove('bg-indigo-600', 'text-white');
        b.classList.add('bg-slate-900', 'text-slate-400');
      });
      btn.classList.add('bg-indigo-600', 'text-white');
      btn.classList.remove('bg-slate-900', 'text-slate-400');
      activeFilters.platform = btn.dataset.platform;
      renderFiltered();
    });
  });

  // Price slider
  const slider = document.getElementById('price-slider');
  const sliderVal = document.getElementById('price-slider-val');
  slider.addEventListener('input', (e) => {
    activeFilters.maxPrice = parseFloat(e.target.value);
    sliderVal.textContent = formatBRL(activeFilters.maxPrice);
    renderFiltered();
  });

  // Outliers only checkbox
  document.getElementById('chk-outliers-only').addEventListener('change', (e) => {
    activeFilters.outliersOnly = e.target.checked;
    renderFiltered();
  });

  // Scan button
  document.getElementById('btn-run-scan').addEventListener('click', triggerScan);

  // Config Modal
  document.getElementById('btn-open-config').addEventListener('click', openConfigModal);
  document.getElementById('btn-close-config').addEventListener('click', closeConfigModal);
  document.getElementById('btn-cancel-config').addEventListener('click', closeConfigModal);
  document.getElementById('btn-save-config').addEventListener('click', saveConfigChanges);

  // Benchmark Modal
  document.getElementById('btn-close-bm').addEventListener('click', () => {
    document.getElementById('modal-benchmark').classList.add('hidden');
  });

  window.addEventListener('resize', () => {
    Plotly.Plots.resize('gpu-chart');
  });
}

// Fetch and load data
async function loadData() {
  try {
    const [listingsRes, summaryRes] = await Promise.all([
      fetch('/api/listings'),
      fetch('/api/summary')
    ]);

    allListings = await listingsRes.json();
    const summary = await summaryRes.json();

    updateKPIs(summary);
    renderFiltered();
  } catch (err) {
    console.error('Erro ao carregar dados:', err);
  }
}

// Load and populate config
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    currentConfig = await res.json();
    if (currentConfig && currentConfig.location) {
      document.getElementById('header-location').textContent = 
        `${currentConfig.location.center_city} - ${currentConfig.location.state} (Raio ${currentConfig.location.radius_km}km)`;
    }
  } catch (err) {
    console.error('Erro ao carregar config:', err);
  }
}

// Update KPI cards
function updateKPIs(summary) {
  document.getElementById('kpi-total').textContent = summary.total_found;
  document.getElementById('kpi-working').textContent = summary.working_count;
  document.getElementById('kpi-defective').textContent = summary.defective_count;

  if (summary.lowest_price > 0) {
    document.getElementById('kpi-lowest-price').textContent = formatBRL(summary.lowest_price);
    const lowestItem = allListings.find(i => i.price === summary.lowest_price);
    if (lowestItem) {
      document.getElementById('kpi-lowest-desc').textContent = `${lowestItem.detected_model} (${lowestItem.city})`;
    }
  }

  if (summary.best_deal) {
    const bd = summary.best_deal;
    document.getElementById('kpi-best-deal-price').textContent = formatBRL(bd.price);
    const diffPct = bd.price_diff_percent || 0;
    document.getElementById('kpi-best-deal-diff').textContent = 
      `${bd.detected_model} (${diffPct > 0 ? '+' : ''}${diffPct.toFixed(0)}% vs Brasil)`;
  }
}

// Filter listings
function getFilteredListings() {
  return allListings.filter(item => {
    // VRAM filter
    if (activeFilters.vram !== 'all' && item.detected_vram_gb !== parseInt(activeFilters.vram)) {
      return false;
    }
    // Condition filter
    if (activeFilters.condition !== 'all' && item.condition !== activeFilters.condition) {
      return false;
    }
    // Platform filter
    if (activeFilters.platform !== 'all' && item.platform.toLowerCase() !== activeFilters.platform.toLowerCase()) {
      return false;
    }
    // Max price
    if (item.price > activeFilters.maxPrice) {
      return false;
    }
    // Outliers only
    if (activeFilters.outliersOnly && !item.is_outlier) {
      return false;
    }
    // Search query
    if (activeFilters.search) {
      const matchText = `${item.title} ${item.city} ${item.detected_model} ${item.platform}`.toLowerCase();
      if (!matchText.includes(activeFilters.search)) {
        return false;
      }
    }
    return true;
  });
}

// Render chart and cards
function renderFiltered() {
  const filtered = getFilteredListings();
  document.getElementById('listings-count').textContent = filtered.length;
  renderPlotlyChart(filtered);
  renderListingsCards(filtered);
  if (window.lucide) {
    lucide.createIcons();
  }
}

// Render interactive Plotly Chart
function renderPlotlyChart(listings) {
  const chartEl = document.getElementById('gpu-chart');
  if (!listings || listings.length === 0) {
    Plotly.purge(chartEl);
    chartEl.innerHTML = '<div class="h-full flex items-center justify-center text-slate-500 text-sm">Nenhuma placa encontrada com os filtros selecionados.</div>';
    return;
  }

  // 1. Placas Funcionais Normais (Verde, Círculo)
  // 2. Placas com Defeito Normais (Vermelho, Quadrado)
  // 3. Outliers vs Placas Iguais (Laranja, Diamante)

  const traces = [
    {
      name: 'Funcional (Verde)',
      x: [], y: [], text: [], customdata: [],
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: '#10B981', // Verde
        size: 12,
        symbol: 'circle',
        line: { color: '#047857', width: 1.5 }
      }
    },
    {
      name: 'Com Defeito / Peças (Vermelho)',
      x: [], y: [], text: [], customdata: [],
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: '#EF4444', // Vermelho
        size: 12,
        symbol: 'square',
        line: { color: '#B91C1C', width: 1.5 }
      }
    },
    {
      name: 'Outlier vs Iguais (Laranja)',
      x: [], y: [], text: [], customdata: [],
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: '#F97316', // Laranja vibrante para Outliers
        size: 15,
        symbol: 'diamond',
        line: { color: '#EA580C', width: 2 }
      }
    }
  ];

  listings.forEach(item => {
    const isOutlier = item.is_outlier;
    const isWorking = item.condition === 'WORKING';

    let traceIdx = 0;
    if (isOutlier) {
      traceIdx = 2; // OBRIGATÓRIO: Qualquer outlier aparece em LARANJA
    } else if (isWorking) {
      traceIdx = 0; // Placa boa/funcional aparece em VERDE
    } else {
      traceIdx = 1; // Placa com defeito aparece em VERMELHO
    }

    traces[traceIdx].x.push(item.detected_model);
    traces[traceIdx].y.push(item.price);
    traces[traceIdx].text.push(item.title);
    traces[traceIdx].customdata.push(item);
  });

  const activeTraces = traces.filter(t => t.x.length > 0);

  const layout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    margin: { l: 60, r: 20, t: 20, b: 65 },
    xaxis: {
      color: '#94A3B8',
      gridcolor: '#1E293B',
      tickfont: { size: 11, color: '#CBD5E1', family: 'Inter, sans-serif' },
      zerolinecolor: '#334155'
    },
    yaxis: {
      title: 'Preço (R$)',
      color: '#94A3B8',
      gridcolor: '#1E293B',
      tickformat: ',.0f',
      tickprefix: 'R$ ',
      tickfont: { size: 11, color: '#CBD5E1', family: 'Inter, sans-serif' },
      zerolinecolor: '#334155'
    },
    showlegend: false,
    hovermode: 'closest'
  };

  const config = {
    responsive: true,
    displayModeBar: false
  };

  Plotly.newPlot('gpu-chart', activeTraces, layout, config);

  const chartDiv = document.getElementById('gpu-chart');
  const hoverCard = document.getElementById('chart-hover-card');

  // Hover interaction: display detailed floating card
  chartDiv.on('plotly_hover', function(data) {
    if (!data.points || data.points.length === 0) return;
    const pt = data.points[0];
    const item = pt.customdata;
    if (!item) return;

    document.getElementById('hover-title').textContent = item.title;
    document.getElementById('hover-price').textContent = formatBRL(item.price);
    const distStr = (item.distance_km !== null && item.distance_km !== undefined) ? ` • ${item.distance_km} km` : '';
    document.getElementById('hover-city').textContent = `${item.city} (${item.platform})${distStr}`;
    document.getElementById('hover-platform').textContent = item.platform;
    document.getElementById('hover-vram').textContent = `${item.detected_vram_gb}GB VRAM`;

    const imgEl = document.getElementById('hover-img');
    imgEl.src = item.image_url || 'https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=100&q=80';

    const condEl = document.getElementById('hover-condition');
    if (item.condition === 'WORKING') {
      condEl.textContent = '100% Funcional';
      condEl.className = 'text-emerald-400 font-medium';
    } else {
      condEl.textContent = 'Com Defeito / Para Peças';
      condEl.className = 'text-rose-400 font-medium';
    }

    const bmEl = document.getElementById('hover-benchmark');
    if (item.price_diff_percent !== null && item.price_diff_percent !== undefined) {
      const diff = item.price_diff_percent;
      const label = diff < -8 ? 'Barata' : (diff > 10 ? 'Cara' : 'Na Média');
      const prefix = diff > 0 ? '+' : '';
      bmEl.textContent = `${label} (${prefix}${diff.toFixed(0)}% vs Brasil)`;
      bmEl.className = diff < -8 ? 'text-emerald-400 font-bold' : (diff > 10 ? 'text-amber-400 font-bold' : 'text-slate-300 font-medium');
    } else {
      bmEl.textContent = 'Sem benchmark';
      bmEl.className = 'text-slate-400';
    }

    const outlierEl = document.getElementById('hover-outlier');
    if (item.is_outlier) {
      outlierEl.classList.remove('hidden');
      const outlierDesc = item.outlier_type === 'LOW_OUTLIER' ? 'MUITO MAIS BARATA' : 'MUITO MAIS CARA';
      outlierEl.textContent = `OUTLIER (${outlierDesc} QUE AS IGUAIS)`;
      outlierEl.className = 'px-1.5 py-0.5 rounded text-[10px] font-bold bg-orange-500/25 text-orange-400 border border-orange-500/50';
    } else {
      outlierEl.classList.add('hidden');
    }

    // Position floating hover card near cursor/marker
    const chartRect = chartDiv.getBoundingClientRect();
    const xPos = pt.xaxis.d2p(pt.x) + chartRect.left - 20;
    const yPos = pt.yaxis.d2p(pt.y) + chartRect.top - 120;

    // Boundary protection inside container
    const left = Math.min(Math.max(10, pt.xaxis.d2p(pt.x) - 150), chartDiv.clientWidth - 330);
    const top = Math.max(10, pt.yaxis.d2p(pt.y) - 150);

    hoverCard.style.left = `${left}px`;
    hoverCard.style.top = `${top}px`;
    hoverCard.classList.remove('hidden');
  });

  chartDiv.on('plotly_unhover', function() {
    hoverCard.classList.add('hidden');
  });

  // CRITICAL REQUIREMENT: Click point opens listing URL in new tab!
  chartDiv.on('plotly_click', function(data) {
    if (!data.points || data.points.length === 0) return;
    const item = data.points[0].customdata;
    if (item && item.url) {
      window.open(item.url, '_blank');
    }
  });
}

// Render cards below chart
function renderListingsCards(listings) {
  const container = document.getElementById('listings-container');
  container.innerHTML = '';

  if (!listings || listings.length === 0) {
    container.innerHTML = '<div class="col-span-full py-8 text-center text-slate-500 text-sm">Nenhum anúncio correspondente aos filtros.</div>';
    return;
  }

  listings.forEach(item => {
    const isWorking = item.condition === 'WORKING';
    const isOutlier = item.is_outlier;

    // Badges
    const condBadge = isWorking 
      ? '<span class="badge-working text-[11px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Funcional</span>'
      : '<span class="badge-defective text-[11px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Com Defeito</span>';

    let bmBadge = '';
    if (item.price_diff_percent !== null && item.price_diff_percent !== undefined) {
      const diff = item.price_diff_percent;
      const prefix = diff > 0 ? '+' : '';
      if (item.price_classification === 'OPPORTUNITY') {
        bmBadge = `<span class="badge-opportunity text-[10px] font-bold px-2 py-0.5 rounded-full">Oportunidade (${prefix}${diff.toFixed(0)}%)</span>`;
      } else if (item.price_classification === 'CHEAP') {
        bmBadge = `<span class="badge-cheap text-[10px] font-bold px-2 py-0.5 rounded-full">Barata (${prefix}${diff.toFixed(0)}%)</span>`;
      } else if (item.price_classification === 'AVERAGE') {
        bmBadge = `<span class="badge-average text-[10px] font-medium px-2 py-0.5 rounded-full">Na Média (${prefix}${diff.toFixed(0)}%)</span>`;
      } else if (item.price_classification === 'EXPENSIVE') {
        bmBadge = `<span class="badge-expensive text-[10px] font-medium px-2 py-0.5 rounded-full">Cara (${prefix}${diff.toFixed(0)}%)</span>`;
      } else if (item.price_classification === 'VERY_EXPENSIVE') {
        bmBadge = `<span class="badge-very-expensive text-[10px] font-bold px-2 py-0.5 rounded-full">Muito Cara (${prefix}${diff.toFixed(0)}%)</span>`;
      }
    }

    const outlierBadge = isOutlier 
      ? '<span class="outlier-badge px-2 py-0.5 text-[10px] font-bold rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/40">OUTLIER VS IGUAIS</span>'
      : '';

    const imgUrl = item.image_url || 'https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=300&q=80';

    const card = document.createElement('div');
    card.className = `glass-panel rounded-xl overflow-hidden p-4 flex flex-col justify-between border transition duration-200 hover:-translate-y-0.5 ${isOutlier ? 'border-orange-500/50 shadow-lg shadow-orange-500/10' : 'border-slate-800'}`;
    
    card.innerHTML = `
      <div>
        <div class="flex items-start gap-3">
          <div class="relative w-20 h-20 rounded-lg overflow-hidden bg-slate-800 flex-shrink-0">
            <img src="${imgUrl}" alt="${item.title}" class="w-full h-full object-cover">
            <span class="absolute bottom-1 left-1 px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-black/80 text-white">
              ${item.platform}
            </span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-1.5">
              ${condBadge}
              ${outlierBadge}
              <span class="text-[11px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                ${item.detected_vram_gb}GB VRAM
              </span>
            </div>
            <h4 class="text-xs font-semibold text-white mt-1.5 line-clamp-2" title="${item.title}">${item.title}</h4>
            <div class="text-base font-bold text-white mt-1">${formatBRL(item.price)}</div>
          </div>
        </div>

        <div class="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <span class="flex items-center gap-1">
            <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-500"></i> ${item.city} ${item.distance_km !== null && item.distance_km !== undefined ? '<span class="text-[10px] text-slate-400 font-mono">(' + item.distance_km + ' km)</span>' : ''}
          </span>
          <div>${bmBadge}</div>
        </div>

        ${!isWorking && item.defect_reasons && item.defect_reasons.length > 0 ? `
          <div class="mt-2 text-[11px] text-rose-300 bg-rose-950/30 border border-rose-900/40 p-1.5 rounded-lg flex items-center gap-1">
            <i data-lucide="alert-circle" class="w-3 h-3 flex-shrink-0"></i>
            <span class="truncate">Motivo: ${item.defect_reasons.join(', ')}</span>
          </div>
        ` : ''}
      </div>

      <div class="mt-4 pt-3 border-t border-slate-800 flex items-center gap-2">
        <button class="btn-view-benchmark flex-1 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition flex items-center justify-center gap-1" data-id="${item.id}">
          <i data-lucide="bar-chart-2" class="w-3.5 h-3.5"></i> Comparativo
        </button>
        <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="flex-1 py-1.5 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition flex items-center justify-center gap-1 shadow-sm">
          <span>Abrir Anúncio</span>
          <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
        </a>
      </div>
    `;

    // Benchmark button click
    card.querySelector('.btn-view-benchmark').addEventListener('click', () => {
      openBenchmarkModal(item);
    });

    container.appendChild(card);
  });
}

// Trigger live scraping
async function triggerScan() {
  const scanBtn = document.getElementById('btn-run-scan');
  const scanIcon = document.getElementById('scan-icon');
  const indicator = document.getElementById('scan-status-indicator');

  scanBtn.disabled = true;
  scanIcon.classList.add('animate-spin');
  indicator.classList.remove('hidden');
  indicator.classList.add('flex');

  try {
    const res = await fetch('/api/scan', { method: 'POST' });
    const data = await res.json();
    console.log('Varredura disparada:', data);

    // Poll status every 2 seconds
    const interval = setInterval(async () => {
      const statusRes = await fetch('/api/scan/status');
      const status = await statusRes.json();
      if (!status.is_scanning) {
        clearInterval(interval);
        scanBtn.disabled = false;
        scanIcon.classList.remove('animate-spin');
        indicator.classList.add('hidden');
        indicator.classList.remove('flex');
        await loadData();
      }
    }, 2000);
  } catch (err) {
    console.error('Erro na varredura:', err);
    scanBtn.disabled = false;
    scanIcon.classList.remove('animate-spin');
    indicator.classList.add('hidden');
  }
}

// Check scan status on page load
async function checkScanStatus() {
  try {
    const statusRes = await fetch('/api/scan/status');
    const status = await statusRes.json();
    if (status.is_scanning) {
      const indicator = document.getElementById('scan-status-indicator');
      const scanBtn = document.getElementById('btn-run-scan');
      const scanIcon = document.getElementById('scan-icon');
      indicator.classList.remove('hidden');
      indicator.classList.add('flex');
      scanBtn.disabled = true;
      scanIcon.classList.add('animate-spin');
    }
  } catch (e) {}
}

// Open Benchmark Modal
function openBenchmarkModal(item) {
  const modal = document.getElementById('modal-benchmark');
  const title = document.getElementById('bm-modal-title');
  const body = document.getElementById('bm-modal-body');

  title.textContent = `Comparativo Nacional: ${item.detected_model}`;

  const bm = item.national_benchmark;
  if (!bm || bm.median_price <= 0) {
    body.innerHTML = `
      <div class="p-4 bg-slate-950 rounded-xl text-center text-slate-400">
        Estatísticas nacionais ainda sendo consolidadas para este modelo.
      </div>
    `;
    modal.classList.remove('hidden');
    return;
  }

  const diffBRL = item.price_diff_brl || (item.price - bm.median_price);
  const diffPct = item.price_diff_percent || 0;
  const isCheaper = diffBRL <= 0;

  body.innerHTML = `
    <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
      <div class="flex items-center justify-between">
        <span class="text-slate-400">Preço Local em ${item.city}:</span>
        <span class="text-base font-bold text-white">${formatBRL(item.price)}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-slate-400">Mediana Nacional (Brasil):</span>
        <span class="text-base font-bold text-slate-300">${formatBRL(bm.median_price)}</span>
      </div>
      <div class="flex items-center justify-between pt-2 border-t border-slate-800">
        <span class="text-slate-300 font-semibold">Diferença vs Mediana:</span>
        <span class="text-base font-bold ${isCheaper ? 'text-emerald-400' : 'text-amber-400'}">
          ${isCheaper ? 'Economia de ' : 'Ágio de '} ${formatBRL(Math.abs(diffBRL))} (${diffPct > 0 ? '+' : ''}${diffPct.toFixed(1)}%)
        </span>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-2 text-center">
      <div class="p-2.5 bg-slate-950 rounded-lg border border-slate-800">
        <div class="text-[10px] text-slate-500 uppercase font-semibold">Mínimo Brasil</div>
        <div class="text-xs font-bold text-emerald-400 mt-1">${formatBRL(bm.min_price)}</div>
      </div>
      <div class="p-2.5 bg-slate-950 rounded-lg border border-slate-800">
        <div class="text-[10px] text-slate-500 uppercase font-semibold">Média Brasil</div>
        <div class="text-xs font-bold text-slate-300 mt-1">${formatBRL(bm.mean_price)}</div>
      </div>
      <div class="p-2.5 bg-slate-950 rounded-lg border border-slate-800">
        <div class="text-[10px] text-slate-500 uppercase font-semibold">Máximo Brasil</div>
        <div class="text-xs font-bold text-rose-400 mt-1">${formatBRL(bm.max_price)}</div>
      </div>
    </div>

    <div class="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-400">
      <div class="flex justify-between text-[11px] mb-1">
        <span>Faixa Típica (Q1 - Q3):</span>
        <span class="text-slate-200 font-medium">${formatBRL(bm.q1_price)} até ${formatBRL(bm.q3_price)}</span>
      </div>
      <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden mt-1 relative">
        <div class="bg-indigo-500 h-full rounded-full" style="width: ${Math.min(100, Math.max(10, ((item.price - bm.min_price) / (bm.max_price - bm.min_price || 1)) * 100))}%"></div>
      </div>
    </div>

    <div class="text-center pt-2">
      <a href="${item.url}" target="_blank" class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs">
        <span>Ir para o Anúncio Original</span>
        <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
      </a>
    </div>
  `;

  if (window.lucide) {
    lucide.createIcons();
  }
  modal.classList.remove('hidden');
}

// Config Modal controls
function openConfigModal() {
  if (!currentConfig) return;
  document.getElementById('cfg-min-vram').value = currentConfig.hardware.min_vram_gb;
  document.getElementById('cfg-max-vram').value = currentConfig.hardware.max_vram_gb;
  document.getElementById('cfg-max-price').value = currentConfig.hardware.max_price_brl;

  document.getElementById('cfg-center-city').value = currentConfig.location.center_city;
  document.getElementById('cfg-radius').value = currentConfig.location.radius_km;
  document.getElementById('cfg-target-cities').value = currentConfig.location.target_cities.join(', ');

  document.getElementById('cfg-fb-email').value = currentConfig.scrapers.facebook.email || '';
  document.getElementById('cfg-fb-password').value = currentConfig.scrapers.facebook.password || '';

  document.getElementById('cfg-defect-keywords').value = currentConfig.defect_detection.keywords.join(', ');

  document.getElementById('modal-config').classList.remove('hidden');
}

function closeConfigModal() {
  document.getElementById('modal-config').classList.add('hidden');
}

async function saveConfigChanges() {
  if (!currentConfig) return;

  currentConfig.hardware.min_vram_gb = parseInt(document.getElementById('cfg-min-vram').value) || 16;
  currentConfig.hardware.max_vram_gb = parseInt(document.getElementById('cfg-max-vram').value) || 32;
  currentConfig.hardware.max_price_brl = parseFloat(document.getElementById('cfg-max-price').value) || 5000;

  currentConfig.location.center_city = document.getElementById('cfg-center-city').value.trim();
  currentConfig.location.radius_km = parseInt(document.getElementById('cfg-radius').value) || 40;
  currentConfig.location.target_cities = document.getElementById('cfg-target-cities').value.split(',').map(s => s.trim()).filter(Boolean);

  currentConfig.scrapers.facebook.email = document.getElementById('cfg-fb-email').value.trim();
  currentConfig.scrapers.facebook.password = document.getElementById('cfg-fb-password').value.trim();

  currentConfig.defect_detection.keywords = document.getElementById('cfg-defect-keywords').value.split(',').map(s => s.trim()).filter(Boolean);

  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentConfig)
    });
    const result = await res.json();
    alert('Configurações salvas com sucesso no config.yaml!');
    closeConfigModal();
    await loadConfig();
    await loadData();
  } catch (err) {
    alert('Erro ao salvar configurações: ' + err);
  }
}
