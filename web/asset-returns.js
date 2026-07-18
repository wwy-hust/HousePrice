let assetReturnData = null;
let newestYearFirst = true;
let selectedAssetKey = null;
let transientAssetKey = null;
let hiddenAssetKeys = new Set();
let assetReturnsUpdatePollTimer = null;
let assetReturnControlsBound = false;

const ASSET_VISIBILITY_STORAGE_KEY = 'asset-return-hidden-assets';

function createReturnSummaryCard(label, value, detail) {
    const card = document.createElement('div');
    card.className = 'scd';

    const labelElement = document.createElement('div');
    labelElement.className = 'l';
    labelElement.textContent = label;

    const valueElement = document.createElement('div');
    valueElement.className = 'v';
    valueElement.textContent = value;

    const detailElement = document.createElement('div');
    detailElement.className = 'd';
    detailElement.textContent = detail;

    card.append(labelElement, valueElement, detailElement);
    return card;
}

function formatReturn(value) {
    const sign = value > 0 ? '+' : '';
    const maximumFractionDigits = Math.abs(value) >= 100 ? 1 : 2;
    return `${sign}${new Intl.NumberFormat('zh-CN', {
        minimumFractionDigits: 0,
        maximumFractionDigits,
    }).format(value)}%`;
}

function getYearLabel(year) {
    return Number(assetReturnData.partial_year) === Number(year)
        ? `${year} YTD`
        : String(year);
}

function hexToRgba(hex, alpha) {
    const normalized = hex.replace('#', '');
    const value = Number.parseInt(normalized, 16);
    const red = (value >> 16) & 255;
    const green = (value >> 8) & 255;
    const blue = value & 255;
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function getAssetsByKey() {
    return new Map(assetReturnData.assets.map(asset => [asset.key, asset]));
}

function getVisibleAssets() {
    return assetReturnData.assets.filter(asset => !hiddenAssetKeys.has(asset.key));
}

function getRankedReturns(year) {
    const assetsByKey = getAssetsByKey();
    return Object.entries(assetReturnData.returns[String(year)] || {})
        .map(([key, value]) => ({ asset: assetsByKey.get(key), value }))
        .filter(item => (
            item.asset
            && !hiddenAssetKeys.has(item.asset.key)
            && Number.isFinite(item.value)
        ))
        .sort((left, right) => right.value - left.value);
}

function renderReturnSummary() {
    const summary = document.getElementById('assetReturnSummary');
    const years = Object.keys(assetReturnData.returns).map(Number);
    const latestYear = Math.max(...years);
    const latestReturns = getRankedReturns(latestYear);
    const winner = latestReturns[0];
    const positiveCount = latestReturns.filter(item => item.value > 0).length;
    const groups = new Set(assetReturnData.assets.map(asset => asset.group));
    const visibleCount = getVisibleAssets().length;

    summary.replaceChildren(
        createReturnSummaryCard(
            '显示资产',
            `${visibleCount} / ${assetReturnData.assets.length} 类`,
            `${groups.size} 个资产组，可自定义隐藏`
        ),
        createReturnSummaryCard(
            '时间范围',
            `${assetReturnData.start_year}–${assetReturnData.end_year}`,
            `共 ${years.length} 个自然年`
        ),
        createReturnSummaryCard(
            `${getYearLabel(latestYear)} 冠军`,
            winner ? winner.asset.short_name : '—',
            winner ? formatReturn(winner.value) : '当前未显示资产'
        ),
        createReturnSummaryCard(
            `${getYearLabel(latestYear)} 上涨`,
            `${positiveCount} / ${latestReturns.length}`,
            '按价格收益率统计'
        )
    );
}

function setActiveAsset(key) {
    const activeKey = key || selectedAssetKey;
    const targets = document.querySelectorAll('[data-asset-key]');
    targets.forEach(element => {
        const matches = activeKey && element.dataset.assetKey === activeKey;
        element.classList.toggle('is-highlighted', Boolean(matches));
        element.classList.toggle('is-muted', Boolean(activeKey && !matches));
        if (element.classList.contains('asset-return-legend-item')) {
            element.setAttribute('aria-pressed', String(selectedAssetKey === element.dataset.assetKey));
        }
    });

    const table = document.getElementById('assetReturnTable');
    if (table) table.classList.toggle('has-active-asset', Boolean(activeKey));
}

function bindAssetInteraction(element, assetKey) {
    element.dataset.assetKey = assetKey;
    element.addEventListener('pointerenter', event => {
        if (event.pointerType === 'touch') return;
        transientAssetKey = assetKey;
        setActiveAsset(transientAssetKey);
    });
    element.addEventListener('pointerleave', () => {
        transientAssetKey = null;
        setActiveAsset(null);
    });
    element.addEventListener('focus', () => {
        transientAssetKey = assetKey;
        setActiveAsset(transientAssetKey);
    });
    element.addEventListener('blur', () => {
        transientAssetKey = null;
        setActiveAsset(null);
    });
    element.addEventListener('click', () => {
        selectedAssetKey = selectedAssetKey === assetKey ? null : assetKey;
        transientAssetKey = null;
        setActiveAsset(null);
    });
}

function renderLegend() {
    const legend = document.getElementById('assetReturnLegend');
    legend.replaceChildren();

    getVisibleAssets().forEach(asset => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'asset-return-legend-item';
        button.style.setProperty('--asset-color', asset.color);
        button.style.setProperty('--asset-soft-color', hexToRgba(asset.color, 0.18));
        button.setAttribute('aria-pressed', 'false');

        const swatch = document.createElement('span');
        swatch.className = 'asset-return-legend-swatch';
        const label = document.createElement('span');
        label.textContent = asset.short_name;
        button.append(swatch, label);

        bindAssetInteraction(button, asset.key);
        legend.appendChild(button);
    });
}

function saveHiddenAssets() {
    try {
        localStorage.setItem(
            ASSET_VISIBILITY_STORAGE_KEY,
            JSON.stringify([...hiddenAssetKeys])
        );
    } catch (error) {
        console.warn('无法保存资产显示设置:', error);
    }
}

function updateVisibilityButton() {
    const button = document.getElementById('assetVisibilityToggle');
    button.textContent =
        `显示资产 ${getVisibleAssets().length}/${assetReturnData.assets.length}`;
}

function refreshAssetViews() {
    if (selectedAssetKey && hiddenAssetKeys.has(selectedAssetKey)) {
        selectedAssetKey = null;
    }
    transientAssetKey = null;
    renderReturnSummary();
    renderLegend();
    renderReturnTable();
    renderVisibilityOptions();
    updateVisibilityButton();
}

function renderVisibilityOptions() {
    const options = document.getElementById('assetVisibilityOptions');
    options.replaceChildren();

    assetReturnData.assets.forEach(asset => {
        const label = document.createElement('label');
        label.className = 'asset-visibility-option';
        label.style.setProperty('--asset-color', asset.color);

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = !hiddenAssetKeys.has(asset.key);
        checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
                hiddenAssetKeys.delete(asset.key);
            } else {
                hiddenAssetKeys.add(asset.key);
            }
            saveHiddenAssets();
            refreshAssetViews();
        });

        const swatch = document.createElement('span');
        swatch.className = 'asset-return-legend-swatch';
        const name = document.createElement('span');
        name.textContent = asset.short_name;
        label.append(checkbox, swatch, name);
        options.appendChild(label);
    });
}

function restoreHiddenAssets() {
    try {
        const savedKeys = JSON.parse(
            localStorage.getItem(ASSET_VISIBILITY_STORAGE_KEY) || '[]'
        );
        const validKeys = new Set(assetReturnData.assets.map(asset => asset.key));
        hiddenAssetKeys = new Set(
            Array.isArray(savedKeys) ? savedKeys.filter(key => validKeys.has(key)) : []
        );
    } catch (error) {
        hiddenAssetKeys = new Set();
        console.warn('无法读取资产显示设置:', error);
    }
}

function createReturnCell(item, rank, year) {
    const cell = document.createElement('button');
    cell.type = 'button';
    cell.className = `asset-return-cell ${item.value >= 0 ? 'is-up' : 'is-down'}`;
    cell.style.setProperty('--asset-color', item.asset.color);
    cell.style.setProperty('--asset-soft-color', hexToRgba(item.asset.color, 0.32));
    cell.title = `${year} 年第 ${rank} 名：${item.asset.name} ${formatReturn(item.value)}`;
    cell.setAttribute(
        'aria-label',
        `${year} 年第 ${rank} 名，${item.asset.name}，收益率 ${formatReturn(item.value)}`
    );

    const rankElement = document.createElement('span');
    rankElement.className = 'asset-return-rank';
    rankElement.textContent = rank;

    const name = document.createElement('span');
    name.className = 'asset-return-name';
    name.textContent = item.asset.short_name;

    const value = document.createElement('strong');
    value.className = 'asset-return-value';
    value.textContent = formatReturn(item.value);

    cell.append(rankElement, name, value);
    bindAssetInteraction(cell, item.asset.key);
    return cell;
}

function renderReturnTable() {
    const table = document.getElementById('assetReturnTable');
    const years = Object.keys(assetReturnData.returns).map(Number)
        .sort((left, right) => newestYearFirst ? right - left : left - right);
    table.replaceChildren();

    years.forEach(year => {
        const ranked = getRankedReturns(year);
        const row = document.createElement('section');
        row.className = 'asset-return-row';
        row.setAttribute('aria-label', `${year} 年资产收益排名`);

        const yearLabel = document.createElement('div');
        yearLabel.className = 'asset-return-year';
        const yearNumber = document.createElement('span');
        yearNumber.textContent = year;
        yearLabel.appendChild(yearNumber);
        if (Number(assetReturnData.partial_year) === year) {
            const ytd = document.createElement('small');
            ytd.textContent = 'YTD';
            yearLabel.appendChild(ytd);
        }
        row.appendChild(yearLabel);

        const cells = document.createElement('div');
        cells.className = 'asset-return-cells';
        ranked.forEach((item, index) => {
            cells.appendChild(createReturnCell(item, index + 1, year));
        });
        row.appendChild(cells);
        table.appendChild(row);
    });

    setActiveAsset(transientAssetKey);
}

function renderSources() {
    document.getElementById('assetReturnMethodology').textContent =
        assetReturnData.methodology;

    const sources = document.getElementById('assetReturnSources');
    sources.replaceChildren();
    assetReturnData.sources.forEach(source => {
        if (!source.url) {
            const text = document.createElement('span');
            text.textContent = source.name;
            sources.appendChild(text);
            return;
        }
        const link = document.createElement('a');
        link.href = source.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = source.name;
        sources.appendChild(link);
    });
}

function appendAssetReturnsUpdateLog(text, type) {
    if (!text) return;
    const log = document.getElementById('assetReturnsUpdateLog');
    const line = document.createElement('div');
    if (type) line.className = `log-${type}`;
    line.textContent = text;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
}

function finishAssetReturnsUpdate(success, message) {
    const progress = document.getElementById('assetReturnsUpdateProgress');
    progress.className = 'update-progress-bar';
    progress.style.width = '100%';
    progress.style.background = success
        ? 'linear-gradient(90deg, #38a169, #48bb78)'
        : 'linear-gradient(90deg, #e53e3e, #fc8181)';
    document.getElementById('assetReturnsUpdateTitle').textContent =
        success ? '更新完成' : '更新失败';
    document.getElementById('assetReturnsUpdateFooter').style.display = 'block';

    const button = document.getElementById('updateAssetReturnsBtn');
    button.disabled = false;
    button.classList.remove('spinning');
    appendAssetReturnsUpdateLog(message, success ? 'success' : 'error');

    if (success) {
        loadAssetReturnData().catch(() => {});
    }
}

function startAssetReturnsUpdatePolling() {
    let offset = 0;
    assetReturnsUpdatePollTimer = setInterval(async () => {
        try {
            const response = await fetch(
                `/api/asset-returns/update/status?offset=${offset}`
            );
            const status = await response.json();
            (status.new_logs || []).forEach(line => appendAssetReturnsUpdateLog(line));
            offset = status.total_logs;

            if (!status.running && status.success !== null) {
                clearInterval(assetReturnsUpdatePollTimer);
                assetReturnsUpdatePollTimer = null;
                finishAssetReturnsUpdate(
                    status.success,
                    status.success
                        ? '最新年度 YTD 数据已写入并刷新。'
                        : `更新失败：${status.error || '未知错误'}`
                );
            }
        } catch (_) {
            // 临时网络错误时继续下一轮轮询。
        }
    }, 800);
}

async function triggerAssetReturnsUpdate() {
    const button = document.getElementById('updateAssetReturnsBtn');
    const progress = document.getElementById('assetReturnsUpdateProgress');
    document.getElementById('assetReturnsUpdateLog').replaceChildren();
    document.getElementById('assetReturnsUpdateTitle').textContent =
        '正在更新当年收益率';
    document.getElementById('assetReturnsUpdateFooter').style.display = 'none';
    document.getElementById('assetReturnsUpdateModal').classList.add('visible');
    progress.className = 'update-progress-bar indeterminate';
    progress.style.width = '';
    progress.style.background = '';
    button.disabled = true;
    button.classList.add('spinning');

    try {
        const response = await fetch('/api/asset-returns/update');
        const result = await response.json();
        appendAssetReturnsUpdateLog(result.message);
        if (result.ok) {
            startAssetReturnsUpdatePolling();
        } else {
            finishAssetReturnsUpdate(false, result.message);
        }
    } catch (error) {
        finishAssetReturnsUpdate(false, `请求失败：${error.message}`);
    }
}

function closeAssetReturnsUpdateModal() {
    document.getElementById('assetReturnsUpdateModal').classList.remove('visible');
    if (assetReturnsUpdatePollTimer) {
        clearInterval(assetReturnsUpdatePollTimer);
        assetReturnsUpdatePollTimer = null;
    }
}

function bindControls() {
    const sortButton = document.getElementById('assetReturnSort');
    sortButton.addEventListener('click', () => {
        newestYearFirst = !newestYearFirst;
        sortButton.textContent = newestYearFirst ? '年份：新 → 旧' : '年份：旧 → 新';
        renderReturnTable();
    });

    const visibility = document.querySelector('.asset-visibility');
    const visibilityToggle = document.getElementById('assetVisibilityToggle');
    const visibilityPanel = document.getElementById('assetVisibilityPanel');
    visibilityToggle.addEventListener('click', () => {
        const willOpen = visibilityPanel.hidden;
        visibilityPanel.hidden = !willOpen;
        visibilityToggle.setAttribute('aria-expanded', String(willOpen));
    });

    document.getElementById('showAllAssets').addEventListener('click', () => {
        hiddenAssetKeys.clear();
        saveHiddenAssets();
        refreshAssetViews();
    });

    document.addEventListener('click', event => {
        if (visibility.contains(event.target)) return;
        visibilityPanel.hidden = true;
        visibilityToggle.setAttribute('aria-expanded', 'false');
    });

    document.addEventListener('keydown', event => {
        if (event.key !== 'Escape' || visibilityPanel.hidden) return;
        visibilityPanel.hidden = true;
        visibilityToggle.setAttribute('aria-expanded', 'false');
        visibilityToggle.focus();
    });

    document.getElementById('updateAssetReturnsBtn').addEventListener(
        'click',
        triggerAssetReturnsUpdate
    );
    document.getElementById('closeAssetReturnsUpdateBtn').addEventListener(
        'click',
        closeAssetReturnsUpdateModal
    );
}

async function loadAssetReturnData() {
    try {
        const response = await fetch(`/api/data/asset_returns_ranking.json?t=${Date.now()}`);
        if (!response.ok) throw new Error(`数据请求失败（${response.status}）`);
        assetReturnData = await response.json();
        restoreHiddenAssets();
        renderReturnSummary();
        renderLegend();
        renderReturnTable();
        renderVisibilityOptions();
        updateVisibilityButton();
        renderSources();
        if (!assetReturnControlsBound) {
            bindControls();
            assetReturnControlsBound = true;
        }
    } catch (error) {
        const table = document.getElementById('assetReturnTable');
        table.innerHTML = `<div class="asset-return-loading is-error">${error.message}</div>`;
        console.error('加载资产收益排名失败:', error);
    }
}

loadAssetReturnData();
