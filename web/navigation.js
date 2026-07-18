(() => {
    const categories = [
        { key: 'price', label: '房价', href: '/' },
        { key: 'retail', label: '社零', href: '/retail.html' },
        { key: 'industry', label: '工业企业', href: '/industry.html' },
        { key: 'assets', label: '关注资产价格', href: '/assets.html' },
        { key: 'asset-returns', label: '资产收益', href: '/asset-returns.html' },
        { key: 'cycles', label: '经济周期', href: '/cycles.html' },
    ];

    function getActiveCategory() {
        const path = window.location.pathname;
        if (path.endsWith('/retail.html')) return 'retail';
        if (path.endsWith('/industry.html')) return 'industry';
        if (path.endsWith('/assets.html')) return 'assets';
        if (path.endsWith('/asset-returns.html')) return 'asset-returns';
        if (path.endsWith('/cycles.html')) return 'cycles';
        return 'price';
    }

    function renderCategoryNav() {
        const container = document.querySelector('[data-category-nav]');
        if (!container) return;

        const activeCategory = getActiveCategory();
        const nav = document.createElement('nav');
        nav.className = 'category-nav';
        nav.setAttribute('aria-label', '数据分类');

        categories.forEach(category => {
            const link = document.createElement('a');
            link.className = 'category-tab';
            link.href = category.href;
            link.textContent = category.label;

            if (category.key === activeCategory) {
                link.classList.add('active');
                link.setAttribute('aria-current', 'page');
            }

            nav.appendChild(link);
        });

        container.replaceChildren(nav);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderCategoryNav);
    } else {
        renderCategoryNav();
    }
})();
