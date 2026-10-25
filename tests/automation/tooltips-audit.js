// SPDX-License-Identifier: GPL-3.0-or-later
// Run only in a disposable diagnostic document with tooltips.js installed.
(async function () {
    const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
    const checks = [];
    function check(name, result) { if (!result) throw new Error(name); checks.push(name); }
    const panel = document.createElement('div');
    panel.style.cssText = 'position:fixed;left:100px;top:200px;width:400px;z-index:100000;';
    panel.innerHTML = '<button id="pbi-tip-test" title="Detalhe &lt;b&gt;literal&lt;/b&gt;">Teste</button>' +
        '<div title="Ancestral"><span id="pbi-tip-child">Texto</span><span id="pbi-tip-empty" title="">Sem dica</span></div>' +
        '<svg width="200" height="50"><g id="pbi-tip-svg" aria-labelledby="pbi-tip-svg-title"><title id="pbi-tip-svg-title">Produto A: 42</title><rect width="50" height="30"/></g></svg>' +
        '<div id="pbi-tip-rich" role="tooltip" hidden><table><tr><td>Produto A</td><td>42</td></tr></table></div>';
    document.body.appendChild(panel);
    const button = panel.querySelector('button');
    const tip = document.querySelector('[data-pbi-linux-tooltip]');
    function event(el, type, fields = {}) {
        const e = el.ownerDocument.createEvent('Event'); e.initEvent(type, true, false);
        for (const [key,value] of Object.entries(fields)) Object.defineProperty(e,key,{value});
        el.dispatchEvent(e);
    }
    const enter = (el, x = 150, y = 230) => event(el,'mouseover',{pointerType:'mouse',clientX:x,clientY:y});
    const leave = el => event(el,'mouseout',{pointerType:'mouse',relatedTarget:null});
    try {
        const rich = panel.querySelector('#pbi-tip-rich'), richBefore = rich.outerHTML;
        enter(button); await wait(550);
        check('HTML title has no native text while hovered', button.getAttribute('title') === '');
        check('In-page text is visible and never parsed as HTML', tip.matches(':popover-open') && tip.textContent === 'Detalhe <b>literal</b>' && !tip.querySelector('b'));
        check('Existing rich visual tooltip is unchanged', rich.outerHTML === richBefore);
        check('Tooltip description linked to original control', button.getAttribute('aria-describedby').split(' ').includes(tip.id));
        let escaped = 0;
        const key = e => { if (e.key === 'Escape') escaped++; };
        button.addEventListener('keydown', key);
        event(button,'keydown',{key:'Escape'});
        check('Escape dismisses without swallowing application keys', !tip.matches(':popover-open') && escaped === 1);
        let clicks = 0; button.onclick = () => clicks++; button.click();
        check('Original control click still works', clicks === 1);
        leave(button);
        check('Original title and description restored on leave', button.title === 'Detalhe <b>literal</b>' && !button.hasAttribute('aria-describedby'));
        rich.hidden = false;
        const visibleRich = rich.outerHTML;
        enter(button); await wait(550);
        check('Visible rich visual tooltip is preferred without mutation or duplicate', !tip.matches(':popover-open') && rich.outerHTML === visibleRich);
        leave(button); rich.hidden = true;
        const child = panel.querySelector('#pbi-tip-child');
        enter(child); await wait(550);
        check('Inherited title displayed and suppressed natively', tip.textContent === 'Ancestral' && child.parentElement.title === '');
        leave(child);
        const empty = panel.querySelector('#pbi-tip-empty');
        enter(empty); await wait(550);
        check('Explicit empty title blocks ancestor hint', !tip.matches(':popover-open'));
        leave(empty);
        enter(button); button.title = 'Atualizado'; await wait(600);
        check('Dynamically updated title displays current value', button.title === '' && tip.textContent === 'Atualizado' && tip.matches(':popover-open'));
        leave(button);
        check('Dynamic title survives restoration', button.title === 'Atualizado');
        enter(button); button.title = ''; leave(button);
        check('Immediate application title clearing is not overwritten on leave', button.hasAttribute('title') && button.title === '');
        button.title = 'Restaurado';
        enter(button); button.removeAttribute('title'); await wait(600); leave(button);
        check('Application title removal is preserved', !button.hasAttribute('title'));
        const svg = panel.querySelector('#pbi-tip-svg'), title = panel.querySelector('title'), text = title.firstChild;
        enter(svg.querySelector('rect')); await wait(550);
        check('SVG visual title displays in page', tip.textContent === 'Produto A: 42' && tip.matches(':popover-open') && title.textContent === '');
        leave(svg);
        check('SVG title node, value and accessible reference restored', title.firstChild === text && text.data === 'Produto A: 42' && svg.getAttribute('aria-labelledby') === title.id);
        button.title = 'Borda'; enter(button,innerWidth-1,innerHeight-1); await wait(550);
        const r = tip.getBoundingClientRect();
        check('Tooltip fits right and bottom viewport edges', r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight);
        leave(button);
        event(button,'focusin'); await wait(550);
        check('Keyboard focus displays description', tip.matches(':popover-open') && tip.textContent === 'Borda');
        event(button,'focusout');
        const iframe = document.createElement('iframe');
        iframe.srcdoc = '<button title="Dica do visual">Visual</button>';
        panel.appendChild(iframe);
        for (let i=0;i<30 && !iframe.contentDocument?.documentElement.hasAttribute('data-pbi-linux-tooltips');i++) await wait(50);
        const b = iframe.contentDocument.querySelector('button');
        event(b,'mouseover',{pointerType:'mouse',clientX:25,clientY:25});
        await wait(550);
        const frameTip = iframe.contentDocument.querySelector('[data-pbi-linux-tooltip]');
        check('Same-origin visual frame has independent in-page tooltip', b.title === '' && frameTip.matches(':popover-open') && frameTip.textContent === 'Dica do visual');
        enter(button); await wait(550); button.remove(); await wait(50);
        check('Removed hover target cannot leave stale tooltip', !tip.matches(':popover-open'));
        return {passed:true, checks, scope:'DOM interaction in the pinned WebView2; separate native/compositor and real visual checks required'};
    } finally { leave(panel); panel.remove(); }
})();
