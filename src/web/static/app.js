// GPU Hunter - Interactive Client Application

let allListings = [];
let currentConfig = null;
let currentLowestItem = null;
let currentBestDealItem = null;
let activeFilters = {
  minVram: 16,
  maxVram: 32,
  condition: 'all',
  platform: 'all',
  maxPrice: 5000,
  search: '',
  outliersOnly: false
};

const formatBRL = (val) => {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
};

// Retorna URL direta do anúncio real
const getEffectiveListingUrl = (item) => {
  if (!item) return '#';
  return item.url || '#';
};

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  setupEventListeners();
  await loadCities();
  await loadConfig();
  await loadData();
  checkScanStatus();
});

// Setup event listeners
function setupEventListeners() {
  // --- PASSO 1: ATUALIZAÇÃO DO BANCO DE DADOS (WEB SCRAPING) ---
  const updateDbBtn = document.getElementById('btn-update-db');
  if (updateDbBtn) {
    updateDbBtn.addEventListener('click', triggerScan);
  }

  // --- PASSO 2: FILTROS INSTANTÂNEOS NO BANCO DE DADOS ---
  // Range de VRAM Mínima e Máxima
  const minVramInput = document.getElementById('input-min-vram');
  if (minVramInput) {
    minVramInput.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      activeFilters.minVram = (!isNaN(val) && val >= 0) ? val : 0;
      renderFiltered();
    });
  }

  const maxVramInput = document.getElementById('input-max-vram');
  if (maxVramInput) {
    maxVramInput.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      activeFilters.maxVram = (!isNaN(val) && val >= 0) ? val : 999;
      renderFiltered();
    });
  }

  // Presets rápidos de VRAM
  document.querySelectorAll('.vram-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.vram-preset-btn').forEach(b => {
        b.classList.remove('bg-purple-600/30', 'text-purple-200', 'border-purple-500/50', 'font-bold');
        b.classList.add('bg-slate-900', 'text-slate-300');
      });
      btn.classList.remove('bg-slate-900', 'text-slate-300');
      btn.classList.add('bg-purple-600/30', 'text-purple-200', 'border-purple-500/50', 'font-bold');

      const minV = parseInt(btn.dataset.min);
      const maxV = parseInt(btn.dataset.max);
      activeFilters.minVram = minV;
      activeFilters.maxVram = maxV;
      if (minVramInput) minVramInput.value = minV;
      if (maxVramInput) maxVramInput.value = maxV;
      renderFiltered();
    });
  });

  // Search input
  const searchInput = document.getElementById('filter-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      activeFilters.search = e.target.value.toLowerCase().trim();
      renderFiltered();
    });
  }

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

  // Editable Max Price (Sem teto fixo, qualquer valor)
  const priceInput = document.getElementById('input-max-price');
  if (priceInput) {
    priceInput.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      activeFilters.maxPrice = (!isNaN(val) && val > 0) ? val : 99999999;
      renderFiltered();
    });
  }

  // Outliers only checkbox
  const chkOutliers = document.getElementById('chk-outliers-only');
  if (chkOutliers) {
    chkOutliers.addEventListener('change', (e) => {
      activeFilters.outliersOnly = e.target.checked;
      renderFiltered();
    });
  }

  // Toggle log box visibility button
  const toggleLogsBtn = document.getElementById('btn-toggle-logs');
  if (toggleLogsBtn) {
    toggleLogsBtn.addEventListener('click', () => {
      const logBox = document.getElementById('progress-log-box');
      if (logBox) {
        logBox.classList.toggle('hidden');
      }
    });
  }

  // Config Modal
  document.getElementById('btn-open-config').addEventListener('click', openConfigModal);
  document.getElementById('btn-close-config').addEventListener('click', closeConfigModal);
  document.getElementById('btn-cancel-config').addEventListener('click', closeConfigModal);
  document.getElementById('btn-save-config').addEventListener('click', saveConfigChanges);

  // Benchmark Modal
  document.getElementById('btn-close-bm').addEventListener('click', () => {
    document.getElementById('modal-benchmark').classList.add('hidden');
  });

  // Top KPI Card: Menor Preço Local (Click to open, Hover to view preview)
  const cardLowest = document.getElementById('card-kpi-lowest');
  if (cardLowest) {
    cardLowest.addEventListener('click', () => {
      if (currentLowestItem) {
        window.open(getEffectiveListingUrl(currentLowestItem), '_blank', 'noopener,noreferrer');
      }
    });
    cardLowest.addEventListener('mouseenter', () => {
      if (currentLowestItem) {
        showKpiPreview(currentLowestItem, cardLowest);
      }
    });
    cardLowest.addEventListener('mouseleave', () => {
      hideKpiPreview();
    });
  }

  // Top KPI Card: Melhor Oportunidade (Click to open, Hover to view preview)
  const cardBestDeal = document.getElementById('card-kpi-best-deal');
  if (cardBestDeal) {
    cardBestDeal.addEventListener('click', () => {
      if (currentBestDealItem) {
        window.open(getEffectiveListingUrl(currentBestDealItem), '_blank', 'noopener,noreferrer');
      }
    });
    cardBestDeal.addEventListener('mouseenter', () => {
      if (currentBestDealItem) {
        showKpiPreview(currentBestDealItem, cardBestDeal);
      }
    });
    cardBestDeal.addEventListener('mouseleave', () => {
      hideKpiPreview();
    });
  }

  window.addEventListener('resize', () => {
    Plotly.Plots.resize('gpu-chart');
  });
}

// Carrega cidades conhecidas para o datalist de Passo 1
async function loadCities() {
  try {
    const res = await fetch('/api/cities');
    const cities = await res.json();
    const datalist = document.getElementById('cities-list');
    if (datalist && Array.isArray(cities)) {
      datalist.innerHTML = cities.map(c => `<option value="${escapeHtml(c)}">`).join('');
    }
  } catch (e) {
    console.warn('Erro ao carregar cidades:', e);
  }
}

// Fetch and load data
async function loadData() {
  try {
    const [listingsRes, statsRes] = await Promise.all([
      fetch('/api/listings'),
      fetch('/api/database/stats')
    ]);

    allListings = await listingsRes.json();
    const stats = await statsRes.json();

    updateDatabaseBadges(stats.total_listings !== undefined ? stats.total_listings : allListings.length);
    renderFiltered();
  } catch (err) {
    console.error('Erro ao carregar dados:', err);
  }
}

// Atualiza contadores do banco de dados na UI
function updateDatabaseBadges(totalCount) {
  const headerBadge = document.getElementById('header-db-count');
  const badgeDb = document.getElementById('badge-db-count');
  const step2Total = document.getElementById('step-2-total');
  const emptyNotice = document.getElementById('empty-db-notice');

  if (headerBadge) headerBadge.textContent = totalCount;
  if (badgeDb) badgeDb.textContent = totalCount;
  if (step2Total) step2Total.textContent = totalCount;

  if (emptyNotice) {
    if (totalCount === 0) {
      emptyNotice.classList.remove('hidden');
    } else {
      emptyNotice.classList.add('hidden');
    }
  }
}

// Load and populate config
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    currentConfig = await res.json();
    if (currentConfig && currentConfig.location) {
      const city = currentConfig.location.center_city || 'Veranópolis';
      const rad = currentConfig.location.radius_km || 50;
      document.getElementById('header-location').textContent = 
        `${city} - RS e Região (Raio ${rad}km)`;
      const cityInput = document.getElementById('input-center-city');
      const radInput = document.getElementById('input-radius-km');
      if (cityInput && !cityInput.value) cityInput.value = city;
      if (radInput && !radInput.value) radInput.value = rad;
    }
  } catch (err) {
    console.error('Erro ao carregar config:', err);
  }
}

// Recalcula KPIs instantaneamente para a seleção filtrada em memória
function recalculateKPIs(filtered) {
  const kpiTotal = document.getElementById('kpi-total');
  const kpiWorking = document.getElementById('kpi-working');
  const kpiDefective = document.getElementById('kpi-defective');
  const kpiDesc = document.getElementById('kpi-filter-desc');

  if (kpiTotal) kpiTotal.textContent = filtered.length;

  const workingItems = filtered.filter(i => i.condition === 'WORKING');
  const defectiveItems = filtered.filter(i => i.condition === 'DEFECTIVE');

  if (kpiWorking) kpiWorking.textContent = workingItems.length;
  if (kpiDefective) kpiDefective.textContent = defectiveItems.length;

  if (kpiDesc) {
    const maxP = activeFilters.maxPrice >= 999999 ? 'Sem limite' : `R$ ${activeFilters.maxPrice.toLocaleString('pt-BR')}`;
    kpiDesc.textContent = `VRAM ${activeFilters.minVram} a ${activeFilters.maxVram} GB (até ${maxP})`;
  }

  // Menor Preço Local entre os filtrados
  const candidateLowest = workingItems.length > 0 ? workingItems : filtered;
  let lowestItem = null;
  if (candidateLowest.length > 0) {
    lowestItem = candidateLowest.reduce((prev, curr) => (curr.price > 0 && curr.price < prev.price) ? curr : prev, candidateLowest[0]);
  }
  currentLowestItem = lowestItem;

  const lowestPriceEl = document.getElementById('kpi-lowest-price');
  const lowestDescEl = document.getElementById('kpi-lowest-desc');
  const cardLowest = document.getElementById('card-kpi-lowest');

  if (lowestItem && lowestItem.price > 0) {
    if (lowestPriceEl) lowestPriceEl.textContent = formatBRL(lowestItem.price);
    if (lowestDescEl) lowestDescEl.textContent = `${lowestItem.detected_model} (${lowestItem.city})`;
    if (cardLowest) cardLowest.setAttribute('title', `Clique para abrir o anúncio de ${lowestItem.detected_model} na ${lowestItem.platform}`);
  } else {
    if (lowestPriceEl) lowestPriceEl.textContent = 'R$ 0';
    if (lowestDescEl) lowestDescEl.textContent = '-';
  }

  // Melhor Oportunidade: placa funcional com maior desconto vs mediana nacional
  let bestDealItem = null;
  let bestDiff = 99999;
  for (const item of (workingItems.length > 0 ? workingItems : filtered)) {
    if (item.price_diff_percent !== null && item.price_diff_percent !== undefined) {
      if (item.price_diff_percent < bestDiff) {
        bestDiff = item.price_diff_percent;
        bestDealItem = item;
      }
    }
  }
  currentBestDealItem = bestDealItem;

  const bestPriceEl = document.getElementById('kpi-best-deal-price');
  const bestDiffEl = document.getElementById('kpi-best-deal-diff');
  const cardBestDeal = document.getElementById('card-kpi-best-deal');

  if (bestDealItem) {
    if (bestPriceEl) bestPriceEl.textContent = formatBRL(bestDealItem.price);
    const diffPct = bestDealItem.price_diff_percent || 0;
    if (bestDiffEl) bestDiffEl.textContent = `${bestDealItem.detected_model} (${diffPct > 0 ? '+' : ''}${diffPct.toFixed(0)}% vs Brasil)`;
    if (cardBestDeal) cardBestDeal.setAttribute('title', `Clique para abrir o anúncio de ${bestDealItem.detected_model} na ${bestDealItem.platform}`);
  } else {
    if (bestPriceEl) bestPriceEl.textContent = 'R$ 0';
    if (bestDiffEl) bestDiffEl.textContent = 'vs Mediana Brasil';
  }
}

// Show Floating Preview Popover for Top KPI Cards (with photo, title, model, condition, benchmark)
function showKpiPreview(item, cardEl) {
  const popover = document.getElementById('kpi-preview-card');
  if (!popover || !item) return;

  // Photo / Thumbnail
  const imgEl = document.getElementById('kpi-prev-img');
  const noImgEl = document.getElementById('kpi-prev-no-img');
  if (item.image_url) {
    imgEl.src = item.image_url;
    imgEl.classList.remove('hidden');
    noImgEl.classList.add('hidden');
    imgEl.onerror = () => {
      imgEl.classList.add('hidden');
      noImgEl.classList.remove('hidden');
    };
  } else {
    imgEl.classList.add('hidden');
    noImgEl.classList.remove('hidden');
  }

  // Platform badge
  const platformEl = document.getElementById('kpi-prev-platform');
  const isFb = (item.platform || '').toLowerCase().includes('facebook');
  platformEl.textContent = item.platform || 'OLX';
  if (isFb) {
    platformEl.className = 'absolute top-2 left-2 px-2 py-0.5 rounded-md text-[11px] font-bold shadow bg-blue-600/90 text-white border border-blue-400';
  } else {
    platformEl.className = 'absolute top-2 left-2 px-2 py-0.5 rounded-md text-[11px] font-bold shadow bg-amber-600/90 text-white border border-amber-400';
  }

  // Status & Outlier badges
  const badgesEl = document.getElementById('kpi-prev-badges');
  badgesEl.innerHTML = '';
  if (item.condition === 'WORKING') {
    badgesEl.innerHTML += '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/25 text-emerald-300 border border-emerald-500/40">🟢 Funcional</span>';
  } else {
    badgesEl.innerHTML += '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/25 text-rose-300 border border-rose-500/40">🔴 Com Defeito</span>';
  }
  if (item.is_outlier) {
    const outlierDesc = item.outlier_type === 'LOW_OUTLIER' ? 'MUITO BARATA' : 'MUITO CARA';
    badgesEl.innerHTML += `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-500/25 text-orange-300 border border-orange-500/40">⚠️ Outlier vs Iguais (${outlierDesc})</span>`;
  }

  // Model & VRAM
  document.getElementById('kpi-prev-model').textContent = item.detected_model || 'NVIDIA';
  document.getElementById('kpi-prev-vram').textContent = `${item.detected_vram_gb || '--'}GB VRAM`;
  document.getElementById('kpi-prev-title').textContent = item.title;
  document.getElementById('kpi-prev-price').textContent = formatBRL(item.price);

  // Compute capability
  const computeEl = document.getElementById('kpi-prev-compute');
  if (computeEl) {
    const tflops = item.compute_tflops !== null && item.compute_tflops !== undefined ? `${item.compute_tflops} TFLOPS` : '--';
    const arch = item.architecture ? ` (${item.architecture})` : '';
    computeEl.textContent = `${tflops}${arch}`;
  }

  // Location & Distance
  const distStr = (item.distance_km !== null && item.distance_km !== undefined) ? ` (${item.distance_km} km de Veranópolis)` : '';
  document.getElementById('kpi-prev-location').textContent = `${item.city || 'Serra Gaúcha'}${distStr}`;

  // Condition
  const condEl = document.getElementById('kpi-prev-condition');
  if (item.condition === 'WORKING') {
    condEl.textContent = '🟢 Funcional (Sem defeitos)';
    condEl.className = 'font-semibold text-emerald-400';
  } else {
    const reason = (item.defect_reasons && item.defect_reasons.length > 0) ? ` (${item.defect_reasons[0]})` : '';
    condEl.textContent = `🔴 Para conserto / peças${reason}`;
    condEl.className = 'font-semibold text-rose-400';
  }

  // Benchmark vs Brasil
  const bmEl = document.getElementById('kpi-prev-benchmark');
  if (item.price_diff_percent !== null && item.price_diff_percent !== undefined) {
    const diff = item.price_diff_percent;
    const prefix = diff > 0 ? '+' : '';
    const med = item.national_benchmark ? formatBRL(item.national_benchmark.median_price) : '';
    bmEl.textContent = `${med ? `${med} • ` : ''}${prefix}${diff.toFixed(0)}% (${item.price_classification || 'Benchmark'})`;
    bmEl.className = diff < -8 ? 'font-bold text-emerald-400' : (diff > 10 ? 'font-bold text-amber-400' : 'font-medium text-slate-300');
  } else {
    bmEl.textContent = 'Sem dados de benchmark nacional';
    bmEl.className = 'text-slate-400 font-normal';
  }

  // Update Call-to-action text
  const ctaEl = document.getElementById('kpi-prev-cta-text');
  if (ctaEl) {
    ctaEl.textContent = `Clique para abrir o anúncio real na ${item.platform}`;
  }

  // Dynamic Positioning
  const rect = cardEl.getBoundingClientRect();
  const popoverWidth = 340;
  let left = rect.left + (rect.width / 2) - (popoverWidth / 2);
  if (left < 16) left = 16;
  if (left + popoverWidth > window.innerWidth - 16) {
    left = window.innerWidth - popoverWidth - 16;
  }

  let top = rect.bottom + 8;
  const popoverHeight = 380;
  if (top + popoverHeight > window.innerHeight && rect.top > popoverHeight + 16) {
    top = rect.top - popoverHeight - 8;
  }

  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
  popover.classList.remove('hidden');

  if (window.lucide) {
    lucide.createIcons();
  }
}

// Hide Floating Preview Popover
function hideKpiPreview() {
  const popover = document.getElementById('kpi-preview-card');
  if (popover) {
    popover.classList.add('hidden');
  }
}

// Filter listings
function getFilteredListings() {
  return allListings.filter(item => {
    // VRAM range filter (de X a Y GB)
    const vram = item.detected_vram_gb;
    if (vram !== null && vram !== undefined) {
      if (activeFilters.minVram !== null && activeFilters.minVram !== undefined && vram < activeFilters.minVram) {
        return false;
      }
      if (activeFilters.maxVram !== null && activeFilters.maxVram !== undefined && vram > activeFilters.maxVram) {
        return false;
      }
    } else {
      // Se a VRAM não pôde ser identificada e o filtro exige > 0, exclui se minVram > 0
      if (activeFilters.minVram && activeFilters.minVram > 0) {
        return false;
      }
    }

    // Condition filter
    if (activeFilters.condition !== 'all' && item.condition !== activeFilters.condition) {
      return false;
    }

    // Platform filter
    if (activeFilters.platform !== 'all' && item.platform.toLowerCase() !== activeFilters.platform.toLowerCase()) {
      return false;
    }

    // Max price (sem teto pré-fixado)
    if (activeFilters.maxPrice && item.price > activeFilters.maxPrice) {
      return false;
    }

    // Outliers only
    if (activeFilters.outliersOnly && !item.is_outlier) {
      return false;
    }

    // Search query
    if (activeFilters.search) {
      const matchText = `${item.title} ${item.city} ${item.detected_model} ${item.platform} ${item.architecture || ''}`.toLowerCase();
      if (!matchText.includes(activeFilters.search)) {
        return false;
      }
    }
    return true;
  });
}

// Render chart, KPIs and cards instantaneously
function renderFiltered() {
  const filtered = getFilteredListings();

  // Contadores instantâneos
  const step2Count = document.getElementById('step-2-count');
  if (step2Count) step2Count.textContent = filtered.length;

  const listingsCount = document.getElementById('listings-count');
  if (listingsCount) listingsCount.textContent = filtered.length;

  // Recalcula KPIs em memória para a seleção filtrada
  recalculateKPIs(filtered);

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
    chartEl.innerHTML = '<div class="h-full flex items-center justify-center text-slate-500 text-sm">Nenhuma placa real encontrada com os filtros selecionados.</div>';
    return;
  }

  // Mapeia cada modelo para seu poder computacional (FP32 TFLOPS oficial)
  // Requisito Crítico: Quanto mais poderosa computacionalmente a GPU, mais à direita no eixo X!
  const modelMap = {};
  listings.forEach(item => {
    const m = item.detected_model || 'NVIDIA';
    const tf = (item.compute_tflops !== null && item.compute_tflops !== undefined) ? item.compute_tflops : 15.0;
    if (!modelMap[m] || tf > modelMap[m].tflops) {
      modelMap[m] = { model: m, tflops: tf };
    }
  });

  // Ordena rigorosamente do menor para o maior poder computacional
  // Assim as GPUs mais fortes (ex: 4090, 4080, 3090) ficam sempre mais à direita!
  const sortedModels = Object.values(modelMap).sort((a, b) => a.tflops - b.tflops);

  const modelToAxisLabel = {};
  const categoryArray = [];
  sortedModels.forEach(m => {
    const label = `${m.model}<br><span style="font-size:10px;color:#A5B4FC">${m.tflops} TF</span>`;
    modelToAxisLabel[m.model] = label;
    categoryArray.push(label);
  });

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
        size: 13,
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
        size: 13,
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
        size: 16,
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

    const xAxisLabel = modelToAxisLabel[item.detected_model] || item.detected_model;
    traces[traceIdx].x.push(xAxisLabel);
    traces[traceIdx].y.push(item.price);
    traces[traceIdx].text.push(item.title);
    traces[traceIdx].customdata.push(item);
  });

  const activeTraces = traces.filter(t => t.x.length > 0);

  const layout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    margin: { l: 60, r: 20, t: 20, b: 75 },
    xaxis: {
      title: {
        text: 'Capacidade Computacional FP32 (TFLOPS) — Mais Poderosa à Direita ➔',
        font: { size: 12, color: '#A5B4FC', family: 'Inter, sans-serif' }
      },
      color: '#94A3B8',
      gridcolor: '#1E293B',
      categoryorder: 'array',
      categoryarray: categoryArray, // Ordem estritamente ordenada por TFLOPS
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

    // Compute metrics
    const computeEl = document.getElementById('hover-compute');
    if (computeEl) {
      const tflops = item.compute_tflops !== null && item.compute_tflops !== undefined ? `${item.compute_tflops} TFLOPS` : '--';
      const arch = item.architecture ? ` (${item.architecture})` : '';
      computeEl.textContent = `${tflops}${arch}`;
    }

    const costTflopsEl = document.getElementById('hover-cost-tflops');
    if (costTflopsEl) {
      if (item.compute_tflops && item.compute_tflops > 0 && item.price > 0) {
        costTflopsEl.textContent = `${formatBRL(item.price / item.compute_tflops)} / TFLOPS`;
      } else {
        costTflopsEl.textContent = '-';
      }
    }

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
    if (item) {
      window.open(getEffectiveListingUrl(item), '_blank', 'noopener,noreferrer');
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

    const computeBadge = (item.compute_tflops !== null && item.compute_tflops !== undefined)
      ? `<span class="text-[11px] font-bold px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30" title="Capacidade Computacional: ${item.compute_tflops} TFLOPS FP32 (${item.architecture || 'NVIDIA'})">${item.compute_tflops} TF</span>`
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
              ${computeBadge}
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
        <a href="${getEffectiveListingUrl(item)}" target="_blank" rel="noopener noreferrer" class="flex-1 py-1.5 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition flex items-center justify-center gap-1 shadow-sm" title="Abrir anúncio original">
          <span>Abrir Anúncio ↗</span>
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

// Helpers
function escapeHtml(text) {
  if (!text) return '';
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

function resetScanButtons() {
  const updateDbBtn = document.getElementById('btn-update-db');
  const updateDbIcon = document.getElementById('update-db-icon');
  const indicator = document.getElementById('scan-status-indicator');

  if (updateDbBtn) updateDbBtn.disabled = false;
  if (updateDbIcon) updateDbIcon.classList.remove('animate-spin');
  if (indicator) {
    indicator.classList.add('hidden');
    indicator.classList.remove('flex');
  }
}

let pollInterval = null;

function startProgressPolling() {
  if (pollInterval) clearInterval(pollInterval);

  const progressPanel = document.getElementById('live-progress-panel');
  if (progressPanel) progressPanel.classList.remove('hidden');

  pollInterval = setInterval(async () => {
    try {
      const res = await fetch('/api/scan/progress');
      const prog = await res.json();

      updateProgressUI(prog);

      if (!prog.is_scanning && prog.current_step >= prog.total_steps) {
        clearInterval(pollInterval);
        pollInterval = null;
        resetScanButtons();

        // Atualiza cabeçalho para finalizado
        const titleText = document.getElementById('progress-title-text');
        if (titleText) titleText.textContent = 'Varredura Concluída';
        const ping = document.getElementById('scan-pulse-ping');
        if (ping) ping.classList.add('hidden');
        const pctText = document.getElementById('progress-percent-text');
        if (pctText) pctText.textContent = '100%';
        const barFill = document.getElementById('progress-bar-fill');
        if (barFill) barFill.style.width = '100%';

        await loadData();
      }
    } catch (e) {
      console.warn('Erro ao consultar progresso da varredura:', e);
    }
  }, 800);
}

function updateProgressUI(prog) {
  if (!prog) return;

  const stepPill = document.getElementById('progress-step-pill');
  const taskText = document.getElementById('progress-current-task');
  const foundCount = document.getElementById('progress-found-count');
  const percentText = document.getElementById('progress-percent-text');
  const barFill = document.getElementById('progress-bar-fill');
  const logBox = document.getElementById('progress-log-box');

  const total = prog.total_steps || 7;
  const current = prog.current_step || 1;
  const pct = Math.min(100, Math.round((current / total) * 100));

  if (stepPill) stepPill.textContent = `Etapa ${current} de ${total}`;
  if (taskText) taskText.textContent = prog.current_task || 'Executando tarefas...';
  if (foundCount) foundCount.textContent = prog.found_count || 0;
  if (percentText) percentText.textContent = `${pct}%`;
  if (barFill) barFill.style.width = `${pct}%`;

  if (logBox && prog.logs && prog.logs.length > 0) {
    logBox.innerHTML = prog.logs.map(log => {
      const isSuccess = log.includes('✅') || log.includes('🏁');
      const isWarn = log.includes('⚠️') || log.includes('❌');
      const color = isSuccess ? 'text-emerald-400 font-medium' : (isWarn ? 'text-amber-400' : 'text-slate-300');
      return `<div class="${color} py-0.5 leading-relaxed">${escapeHtml(log)}</div>`;
    }).join('');
    logBox.scrollTop = logBox.scrollHeight;
  }
}

// Trigger live scraping with custom parameters from Passo 1
async function triggerScan() {
  const cityInput = document.getElementById('input-center-city');
  const radiusInput = document.getElementById('input-radius-km');
  const centerCity = (cityInput ? cityInput.value : '').trim() || 'Veranópolis';
  const radiusKm = radiusInput ? parseFloat(radiusInput.value) : 50;

  const updateDbBtn = document.getElementById('btn-update-db');
  const updateDbIcon = document.getElementById('update-db-icon');
  const indicator = document.getElementById('scan-status-indicator');
  const progressPanel = document.getElementById('live-progress-panel');

  if (updateDbBtn) updateDbBtn.disabled = true;
  if (updateDbIcon) updateDbIcon.classList.add('animate-spin');
  if (indicator) {
    indicator.classList.remove('hidden');
    indicator.classList.add('flex');
  }

  // Revela o painel de tarefas ao vivo
  if (progressPanel) {
    progressPanel.classList.remove('hidden');
    const titleText = document.getElementById('progress-title-text');
    if (titleText) titleText.textContent = 'Varredura em Andamento';
    const ping = document.getElementById('scan-pulse-ping');
    if (ping) ping.classList.remove('hidden');
  }

  try {
    const res = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        live: true,
        center_city: centerCity,
        radius_km: radiusKm
      })
    });
    const data = await res.json();
    console.log('Varredura disparada:', data);

    startProgressPolling();
  } catch (err) {
    console.error('Erro na varredura:', err);
    resetScanButtons();
  }
}

// Check scan status on page load
async function checkScanStatus() {
  try {
    const statusRes = await fetch('/api/scan/status');
    const status = await statusRes.json();
    if (status.is_scanning) {
      const updateDbBtn = document.getElementById('btn-update-db');
      const updateDbIcon = document.getElementById('update-db-icon');
      const indicator = document.getElementById('scan-status-indicator');

      if (updateDbBtn) updateDbBtn.disabled = true;
      if (updateDbIcon) updateDbIcon.classList.add('animate-spin');
      if (indicator) {
        indicator.classList.remove('hidden');
        indicator.classList.add('flex');
      }

      startProgressPolling();
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
