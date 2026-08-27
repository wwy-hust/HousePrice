let assetData = null;
let activeAssetCategory = '全部';
let showReportedReferencePoints = false;
let assetCharts = [];
let assetBrushes = [];
let assetUpdatePollTimer = null;

const ASSET_COLORS = {
    SULFUR: '#f59e0b',
    PYRITE: '#ca8a04',
    ALUMINA: '#64748b',
    ALUMINUM: '#0ea5e9',
    GOLD: '#d4a017',
    SILVER: '#94a3b8',
    COPPER: '#c2410c',
    TIN: '#78716c',
    NICKEL: '#14b8a6',
    COAL: '#334155',
    COKING_COAL: '#78350f',
    CRUDE_OIL: '#18181b',
    BRENT_CRUDE: '#2563eb',
    ARGON: '#38bdf8',
    CORN: '#eab308',
    SOYBEAN: '#65a30d',
    WHEAT: '#d97706',
    SUGAR: '#ec4899',
    COTTON: '#64748b',
    LIVE_HOG: '#f97316',
    COFFEE: '#78350f',
    COCOA: '#92400e',
    PALM_OIL: '#16a34a',
    NATURAL_RUBBER: '#0f766e',
    PHOSPHATE_ROCK: '#84cc16',
    DISPERSE_BLACK: '#4f46e5',
    DISPERSE_BLUE_60: '#06b6d4',
    DYE_REDUCTION: '#db2777',
    H_ACID: '#dc2626',
    SB_CN: '#b45309',
    SB_INTL: '#0f766e',
    W_CN: '#475569',
    W_INTL: '#2563eb',
    IN_CN: '#6366f1',
    RE_CN: '#be123c',
    GE_CN: '#9333ea',
    VIT_A: '#e11d48',
    VD3: '#8b5cf6',
    VIT_E: '#059669',
    VIT_C: '#f97316',
    VIT_B1: '#2563eb',
    VIT_B2: '#0891b2',
    VIT_B6: '#7c3aed',
    VIT_B12: '#c026d3',
    VIT_K3: '#65a30d',
    ALLULOSE: '#0d9488',
    SUCRALOSE: '#e11d48',
    ERYTHRITOL: '#0284c7',
    ACESULFAME_K: '#d97706',
    ASPARTAME: '#7c3aed',
    CYCLAMATE: '#0891b2',
    SACCHARIN_SODIUM: '#475569',
    STEVIA_GLYCOSIDE: '#16a34a',
    XYLITOL: '#c2410c',
    BLOOD_ALBUMIN: '#dc2626',
    BLOOD_IVIG: '#9333ea',
    TD3C: '#ef4444',
    TD3C_WS: '#f97316',
    TD15: '#3b82f6',
    TD15_WS: '#06b6d4',
    PDCI: '#8b5cf6',
    MONKEY: '#10b981',
};

const ASSET_PRIORITY = {
    GOLD: 0,
    SILVER: 1,
    COPPER: 2,
    ALUMINUM: 3,
};

function indexAtOrAfter(dates, target) {
    for (let index = 0; index < dates.length; index += 1) {
        if (dates[index] >= target) return index;
    }
    return dates.length - 1;
}

function dateTimestamp(value) {
    return new Date(`${value}T00:00:00`).getTime();
}

function createAssetBrush(container, dates, values, color, onChange) {
    if (dates.length < 2) {
        container.hidden = true;
        return null;
    }

    const current = document.createElement('div');
    current.className = 'asset-brush-current';
    const leftLabel = document.createElement('b');
    const rightLabel = document.createElement('b');
    current.append(leftLabel, rightLabel);

    const track = document.createElement('div');
    track.className = 'asset-brush-track';
    const spark = document.createElement('canvas');
    spark.className = 'asset-brush-spark';
    const windowElement = document.createElement('div');
    windowElement.className = 'asset-brush-window';
    const leftHandle = document.createElement('div');
    leftHandle.className = 'asset-brush-handle left';
    const rightHandle = document.createElement('div');
    rightHandle.className = 'asset-brush-handle right';
    windowElement.append(leftHandle, rightHandle);
    track.append(spark, windowElement);

    const ticks = document.createElement('div');
    ticks.className = 'asset-brush-ticks';
    container.append(current, track, ticks);

    const pointCount = dates.length;
    let startIndex = 0;
    let endIndex = pointCount - 1;

    const place = (element, fraction) => {
        element.style.left = `${fraction * 100}%`;
        element.style.transform = fraction < 0.035
            ? 'translateX(0)'
            : fraction > 0.965
                ? 'translateX(-100%)'
                : 'translateX(-50%)';
    };

    const firstYear = Number(dates[0].slice(0, 4));
    const lastYear = Number(dates[pointCount - 1].slice(0, 4));
    const yearStep = lastYear - firstYear > 12 ? 2 : 1;
    for (let year = firstYear; year <= lastYear; year += yearStep) {
        const index = indexAtOrAfter(dates, `${year}-01-01`);
        const tick = document.createElement('span');
        tick.className = 'asset-brush-tick';
        tick.textContent = year;
        ticks.appendChild(tick);
        place(tick, index / (pointCount - 1));
    }

    function drawSparkline() {
        const width = track.clientWidth;
        const height = track.clientHeight;
        if (!width) return;
        const ratio = window.devicePixelRatio || 1;
        spark.width = Math.round(width * ratio);
        spark.height = Math.round(height * ratio);
        const context = spark.getContext('2d');
        context.scale(ratio, ratio);
        context.clearRect(0, 0, width, height);
        const validValues = values.filter(value => Number.isFinite(value));
        if (!validValues.length) return;
        const minimum = Math.min(...validValues);
        const maximum = Math.max(...validValues);
        const range = maximum - minimum || 1;
        context.beginPath();
        let started = false;
        values.forEach((value, index) => {
            if (!Number.isFinite(value)) return;
            const x = (index / (pointCount - 1)) * width;
            const y = height - ((value - minimum) / range) * (height * 0.7)
                - height * 0.15;
            if (started) context.lineTo(x, y);
            else {
                context.moveTo(x, y);
                started = true;
            }
        });
        context.strokeStyle = `${color}88`;
        context.lineWidth = 1.4;
        context.stroke();
        context.lineTo(width, height);
        context.lineTo(0, height);
        context.closePath();
        context.fillStyle = `${color}12`;
        context.fill();
    }

    function applyRange(fireChange = true) {
        const width = track.clientWidth || 1;
        const startFraction = startIndex / (pointCount - 1);
        const endFraction = endIndex / (pointCount - 1);
        windowElement.style.left = `${startFraction * width}px`;
        windowElement.style.width = `${Math.max(
            (endFraction - startFraction) * width,
            12
        )}px`;
        leftLabel.textContent = dates[startIndex];
        rightLabel.textContent = dates[endIndex];
        place(leftLabel, startFraction);
        place(rightLabel, endFraction);
        if (fireChange) onChange(dates[startIndex], dates[endIndex]);
    }

    let dragMode = null;
    let dragStartX = 0;
    let initialStart = 0;
    let initialEnd = 0;
    const pointerX = event => {
        const bounds = track.getBoundingClientRect();
        const clientX = event.touches ? event.touches[0].clientX : event.clientX;
        return clientX - bounds.left;
    };
    const stopDrag = () => {
        dragMode = null;
        document.removeEventListener('mousemove', moveDrag);
        document.removeEventListener('mouseup', stopDrag);
        document.removeEventListener('touchmove', moveDrag);
        document.removeEventListener('touchend', stopDrag);
    };
    const moveDrag = event => {
        if (!dragMode) return;
        event.preventDefault();
        const width = track.clientWidth || 1;
        const offset = Math.round(
            ((pointerX(event) - dragStartX) / width) * (pointCount - 1)
        );
        if (dragMode === 'window') {
            const span = initialEnd - initialStart;
            let nextStart = initialStart + offset;
            let nextEnd = initialEnd + offset;
            if (nextStart < 0) {
                nextStart = 0;
                nextEnd = span;
            }
            if (nextEnd > pointCount - 1) {
                nextEnd = pointCount - 1;
                nextStart = pointCount - 1 - span;
            }
            startIndex = nextStart;
            endIndex = nextEnd;
        } else if (dragMode === 'left') {
            startIndex = Math.min(
                Math.max(0, initialStart + offset),
                endIndex - 1
            );
        } else {
            endIndex = Math.max(
                Math.min(pointCount - 1, initialEnd + offset),
                startIndex + 1
            );
        }
        applyRange();
    };
    const startDrag = (event, mode) => {
        dragMode = mode;
        dragStartX = pointerX(event);
        initialStart = startIndex;
        initialEnd = endIndex;
        event.preventDefault();
        event.stopPropagation();
        document.addEventListener('mousemove', moveDrag);
        document.addEventListener('mouseup', stopDrag);
        document.addEventListener('touchmove', moveDrag, { passive: false });
        document.addEventListener('touchend', stopDrag);
    };

    windowElement.addEventListener(
        'mousedown',
        event => startDrag(event, 'window')
    );
    windowElement.addEventListener(
        'touchstart',
        event => startDrag(event, 'window'),
        { passive: false }
    );
    leftHandle.addEventListener(
        'mousedown',
        event => startDrag(event, 'left')
    );
    leftHandle.addEventListener(
        'touchstart',
        event => startDrag(event, 'left'),
        { passive: false }
    );
    rightHandle.addEventListener(
        'mousedown',
        event => startDrag(event, 'right')
    );
    rightHandle.addEventListener(
        'touchstart',
        event => startDrag(event, 'right'),
        { passive: false }
    );

    const brush = {
        redraw() {
            drawSparkline();
            applyRange(false);
        },
        destroy: stopDrag,
    };
    requestAnimationFrame(() => {
        drawSparkline();
        applyRange();
    });
    return brush;
}

function formatNumber(value, maximumFractionDigits = 2) {
    if (value == null || Number.isNaN(Number(value))) return '-';
    return new Intl.NumberFormat('zh-CN', {
        maximumFractionDigits,
    }).format(value);
}

function formatDate(value) {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    }).format(date);
}

function createSummaryCard(label, value, detail) {
    const card = document.createElement('div');
    card.className = 'scd';

    const labelElement = document.createElement('div');
    labelElement.className = 'l';
    labelElement.textContent = label;

    const valueElement = document.createElement('div');
    valueElement.className = 'v';
    valueElement.style.fontSize = '20px';
    valueElement.style.color = '#667eea';
    valueElement.textContent = value;

    const detailElement = document.createElement('div');
    detailElement.className = 'd';
    detailElement.textContent = detail;

    card.append(labelElement, valueElement, detailElement);
    return card;
}

function renderSummary() {
    const summary = document.getElementById('assetSummary');
    const assets = assetData.assets || [];
    const pointCount = assets.reduce((total, asset) => total + asset.series.length, 0);
    const latestDates = assets
        .map(asset => asset.latest && asset.latest.date)
        .filter(Boolean)
        .sort();

    summary.replaceChildren(
        createSummaryCard('关注资产', `${assets.length} 项`, '跨多个产业领域'),
        createSummaryCard(
            '资产分类',
            `${(assetData.categories || []).length} 类`,
            (assetData.categories || []).map(category => category.name).join(' · ')
        ),
        createSummaryCard(
            '最新数据日期',
            formatDate(latestDates[latestDates.length - 1]),
            '各资产更新频率不同'
        ),
        createSummaryCard(
            '历史数据点',
            formatNumber(pointCount, 0),
            `导出于 ${formatDate(assetData.generated_at)}`
        )
    );

    document.getElementById('assetUpdatedAt').textContent =
        `数据生成时间：${formatDate(assetData.generated_at)}`;
}

function renderFilters() {
    const filters = document.getElementById('assetFilters');
    const categories = ['全部', ...(assetData.categories || []).map(item => item.name)];
    filters.replaceChildren();

    categories.forEach(category => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `asset-filter${category === activeAssetCategory ? ' active' : ''}`;
        button.textContent = category;
        button.addEventListener('click', () => {
            activeAssetCategory = category;
            renderFilters();
            renderAssets();
        });
        filters.appendChild(button);
    });

    const referenceToggle = document.createElement('label');
    referenceToggle.className = 'asset-reference-toggle';
    const referenceCheckbox = document.createElement('input');
    referenceCheckbox.type = 'checkbox';
    referenceCheckbox.checked = showReportedReferencePoints;
    referenceCheckbox.addEventListener('change', () => {
        showReportedReferencePoints = referenceCheckbox.checked;
        renderAssets();
    });
    const referenceTrack = document.createElement('span');
    referenceTrack.className = 'asset-reference-toggle-track';
    const referenceLabel = document.createElement('span');
    referenceLabel.textContent = '显示旧报道参考点';
    referenceToggle.append(referenceCheckbox, referenceTrack, referenceLabel);
    filters.appendChild(referenceToggle);
}

function getPriceChange(asset) {
    const comparableSeries = (asset.series || []).filter(
        point => point.point_type !== 'reported_reference'
    );
    if (comparableSeries.length < 2) return null;
    const latest = comparableSeries[comparableSeries.length - 1].price;
    const previous = comparableSeries[comparableSeries.length - 2].price;
    if (!previous) return null;
    return (latest - previous) / previous;
}

function createAssetCard(asset, index) {
    const card = document.createElement('article');
    card.className = 'asset-card';

    const header = document.createElement('div');
    header.className = 'asset-card-header';

    const title = document.createElement('div');
    title.className = 'asset-card-title';
    const heading = document.createElement('h3');
    heading.textContent = asset.name;
    const meta = document.createElement('p');
    meta.textContent = `${asset.code} · ${asset.category}`;
    title.append(heading, meta);

    const latest = document.createElement('div');
    latest.className = 'asset-latest';
    const latestValue = document.createElement('strong');
    latestValue.textContent = asset.latest
        ? `${formatNumber(asset.latest.price)} ${asset.unit}`
        : '-';

    const change = getPriceChange(asset);
    if (change != null) {
        latestValue.classList.add(change >= 0 ? 'up' : 'down');
    }

    const latestDetail = document.createElement('small');
    latestDetail.textContent = asset.latest
        ? `${formatDate(asset.latest.date)}${change == null ? '' : ` · ${change >= 0 ? '+' : ''}${(change * 100).toFixed(1)}%`}`
        : '暂无数据';
    latest.append(latestValue, latestDetail);
    header.append(title, latest);

    const chartContainer = document.createElement('div');
    chartContainer.className = 'asset-chart';
    const canvas = document.createElement('canvas');
    canvas.id = `assetChart-${index}`;
    if (asset.series && asset.series.length) {
        chartContainer.appendChild(canvas);
    } else {
        const emptyChart = document.createElement('div');
        emptyChart.className = 'asset-chart-empty';
        emptyChart.textContent = '报道参考点已隐藏，打开上方开关后可查看';
        chartContainer.appendChild(emptyChart);
    }

    const brushContainer = document.createElement('div');
    brushContainer.className = 'asset-brush';

    const referencePoints = (asset.series || []).filter(
        point => point.point_type === 'reported_reference'
    );
    const hiddenReferenceCount = asset.hiddenReferenceCount || 0;
    const referenceNote = document.createElement('div');
    referenceNote.className = 'asset-reference-note';
    const visibleReferenceText = referencePoints.length
        ? `含 ${referencePoints.length} 个报道参考点：仅来自新闻、研报或企业报价，`
            + '不是严谨的连续行情；三角形标记与主序列不可直接等同。'
        : '';
    const hiddenReferenceText = hiddenReferenceCount
        ? `另有 ${hiddenReferenceCount} 个旧报道参考点已隐藏，可使用上方开关显示。`
        : '';
    referenceNote.textContent = [visibleReferenceText, hiddenReferenceText]
        .filter(Boolean)
        .join(' ');

    const source = document.createElement('div');
    source.className = 'asset-source';
    const sourceName = document.createElement('span');
    sourceName.textContent = `数据来源：${asset.source}`;
    source.appendChild(sourceName);
    if (asset.latest && asset.latest.source_url) {
        const sourceLink = document.createElement('a');
        sourceLink.href = asset.latest.source_url;
        sourceLink.target = '_blank';
        sourceLink.rel = 'noopener noreferrer';
        sourceLink.textContent = '查看原文';
        source.appendChild(sourceLink);
    }

    card.append(header, chartContainer, brushContainer);
    if (referencePoints.length || hiddenReferenceCount) {
        card.appendChild(referenceNote);
    }
    card.appendChild(source);
    return { card, canvas, brushContainer };
}

function createAssetChart(canvas, asset) {
    const color = ASSET_COLORS[asset.code] || '#667eea';
    const toChartPoint = point => ({
        x: dateTimestamp(point.date),
        y: point.price,
        point,
    });
    const mainPoints = asset.series.filter(
        point => point.point_type !== 'reported_reference'
    );
    const referencePoints = asset.series.filter(
        point => point.point_type === 'reported_reference'
    );
    const mainData = mainPoints.map(toChartPoint);
    const referenceData = referencePoints.map(toChartPoint);
    const hasRange = asset.series.some(
        point =>
            point.point_type !== 'reported_reference'
            && point.price_low != null
            && point.price_high != null
    );
    const datasets = [{
        label: `${asset.name}（${asset.unit}）`,
        data: mainData,
        borderColor: color,
        backgroundColor: `${color}14`,
        borderWidth: 2,
        pointRadius: mainData.length > 80 ? 0 : 2,
        pointHoverRadius: 5,
        tension: 0.18,
        fill: true,
    }];

    if (hasRange) {
        datasets.push(
            {
                label: '区间上限',
                data: mainPoints
                    .filter(point => point.price_high != null)
                    .map(point => ({ ...toChartPoint(point), y: point.price_high })),
                borderColor: `${color}99`,
                borderDash: [4, 3],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
            },
            {
                label: '区间下限',
                data: mainPoints
                    .filter(point => point.price_low != null)
                    .map(point => ({ ...toChartPoint(point), y: point.price_low })),
                borderColor: `${color}99`,
                borderDash: [4, 3],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
            }
        );
    }
    if (referenceData.length) {
        datasets.push({
            label: '报道参考点（非连续）',
            data: referenceData,
            borderColor: '#b7791f',
            backgroundColor: '#fff7ed',
            borderWidth: 2,
            pointStyle: 'triangle',
            pointRadius: 5,
            pointHoverRadius: 7,
            showLine: false,
            fill: false,
        });
    }

    return new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { datasets },
        options: {
            animation: false,
            parsing: false,
            normalized: true,
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                decimation: {
                    enabled: mainData.length > 600,
                    algorithm: 'lttb',
                    samples: 600,
                },
                legend: {
                    display: hasRange || referenceData.length > 0,
                    labels: { usePointStyle: true, boxWidth: 8, font: { size: 10 } },
                },
                tooltip: {
                    callbacks: {
                        title: contexts => {
                            const point = contexts[0] && contexts[0].raw.point;
                            return point
                                ? point.date_label || formatDate(point.date)
                                : '';
                        },
                        label: context =>
                            `${context.dataset.label}: ${formatNumber(context.raw.y)} ${asset.unit}`,
                        afterLabel: context => {
                            const point = context.raw.point;
                            if (!point || point.point_type !== 'reported_reference') {
                                return '';
                            }
                            return [
                                `说明：${point.quality_note || '报道参考，非连续行情。'}`,
                                point.comparability_note
                                    ? `口径：${point.comparability_note}`
                                    : '',
                            ].filter(Boolean);
                        },
                    },
                },
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'month', displayFormats: { month: 'yyyy-MM' } },
                    grid: { display: false },
                },
                y: {
                    ticks: {
                        callback: value => formatNumber(value),
                    },
                    grid: { color: '#f0f2f5' },
                },
            },
        },
    });
}

function renderAssets() {
    assetCharts.forEach(chart => chart.destroy());
    assetBrushes.forEach(brush => brush.destroy());
    assetCharts = [];
    assetBrushes = [];

    const grid = document.getElementById('assetGrid');
    const assets = (assetData.assets || [])
        .filter(
            asset => activeAssetCategory === '全部'
                || asset.category === activeAssetCategory
        )
        .sort(
            (left, right) =>
                (ASSET_PRIORITY[left.code] ?? Number.MAX_SAFE_INTEGER)
                - (ASSET_PRIORITY[right.code] ?? Number.MAX_SAFE_INTEGER)
        );
    grid.replaceChildren();

    if (!assets.length) {
        const empty = document.createElement('div');
        empty.className = 'asset-empty';
        empty.textContent = '该分类暂无资产价格数据';
        grid.appendChild(empty);
        return;
    }

    assets.forEach((asset, index) => {
        const hiddenReferencePoints = asset.series.filter(
            point => point.default_hidden === true
        );
        const visibleSeries = showReportedReferencePoints
            ? asset.series
            : asset.series.filter(
                point => point.default_hidden !== true
            );
        const visibleAsset = {
            ...asset,
            series: visibleSeries,
            latest: visibleSeries[visibleSeries.length - 1] || null,
            hiddenReferenceCount: showReportedReferencePoints
                ? 0
                : hiddenReferencePoints.length,
        };
        const { card, canvas, brushContainer } = createAssetCard(
            visibleAsset,
            index
        );
        grid.appendChild(card);
        if (visibleAsset.series.length) {
            const chart = createAssetChart(canvas, visibleAsset);
            assetCharts.push(chart);
            const dates = visibleAsset.series.map(point => point.date);
            const values = visibleAsset.series.map(point => Number(point.price));
            const brush = createAssetBrush(
                brushContainer,
                dates,
                values,
                ASSET_COLORS[visibleAsset.code] || '#667eea',
                (startDate, endDate) => {
                    chart.options.scales.x.min = dateTimestamp(startDate);
                    chart.options.scales.x.max = dateTimestamp(endDate);
                    chart.update('none');
                }
            );
            if (brush) assetBrushes.push(brush);
        } else {
            brushContainer.hidden = true;
        }
    });
}

async function loadAssetData() {
    const response = await fetch(`/api/data/asset_price_data.json?t=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    assetData = await response.json();

    const validCategories = new Set(
        (assetData.categories || []).map(category => category.name)
    );
    if (activeAssetCategory !== '全部' && !validCategories.has(activeAssetCategory)) {
        activeAssetCategory = '全部';
    }

    renderSummary();
    renderFilters();
    renderAssets();
}

function appendAssetUpdateLog(text, type) {
    if (!text) return;
    const log = document.getElementById('assetUpdateLog');
    const line = document.createElement('div');
    if (type) line.className = `log-${type}`;
    line.textContent = text;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
}

function finishAssetUpdate(success, message) {
    const progress = document.getElementById('assetUpdateProgress');
    progress.className = 'update-progress-bar';
    progress.style.width = '100%';
    progress.style.background = success
        ? 'linear-gradient(90deg, #38a169, #48bb78)'
        : 'linear-gradient(90deg, #e53e3e, #fc8181)';
    document.getElementById('assetUpdateTitle').textContent =
        success ? '拉取完成' : '拉取未完全成功';
    document.getElementById('assetUpdateFooter').style.display = 'block';

    const button = document.getElementById('updateAssetBtn');
    button.disabled = false;
    button.classList.remove('spinning');
    appendAssetUpdateLog(message, success ? 'success' : 'error');

    loadAssetData().catch(() => {});
}

function startAssetUpdatePolling() {
    let offset = 0;
    assetUpdatePollTimer = setInterval(async () => {
        try {
            const response = await fetch(`/api/asset/update/status?offset=${offset}`);
            const status = await response.json();
            (status.new_logs || []).forEach(line => appendAssetUpdateLog(line));
            offset = status.total_logs;

            if (!status.running && status.success !== null) {
                clearInterval(assetUpdatePollTimer);
                assetUpdatePollTimer = null;
                finishAssetUpdate(
                    status.success,
                    status.success
                        ? '资产价格已更新，页面数据已刷新。'
                        : `部分或全部数据拉取失败：${status.error || '未知错误'}`
                );
            }
        } catch (_) {
            // 临时网络错误时继续下一轮轮询。
        }
    }, 800);
}

async function triggerAssetUpdate() {
    const button = document.getElementById('updateAssetBtn');
    const progress = document.getElementById('assetUpdateProgress');
    document.getElementById('assetUpdateLog').replaceChildren();
    document.getElementById('assetUpdateTitle').textContent = '正在拉取资产价格';
    document.getElementById('assetUpdateFooter').style.display = 'none';
    document.getElementById('assetUpdateModal').classList.add('visible');
    progress.className = 'update-progress-bar indeterminate';
    progress.style.width = '';
    progress.style.background = '';
    button.disabled = true;
    button.classList.add('spinning');

    try {
        const response = await fetch('/api/asset/update');
        const result = await response.json();
        appendAssetUpdateLog(result.message);
        if (result.ok) {
            startAssetUpdatePolling();
        } else {
            finishAssetUpdate(false, result.message);
        }
    } catch (error) {
        finishAssetUpdate(false, `请求失败：${error.message}`);
    }
}

function closeAssetUpdateModal() {
    document.getElementById('assetUpdateModal').classList.remove('visible');
    if (assetUpdatePollTimer) {
        clearInterval(assetUpdatePollTimer);
        assetUpdatePollTimer = null;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('updateAssetBtn').addEventListener('click', triggerAssetUpdate);
    document.getElementById('closeAssetUpdateBtn').addEventListener('click', closeAssetUpdateModal);
    loadAssetData().catch(error => {
        document.getElementById('assetGrid').innerHTML =
            `<div class="asset-empty">资产价格数据加载失败：${error.message}</div>`;
    });
});

window.addEventListener('resize', () => {
    assetBrushes.forEach(brush => brush.redraw());
});
