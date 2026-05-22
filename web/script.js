const cursorGlow = document.getElementById('cursor-glow');
let cursorRaf = null;
let mx = -9999, my = -9999;

document.addEventListener('mousemove', (e) => {
  mx = e.clientX; my = e.clientY;
  if (!cursorRaf) {
    cursorRaf = requestAnimationFrame(() => {
      cursorGlow.style.left = mx + 'px';
      cursorGlow.style.top  = my + 'px';
      cursorRaf = null;
    });
  }
});

document.addEventListener('mouseover', (e) => {
  const t = e.target.closest('.glass-panel, .btn, .nav-links li, .toggle');
  if (t) {
    cursorGlow.style.background = 'radial-gradient(circle, rgba(139,92,246,0.10) 0%, rgba(139,92,246,0.035) 35%, transparent 70%)';
  } else {
    cursorGlow.style.background = 'radial-gradient(circle, rgba(139,92,246,0.06) 0%, rgba(139,92,246,0.022) 35%, transparent 70%)';
  }
});

const navItems   = document.querySelectorAll('.nav-links li');
const tabSections = document.querySelectorAll('.tab-content');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        navItems.forEach(n => n.classList.remove('active'));
        tabSections.forEach(s => s.classList.remove('active'));
        item.classList.add('active');
        document.getElementById(item.dataset.target).classList.add('active');
    });
});

const threadsSlider = document.getElementById('threads-slider');
const threadsVal    = document.getElementById('threads-val');
threadsSlider.addEventListener('input', () => {
    const val = threadsSlider.value;
    threadsVal.textContent = val;
    eel.api_update_threads(parseInt(val))();
});

const stopAfterEntry = document.getElementById('stop-after-entry');
const stopAfterVal   = document.getElementById('stop-after-val');
stopAfterEntry.addEventListener('input', () => {
    stopAfterVal.textContent = stopAfterEntry.value;
});

const authMode    = document.getElementById('auth-mode');
const userBox     = document.getElementById('user-settings-box');
const passBox     = document.getElementById('pass-settings-box');

function applyAuthMode(mode) {
    userBox.style.display = (mode === 'password') ? 'none' : 'block';
    passBox.style.display = (mode === 'username') ? 'none' : 'block';
}

authMode.addEventListener('change', () => applyAuthMode(authMode.value));
applyAuthMode(authMode.value);

const consoleOut = document.getElementById('console-output');

function sanitize(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

eel.expose(update_console);
function update_console(msg, type = 'system') {
    const div = document.createElement('div');
    div.className = `log-entry ${type}`;
    div.innerHTML = sanitize(msg);
    consoleOut.appendChild(div);
    consoleOut.scrollTop = consoleOut.scrollHeight;
}

function get_config() {
    return {
        target_url:       document.getElementById('target-url').value.trim(),
        session_name:     document.getElementById('session-name').value.trim(),
        auth_mode:        authMode.value,
        threads:          parseInt(threadsSlider.value),
        stealth:          document.getElementById('stealth-mode').checked,
        auto_spoof:       document.getElementById('auto-spoof').checked,
        telegram_token:   document.getElementById('tg-token').value.trim(),
        telegram_chat:    document.getElementById('tg-chat').value.trim(),
        stop_after:       parseInt(stopAfterEntry.value) || 1,

        user_field:       document.getElementById('user-field').value.trim(),
        user_static_val:  document.getElementById('user-static').value.trim(),
        user_char_type:   document.getElementById('user-char').value,
        user_min_len:     parseInt(document.getElementById('user-min').value),
        user_max_len:     parseInt(document.getElementById('user-max').value),
        user_start:       document.getElementById('user-start').value.trim(),
        user_contains:    document.getElementById('user-contains').value.trim(),
        user_end:         document.getElementById('user-end').value.trim(),

        pass_field:       document.getElementById('pass-field').value.trim(),
        pass_static_val:  document.getElementById('pass-static').value.trim(),
        pass_char_type:   document.getElementById('pass-char').value,
        pass_min_len:     parseInt(document.getElementById('pass-min').value),
        pass_max_len:     parseInt(document.getElementById('pass-max').value),
        pass_start:       document.getElementById('pass-start').value.trim(),
        pass_contains:    document.getElementById('pass-contains').value.trim(),
        pass_end:         document.getElementById('pass-end').value.trim(),

        analytic_mode:    document.getElementById('enable-learning').checked,
        manual_samples:   document.getElementById('manual-samples').value,
    };
}

function fill_config(cfg) {
    if (!cfg) return;
    const s = (id, v) => { const el = document.getElementById(id); if (el && v !== undefined) el.value = v; };
    const c = (id, v) => { const el = document.getElementById(id); if (el && v !== undefined) el.checked = v; };

    s('target-url',   cfg.target_url);
    s('session-name', cfg.session_name);
    s('auth-mode',    cfg.auth_mode);
    s('tg-token',     cfg.telegram_token);
    s('tg-chat',      cfg.telegram_chat);
    c('stealth-mode', cfg.stealth);
    c('auto-spoof',   cfg.auto_spoof);
    c('enable-learning', cfg.analytic_mode);
    s('manual-samples', cfg.manual_samples);

    if (cfg.threads) { threadsSlider.value = cfg.threads; threadsVal.textContent = cfg.threads; }
    if (cfg.stop_after) { stopAfterEntry.value = cfg.stop_after; stopAfterVal.textContent = cfg.stop_after; }

    s('user-field',   cfg.user_field);
    s('user-static',  cfg.user_static_val);
    s('user-char',    cfg.user_char_type);
    s('user-min',     cfg.user_min_len);
    s('user-max',     cfg.user_max_len);
    s('user-start',   cfg.user_start || '');
    s('user-contains', cfg.user_contains || '');
    s('user-end',     cfg.user_end || '');

    s('pass-field',   cfg.pass_field);
    s('pass-static',  cfg.pass_static_val);
    s('pass-char',    cfg.pass_char_type);
    s('pass-min',     cfg.pass_min_len);
    s('pass-max',     cfg.pass_max_len);
    s('pass-start',   cfg.pass_start || '');
    s('pass-contains', cfg.pass_contains || '');
    s('pass-end',     cfg.pass_end || '');

    applyAuthMode(authMode.value);
}

function autoSaveConfig() {
    try {
        const cfg = get_config();
        eel.api_auto_save_config(cfg)();
    } catch(e) {}
}

document.addEventListener('input',  autoSaveConfig);
document.addEventListener('change', autoSaveConfig);

const btnStart  = document.getElementById('btn-start');
const btnPause  = document.getElementById('btn-pause');
const btnStop   = document.getElementById('btn-stop');
const statusBadge = document.getElementById('status-badge');

let statsInterval = null;
let lastStats = { tried: 0, valid: 0, errors: 0, elapsed: 0, rps: 0 };

function formatElapsed(secs) {
    const m = String(Math.floor(secs / 60)).padStart(2, '0');
    const s = String(Math.floor(secs % 60)).padStart(2, '0');
    return `${m}:${s}`;
}

function animatePulse(element) {
    element.classList.remove('pulse');
    void element.offsetWidth;
    element.classList.add('pulse');
    setTimeout(() => element.classList.remove('pulse'), 500);
}

function startStatsTicker() {
    if (statsInterval) return;
    statsInterval = setInterval(async () => {
        const s = await eel.api_get_stats()();
        if (!s) return;
        
        const triedEl = document.getElementById('stat-tried');
        if (s.tried !== lastStats.tried) {
            triedEl.textContent = s.tried.toLocaleString();
            animatePulse(triedEl);
        }
        
        const validEl = document.getElementById('stat-valid');
        if (s.valid !== lastStats.valid) {
            validEl.textContent = s.valid;
            animatePulse(validEl);
        }
        
        const errorsEl = document.getElementById('stat-errors');
        if (s.errors !== lastStats.errors) {
            errorsEl.textContent = s.errors || 0;
            animatePulse(errorsEl);
        }
        
        const rpsEl = document.getElementById('stat-rps');
        if (s.rps !== lastStats.rps) {
            rpsEl.textContent = s.rps;
            animatePulse(rpsEl);
        }
        
        const elapsedEl = document.getElementById('stat-elapsed');
        if (s.elapsed !== lastStats.elapsed) {
            elapsedEl.textContent = formatElapsed(s.elapsed);
        }
        
        const successRate = s.tried > 0 ? (s.valid / s.tried * 100).toFixed(1) : 0;
        const rateEl = document.getElementById('stat-success-rate');
        rateEl.innerHTML = `${successRate}<span style="font-size:0.7em">%</span>`;
        
        lastStats = { ...s };
    }, 1000);
}

function stopStatsTicker() {
    clearInterval(statsInterval);
    statsInterval = null;
}

function setRunningState(running) {
    btnStart.disabled = running;
    btnPause.disabled = !running;
    btnStop.disabled  = !running;
    if (running) {
        statusBadge.textContent = 'Running';
        statusBadge.classList.add('active');
        startStatsTicker();
    } else {
        statusBadge.textContent = 'Idle';
        statusBadge.classList.remove('active');
        btnPause.textContent = '⏸ Pause';
        stopStatsTicker();
    }
}

btnStart.addEventListener('click', async () => {
    const cfg = get_config();
    setRunningState(true);
    await eel.api_start_attack(cfg)();
});

btnPause.addEventListener('click', async () => {
    const paused = await eel.api_pause_attack()();
    if (paused) {
        btnPause.textContent = '▶ Resume';
        statusBadge.textContent = 'Paused';
    } else {
        btnPause.textContent = '⏸ Pause';
        statusBadge.textContent = 'Running';
    }
});

btnStop.addEventListener('click', async () => {
    await eel.api_stop_attack()();
});

eel.expose(on_attack_stopped);
function on_attack_stopped() {
    eel.api_get_stats()().then(s => {
        if (s) {
            document.getElementById('stat-tried').textContent = s.tried.toLocaleString();
            document.getElementById('stat-valid').textContent = s.valid;
            document.getElementById('stat-errors').textContent = s.errors || 0;
            document.getElementById('stat-rps').textContent = s.rps;
            document.getElementById('stat-elapsed').textContent = formatElapsed(s.elapsed);
            const successRate = s.tried > 0 ? (s.valid / s.tried * 100).toFixed(1) : 0;
            document.getElementById('stat-success-rate').innerHTML = `${successRate}<span style="font-size:0.7em">%</span>`;
        }
    });
    setRunningState(false);
}

const validHitsList = document.getElementById('valid-hits-list');
const validHits = [];

eel.expose(on_valid_found);
function on_valid_found(value) {
    validHits.push(value);

    if (validHits.length === 1) validHitsList.innerHTML = '';

    const entry = document.createElement('div');
    entry.className = 'valid-hit-entry';
    entry.textContent = value;
    entry.title = 'Click to copy';
    entry.addEventListener('click', () => {
        navigator.clipboard.writeText(value);
        entry.style.background = 'rgba(74,222,128,0.28)';
        setTimeout(() => entry.style.background = '', 600);
    });
    validHitsList.appendChild(entry);
    validHitsList.scrollTop = validHitsList.scrollHeight;
}

document.getElementById('btn-copy-valid').addEventListener('click', () => {
    if (!validHits.length) return;
    navigator.clipboard.writeText(validHits.join('\n'));
    const btn = document.getElementById('btn-copy-valid');
    btn.textContent = '✓ Copied';
    setTimeout(() => btn.textContent = 'Copy', 1500);
});
const reconnectModal = document.getElementById('reconnect-modal');

eel.expose(on_wrong_network);
function on_wrong_network(expectedSsid, currentSsid, newMac) {
    if (!reconnectModal) return;
    document.getElementById('modal-expected-ssid').textContent = expectedSsid || '(unknown)';
    document.getElementById('modal-current-ssid').textContent  = currentSsid  || 'not connected';
    document.getElementById('modal-ssid-name').textContent     = expectedSsid || '(unknown)';
    reconnectModal.style.display = 'flex';
    update_console(
        `[!] Wrong network after spoof! Expected: "${expectedSsid}" | Got: "${currentSsid}". Waiting for manual reconnect.`,
        'error'
    );
}

const btnResumeReconnect = document.getElementById('btn-resume-reconnect');
if (btnResumeReconnect) {
    btnResumeReconnect.addEventListener('click', async () => {
        const result = await eel.api_resume_after_reconnect()();
        if (result && result.ok) {
            reconnectModal.style.display = 'none';
            update_console('[+] Network verified — attack resumed.', 'success');
        } else {
            const current  = result ? result.current  : '?';
            const expected = result ? result.expected : '?';
            document.getElementById('modal-current-ssid').textContent = current || 'not connected';
            update_console(`[!] Still on wrong network: "${current}". Please connect to "${expected}" first.`, 'error');
        }
    });
}

async function runScan() {
    const target  = document.getElementById('scan-url').value.trim();
    const btn     = document.getElementById('btn-scan');
    const inline  = document.getElementById('scan-result-inline');

    btn.disabled    = true;
    btn.textContent = '⏳';
    inline.style.display = 'block';
    inline.innerHTML = '<span style="color:var(--t3)">Scanning...</span>';

    let result;
    try {
        result = await eel.api_smart_setup(target)();
    } catch (err) {
        inline.innerHTML = `<span style="color:var(--red)">❌ Error: ${err}</span>`;
        btn.disabled    = false;
        btn.textContent = '⚡ Scan';
        return;
    }

    btn.disabled    = false;
    btn.textContent = '⚡ Scan';

    if (!result || !result.success) {
        inline.innerHTML = `<span style="color:var(--red)">❌ ${result ? result.error : 'Unknown error'}</span>`;
        return;
    }

    const authLabel = result.auth_mode === 'username' ? 'Username Only' : 'Username + Password';
    const allFields = Object.entries(result.all_fields || {})
        .map(([n, t]) => `<span style="color:var(--p400)">${n}</span> <span style="color:var(--t3)">(${t})</span>`)
        .join(' &nbsp;·&nbsp; ');

    inline.innerHTML = `
        <div style="color:var(--green);font-weight:600;margin-bottom:6px">✅ Portal detected!</div>
        <div><span style="color:var(--t3)">URL:</span> ${result.portal_url}</div>
        <div><span style="color:var(--t3)">Action:</span> ${result.form_action}</div>
        <div><span style="color:var(--t3)">Auth:</span> ${authLabel}</div>
        <div style="margin-top:4px"><span style="color:var(--t3)">Fields:</span> ${allFields}</div>
    `;

    const set = (id, v) => { const el = document.getElementById(id); if (el && v) el.value = v; };
    set('target-url',  result.form_action);
    set('user-field',  result.fields.username);
    set('pass-field',  result.fields.password || '');

    const modeEl = document.getElementById('auth-mode');
    if (modeEl) {
        modeEl.value = result.auth_mode === 'username' ? 'username' : 'both';
        applyAuthMode(modeEl.value);
    }
}

document.getElementById('btn-scan').addEventListener('click', runScan);

document.getElementById('btn-analyze').addEventListener('click', async () => {
    const text = document.getElementById('manual-samples').value;
    if (!text.trim()) return;
    const btn = document.getElementById('btn-analyze');
    btn.textContent = '⏳';
    const result = await eel.api_analyze_samples(text)();
    btn.textContent = '🧠 Analyze Samples';
    if (result.error) {
        document.getElementById('pattern-results').value = 'Error: ' + result.error;
        return;
    }
    const lines = [];
    if (result.user_patterns) {
        lines.push('Username patterns (position → char → probability):');
        result.user_patterns.forEach((pos, i) => {
            const top = Object.entries(pos).sort((a, b) => b[1] - a[1]).slice(0, 3);
            lines.push(`  pos ${i + 1}: ` + top.map(([c, p]) => `"${c}" ${(p * 100).toFixed(0)}%`).join(', '));
        });
    }
    if (result.pass_patterns) {
        lines.push('Password patterns:');
        result.pass_patterns.forEach((pos, i) => {
            const top = Object.entries(pos).sort((a, b) => b[1] - a[1]).slice(0, 3);
            lines.push(`  pos ${i + 1}: ` + top.map(([c, p]) => `"${c}" ${(p * 100).toFixed(0)}%`).join(', '));
        });
    }
    document.getElementById('pattern-results').value = lines.join('\n') || 'No patterns extracted.';
});

document.getElementById('btn-save-config').addEventListener('click', async () => {
    const cfg = get_config();
    update_console('[*] Saving profile...', 'system');
    const ok = await eel.api_save_profile(cfg)();
    update_console(ok ? '[+] Profile saved!' : '[-] Save cancelled.', ok ? 'success' : 'warning');
});

document.getElementById('btn-load-config').addEventListener('click', async () => {
    update_console('[*] Loading profile...', 'system');
    const cfg = await eel.api_load_profile()();
    if (cfg) {
        fill_config(cfg);
        update_console('[+] Profile loaded!', 'success');
    } else {
        update_console('[-] Load cancelled.', 'warning');
    }
});

window.addEventListener('load', async () => {
    const cfg = await eel.api_get_config()();
    fill_config(cfg);
    loadAdapters();
});

let selectedAdapterIps = [];

async function loadAdapters() {
    const list = document.getElementById('adapter-list');
    list.innerHTML = '<div style="color:var(--t3);font-size:12px;text-align:center;padding:20px 0">Loading...</div>';

    let adapters = [];
    try {
        adapters = await eel.api_get_adapters()();
    } catch (e) {
        list.innerHTML = `<div style="color:var(--red);font-size:12px">❌ Failed to load adapters: ${e}</div>`;
        return;
    }

    if (!adapters || adapters.length === 0) {
        list.innerHTML = '<div style="color:var(--t3);font-size:12px;text-align:center;padding:20px 0">No active adapters found.</div>';
        return;
    }

    selectedAdapterIps = selectedAdapterIps.filter(ip => adapters.some(a => a.ip === ip));
    await eel.api_set_adapters(selectedAdapterIps)();

    if (selectedAdapterIps.length === 0) {
        const def = adapters.find(a => a.is_default);
        if (def) {
            selectedAdapterIps = [def.ip];
            await eel.api_set_adapters(selectedAdapterIps)();
        }
    }

    list.innerHTML = '';
    adapters.forEach(adapter => {
        list.appendChild(buildAdapterCard(adapter, selectedAdapterIps));
    });

    updateStatusBox();
}

function buildAdapterCard(adapter, selectedIps) {
    const isSelected = selectedIps.includes(adapter.ip);

    const card = document.createElement('div');
    card.className = 'adapter-card' + (isSelected ? ' selected' : '');
    card.dataset.ip = adapter.ip;

    const internetBadge = adapter.is_default
        ? `<span class="adapter-internet-badge">🌐 Internet</span>`
        : '';

    card.innerHTML = `
        <div class="adapter-card-inner">
            <div class="adapter-checkbox" style="font-size:18px; color:var(${isSelected ? '--p400' : '--t3'}); width:20px; text-align:center; transition:color 0.18s ease; flex-shrink:0;">${isSelected ? '☑' : '☐'}</div>
            <div class="adapter-info">
                <div class="adapter-name">🔌 ${sanitize(adapter.name)} ${internetBadge}</div>
                <div class="adapter-ip">${sanitize(adapter.ip)}</div>
                <div class="adapter-desc">${sanitize(adapter.description)}</div>
            </div>
            <div class="adapter-ip-badge">${sanitize(adapter.ip)}</div>
        </div>`;

    card.addEventListener('click', () => toggleAdapter(adapter));
    return card;
}

async function toggleAdapter(adapter) {
    const idx = selectedAdapterIps.indexOf(adapter.ip);
    if (idx === -1) {
        selectedAdapterIps.push(adapter.ip);
    } else {
        if (selectedAdapterIps.length > 1) {
            selectedAdapterIps.splice(idx, 1);
        } else {
            update_console(`[!] You must have at least one adapter selected.`, 'warning');
            return;
        }
    }

    const list = document.getElementById('adapter-list');
    list.querySelectorAll('.adapter-card').forEach(c => {
        const selected = selectedAdapterIps.includes(c.dataset.ip);
        c.classList.toggle('selected', selected);
        c.querySelector('.adapter-checkbox').textContent = selected ? '☑' : '☐';
        c.querySelector('.adapter-checkbox').style.color = `var(${selected ? '--p400' : '--t3'})`;
    });

    await eel.api_set_adapters(selectedAdapterIps)();

    updateStatusBox();
    update_console(`[*] Adapters bound → ${selectedAdapterIps.join(', ')}`, 'system');
}

function updateStatusBox() {
    const statusBox = document.getElementById('adapter-status-box');
    const statusTxt = document.getElementById('adapter-status-text');
    if (selectedAdapterIps.length > 0) {
        statusBox.style.display = 'block';
        statusTxt.textContent = `  ${selectedAdapterIps.join(' | ')}`;
    } else {
        statusBox.style.display = 'none';
    }
}

document.querySelectorAll('.nav-links li').forEach(item => {
    if (item.dataset.target === 'adapter-tab') {
        item.addEventListener('click', loadAdapters);
    }
});

document.getElementById('btn-refresh-adapters').addEventListener('click', loadAdapters);
