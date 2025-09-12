// 全局变量
let chart = null;
let allCities = [];
let currentData = null;

// 城市列表 - 70个大中城市
const CITIES = [
    "三亚", "上海", "东莞", "中山", "丹东", "乌鲁木齐", "兰州", "北京", "南京", "南宁",
    "南昌", "南通", "厦门", "唐山", "哈尔滨", "呼和浩特", "大理", "大连", "天津", "太原",
    "宁波", "安庆", "宜昌", "常德", "广州", "廊坊", "徐州", "惠州", "成都", "扬州",
    "无锡", "昆明", "杭州", "桂林", "武汉", "泉州", "济南", "济宁", "海口", "深圳",
    "温州", "湖州", "湘潭", "烟台", "牡丹江", "珠海", "福州", "秦皇岛", "绵阳", "肇庆",
    "西宁", "西安", "贵阳", "赣州", "遵义", "郑州", "重庆", "金华", "锦州", "长春",
    "长沙", "韶关", "青岛", "韩城", "包头", "北海", "平顶山", "银川", "丽水", "石家庄"
];

// 数据文件映射
const DATA_FILES = {
    'new_house_basic': 'new_house_basic_index.json',
    'used_house_basic': 'used_house_basic_index.json',
    'new_house_classified': {
        '90_below': 'new_house_classified_90_below.json',
        '90_144': 'new_house_classified_90_144.json',
        '144_above': 'new_house_classified_144_above.json'
    },
    'used_house_classified': {
        '90_below': 'used_house_classified_90_below.json',
        '90_144': 'used_house_classified_90_144.json',
        '144_above': 'used_house_classified_144_above.json'
    }
};

// DOM元素变量
let cityGrid, classificationOptions, updateBtn, loading, noData, statsSection;

// 全局错误处理
window.addEventListener('error', function(e) {
    console.error('全局错误:', e.error);
});

// Chart.js检查
function checkChartJS() {
    if (typeof Chart === 'undefined') {
        console.error('Chart.js未加载!');
        return false;
    }
    console.log('Chart.js版本:', Chart.version || 'unknown');
    return true;
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面DOM加载完成，开始初始化');
    
    // 检查Chart.js
    if (!checkChartJS()) {
        console.error('Chart.js未正确加载，图表功能将不可用');
        return;
    }
    
    // 添加延时确保DOM完全准备好
    setTimeout(function() {
        console.log('开始获取DOM元素...');
        console.log('document.readyState:', document.readyState);
        
        // 获取DOM元素
        cityGrid = document.getElementById('cityGrid');
        classificationOptions = document.getElementById('classificationOptions');
        updateBtn = document.getElementById('updateChart');
        loading = document.getElementById('loading');
        noData = document.getElementById('noData');
        statsSection = document.getElementById('statsSection');
        
        // 详细的cityGrid检查
        console.log('cityGrid 详细检查:');
        console.log('- cityGrid 元素:', cityGrid);
        console.log('- cityGrid 类型:', typeof cityGrid);
        console.log('- cityGrid 是否为null:', cityGrid === null);
        
        if (!cityGrid) {
            console.error('cityGrid 未找到，进行详细诊断:');
            console.log('- 当前页面URL:', window.location.href);
            console.log('- document.body 存在:', !!document.body);
            console.log('- 查找所有id元素:', Array.from(document.querySelectorAll('[id]')).map(el => ({id: el.id, tagName: el.tagName})));
            
            // 尝试其他方式查找
            const cityGridByQuery = document.querySelector('#cityGrid');
            const cityGridByClass = document.querySelector('.city-grid');
            console.log('- 通过querySelector查找:', cityGridByQuery);
            console.log('- 通过class查找:', cityGridByClass);
        }
    
        console.log('DOM元素获取结果:', {
            cityGrid: !!cityGrid,
            classificationOptions: !!classificationOptions,
            updateBtn: !!updateBtn,
            loading: !!loading,
            noData: !!noData,
            statsSection: !!statsSection
        });
        
        // 如果关键元素未找到，停止初始化
        if (!cityGrid) {
            console.error('关键DOM元素 cityGrid 未找到，停止初始化');
            return;
        }
    
    // 初始化功能
    console.log('开始初始化城市选择器');
    initializeCitySelect();
    
    console.log('开始初始化事件监听器');
    initializeEventListeners();
    
    console.log('开始初始化图表');
    initializeChart();
    
    console.log('所有初始化完成');
    
    // 显示空的图表框架，隐藏加载和无数据提示
    hideLoading();
    noData.style.display = 'none';
    statsSection.style.display = 'none';
    }, 100); // 100ms延时确保DOM完全准备好
});

// 初始化城市选择器
function initializeCitySelect() {
    console.log('initializeCitySelect 被调用');
    console.log('cityGrid 元素:', cityGrid);
    console.log('CITIES 数组长度:', CITIES.length);
    console.log('CITIES 前5个城市:', CITIES.slice(0, 5));
    
    if (!cityGrid) {
        console.error('cityGrid 元素未找到！无法初始化城市选择器');
        console.error('请确保HTML中存在 <div id="cityGrid"></div> 元素');
        return;
    }
    
    // 按拼音首字母排序城市
    const sortedCities = CITIES.sort((a, b) => a.localeCompare(b, 'zh-CN'));
    
    sortedCities.forEach(city => {
        const cityOption = document.createElement('label');
        cityOption.className = 'city-option';
        
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'city';
        radio.value = city;
        
        const span = document.createElement('span');
        span.textContent = city;
        
        cityOption.appendChild(radio);
        cityOption.appendChild(span);
        
        // 添加点击事件
        cityOption.addEventListener('click', function() {
            console.log(`🎯 用户点击城市: ${city}`);
            
            // 移除所有选中状态
            document.querySelectorAll('.city-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            // 添加选中状态
            this.classList.add('selected');
            radio.checked = true;
            
            console.log(`✅ 城市选择已更新: ${city}`);
            
            // 自动更新图表
            updateChart();
        });
        
        cityGrid.appendChild(cityOption);
    });
}

// 初始化事件监听器
function initializeEventListeners() {
    // 内容类型选择监听
    document.querySelectorAll('input[name="content-type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const isClassified = this.value.includes('classified');
            classificationOptions.style.display = isClassified ? 'block' : 'none';
            
            // 如果有选中的城市，自动更新图表
            if (getSelectedCity()) {
                updateChart();
            }
        });
    });

    // 面积类型选择监听
    document.querySelectorAll('input[name="area-type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            // 如果有选中的城市，自动更新图表
            if (getSelectedCity()) {
                updateChart();
            }
        });
    });

    // 更新图表按钮
    updateBtn.addEventListener('click', updateChart);
}

// 初始化图表
function initializeChart() {
    console.log('开始初始化图表');
    
    const canvas = document.getElementById('priceChart');
    if (!canvas) {
        console.error('找不到图表画布元素');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('无法获取2D上下文');
        return;
    }
    
    console.log('Canvas和Context获取成功');
    
    try {
        chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: {
                    display: true,
                    text: '请选择城市查看房价指数变化趋势',
                    font: {
                        size: 18,
                        weight: 'bold'
                    },
                    color: '#4a5568'
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(102, 126, 234, 0.8)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        title: function(tooltipItems) {
                            const dataPoint = tooltipItems[0];
                            if (dataPoint && dataPoint.raw && dataPoint.raw.rawData) {
                                const dateStr = dataPoint.raw.rawData.date;
                                if (dateStr) {
                                    const [year, month] = dateStr.split('-');
                                    return `${year}年${month.padStart(2, '0')}月`;
                                }
                            }
                            // 备用方案：从label解析
                            const dateStr = tooltipItems[0].label;
                            if (dateStr) {
                                const date = new Date(dateStr);
                                if (!isNaN(date.getTime())) {
                                    return `${date.getFullYear()}年${(date.getMonth() + 1).toString().padStart(2, '0')}月`;
                                }
                            }
                            return '';
                        },
                        label: function(context) {
                            const dataset = context.dataset;
                            const dataPoint = dataset.data[context.dataIndex];
                            const rawData = dataPoint.rawData;
                            
                            let label = dataset.label + ': ' + context.parsed.y.toFixed(2);
                            
                            // 显示详细信息
                            if (rawData) {
                                const labels = [label];
                                
                                // 环比指数
                                if (rawData.month_on_month) {
                                    labels.push(`环比指数: ${rawData.month_on_month.toFixed(2)}`);
                                }
                                
                                // 同比指数
                                if (rawData.year_on_year) {
                                    labels.push(`同比指数: ${rawData.year_on_year.toFixed(2)}`);
                                }
                                
                                // 增长率（如果存在）
                                if (rawData.growth_rate !== null && rawData.growth_rate !== undefined) {
                                    labels.push(`月增长率: ${(rawData.growth_rate * 100).toFixed(3)}%`);
                                }
                                
                                return labels;
                            }
                            
                            return label;
                        },
                        labelColor: function(context) {
                            return {
                                borderColor: context.dataset.borderColor,
                                backgroundColor: context.dataset.borderColor
                            };
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'month',
                        parser: 'yyyy-MM',
                        displayFormats: {
                            month: 'yyyy年MM月'
                        },
                        tooltipFormat: 'yyyy年MM月'
                    },
                    title: {
                        display: true,
                        text: '时间'
                    },
                    ticks: {
                        maxTicksLimit: 12,
                        source: 'data',
                        callback: function(value, index, values) {
                            const date = new Date(value);
                            return `${date.getFullYear()}年${(date.getMonth() + 1).toString().padStart(2, '0')}月`;
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '指数'
                    }
                }
            },
            elements: {
                point: {
                    radius: 4,
                    hoverRadius: 6,
                    borderWidth: 2,
                    hoverBorderWidth: 3
                },
                line: {
                    borderWidth: 3,
                    tension: 0.1
                }
            }
        }
        });
        
        console.log('图表对象创建成功:', chart);
        
    } catch (error) {
        console.error('创建图表时发生错误:', error);
    }
}

// 获取当前选择的数据类型（用于新API）
function getCurrentDataType() {
    const contentType = document.querySelector('input[name="content-type"]:checked').value;
    
    if (contentType.includes('classified')) {
        const areaType = document.querySelector('input[name="area-type"]:checked').value;
        return `${contentType}_${areaType}`;
    } else {
        return contentType;
    }
}

// 获取当前选择的数据文件名（备用方法）
function getCurrentDataFile() {
    const contentType = document.querySelector('input[name="content-type"]:checked').value;
    
    if (contentType.includes('classified')) {
        const areaType = document.querySelector('input[name="area-type"]:checked').value;
        return DATA_FILES[contentType][areaType];
    } else {
        return DATA_FILES[contentType];
    }
}

// 获取当前选中的城市
function getSelectedCity() {
    const selectedRadio = document.querySelector('input[name="city"]:checked');
    return selectedRadio ? selectedRadio.value : null;
}

// 更新图表
async function updateChart() {
    console.log('updateChart 函数被调用');
    
    const selectedCity = getSelectedCity();
    console.log('选中的城市:', selectedCity);
    
    if (!selectedCity) {
        console.log('未选择城市，显示提示信息');
        // 更新图表标题为提示信息，但保持图表框架显示
        chart.options.plugins.title.text = '请选择城市查看房价指数变化趋势';
        chart.data.datasets = [];
        chart.update();
        // 隐藏统计信息，但保持图表可见
        statsSection.style.display = 'none';
        hideLoading();
        return;
    }

    console.log('显示加载状态');
    showLoading();
    
    try {
        const dataType = getCurrentDataType();
        console.log('数据类型:', dataType);
        
        const response = await fetchCityData(selectedCity, dataType);
        console.log('获取到城市数据响应');
        
        const cityData = response.city_data;
        console.log('城市数据:', cityData ? `找到，状态: ${cityData.status}` : '未找到');
        console.log('完整响应数据:', response);
        
        if (!cityData || cityData.status !== 'success') {
            console.log('城市数据状态无效:', cityData?.status);
            hideLoading();
            showNoData('该城市暂无数据');
            return;
        }
        
        // 检查数据源
        const hasRawData = cityData.raw_data && cityData.raw_data.length > 0;
        const hasCorrectedData = cityData.corrected_result && cityData.corrected_result.length > 0;
        
        console.log('数据源检查:', {
            hasRawData,
            hasCorrectedData,
            rawDataLength: cityData.raw_data?.length || 0,
            correctedDataLength: cityData.corrected_result?.length || 0
        });
        
        if (!hasRawData && !hasCorrectedData) {
            console.log('没有可用的数据源');
            hideLoading();
            showNoData('该城市暂无数据');
            return;
        }

        console.log('开始渲染图表和统计信息');
        console.log(`🏙️ 选择城市: ${selectedCity}`);
        console.log(`📋 数据类型: ${dataType}`);
        console.log(`📊 城市数据状态: ${cityData.status}`);
        console.log(`📅 数据时间范围: ${cityData.time_range?.start} - ${cityData.time_range?.end}`);
        console.log(`🔢 数据记录数: ${cityData.data_count}`);
        
        currentData = cityData;
        renderChart(cityData);
        updateStats(cityData);
        hideLoading();
        console.log('✅ 图表更新完成');
        
    } catch (error) {
        console.error('数据加载失败:', error);
        hideLoading();
        showNoData('数据加载失败，请稍后重试');
    }
}

// 获取数据 - 使用轻量级单城市API
async function fetchCityData(cityName, dataType) {
    console.log(`请求城市数据: ${cityName} - ${dataType}`);
    const url = `/api/city/${encodeURIComponent(cityName)}/${dataType}`;
    console.log(`请求URL: ${url}`);
    
    const response = await fetch(url);
    console.log(`响应状态: ${response.status} ${response.statusText}`);
    
    if (!response.ok) {
        const errorText = await response.text();
        console.error(`HTTP错误详情:`, errorText);
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorText}`);
    }
    
    const data = await response.json();
    console.log(`成功获取城市数据: ${cityName}, 响应大小: ${JSON.stringify(data).length} 字符`);
    console.log('响应数据结构:', Object.keys(data));
    
    return data;
}

// 获取完整数据（备用方法）
async function fetchData(fileName) {
    console.log(`请求完整数据文件: ${fileName}`);
    const response = await fetch(`/api/data/${fileName}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log(`成功获取完整数据, 城市数量: ${data.cities?.length || 0}`);
    return data;
}

// 渲染图表
function renderChart(cityData) {
    console.log('renderChart 开始，城市:', cityData.city);
    
    if (!chart) {
        console.error('chart 对象未初始化');
        showNoData('图表初始化失败');
        return;
    }
    
    try {
        console.log('渲染实际价格指数图表');

        // 优先使用corrected_result数据，如果没有则使用raw_data
        let sourceData;
        let dataSource;
        if (cityData.corrected_result && cityData.corrected_result.length > 0) {
            sourceData = cityData.corrected_result;
            dataSource = 'corrected_result';
            console.log('使用矫正后数据 (corrected_result), 数据量:', sourceData.length);
        } else if (cityData.raw_data && cityData.raw_data.length > 0) {
            sourceData = cityData.raw_data;
            dataSource = 'raw_data';
            console.log('使用原始数据 (raw_data), 数据量:', sourceData.length);
        } else {
            console.error('没有可用的数据源');
            showNoData('该城市暂无可用数据');
            return;
        }
        
        console.log('数据源示例:', sourceData.slice(0, 2));

        // 过滤从2020年11月开始的数据并按时间排序
        const filteredData = sourceData.filter(item => {
            const dateStr = item.date;
            if (!dateStr) return false;
            
            // 解析日期格式 YYYY-MM
            const [year, month] = dateStr.split('-').map(Number);
            const itemDate = new Date(year, month - 1, 1); // month-1 because Date months are 0-indexed
            const startDate = new Date(2020, 10, 1); // 2020年11月
            
            return itemDate >= startDate;
        });
        
        const sortedData = filteredData.sort((a, b) => {
            const [yearA, monthA] = a.date.split('-').map(Number);
            const [yearB, monthB] = b.date.split('-').map(Number);
            const dateA = new Date(yearA, monthA - 1, 1);
            const dateB = new Date(yearB, monthB - 1, 1);
            return dateA - dateB;
        });
        
        // 测试日期解析
        if (sortedData.length > 0) {
            const firstItem = sortedData[0];
            console.log('第一个数据项:', firstItem);
            console.log('日期字段:', firstItem.date);
            
            const [year, month] = firstItem.date.split('-');
            console.log('解析结果:', { year: parseInt(year), month: parseInt(month) });
            
            const testDate = new Date(parseInt(year), parseInt(month) - 1, 1);
            console.log('创建的Date对象:', testDate);
            console.log('时间戳:', testDate.getTime());
        }

        console.log('数据排序完成，数据点数量:', sortedData.length);
        console.log('时间范围:', sortedData[0]?.date, '到', sortedData[sortedData.length-1]?.date);
        console.log('数据源:', dataSource);
        
        // 输出actual_value数据
        console.log('='.repeat(80));
        console.log(`📊 ${cityData.city} - actual_value 数据详情:`);
        console.log('='.repeat(80));
        
        const actualValueData = sortedData.map(item => ({
            date: item.date,
            actual_value: item.actual_value,
            month_on_month: item.month_on_month,
            year_on_year: item.year_on_year,
            growth_rate: item.growth_rate
        }));
        
        console.table(actualValueData);
        
        console.log('📈 actual_value 统计信息:');
        const actualValues = sortedData.map(item => item.actual_value).filter(v => v !== undefined && v !== null);
        if (actualValues.length > 0) {
            console.log(`- 数据点数量: ${actualValues.length}`);
            console.log(`- 最小值: ${Math.min(...actualValues).toFixed(4)}`);
            console.log(`- 最大值: ${Math.max(...actualValues).toFixed(4)}`);
            console.log(`- 最新值: ${actualValues[actualValues.length - 1].toFixed(4)}`);
            console.log(`- 总增长: ${((actualValues[actualValues.length - 1] - 100)).toFixed(4)} (${((actualValues[actualValues.length - 1] - 100)).toFixed(2)}%)`);
        }
        console.log('='.repeat(80));

        const datasets = [];
        
        // 主要数据：实际价格指数 (actual_value)
        if (sortedData[0] && 'actual_value' in sortedData[0]) {
            const actualValueData = sortedData.map(item => {
                try {
                    // 处理日期格式：从"2020-11"转换为Date对象
                    const [year, month] = item.date.split('-');
                    const yearNum = parseInt(year);
                    const monthNum = parseInt(month);
                    
                    if (isNaN(yearNum) || isNaN(monthNum) || monthNum < 1 || monthNum > 12) {
                        console.error('无效的日期格式:', item.date);
                        return null;
                    }
                    
                    const dateObj = new Date(yearNum, monthNum - 1, 1); // month-1因为Date的月份从0开始
                    
                    if (isNaN(dateObj.getTime())) {
                        console.error('无法创建有效的Date对象:', item.date);
                        return null;
                    }
                    
                    return {
                        x: dateObj.getTime(), // 使用时间戳避免格式问题
                        y: item.actual_value || 100,
                        rawData: item // 保存原始数据用于tooltip
                    };
                } catch (error) {
                    console.error('日期处理错误:', error, '数据项:', item);
                    return null;
                }
            }).filter(item => item !== null); // 过滤掉无效的数据项
            
            datasets.push({
                label: '实际价格指数',
                data: actualValueData,
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                pointBackgroundColor: '#28a745',
                pointBorderColor: '#ffffff',
                fill: false,
                tension: 0.1,
                borderWidth: 3
            });
            
            console.log('添加实际价格指数数据集，数据点:', actualValueData.length);
        } else {
            // 如果没有actual_value，使用raw_data创建基础显示
            const rawValueData = sortedData.map(item => {
                try {
                    // 处理日期格式：从"2020-11"转换为Date对象
                    const [year, month] = item.date.split('-');
                    const yearNum = parseInt(year);
                    const monthNum = parseInt(month);
                    
                    if (isNaN(yearNum) || isNaN(monthNum) || monthNum < 1 || monthNum > 12) {
                        console.error('无效的日期格式:', item.date);
                        return null;
                    }
                    
                    const dateObj = new Date(yearNum, monthNum - 1, 1); // month-1因为Date的月份从0开始
                    
                    if (isNaN(dateObj.getTime())) {
                        console.error('无法创建有效的Date对象:', item.date);
                        return null;
                    }
                    
                    return {
                        x: dateObj.getTime(), // 使用时间戳避免格式问题
                        y: item.month_on_month || 100,
                        rawData: item
                    };
                } catch (error) {
                    console.error('日期处理错误:', error, '数据项:', item);
                    return null;
                }
            }).filter(item => item !== null); // 过滤掉无效的数据项
            
            datasets.push({
                label: '环比指数',
                data: rawValueData,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#ffffff',
                fill: false,
                tension: 0.1,
                borderWidth: 3
            });
            
            console.log('使用环比指数作为主要数据，数据点:', rawValueData.length);
        }

        console.log('准备更新图表，数据集数量:', datasets.length);
        console.log('数据集详情:', datasets.map(d => `${d.label}: ${d.data.length}个点`));
        
        chart.data.datasets = datasets;
        
        // 更新图表标题
        const contentTypeText = document.querySelector('input[name="content-type"]:checked').nextElementSibling.textContent;
        const areaTypeText = document.querySelector('input[name="content-type"]:checked').value.includes('classified') ?
            ' - ' + document.querySelector('input[name="area-type"]:checked').nextElementSibling.textContent : '';
        
        const newTitle = `${cityData.city} ${contentTypeText}${areaTypeText}`;
        console.log('更新图表标题为:', newTitle);
        
        chart.options.plugins.title.text = newTitle;
    
        console.log('调用 chart.update()');
        chart.update();
        console.log('chart.update() 完成');
        
    } catch (error) {
        console.error('渲染图表时发生错误:', error);
        showNoData('图表渲染失败: ' + error.message);
    }
}

// 更新统计信息
function updateStats(cityData) {
    // 优先使用corrected_result数据，如果没有则使用raw_data
    let sourceData;
    if (cityData.corrected_result && cityData.corrected_result.length > 0) {
        sourceData = cityData.corrected_result;
    } else {
        sourceData = cityData.raw_data;
    }
    
    const monthOnMonthValues = sourceData.map(item => item.month_on_month).filter(v => v !== null);
    const yearOnYearValues = sourceData.map(item => item.year_on_year).filter(v => v !== null);
    const actualValues = sourceData.map(item => item.actual_value).filter(v => v !== null && v !== undefined);
    
    document.getElementById('dataCount').textContent = cityData.data_count;
    document.getElementById('timeRange').textContent = `${cityData.time_range.start} 至 ${cityData.time_range.end}`;
    document.getElementById('monthMax').textContent = monthOnMonthValues.length ? Math.max(...monthOnMonthValues).toFixed(1) : '-';
    document.getElementById('monthMin').textContent = monthOnMonthValues.length ? Math.min(...monthOnMonthValues).toFixed(1) : '-';
    document.getElementById('yearMax').textContent = yearOnYearValues.length ? Math.max(...yearOnYearValues).toFixed(1) : '-';
    document.getElementById('yearMin').textContent = yearOnYearValues.length ? Math.min(...yearOnYearValues).toFixed(1) : '-';
    
    // 如果有实际价格指数数据，显示额外的统计信息
    if (actualValues.length > 0) {
        const actualMax = Math.max(...actualValues);
        const actualMin = Math.min(...actualValues);
        const actualLatest = actualValues[actualValues.length - 1];
        const totalGrowth = ((actualLatest - 100) / 100 * 100);
        
        console.log(`实际价格指数统计 - 范围: ${actualMin.toFixed(2)} - ${actualMax.toFixed(2)}, 最新: ${actualLatest.toFixed(2)}, 总增长: ${totalGrowth.toFixed(2)}%`);
    }
    
    statsSection.style.display = 'block';
}

// 显示加载状态
function showLoading() {
    loading.style.display = 'flex';
    noData.style.display = 'none';
    statsSection.style.display = 'none';
    if (chart) {
        chart.options.plugins.title.text = '正在加载数据...';
        chart.data.datasets = [];
        chart.update();
    }
}

// 隐藏加载状态
function hideLoading() {
    loading.style.display = 'none';
}

// 显示无数据状态
function showNoData(message = '请选择城市以查看数据') {
    loading.style.display = 'none';
    noData.style.display = 'none'; // 不显示noData提示，而是在图表标题中显示
    statsSection.style.display = 'none';
    if (chart) {
        chart.options.plugins.title.text = message;
        chart.data.datasets = [];
        chart.update();
    }
}

// 导出功能（可选）
function exportChart() {
    if (chart && currentData) {
        const link = document.createElement('a');
        link.download = `${currentData.city}_房价指数图表.png`;
        link.href = chart.toBase64Image();
        link.click();
    }
}

// 添加导出按钮事件（如果需要的话）
// document.getElementById('exportBtn')?.addEventListener('click', exportChart);
