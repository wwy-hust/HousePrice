let assetData = null;
let activeAssetCategory = '全部';
let assetCharts = [];
let assetUpdatePollTimer = null;

const ASSET_COLORS = {
    SULFUR: '#f59e0b',
    VD3: '#8b5cf6',
    TD3C: '#ef4444',
    TD3C_WS: '#f97316',
    TD15: '#3b82f6',
    TD15_WS: '#06b6d4',
    MONKEY: '#10b981',
};

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
}

function getPriceChange(asset) {
    if (!asset.series || asset.series.length < 2) return null;
    const latest = asset.series[asset.series.length - 1].price;
    const previous = asset.series[asset.series.length - 2].price;
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
    chartContainer.appendChild(canvas);

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

    card.append(header, chartContainer, source);
    return { card, canvas };
}

function createAssetChart(canvas, asset) {
    const color = ASSET_COLORS[asset.code] || '#667eea';
    const mainData = asset.series.map(point => ({ x: point.date, y: point.price }));
    const hasRange = asset.series.some(
        point => point.price_low != null && point.price_high != null
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
                data: asset.series
                    .filter(point => point.price_high != null)
                    .map(point => ({ x: point.date, y: point.price_high })),
                borderColor: `${color}99`,
                borderDash: [4, 3],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
            },
            {
                label: '区间下限',
                data: asset.series
                    .filter(point => point.price_low != null)
                    .map(point => ({ x: point.date, y: point.price_low })),
                borderColor: `${color}99`,
                borderDash: [4, 3],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
            }
        );
    }

    return new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: hasRange,
                    labels: { usePointStyle: true, boxWidth: 8, font: { size: 10 } },
                },
                tooltip: {
                    callbacks: {
                        label: context =>
                            `${context.dataset.label}: ${formatNumber(context.raw.y)} ${asset.unit}`,
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
    assetCharts = [];

    const grid = document.getElementById('assetGrid');
    const assets = (assetData.assets || []).filter(
        asset => activeAssetCategory === '全部' || asset.category === activeAssetCategory
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
        const { card, canvas } = createAssetCard(asset, index);
        grid.appendChild(card);
        if (asset.series.length) {
            assetCharts.push(createAssetChart(canvas, asset));
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
