(() => {
    const HORIZON_YEARS = 60;
    const HISTORICAL_START = 1782;
    const HISTORICAL_END = 2034;
    const DEFAULT_MONTH_WIDTH = 12;
    const TOTAL_MONTHS = (HISTORICAL_END - HISTORICAL_START) * 12;

    const HISTORICAL_CYCLES = [
        {
            name: 'Ⅰ 蒸汽/纺织',
            technology: '纺织机 + 蒸汽机',
            start: 1782,
            end: 1845,
            duration: 63,
            color: '#8ebf73',
            phases: [
                [
                    '繁荣',
                    '1782-01',
                    '1802-01',
                    '纺织机械化与蒸汽机商业化推动第一轮长波繁荣。',
                ],
                [
                    '衰退（拿破仑战争）',
                    '1802-01',
                    '1815-01',
                    '拿破仑战争扰动正常经济波动，属于范·杜因衰退阶段中的战争窗口。',
                ],
                [
                    '衰退',
                    '1815-01',
                    '1825-01',
                    '战后产能扩张趋缓，技术红利递减并走向1825年工业危机。',
                ],
                [
                    '萧条',
                    '1825-01',
                    '1836-01',
                    '工业危机后产能、价格与投资长期低迷。',
                ],
                [
                    '复苏',
                    '1836-01',
                    '1845-01',
                    '铁路和炼钢技术开始孕育，为第二波长周期铺路。',
                ],
            ],
        },
        {
            name: 'Ⅱ 钢铁/铁路',
            technology: '贝塞麦炼钢 + 铁路',
            start: 1845,
            end: 1892,
            duration: 47,
            color: '#95c8a2',
            phases: [
                [
                    '繁荣',
                    '1845-01',
                    '1866-01',
                    '铁路建设与炼钢技术扩散推动重工业繁荣。',
                ],
                [
                    '衰退',
                    '1866-01',
                    '1873-01',
                    '铁路和钢铁产能逐渐过剩，最终走向1873年全球危机。',
                ],
                [
                    '萧条',
                    '1873-01',
                    '1883-01',
                    '长萧条前段，通缩、银行风险与重工业出清持续。',
                ],
                [
                    '复苏',
                    '1883-01',
                    '1893-01',
                    '电力、化工和内燃机技术蓄力，衔接第三波长周期。',
                ],
            ],
        },
        {
            name: 'Ⅲ 电气/重化',
            technology: '电力 + 化工 + 内燃机',
            start: 1892,
            end: 1948,
            duration: 56,
            color: '#75bfd7',
            phases: [
                [
                    '繁荣',
                    '1892-01',
                    '1913-01',
                    '电力、化工和内燃机集中商业化，美德工业快速扩张。',
                ],
                [
                    '衰退（一战）',
                    '1913-01',
                    '1920-01',
                    '第一次世界大战形成战争窗口，归入范·杜因衰退阶段。',
                ],
                [
                    '衰退',
                    '1920-01',
                    '1929-01',
                    '战后金融杠杆和产能矛盾累积，最终走向1929年股灾。',
                ],
                [
                    '萧条',
                    '1929-01',
                    '1937-01',
                    '大萧条、银行危机与全球通缩集中爆发。',
                ],
                [
                    '复苏',
                    '1937-01',
                    '1948-01',
                    '汽车、石化与电子计算技术发展，衔接第四波长周期。',
                ],
            ],
        },
        {
            name: 'Ⅳ 汽车/计算机',
            technology: '汽车 + 石化 + 电子计算机',
            start: 1948,
            end: 1991,
            duration: 43,
            color: '#7bb4d0',
            phases: [
                [
                    '繁荣',
                    '1948-01',
                    '1966-01',
                    '汽车、石化和电子计算机推动战后生产率与消费扩张。',
                ],
                [
                    '衰退',
                    '1966-01',
                    '1973-01',
                    '战后增长动能减弱，资本回报和生产率逐渐放缓。',
                ],
                [
                    '萧条',
                    '1973-01',
                    '1982-01',
                    '石油危机与滞胀主导经济调整。',
                ],
                [
                    '复苏',
                    '1982-01',
                    '1991-01',
                    '半导体、个人计算机与通信技术扩散，信息长波开始孕育。',
                ],
            ],
        },
        {
            name: 'Ⅴ 信息与AI',
            technology: 'ICT / 互联网 / AI',
            start: 1991,
            end: 2033,
            duration: 42,
            color: '#e58b76',
            phases: [
                [
                    '繁荣',
                    '1991-01',
                    '2008-01',
                    'ICT、互联网与全球化推动第五波繁荣。',
                ],
                [
                    '衰退',
                    '2008-01',
                    '2015-01',
                    '金融危机后技术红利递减，进入范·杜因衰退阶段的核心区间。',
                ],
                [
                    '衰退/萧条争议窗',
                    '2015-01',
                    '2020-01',
                    '不同口径把萧条起点定在2015年或2020年，因此保留为过渡窗口。',
                ],
                [
                    '萧条',
                    '2020-01',
                    '2025-01',
                    '旧技术红利与债务周期出清，AI和新能源开始孕育。',
                ],
                [
                    '萧条终点争议窗',
                    '2025-01',
                    '2030-01',
                    '不同口径把萧条终点定在2025年或2030年，第六波已开始接力。',
                ],
                [
                    '第六波接力中',
                    '2030-01',
                    '2034-01',
                    'AI、新能源等新技术对应的第六波处于接力和确认过程中。',
                ],
            ],
        },
    ];

    const HISTORICAL_GAPS = [];

    const MONTHLY_CYCLES = [
        {
            key: 'kondratiev',
            name: '康波周期',
            range: '历史研究分期',
            type: 'history',
            colors: ['#5f8f4f', '#d4aa43', '#b65d59', '#526c91', '#aab1bd'],
        },
        {
            key: 'kuznets',
            name: '库兹涅茨周期',
            range: '20 年理论模拟',
            type: 'model',
            durationMonths: 240,
            phases: ['复苏', '扩张', '放缓', '收缩'],
            colors: ['#297c88', '#399b84', '#d49a3a', '#ba654d'],
        },
        {
            key: 'juglar',
            name: '朱格拉周期',
            range: '10 年理论模拟',
            type: 'model',
            durationMonths: 120,
            phases: ['复苏', '繁荣', '危机', '萧条'],
            colors: ['#3d8b63', '#76a743', '#d59a31', '#c45b55'],
        },
        {
            key: 'kitchin',
            name: '基钦周期',
            range: '4 年理论模拟',
            type: 'model',
            durationMonths: 48,
            phases: ['被动去库', '主动补库', '被动补库', '主动去库'],
            colors: ['#337fb5', '#4e9d68', '#d39b38', '#bd5c58'],
        },
    ];

    const CYCLES = [
        {
            key: 'kondratiev',
            shortName: '康波',
            name: '康波周期',
            duration: 60,
            range: '约 45–60 年',
            focus: '技术革命与资本积累',
            description: '观察技术范式、基础设施和长期资本积累的扩散与更替。',
            colors: ['#3f67c7', '#6957b8', '#9a669d', '#67738c'],
            phases: [
                { name: '复苏', detail: '新技术与新产业开始扩散，投资信心从低位修复。' },
                { name: '繁荣', detail: '创新红利广泛释放，投资、生产率与需求共同扩张。' },
                { name: '衰退', detail: '收益率下降、债务压力累积，原有增长模式逐渐放缓。' },
                { name: '萧条', detail: '产能与债务出清，旧范式收缩，并孕育下一轮创新。' },
            ],
        },
        {
            key: 'kuznets',
            shortName: '库兹涅茨',
            name: '库兹涅茨周期',
            duration: 20,
            range: '约 15–25 年',
            focus: '建筑、人口与基础设施投资',
            description: '常被用于观察人口迁移、房地产建设和基础设施投资的中长期波动。',
            colors: ['#297c88', '#399b84', '#d49a3a', '#ba654d'],
            phases: [
                { name: '复苏', detail: '人口、住房或基础设施需求回升，建设活动逐步企稳。' },
                { name: '扩张', detail: '建设投资与城市化需求加速，相关产业链同步扩张。' },
                { name: '放缓', detail: '供给逐渐充足，新增需求和投资回报开始下降。' },
                { name: '收缩', detail: '建设活动调整、存量消化，资本开支进入低位。' },
            ],
        },
        {
            key: 'juglar',
            shortName: '朱格拉',
            name: '朱格拉周期',
            duration: 10,
            range: '约 7–11 年',
            focus: '设备投资与固定资本更新',
            description: '主要刻画企业设备投资、产能扩张和固定资本更新形成的商业周期。',
            colors: ['#3d8b63', '#76a743', '#d59a31', '#c45b55'],
            phases: [
                { name: '复苏', detail: '需求和利润改善，企业开工率与投资意愿逐步回升。' },
                { name: '繁荣', detail: '设备投资和产能扩张加速，信用与盈利处于高位。' },
                { name: '危机', detail: '供需错配或融资条件收紧，盈利和投资出现拐点。' },
                { name: '萧条', detail: '过剩产能出清，资本开支收缩并等待下一轮更新。' },
            ],
        },
        {
            key: 'kitchin',
            shortName: '基钦',
            name: '基钦周期',
            duration: 4,
            range: '约 3–5 年',
            focus: '企业库存调整',
            description: '以需求和库存增速的组合变化，刻画企业补库存与去库存过程。',
            colors: ['#337fb5', '#4e9d68', '#d39b38', '#bd5c58'],
            phases: [
                { name: '被动去库', detail: '需求先回暖而生产调整偏慢，库存增速继续下降。' },
                { name: '主动补库', detail: '需求改善得到确认，企业主动扩大生产并增加库存。' },
                { name: '被动补库', detail: '需求转弱快于生产调整，商品被动积压、库存上升。' },
                { name: '主动去库', detail: '企业削减生产和采购以消化库存，库存增速回落。' },
            ],
        },
    ];

    const timeline = document.getElementById('cycleTimeline');
    const progress = document.getElementById('cycleProgress');
    const stepDescription = document.getElementById('cycleStepDescription');
    const previousButton = document.getElementById('cyclePrevious');
    const nextButton = document.getElementById('cycleNext');
    const showAllButton = document.getElementById('cycleShowAll');
    const selection = document.getElementById('cycleSelection');
    const guideGrid = document.getElementById('cycleGuideGrid');
    const historicalTimeline = document.getElementById('historicalTimeline');
    const historicalCycleCards = document.getElementById('historicalCycleCards');
    const historicalPhaseList = document.getElementById('historicalPhaseList');
    const monthlyCycleOptions = document.getElementById('monthlyCycleOptions');
    const monthlyTimelineScroll = document.getElementById('monthlyTimelineScroll');
    const monthlyTimelineSelection = document.getElementById('monthlyTimelineSelection');
    const monthlyShowAll = document.getElementById('monthlyShowAll');
    const monthlyJumpNow = document.getElementById('monthlyJumpNow');
    const monthlyZoomOut = document.getElementById('monthlyZoomOut');
    const monthlyZoomIn = document.getElementById('monthlyZoomIn');
    const monthlyZoomRange = document.getElementById('monthlyZoomRange');
    const monthlyZoomReset = document.getElementById('monthlyZoomReset');
    const monthlyZoomValue = document.getElementById('monthlyZoomValue');

    let visibleLevel = 1;
    let selectedButton = null;
    let selectedMonthlyButton = null;
    let monthWidth = DEFAULT_MONTH_WIDTH;
    let zoomFrame = null;
    let dragState = null;
    let suppressTimelineClick = false;
    const visibleMonthlyCycles = new Set(MONTHLY_CYCLES.map(cycle => cycle.key));

    function createElement(tag, className, text) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    }

    function absoluteMonth(isoDate) {
        const [year, month] = isoDate.split('-').map(Number);
        return year * 12 + month - 1;
    }

    function monthOffset(isoDate) {
        return absoluteMonth(isoDate) - HISTORICAL_START * 12;
    }

    function formatAbsoluteMonth(monthIndex) {
        const year = Math.floor(monthIndex / 12);
        const month = (monthIndex % 12) + 1;
        return `${year}.${String(month).padStart(2, '0')}`;
    }

    function formatMonthRange(start, endExclusive) {
        return `${formatAbsoluteMonth(absoluteMonth(start))}—`
            + `${formatAbsoluteMonth(absoluteMonth(endExclusive) - 1)}`;
    }

    function historyPhaseColor(phaseName) {
        const colors = {
            '复苏': '#5f8f4f',
            '繁荣': '#d4aa43',
            '衰退': '#b65d59',
            '衰退（拿破仑战争）': '#9b6b59',
            '衰退（一战）': '#9b6b59',
            '萧条': '#526c91',
            '资料未细分': '#aab1bd',
            '战争干扰期': '#9b7b66',
            '繁荣（战争穿插）': '#c78e3b',
            '本口径未标定': '#aab1bd',
            '过渡期（待确认）': '#8c6bb1',
            '双周期共振段': '#8c6bb1',
            '衰退/萧条争议窗': '#8c6bb1',
            '萧条终点争议窗': '#7566a8',
            '第六波接力中': '#478a7b',
        };
        return colors[phaseName] || '#7c879b';
    }

    function currentMonthOffset() {
        const now = new Date();
        const offset = now.getFullYear() * 12 + now.getMonth() - HISTORICAL_START * 12;
        return Math.max(0, Math.min(TOTAL_MONTHS, offset));
    }

    function appendCurrentAndFuture(track, showLabel = false) {
        const nowOffset = currentMonthOffset();
        const future = createElement('div', 'monthly-future-area');
        future.style.left = `${nowOffset * monthWidth}px`;
        future.style.width = `${(TOTAL_MONTHS - nowOffset) * monthWidth}px`;
        track.appendChild(future);

        const marker = createElement('div', 'historical-now-marker');
        marker.style.left = `${nowOffset * monthWidth}px`;
        if (showLabel) {
            const now = new Date();
            marker.appendChild(createElement(
                'span',
                '',
                `现在 · ${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}`,
            ));
        }
        track.appendChild(marker);
    }

    function selectMonthlyPhase(
        cycleName,
        phaseName,
        start,
        end,
        color,
        button,
        type,
        detail = '',
    ) {
        if (selectedMonthlyButton) selectedMonthlyButton.classList.remove('is-selected');
        selectedMonthlyButton = button;
        selectedMonthlyButton.classList.add('is-selected');

        monthlyTimelineSelection.replaceChildren();
        const dot = createElement('span', 'cycle-selection-dot');
        dot.style.setProperty('--selection-color', color);
        const content = createElement('div');
        content.appendChild(createElement('strong', '', `${cycleName} · ${phaseName}`));
        content.appendChild(createElement(
            'p',
            '',
            `${formatMonthRange(start, end)} · ${type === 'history' ? '历史研究口径' : '理论模拟口径'}`,
        ));
        if (detail) content.appendChild(createElement('p', '', detail));
        monthlyTimelineSelection.append(dot, content);
    }

    function createMonthlySegment(
        cycle,
        phaseName,
        start,
        end,
        color,
        cycleNumber,
        detail = '',
    ) {
        const button = createElement('button', 'monthly-phase-segment');
        button.type = 'button';
        button.style.left = `${monthOffset(start) * monthWidth}px`;
        button.style.width = `${(absoluteMonth(end) - absoluteMonth(start)) * monthWidth}px`;
        button.style.setProperty('--monthly-phase-color', color);
        button.classList.toggle(
            'is-gap',
            ['资料未细分', '本口径未标定', '战争干扰期'].includes(phaseName),
        );
        button.classList.toggle('is-war', phaseName.includes('战争') || phaseName.includes('一战'));
        button.classList.toggle('is-uncertain', phaseName.includes('争议'));
        const prefix = cycleNumber ? `第 ${cycleNumber} 轮 · ` : '';
        button.appendChild(createElement('strong', '', `${prefix}${phaseName}`));
        button.appendChild(createElement('span', '', formatMonthRange(start, end)));
        button.title = `${cycle.name} · ${prefix}${phaseName}\n${formatMonthRange(start, end)}`;
        button.setAttribute(
            'aria-label',
            `${cycle.name}${prefix}${phaseName}，${formatMonthRange(start, end)}`,
        );
        button.addEventListener('click', () => selectMonthlyPhase(
            cycle.name,
            `${prefix}${phaseName}`,
            start,
            end,
            color,
            button,
            cycle.type,
            detail,
        ));
        return button;
    }

    function renderMonthlyAxis() {
        const row = createElement('div', 'monthly-axis-row');
        row.appendChild(createElement('div', 'monthly-row-label', '年份 / 月份'));
        const ruler = createElement('div', 'monthly-axis-ruler');
        ruler.style.width = `${TOTAL_MONTHS * monthWidth}px`;

        for (let year = HISTORICAL_START; year < HISTORICAL_END; year += 1) {
            const yearBlock = createElement('div', 'monthly-axis-year');
            yearBlock.style.left = `${(year - HISTORICAL_START) * 12 * monthWidth}px`;
            yearBlock.style.width = `${12 * monthWidth}px`;
            yearBlock.appendChild(createElement('strong', '', String(year)));
            for (let month = 1; month <= 12; month += 1) {
                const monthTick = createElement('span', '', String(month));
                monthTick.style.left = `${(month - 1) * monthWidth}px`;
                yearBlock.appendChild(monthTick);
            }
            ruler.appendChild(yearBlock);
        }
        appendCurrentAndFuture(ruler, true);
        row.appendChild(ruler);
        historicalTimeline.appendChild(row);
    }

    function renderHistoricalMonthlyTrack(track) {
        const cycle = MONTHLY_CYCLES[0];
        HISTORICAL_CYCLES.forEach((wave, waveIndex) => {
            wave.phases.forEach(([phaseName, start, end, detail]) => {
                track.appendChild(createMonthlySegment(
                    cycle,
                    phaseName,
                    start,
                    end,
                    historyPhaseColor(phaseName),
                    waveIndex + 1,
                    detail,
                ));
            });
        });
        HISTORICAL_GAPS.forEach(([phaseName, start, end, detail]) => {
            track.appendChild(createMonthlySegment(
                cycle,
                phaseName,
                start,
                end,
                historyPhaseColor(phaseName),
                null,
                detail,
            ));
        });
    }

    function dateFromOffset(offset) {
        const absolute = HISTORICAL_START * 12 + offset;
        return `${Math.floor(absolute / 12)}-${String((absolute % 12) + 1).padStart(2, '0')}`;
    }

    function renderModelMonthlyTrack(track, cycle) {
        const phaseDuration = cycle.durationMonths / cycle.phases.length;
        let cycleNumber = 1;
        for (let cycleStart = 0; cycleStart < TOTAL_MONTHS; cycleStart += cycle.durationMonths) {
            cycle.phases.forEach((phaseName, phaseIndex) => {
                const startOffset = cycleStart + phaseIndex * phaseDuration;
                const endOffset = Math.min(startOffset + phaseDuration, TOTAL_MONTHS);
                if (startOffset >= TOTAL_MONTHS) return;
                track.appendChild(createMonthlySegment(
                    cycle,
                    phaseName,
                    dateFromOffset(startOffset),
                    dateFromOffset(endOffset),
                    cycle.colors[phaseIndex],
                    cycleNumber,
                    '',
                ));
            });
            cycleNumber += 1;
        }
    }

    function renderMonthlyRows() {
        MONTHLY_CYCLES.forEach(cycle => {
            if (!visibleMonthlyCycles.has(cycle.key)) return;
            const row = createElement('div', `monthly-cycle-row is-${cycle.type}`);
            const label = createElement('div', 'monthly-row-label');
            label.appendChild(createElement('strong', '', cycle.name));
            label.appendChild(createElement('span', '', cycle.range));
            row.appendChild(label);

            const track = createElement('div', 'monthly-cycle-track');
            track.style.width = `${TOTAL_MONTHS * monthWidth}px`;
            if (cycle.type === 'history') {
                renderHistoricalMonthlyTrack(track);
            } else {
                renderModelMonthlyTrack(track, cycle);
            }
            appendCurrentAndFuture(track);
            row.appendChild(track);
            historicalTimeline.appendChild(row);
        });
    }

    function renderMonthlyOptions() {
        monthlyCycleOptions.replaceChildren();
        MONTHLY_CYCLES.forEach(cycle => {
            const label = createElement('label', 'monthly-cycle-option');
            label.classList.toggle('is-active', visibleMonthlyCycles.has(cycle.key));
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = visibleMonthlyCycles.has(cycle.key);
            input.addEventListener('change', () => {
                if (input.checked) visibleMonthlyCycles.add(cycle.key);
                else visibleMonthlyCycles.delete(cycle.key);
                renderHistoricalTimeline();
            });
            label.append(input, createElement('span', '', cycle.name));
            monthlyCycleOptions.appendChild(label);
        });
    }

    function renderHistoricalDetails() {
        const currentYear = new Date().getFullYear();
        historicalCycleCards.replaceChildren();
        historicalPhaseList.replaceChildren();

        HISTORICAL_CYCLES.forEach((cycle, index) => {
            const card = createElement('article', 'historical-cycle-card');
            card.style.setProperty('--historical-color', cycle.color);
            card.appendChild(createElement('span', 'historical-cycle-order', `第 ${index + 1} 轮`));
            card.appendChild(createElement('strong', '', cycle.name));
            card.appendChild(createElement('span', 'historical-cycle-tech', cycle.technology));
            card.appendChild(createElement(
                'span',
                'historical-cycle-period',
                `${cycle.start}—${cycle.end}`,
            ));
            card.appendChild(createElement('small', '', `${cycle.duration} 年`));
            if (currentYear >= cycle.start && currentYear <= cycle.end) {
                card.classList.add('is-current');
                card.appendChild(createElement('em', '', '当前所处'));
            }
            historicalCycleCards.appendChild(card);

            const detail = createElement('article', 'historical-phase-card');
            const heading = createElement('h3', '', `第 ${index + 1} 轮 · ${cycle.name}`);
            detail.appendChild(heading);
            const list = createElement('ol');
            cycle.phases.forEach(([phaseName, start, end, phaseDetail]) => {
                const item = createElement('li');
                item.style.setProperty('--phase-color', historyPhaseColor(phaseName));
                const summary = createElement('div', 'historical-phase-summary');
                summary.appendChild(createElement('strong', '', phaseName));
                summary.appendChild(createElement('span', '', formatMonthRange(start, end)));
                item.appendChild(summary);
                item.appendChild(createElement('p', '', phaseDetail));
                list.appendChild(item);
            });
            detail.appendChild(list);
            historicalPhaseList.appendChild(detail);
        });

        HISTORICAL_GAPS.forEach(([phaseName, start, end, phaseDetail]) => {
            const detail = createElement('article', 'historical-phase-card is-gap');
            detail.appendChild(createElement('h3', '', phaseName));
            const list = createElement('ol');
            const item = createElement('li');
            item.style.setProperty('--phase-color', historyPhaseColor(phaseName));
            const summary = createElement('div', 'historical-phase-summary');
            summary.appendChild(createElement('strong', '', phaseName));
            summary.appendChild(createElement('span', '', formatMonthRange(start, end)));
            item.append(summary, createElement('p', '', phaseDetail));
            list.appendChild(item);
            detail.appendChild(list);
            historicalPhaseList.appendChild(detail);
        });
    }

    function renderHistoricalTimeline() {
        const previousScrollLeft = monthlyTimelineScroll.scrollLeft;
        historicalTimeline.replaceChildren();
        historicalTimeline.style.setProperty(
            '--monthly-timeline-width',
            `${TOTAL_MONTHS * monthWidth}px`,
        );
        historicalTimeline.style.setProperty('--month-width', `${monthWidth}px`);
        historicalTimeline.style.setProperty('--year-width', `${monthWidth * 12}px`);
        historicalTimeline.classList.toggle('is-compact', monthWidth < 8);
        selectedMonthlyButton = null;
        renderMonthlyOptions();
        renderMonthlyAxis();
        renderMonthlyRows();
        monthlyTimelineScroll.scrollLeft = previousScrollLeft;
    }

    function updateZoomControls() {
        monthlyZoomRange.value = String(monthWidth);
        monthlyZoomValue.value = `${monthWidth} px/月`;
        monthlyZoomOut.disabled = monthWidth <= Number(monthlyZoomRange.min);
        monthlyZoomIn.disabled = monthWidth >= Number(monthlyZoomRange.max);
    }

    function setMonthWidth(nextWidth) {
        const minimum = Number(monthlyZoomRange.min);
        const maximum = Number(monthlyZoomRange.max);
        const clampedWidth = Math.max(minimum, Math.min(maximum, Number(nextWidth)));
        if (clampedWidth === monthWidth) return;

        const centerOffset = monthlyTimelineScroll.scrollLeft
            + monthlyTimelineScroll.clientWidth / 2 - 130;
        const centerMonth = Math.max(0, Math.min(TOTAL_MONTHS, centerOffset / monthWidth));
        monthWidth = clampedWidth;
        renderHistoricalTimeline();
        updateZoomControls();

        requestAnimationFrame(() => {
            monthlyTimelineScroll.scrollLeft = Math.max(
                0,
                130 + centerMonth * monthWidth - monthlyTimelineScroll.clientWidth / 2,
            );
        });
    }

    function scheduleZoom(nextWidth) {
        if (zoomFrame) window.clearTimeout(zoomFrame);
        zoomFrame = window.setTimeout(() => {
            zoomFrame = null;
            setMonthWidth(nextWidth);
        }, 80);
    }

    function beginTimelineDrag(event) {
        if (event.pointerType === 'touch' || event.button !== 0) return;
        dragState = {
            pointerId: event.pointerId,
            startX: event.clientX,
            startScrollLeft: monthlyTimelineScroll.scrollLeft,
            moved: false,
        };
        monthlyTimelineScroll.setPointerCapture(event.pointerId);
        monthlyTimelineScroll.classList.add('is-dragging');
    }

    function moveTimelineDrag(event) {
        if (!dragState || dragState.pointerId !== event.pointerId) return;
        const delta = event.clientX - dragState.startX;
        if (Math.abs(delta) > 4) dragState.moved = true;
        if (!dragState.moved) return;
        event.preventDefault();
        monthlyTimelineScroll.scrollLeft = dragState.startScrollLeft - delta;
    }

    function endTimelineDrag(event) {
        if (!dragState || dragState.pointerId !== event.pointerId) return;
        suppressTimelineClick = dragState.moved;
        dragState = null;
        monthlyTimelineScroll.classList.remove('is-dragging');
        if (monthlyTimelineScroll.hasPointerCapture(event.pointerId)) {
            monthlyTimelineScroll.releasePointerCapture(event.pointerId);
        }
        if (suppressTimelineClick) {
            window.setTimeout(() => {
                suppressTimelineClick = false;
            }, 0);
        }
    }

    function renderAxis() {
        const axis = createElement('div', 'cycle-axis');
        axis.appendChild(createElement('div', 'cycle-row-label', '相对时间'));

        const scale = createElement('div', 'cycle-axis-scale');
        for (let year = 0; year <= HORIZON_YEARS; year += 5) {
            const tick = createElement('span', 'cycle-axis-tick', `${year} 年`);
            tick.style.left = `${(year / HORIZON_YEARS) * 100}%`;
            scale.appendChild(tick);
        }
        axis.appendChild(scale);
        timeline.appendChild(axis);
    }

    function renderCycleRow(cycle, cycleIndex) {
        const row = createElement('div', 'cycle-row');
        row.style.setProperty('--row-delay', `${cycleIndex * 70}ms`);

        const label = createElement('div', 'cycle-row-label');
        label.appendChild(createElement('strong', '', cycle.shortName));
        label.appendChild(createElement('span', '', cycle.range));
        row.appendChild(label);

        const track = createElement('div', 'cycle-track');
        const repeatCount = Math.ceil(HORIZON_YEARS / cycle.duration);

        for (let repeat = 0; repeat < repeatCount; repeat += 1) {
            const start = repeat * cycle.duration;
            const width = Math.min(cycle.duration, HORIZON_YEARS - start);
            const instance = createElement('div', 'cycle-instance');
            instance.style.left = `${(start / HORIZON_YEARS) * 100}%`;
            instance.style.width = `${(width / HORIZON_YEARS) * 100}%`;
            instance.dataset.cycleNumber = String(repeat + 1);

            cycle.phases.forEach((phase, phaseIndex) => {
                const phaseButton = createElement('button', 'cycle-phase');
                phaseButton.type = 'button';
                phaseButton.style.width = '25%';
                phaseButton.style.setProperty('--phase-color', cycle.colors[phaseIndex]);
                phaseButton.setAttribute(
                    'aria-label',
                    `${cycle.name}第 ${repeat + 1} 轮：${phase.name}。${phase.detail}`,
                );
                phaseButton.title = `${cycle.name} · ${phase.name}\n${phase.detail}`;
                phaseButton.appendChild(createElement('span', 'cycle-phase-name', phase.name));
                phaseButton.addEventListener('click', () => selectPhase(
                    cycle,
                    phase,
                    phaseIndex,
                    repeat + 1,
                    phaseButton,
                ));
                instance.appendChild(phaseButton);
            });

            track.appendChild(instance);
        }

        row.appendChild(track);
        timeline.appendChild(row);
    }

    function selectPhase(cycle, phase, phaseIndex, repeat, button) {
        if (selectedButton) selectedButton.classList.remove('is-selected');
        selectedButton = button;
        selectedButton.classList.add('is-selected');

        selection.replaceChildren();
        const dot = createElement('span', 'cycle-selection-dot');
        dot.style.setProperty('--selection-color', cycle.colors[phaseIndex]);
        const content = createElement('div');
        content.appendChild(createElement(
            'strong',
            '',
            `${cycle.name} · ${phase.name}（第 ${repeat} 轮）`,
        ));
        content.appendChild(createElement('p', '', phase.detail));
        selection.append(dot, content);
    }

    function renderProgress() {
        progress.replaceChildren();
        CYCLES.forEach((cycle, index) => {
            const button = createElement('button', 'cycle-progress-step');
            button.type = 'button';
            button.classList.toggle('is-visible', index < visibleLevel);
            button.classList.toggle('is-current', index === visibleLevel - 1);
            button.setAttribute('aria-label', `显示到${cycle.name}`);
            button.setAttribute('aria-pressed', index < visibleLevel ? 'true' : 'false');
            button.appendChild(createElement('span', 'cycle-progress-number', String(index + 1)));
            button.appendChild(createElement('span', 'cycle-progress-name', cycle.shortName));
            button.addEventListener('click', () => setVisibleLevel(index + 1));
            progress.appendChild(button);
        });
    }

    function renderTimeline() {
        timeline.replaceChildren();
        renderAxis();
        CYCLES.slice(0, visibleLevel).forEach(renderCycleRow);
    }

    function updateControls() {
        const current = CYCLES[visibleLevel - 1];
        previousButton.disabled = visibleLevel === 1;
        nextButton.disabled = visibleLevel === CYCLES.length;
        showAllButton.disabled = visibleLevel === CYCLES.length;
        nextButton.textContent = visibleLevel === CYCLES.length
            ? '已全部叠加'
            : `叠加${CYCLES[visibleLevel].shortName}`;
        stepDescription.textContent = visibleLevel === CYCLES.length
            ? '第 4 层：四种周期已全部叠加，可比较长短周期的嵌套'
            : `第 ${visibleLevel} 层：已显示到${current.name}，继续加入更短周期`;
    }

    function setVisibleLevel(level) {
        visibleLevel = Math.max(1, Math.min(CYCLES.length, level));
        selectedButton = null;
        renderProgress();
        renderTimeline();
        updateControls();
    }

    function renderGuide() {
        CYCLES.forEach(cycle => {
            const card = createElement('article', 'cycle-guide-card');
            const header = createElement('div', 'cycle-guide-header');
            const title = createElement('div');
            title.appendChild(createElement('h3', '', cycle.name));
            title.appendChild(createElement('span', '', cycle.range));
            header.appendChild(title);
            header.appendChild(createElement('strong', '', cycle.focus));
            card.appendChild(header);
            card.appendChild(createElement('p', 'cycle-guide-description', cycle.description));

            const phases = createElement('ol', 'cycle-phase-list');
            cycle.phases.forEach((phase, index) => {
                const item = createElement('li');
                item.style.setProperty('--phase-color', cycle.colors[index]);
                item.appendChild(createElement('span', 'cycle-phase-index', String(index + 1)));
                const phaseContent = createElement('div');
                phaseContent.appendChild(createElement('strong', '', phase.name));
                phaseContent.appendChild(createElement('p', '', phase.detail));
                item.appendChild(phaseContent);
                phases.appendChild(item);
            });
            card.appendChild(phases);
            guideGrid.appendChild(card);
        });
    }

    previousButton.addEventListener('click', () => setVisibleLevel(visibleLevel - 1));
    nextButton.addEventListener('click', () => setVisibleLevel(visibleLevel + 1));
    showAllButton.addEventListener('click', () => setVisibleLevel(CYCLES.length));
    monthlyShowAll.addEventListener('click', () => {
        MONTHLY_CYCLES.forEach(cycle => visibleMonthlyCycles.add(cycle.key));
        renderHistoricalTimeline();
    });
    monthlyJumpNow.addEventListener('click', () => {
        const markerPosition = 130 + currentMonthOffset() * monthWidth;
        monthlyTimelineScroll.scrollTo({
            left: Math.max(0, markerPosition - monthlyTimelineScroll.clientWidth / 2),
            behavior: 'smooth',
        });
    });
    monthlyZoomOut.addEventListener('click', () => setMonthWidth(monthWidth - 2));
    monthlyZoomIn.addEventListener('click', () => setMonthWidth(monthWidth + 2));
    monthlyZoomReset.addEventListener('click', () => setMonthWidth(DEFAULT_MONTH_WIDTH));
    monthlyZoomRange.addEventListener('input', event => {
        monthlyZoomValue.value = `${event.target.value} px/月`;
        scheduleZoom(event.target.value);
    });
    monthlyTimelineScroll.addEventListener('pointerdown', beginTimelineDrag);
    monthlyTimelineScroll.addEventListener('pointermove', moveTimelineDrag);
    monthlyTimelineScroll.addEventListener('pointerup', endTimelineDrag);
    monthlyTimelineScroll.addEventListener('pointercancel', endTimelineDrag);
    monthlyTimelineScroll.addEventListener('click', event => {
        if (!suppressTimelineClick) return;
        event.preventDefault();
        event.stopPropagation();
    }, true);

    renderHistoricalTimeline();
    renderHistoricalDetails();
    renderGuide();
    setVisibleLevel(1);
    updateZoomControls();
})();
