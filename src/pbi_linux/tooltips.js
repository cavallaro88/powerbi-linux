// SPDX-License-Identifier: GPL-3.0-or-later
// Keep browser title tips inside WebView. Power BI's rich data tips are untouched.
(function installTooltips(win) {
    'use strict';
    const doc = win.document;
    if (doc.documentElement.hasAttribute('data-pbi-linux-tooltips')) return;
    if (typeof win.HTMLElement.prototype.showPopover !== 'function') return;
    doc.documentElement.setAttribute('data-pbi-linux-tooltips', '1');
    const tip = doc.createElement('div');
    tip.id = 'pbi-linux-tip-' + Math.random().toString(36).slice(2);
    tip.setAttribute('data-pbi-linux-tooltip', '');
    tip.setAttribute('popover', 'manual');
    tip.setAttribute('role', 'tooltip');
    tip.style.cssText = 'position:fixed;inset:auto;margin:0;box-sizing:border-box;' +
        'max-width:calc(100vw - 16px);max-height:calc(100vh - 16px);' +
        'padding:6px 9px;border:1px solid var(--colorNeutralStroke1,GrayText);' +
        'border-radius:3px;background:var(--colorNeutralBackground1,Canvas);' +
        'color:var(--colorNeutralForeground1,CanvasText);font:12px/1.4 Segoe UI,sans-serif;' +
        'white-space:pre-wrap;overflow-wrap:anywhere;overflow:hidden;' +
        'pointer-events:none;user-select:none;direction:inherit;';
    doc.documentElement.appendChild(tip);
    let target = null, timer = null, dismissed = false, x = 0, y = 0;
    const attributes = new Map(), texts = new Map(), labels = new Map();
    let described = null;
    const parent = el => el.parentElement || el.getRootNode().host;
    function hide() {
        win.clearTimeout(timer);
        if (tip.matches(':popover-open')) tip.hidePopover();
        if (described) {
            const tokens = (described.getAttribute('aria-describedby') || '').split(/\s+/).filter(t => t && t !== tip.id);
            if (tokens.length) described.setAttribute('aria-describedby', tokens.join(' '));
            else described.removeAttribute('aria-describedby');
            described = null;
        }
    }
    function restore() {
        changed(observer.takeRecords());
        observer.disconnect();
        hide();
        for (const [el, value] of attributes) {
            if (el.getAttribute('title') === '') el.setAttribute('title', value);
        }
        for (const [node, value] of texts) if (node.data === '') node.data = value;
        for (const [el, value] of labels) {
            if (el.getAttribute('aria-label') === value) el.removeAttribute('aria-label');
        }
        attributes.clear(); texts.clear(); labels.clear(); target = null;
    }
    function show(value, owner) {
        if (!target || !target.isConnected || dismissed || !value.trim()) return;
        // Prefer an existing application tooltip over a second plain title tip.
        if (Array.from(doc.querySelectorAll('[role="tooltip"]')).some(el => {
            if (el === tip || !el.textContent.trim()) return false;
            const r = el.getBoundingClientRect(), style = win.getComputedStyle(el);
            return r.width > 2 && r.height > 2 && style.visibility !== 'hidden' && style.opacity !== '0';
        })) return;
        tip.textContent = value;
        tip.style.left = '8px'; tip.style.top = '8px';
        tip.showPopover();
        const r = tip.getBoundingClientRect();
        const left = Math.max(8, Math.min(x + 12, win.innerWidth - r.width - 8));
        const top = y + 20 + r.height < win.innerHeight - 8 ? y + 20 : y - r.height - 8;
        tip.style.left = left + 'px'; tip.style.top = Math.max(8, top) + 'px';
        const tokens = (owner.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
        if (!tokens.includes(tip.id)) tokens.push(tip.id);
        owner.setAttribute('aria-describedby', tokens.join(' '));
        described = owner;
    }
    function prepare() {
        observer.disconnect();
        hide();
        let value = null, owner = target;
        for (let el = target; el; el = parent(el)) {
            if (el.hasAttribute('title')) {
                if (!attributes.has(el) || el.getAttribute('title') !== '') attributes.set(el, el.getAttribute('title'));
                if (value === null) { value = attributes.get(el); owner = el; }
                el.setAttribute('title', '');
            }
            if (el.namespaceURI === 'http://www.w3.org/2000/svg') {
                const title = Array.from(el.children).find(c => c.localName === 'title');
                if (title) {
                    const walker = doc.createTreeWalker(title, win.NodeFilter.SHOW_TEXT);
                    let node, text = '';
                    while ((node = walker.nextNode())) {
                        if (!texts.has(node) || node.data !== '') texts.set(node, node.data);
                        text += texts.get(node); node.data = '';
                    }
                    if (value === null) { value = text; owner = el; }
                    observer.observe(title, {characterData:true, childList:true, subtree:true});
                }
            }
            observer.observe(el, {attributes:true, attributeFilter:['title']});
        }
        // Retain title-derived names for icon-only controls and SVG graphics.
        if (labels.has(owner) && owner.getAttribute('aria-label') === labels.get(owner)) {
            owner.setAttribute('aria-label', value || ''); labels.set(owner, value || '');
        } else if (value && !owner.hasAttribute('aria-label') && !owner.hasAttribute('aria-labelledby') &&
                (!owner.textContent.trim() || owner.namespaceURI === 'http://www.w3.org/2000/svg')) {
            owner.setAttribute('aria-label', value); labels.set(owner, value);
        }
        timer = win.setTimeout(() => show(value || '', owner), 500);
    }
    function changed(records) {
        for (const record of records) {
            if (record.type === 'attributes') {
                if (record.target.hasAttribute('title')) attributes.set(record.target, record.target.getAttribute('title'));
                else attributes.delete(record.target);
            } else if (record.type === 'characterData') texts.set(record.target, record.target.data);
        }
    }
    const observer = new win.MutationObserver(records => {
        changed(records);
        if (target) prepare();
    });
    function enter(el, px, py) {
        if (!(el instanceof win.Element) || el === tip) return;
        x = px; y = py;
        if (target === el) return;
        restore(); target = el; dismissed = false; prepare();
    }
    function mouse(e) {
        if (!e.buttons && (!e.sourceCapabilities || !e.sourceCapabilities.firesTouchEvents)) enter(e.composedPath()[0], e.clientX, e.clientY);
    }
    // Desktop disables PointerEvent; use its supported mouse-event path.
    doc.addEventListener('mouseover', mouse, true);
    doc.addEventListener('mousemove', mouse, true);
    doc.addEventListener('mouseout', e => { if (!e.relatedTarget) restore(); }, true);
    doc.addEventListener('focusin', e => {
        const r = e.target.getBoundingClientRect(); enter(e.target, r.left, r.bottom);
    }, true);
    doc.addEventListener('focusout', restore, true);
    const dismiss = () => { dismissed = true; hide(); };
    doc.addEventListener('mousedown', dismiss, true);
    doc.addEventListener('keydown', e => { if (e.key === 'Escape') dismiss(); }, true);
    doc.addEventListener('scroll', dismiss, true);
    win.addEventListener('resize', dismiss);
    win.addEventListener('blur', restore);
    // Same-origin visual frames get their own viewport and event listeners.
    const frames = new WeakSet();
    function frame(el) {
        if (frames.has(el)) return;
        frames.add(el);
        const load = () => { try { installTooltips(el.contentWindow); } catch (_) { /* Cross-origin frame. */ } };
        el.addEventListener('load', load); load();
    }
    function scan(node) {
        if (!(node instanceof win.Element)) return;
        if (node.localName === 'iframe') frame(node);
        for (const el of node.querySelectorAll('iframe')) frame(el);
    }
    scan(doc.documentElement);
    new win.MutationObserver(records => {
        if (target && !target.isConnected) restore();
        for (const record of records) for (const node of record.addedNodes) scan(node);
    }).observe(doc.documentElement, {childList:true, subtree:true});
})(window);
