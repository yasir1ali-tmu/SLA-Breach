/**
 * SLA Breach Dashboard & Analyzer - Client Application
 * Vanilla Modern JavaScript (ES6+)
 */

// Application State
const state = {
    allRecords: [],
    filteredRecords: [],
    currentFile: null,
    activeRules: null,
    sortField: 'overdue_days',
    sortDirection: 'desc'
};

// ============================================================================
// Initialization
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    initTabNavigation();
    initFileUpload();
    initTableFilters();
    initSorting();
    initModal();
    loadRules();
});

// ============================================================================
// Tab Navigation
// ============================================================================
function initTabNavigation() {
    const tabUploadBtn = document.getElementById('tab-btn-upload');
    const tabRecordsBtn = document.getElementById('tab-btn-records');
    const tabRulesBtn = document.getElementById('tab-btn-rules');

    if (tabUploadBtn) tabUploadBtn.addEventListener('click', () => switchTab('upload'));
    if (tabRecordsBtn) tabRecordsBtn.addEventListener('click', () => switchTab('records'));
    if (tabRulesBtn) tabRulesBtn.addEventListener('click', () => switchTab('rules'));
}

function switchTab(tabName) {
    const tabs = ['upload', 'records', 'rules'];
    
    tabs.forEach(name => {
        const btn = document.getElementById(`tab-btn-${name}`);
        const content = document.getElementById(`tab-content-${name}`);

        if (name === tabName) {
            // Activate button styling
            if (btn) {
                btn.className = 'tab-button inline-flex items-center px-4 py-2.5 border-b-2 border-indigo-600 font-semibold text-sm text-indigo-600 transition-colors';
            }
            if (content) {
                content.classList.remove('hidden');
            }
        } else {
            // Inactivate button styling
            if (btn) {
                btn.className = 'tab-button inline-flex items-center px-4 py-2.5 border-b-2 border-transparent font-medium text-sm text-slate-600 hover:text-slate-900 hover:border-slate-300 transition-colors';
            }
            if (content) {
                content.classList.add('hidden');
            }
        }
    });
}

// ============================================================================
// Drag and Drop & File Upload
// ============================================================================
function initFileUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    if (!dropZone || !fileInput) return;

    // Open file dialog when clicking drop zone
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files && fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    // Drag-over styling
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-active');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-active');
        }, false);
    });

    // Drop handler
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
            handleFileUpload(dt.files[0]);
        }
    }, false);
}

async function handleFileUpload(file) {
    const allowedExtensions = ['.html', '.htm', '.docx'];
    const fileName = file.name.toLowerCase();
    const hasValidExt = allowedExtensions.some(ext => fileName.endsWith(ext));

    const spinner = document.getElementById('upload-spinner');
    const errorBanner = document.getElementById('upload-error-banner');
    const errorText = document.getElementById('upload-error-text');
    const fileInfoBanner = document.getElementById('file-info-banner');

    if (!hasValidExt) {
        showError(`Invalid file format '${file.name}'. Please upload a Confluence .html/.htm or Word .docx document.`);
        return;
    }

    if (errorBanner) errorBanner.classList.add('hidden');
    if (fileInfoBanner) fileInfoBanner.classList.add('hidden');
    if (spinner) spinner.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            let errorMsg = `Upload failed with HTTP status ${response.status}`;
            try {
                const errJson = await response.json();
                if (errJson.detail) errorMsg = errJson.detail;
            } catch (_) {}
            showError(errorMsg);
            return;
        }

        const data = await response.json();
        state.allRecords = data.records || [];
        state.currentFile = file.name;

        // Populate file metadata banner
        populateFileInfo(file, data);

        // Populate 4 KPI summary cards
        if (data.metrics) {
            updateKpis(data.metrics);
        }

        // Apply filters & render table
        applyFilters();

        // Update badge count on Tab 2 button
        const recordsBadge = document.getElementById('records-badge');
        if (recordsBadge) {
            recordsBadge.textContent = state.allRecords.length;
        }

    } catch (err) {
        showError(`Network or processing error: ${err.message}`);
    } finally {
        if (spinner) spinner.classList.add('hidden');
    }
}

function showError(msg) {
    const errorBanner = document.getElementById('upload-error-banner');
    const errorText = document.getElementById('upload-error-text');
    if (errorBanner && errorText) {
        errorText.textContent = msg;
        errorBanner.classList.remove('hidden');
    }
}

function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function populateFileInfo(file, data) {
    const banner = document.getElementById('file-info-banner');
    const nameEl = document.getElementById('file-info-name');
    const sizeEl = document.getElementById('file-info-size');
    const extractedEl = document.getElementById('file-info-extracted');
    const rowsEl = document.getElementById('file-info-rows');
    const warningsEl = document.getElementById('file-info-warnings');

    if (nameEl) nameEl.textContent = file.name;
    if (sizeEl) sizeEl.textContent = `(${formatBytes(file.size)})`;
    if (extractedEl) {
        const dt = data.extracted_at ? new Date(data.extracted_at) : new Date();
        extractedEl.textContent = dt.toLocaleTimeString();
    }
    if (rowsEl) rowsEl.textContent = data.parsed_count || data.records.length;

    if (warningsEl) {
        const warnings = data.warnings || [];
        if (warnings.length > 0) {
            warningsEl.textContent = `Notice: ${warnings.length} warning(s) during parsing`;
        } else {
            warningsEl.textContent = '';
        }
    }

    if (banner) banner.classList.remove('hidden');
}

// ============================================================================
// Executive KPI Highlights
// ============================================================================
function updateKpis(metrics) {
    const totalEl = document.getElementById('kpi-total-records');
    const breachedEl = document.getElementById('kpi-breached-count');
    const rateEl = document.getElementById('kpi-breach-rate');
    const avgOverdueEl = document.getElementById('kpi-avg-overdue');
    const criticalEl = document.getElementById('kpi-critical-count');
    const kpiSection = document.getElementById('kpi-section');

    if (totalEl) totalEl.textContent = metrics.total_records ?? 0;
    if (breachedEl) breachedEl.textContent = metrics.breached_count ?? 0;
    
    if (rateEl) {
        const rate = (metrics.breach_rate_pct != null) ? metrics.breach_rate_pct.toFixed(1) : '0.0';
        rateEl.textContent = `${rate}%`;
    }

    if (avgOverdueEl) {
        const avg = (metrics.avg_overdue_days != null) ? metrics.avg_overdue_days.toFixed(1) : '0.0';
        avgOverdueEl.textContent = `${avg} days`;
    }

    if (criticalEl) {
        const criticalCount = (metrics.by_severity && metrics.by_severity.CRITICAL) ? metrics.by_severity.CRITICAL : 0;
        criticalEl.textContent = criticalCount;
    }

    if (kpiSection) kpiSection.classList.remove('hidden');
}

// ============================================================================
// Interactive SLA Records Explorer (Filters & Sorting)
// ============================================================================
function initTableFilters() {
    const searchInput = document.getElementById('table-search');
    const prioritySelect = document.getElementById('filter-priority');
    const severitySelect = document.getElementById('filter-severity');
    const breachedOnlyCheckbox = document.getElementById('filter-breached-only');
    const resetBtn = document.getElementById('btn-reset-filters');

    if (searchInput) {
        searchInput.addEventListener('input', () => applyFilters());
    }
    if (prioritySelect) {
        prioritySelect.addEventListener('change', () => applyFilters());
    }
    if (severitySelect) {
        severitySelect.addEventListener('change', () => applyFilters());
    }
    if (breachedOnlyCheckbox) {
        breachedOnlyCheckbox.addEventListener('change', () => applyFilters());
    }
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (prioritySelect) prioritySelect.value = '';
            if (severitySelect) severitySelect.value = '';
            if (breachedOnlyCheckbox) breachedOnlyCheckbox.checked = false;
            applyFilters();
        });
    }
}

function initSorting() {
    const sortHeaders = document.querySelectorAll('.sort-header');
    sortHeaders.forEach(th => {
        th.addEventListener('click', () => {
            const field = th.getAttribute('data-sort');
            if (!field) return;

            if (state.sortField === field) {
                state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                state.sortField = field;
                state.sortDirection = (field === 'overdue_days' || field === 'elapsed_days') ? 'desc' : 'asc';
            }

            updateSortIndicators();
            applySorting();
            renderTable();
        });
    });
}

function updateSortIndicators() {
    const sortHeaders = document.querySelectorAll('.sort-header');
    sortHeaders.forEach(th => {
        const field = th.getAttribute('data-sort');
        const indicator = th.querySelector('.sort-indicator');
        if (!indicator) return;

        if (field === state.sortField) {
            indicator.textContent = state.sortDirection === 'asc' ? '▲' : '▼';
            indicator.className = 'sort-indicator text-indigo-600 font-bold text-[10px]';
        } else {
            indicator.textContent = '▼';
            indicator.className = 'sort-indicator text-slate-300 text-[10px]';
        }
    });
}

function applyFilters() {
    const searchInput = document.getElementById('table-search');
    const prioritySelect = document.getElementById('filter-priority');
    const severitySelect = document.getElementById('filter-severity');
    const breachedOnlyCheckbox = document.getElementById('filter-breached-only');

    const query = (searchInput ? searchInput.value : '').trim().toLowerCase();
    const priority = prioritySelect ? prioritySelect.value : '';
    const severity = severitySelect ? severitySelect.value : '';
    const breachedOnly = breachedOnlyCheckbox ? breachedOnlyCheckbox.checked : false;

    state.filteredRecords = state.allRecords.filter(record => {
        // Priority filter
        if (priority && (record.priority || '').toUpperCase() !== priority.toUpperCase()) {
            return false;
        }

        // Severity filter
        if (severity && (record.severity || '').toUpperCase() !== severity.toUpperCase()) {
            return false;
        }

        // Breached only toggle
        if (breachedOnly && !record.is_breached) {
            return false;
        }

        // Free-text search query across key, summary, team, status
        if (query) {
            const keyText = (record.key || '').toLowerCase();
            const summaryText = (record.summary || '').toLowerCase();
            const teamText = (record.team || '').toLowerCase();
            const statusText = (record.status || '').toLowerCase();
            if (!keyText.includes(query) && !summaryText.includes(query) && !teamText.includes(query) && !statusText.includes(query)) {
                return false;
            }
        }

        return true;
    });

    applySorting();
    renderTable();
}

function applySorting() {
    const field = state.sortField;
    const dirMultiplier = state.sortDirection === 'asc' ? 1 : -1;

    state.filteredRecords.sort((a, b) => {
        let valA = a[field];
        let valB = b[field];

        // Specific handling for nulls
        if (valA == null && valB == null) return 0;
        if (valA == null) return 1;
        if (valB == null) return -1;

        // Severity custom order
        if (field === 'severity') {
            const severityRank = { 'OK': 1, 'WARNING': 2, 'CRITICAL': 3, 'BREACHED': 4 };
            valA = severityRank[valA] || 0;
            valB = severityRank[valB] || 0;
        }

        if (typeof valA === 'number' && typeof valB === 'number') {
            return (valA - valB) * dirMultiplier;
        }

        return String(valA).localeCompare(String(valB)) * dirMultiplier;
    });
}

// Color badges for severities
function getSeverityBadge(severity) {
    const styles = {
        'OK': 'bg-emerald-100 text-emerald-800 border-emerald-300',
        'WARNING': 'bg-amber-100 text-amber-800 border-amber-300',
        'CRITICAL': 'bg-orange-100 text-orange-800 border-orange-300',
        'BREACHED': 'bg-rose-100 text-rose-800 border-rose-300'
    };
    const badgeClass = styles[severity] || 'bg-slate-100 text-slate-800 border-slate-300';
    return `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${badgeClass}">${escapeHtml(severity)}</span>`;
}

// Color badges for priorities
function getPriorityBadge(priority) {
    if (!priority) return `<span class="text-xs text-slate-400">-</span>`;
    const p = priority.toUpperCase();
    let cls = 'bg-slate-100 text-slate-700 border-slate-200';
    if (p.includes('P1') || p.includes('HIGHEST') || p.includes('CRITICAL')) {
        cls = 'bg-red-100 text-red-800 border-red-300 font-bold';
    } else if (p.includes('P2') || p.includes('HIGH')) {
        cls = 'bg-orange-100 text-orange-800 border-orange-300 font-semibold';
    } else if (p.includes('P3') || p.includes('MEDIUM')) {
        cls = 'bg-blue-100 text-blue-800 border-blue-200';
    } else if (p.includes('P4') || p.includes('LOW')) {
        cls = 'bg-slate-100 text-slate-700 border-slate-200';
    }
    return `<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${cls}">${escapeHtml(priority)}</span>`;
}

function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function renderTable() {
    const tbody = document.getElementById('records-table-body');
    const counterEl = document.getElementById('table-counter');
    if (!tbody) return;

    if (counterEl) {
        counterEl.textContent = `Showing ${state.filteredRecords.length} of ${state.allRecords.length} records`;
    }

    if (state.filteredRecords.length === 0) {
        tbody.innerHTML = `
            <tr id="table-empty-state">
                <td colspan="10" class="px-6 py-12 text-center text-slate-400 text-sm">
                    <div class="flex flex-col items-center justify-center">
                        <svg class="w-10 h-10 text-slate-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        <p class="font-medium text-slate-600">${state.allRecords.length === 0 ? 'No records loaded yet.' : 'No records match active filters.'}</p>
                        <p class="text-xs text-slate-400 mt-1">${state.allRecords.length === 0 ? 'Drag-and-drop an export file in the Upload tab to populate this explorer.' : 'Try adjusting your search query or dropdown filter selections.'}</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    const rowsHtml = state.filteredRecords.map((record, index) => {
        const key = escapeHtml(record.key || 'N/A');
        const summary = escapeHtml(record.summary || 'No summary');
        const team = escapeHtml(record.team || 'Unassigned');
        const priorityBadge = getPriorityBadge(record.priority);
        const status = escapeHtml(record.status || 'Unknown');
        const targetDays = (record.sla_target_days != null) ? record.sla_target_days.toFixed(1) : '-';
        const elapsedDays = (record.elapsed_days != null) ? record.elapsed_days.toFixed(1) : '-';
        
        const overdueDaysVal = record.overdue_days != null ? record.overdue_days : 0;
        const overdueDaysStr = (record.overdue_days != null) ? record.overdue_days.toFixed(1) : '-';
        const overdueClass = overdueDaysVal > 0 ? 'text-rose-600 font-bold' : 'text-slate-600';
        
        const severityBadge = getSeverityBadge(record.severity || 'OK');

        return `
            <tr class="table-row-hover hover:bg-slate-50/80 transition-colors">
                <td class="px-4 py-3 font-mono font-semibold text-indigo-600 text-xs">${key}</td>
                <td class="px-4 py-3 max-w-xs truncate text-slate-800" title="${summary}">${summary}</td>
                <td class="px-4 py-3 text-slate-600 text-xs">${team}</td>
                <td class="px-4 py-3">${priorityBadge}</td>
                <td class="px-4 py-3 text-xs text-slate-700">${status}</td>
                <td class="px-4 py-3 text-right font-mono text-xs text-slate-600">${targetDays}</td>
                <td class="px-4 py-3 text-right font-mono text-xs text-slate-600">${elapsedDays}</td>
                <td class="px-4 py-3 text-right font-mono text-xs ${overdueClass}">${overdueDaysStr}</td>
                <td class="px-4 py-3 text-center">${severityBadge}</td>
                <td class="px-4 py-3 text-center">
                    <button type="button" class="btn-view-raw px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 border border-slate-200 transition-colors" data-index="${index}">
                        View Raw
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = rowsHtml;

    // Attach click listeners to "View Raw" buttons
    const rawButtons = tbody.querySelectorAll('.btn-view-raw');
    rawButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = parseInt(btn.getAttribute('data-index'), 10);
            const record = state.filteredRecords[idx];
            if (record) {
                openRawFieldsModal(record);
            }
        });
    });
}

// ============================================================================
// Raw Fields Modal
// ============================================================================
function initModal() {
    const modal = document.getElementById('raw-fields-modal');
    const backdrop = document.getElementById('raw-fields-backdrop');
    const closeBtn = document.getElementById('modal-close-btn');
    const closeBtnFooter = document.getElementById('modal-close-btn-footer');

    if (backdrop) backdrop.addEventListener('click', closeRawFieldsModal);
    if (closeBtn) closeBtn.addEventListener('click', closeRawFieldsModal);
    if (closeBtnFooter) closeBtnFooter.addEventListener('click', closeRawFieldsModal);

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeRawFieldsModal();
        }
    });
}

function openRawFieldsModal(record) {
    const modal = document.getElementById('raw-fields-modal');
    const keyEl = document.getElementById('modal-ticket-key');
    const summaryEl = document.getElementById('modal-ticket-summary');
    const jsonPre = document.getElementById('raw-fields-json');

    if (keyEl) keyEl.textContent = record.key || 'TICKET';
    if (summaryEl) summaryEl.textContent = record.summary || '';
    if (jsonPre) {
        const rawData = {
            ticket_key: record.key,
            parsed_summary: record.summary,
            parsed_team: record.team,
            parsed_priority: record.priority,
            parsed_status: record.status,
            created_date: record.created_date,
            resolved_date: record.resolved_date,
            due_date: record.due_date,
            sla_target_days: record.sla_target_days,
            elapsed_days: record.elapsed_days,
            overdue_days: record.overdue_days,
            severity: record.severity,
            unmapped_raw_fields: record.raw_fields || {}
        };
        jsonPre.textContent = JSON.stringify(rawData, null, 2);
    }

    if (modal) modal.classList.remove('hidden');
}

function closeRawFieldsModal() {
    const modal = document.getElementById('raw-fields-modal');
    if (modal) modal.classList.add('hidden');
}

// ============================================================================
// Rules & Settings Loader
// ============================================================================
async function loadRules() {
    const refreshBtn = document.getElementById('btn-refresh-rules');
    if (refreshBtn && !refreshBtn.dataset.bound) {
        refreshBtn.dataset.bound = 'true';
        refreshBtn.addEventListener('click', loadRules);
    }

    try {
        const response = await fetch('/api/rules');
        if (!response.ok) return;

        const data = await response.json();
        state.activeRules = data;

        // Render Priority Targets
        const prioritiesContainer = document.getElementById('rules-priorities-list');
        const priorityTargets = data.sla_thresholds && (data.sla_thresholds.priority_targets_days || data.sla_thresholds.priority_target_days);
        if (prioritiesContainer && priorityTargets) {
            const targets = priorityTargets;
            let rowsHtml = '<table class="min-w-full text-xs"><thead><tr class="text-slate-400 border-b border-slate-100"><th class="pb-2 text-left">Priority</th><th class="pb-2 text-right">Target Duration</th></tr></thead><tbody class="divide-y divide-slate-100">';
            
            for (const [p, days] of Object.entries(targets)) {
                rowsHtml += `
                    <tr>
                        <td class="py-2 font-semibold text-slate-800">${escapeHtml(p)}</td>
                        <td class="py-2 text-right font-mono text-indigo-600 font-bold">${days} days</td>
                    </tr>
                `;
            }
            rowsHtml += '</tbody></table>';
            prioritiesContainer.innerHTML = rowsHtml;
        }

        // Render Severity Thresholds
        const severityContainer = document.getElementById('rules-severity-list');
        if (severityContainer && data.severity_rules) {
            const s = data.severity_rules;
            const warningPct = s.warning_threshold_pct != null ? s.warning_threshold_pct : 80;
            const breachedThreshold = s.breached_threshold_days != null ? s.breached_threshold_days : (s.breached_overdue_days_threshold != null ? s.breached_overdue_days_threshold : 0);
            const criticalDays = s.critical_overdue_days != null ? s.critical_overdue_days : (s.critical_overdue_days_threshold != null ? s.critical_overdue_days_threshold : 3);
            severityContainer.innerHTML = `
                <div class="space-y-2 text-xs">
                    <div class="flex justify-between py-1.5 border-b border-slate-100">
                        <span class="text-slate-600">Warning Threshold</span>
                        <span class="font-mono font-bold text-amber-600">&ge; ${warningPct}% of target</span>
                    </div>
                    <div class="flex justify-between py-1.5 border-b border-slate-100">
                        <span class="text-slate-600">Breached Criteria</span>
                        <span class="font-mono font-bold text-rose-600">&gt; ${breachedThreshold} days overdue</span>
                    </div>
                    <div class="flex justify-between py-1.5">
                        <span class="text-slate-600">Critical Criteria</span>
                        <span class="font-mono font-bold text-orange-600">&ge; ${criticalDays} days overdue</span>
                    </div>
                </div>
            `;
        }

        // Render Ingestion Constraints
        const limitsContainer = document.getElementById('rules-limits-body');
        if (limitsContainer) {
            const exts = (data.allowed_extensions || []).join(', ');
            const maxSize = data.max_upload_size_mb || 25;
            limitsContainer.innerHTML = `
                <div class="space-y-2 text-xs">
                    <div class="flex justify-between py-1.5 border-b border-slate-100">
                        <span class="text-slate-600">Allowed File Formats</span>
                        <span class="font-mono font-semibold text-slate-800">${escapeHtml(exts)}</span>
                    </div>
                    <div class="flex justify-between py-1.5 border-b border-slate-100">
                        <span class="text-slate-600">Max File Size</span>
                        <span class="font-mono font-bold text-emerald-600">${maxSize} MB</span>
                    </div>
                    <div class="flex justify-between py-1.5">
                        <span class="text-slate-600">Client Processing</span>
                        <span class="font-semibold text-slate-700">Offline-first Browser</span>
                    </div>
                </div>
            `;
        }

    } catch (err) {
        console.error('Failed to load rules:', err);
    }
}
