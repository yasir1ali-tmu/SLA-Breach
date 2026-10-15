import React, { useState, useEffect } from 'react';

export default function App() {
  // -------------------------------------------------------------
  // Application State (Simple and Human-Readable)
  // -------------------------------------------------------------
  const [activeTab, setActiveTab] = useState('upload');
  const [records, setRecords] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rules, setRules] = useState(null);

  // Filters State
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [breachedOnly, setBreachedOnly] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Drag and Drop active state
  const [isDragging, setIsDragging] = useState(false);

  // -------------------------------------------------------------
  // Load SLA Rules on page load
  // -------------------------------------------------------------
  useEffect(() => {
    fetch('/api/rules')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setRules(data);
      })
      .catch((err) => console.log('Could not load rules:', err));
  }, []);

  // -------------------------------------------------------------
  // File Upload Handler (POST /api/upload)
  // -------------------------------------------------------------
  const handleFileUpload = async (file) => {
    if (!file) return;

    // Check extension
    const validExtensions = ['.html', '.htm', '.docx'];
    const fileName = file.name.toLowerCase();
    const hasValidExt = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!hasValidExt) {
      setError('Please upload a Confluence HTML (.html, .htm) or Word (.docx) file.');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      const data = await response.json();

      setRecords(data.records || []);
      setMetrics(data.metrics || null);
      setAnalytics(data.analytics || null);
      setFileInfo({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + ' KB',
        extractedAt: new Date().toLocaleTimeString(),
        totalParsed: data.parsed_count || (data.records ? data.records.length : 0),
      });
    } catch (err) {
      setError(err.message || 'An error occurred while uploading file');
    } finally {
      setLoading(false);
    }
  };

  // Drag & Drop events
  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  // -------------------------------------------------------------
  // Filter Records
  // -------------------------------------------------------------
  const filteredRecords = records.filter((r) => {
    // Search filter
    const q = searchQuery.toLowerCase().trim();
    if (q) {
      const matchKey = r.key && r.key.toLowerCase().includes(q);
      const matchSummary = r.summary && r.summary.toLowerCase().includes(q);
      const matchTeam = r.team && r.team.toLowerCase().includes(q);
      const matchStatus = r.status && r.status.toLowerCase().includes(q);
      if (!matchKey && !matchSummary && !matchTeam && !matchStatus) return false;
    }

    // Priority filter
    if (priorityFilter !== 'ALL' && r.priority !== priorityFilter) {
      return false;
    }

    // Severity filter
    if (severityFilter !== 'ALL' && r.severity !== severityFilter) {
      return false;
    }

    // Breached only toggle
    if (breachedOnly && !r.is_breached) {
      return false;
    }

    return true;
  });

  // Severity Badge Colors
  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'BREACHED':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'WARNING':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col">
      {/* ------------------------------------------------------------- */}
      {/* 1. TOP HEADER & BRANDING                                      */}
      {/* ------------------------------------------------------------- */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-0 sm:h-16 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-0">
          <div className="flex items-center space-x-3">
            {/* Logo Icon */}
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-sm shrink-0">
              <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div className="min-w-0">
              <h1 className="text-base sm:text-lg font-bold text-slate-900 leading-tight truncate sm:whitespace-normal">
                SLA Breach Dashboard & Analyzer
              </h1>
              <p className="text-[11px] sm:text-xs text-slate-500 truncate sm:whitespace-normal">Confluence & Word Export Ticket Ingestion Engine</p>
            </div>
          </div>

          <div className="flex items-center space-x-2 self-start sm:self-auto shrink-0">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span>
              System Ready
            </span>
            <span className="text-xs px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 font-mono font-bold">
              React UI
            </span>
          </div>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* TAB BUTTONS (Horizontal scrollable on mobile)                 */}
        {/* ------------------------------------------------------------- */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-slate-100 flex space-x-4 sm:space-x-6 overflow-x-auto no-scrollbar scroll-smooth">
          <button
            onClick={() => setActiveTab('upload')}
            className={`py-3 text-xs sm:text-sm font-semibold border-b-2 flex items-center space-x-2 transition whitespace-nowrap shrink-0 ${
              activeTab === 'upload'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span>Upload & Overview</span>
          </button>

          <button
            onClick={() => setActiveTab('records')}
            className={`py-3 text-xs sm:text-sm font-semibold border-b-2 flex items-center space-x-2 transition whitespace-nowrap shrink-0 ${
              activeTab === 'records'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span>SLA Records Explorer</span>
            {records.length > 0 && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-700 font-mono">
                {records.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            className={`py-3 text-xs sm:text-sm font-semibold border-b-2 flex items-center space-x-2 transition whitespace-nowrap shrink-0 ${
              activeTab === 'analytics'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span>Visual Analytics</span>
          </button>

          <button
            onClick={() => setActiveTab('rules')}
            className={`py-3 text-xs sm:text-sm font-semibold border-b-2 flex items-center space-x-2 transition whitespace-nowrap shrink-0 ${
              activeTab === 'rules'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span>SLA Rules & Settings</span>
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* 2. MAIN CONTENT AREA                                          */}
      {/* ------------------------------------------------------------- */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-6 space-y-5 sm:space-y-6">

        {/* ============================================================ */}
        {/* TAB 1: UPLOAD & OVERVIEW                                     */}
        {/* ============================================================ */}
        {activeTab === 'upload' && (
          <div className="space-y-6">

            {/* 4 KPI Summary Cards (Placed AT THE TOP above Upload box) */}
            {metrics && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-5">
                {/* Total Records */}
                <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Records</span>
                    <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center font-bold">
                      #
                    </div>
                  </div>
                  <div className="mt-2.5 sm:mt-3">
                    <p className="text-2xl sm:text-3xl font-extrabold text-slate-900">{metrics.total_records}</p>
                    <p className="text-xs text-slate-500 mt-1">Parsed Tickets</p>
                  </div>
                </div>

                {/* Breached Records */}
                <div className="bg-white border border-rose-200 rounded-2xl p-4 sm:p-5 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-rose-600">Breached Records</span>
                    <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-rose-100 text-rose-700">
                      {metrics.breach_rate_pct != null ? metrics.breach_rate_pct.toFixed(1) : 0}%
                    </span>
                  </div>
                  <div className="mt-2.5 sm:mt-3">
                    <p className="text-2xl sm:text-3xl font-extrabold text-rose-600">{metrics.breached_count}</p>
                    <p className="text-xs text-slate-500 mt-1">Overdue Resolution</p>
                  </div>
                </div>

                {/* Avg Overdue Days */}
                <div className="bg-white border border-amber-200 rounded-2xl p-4 sm:p-5 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-amber-600">Avg Overdue</span>
                    <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                      ⏱
                    </div>
                  </div>
                  <div className="mt-2.5 sm:mt-3">
                    <p className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                      {metrics.avg_overdue_days != null ? metrics.avg_overdue_days.toFixed(1) : 0} days
                    </p>
                    <p className="text-xs text-slate-500 mt-1">For Breached Tickets</p>
                  </div>
                </div>

                {/* Critical Tickets */}
                <div className="bg-white border border-orange-200 rounded-2xl p-4 sm:p-5 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-orange-600">Critical Tickets</span>
                    <div className="w-8 h-8 rounded-lg bg-orange-50 text-orange-600 flex items-center justify-center font-bold">
                      ⚡
                    </div>
                  </div>
                  <div className="mt-2.5 sm:mt-3">
                    <p className="text-2xl sm:text-3xl font-extrabold text-orange-600">
                      {metrics.by_severity ? metrics.by_severity.CRITICAL || 0 : 0}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">Overdue &gt;= 3 Days</p>
                  </div>
                </div>
              </div>
            )}

            {/* File Info Banner (If file is uploaded) */}
            {fileInfo && (
              <div className="bg-white border border-slate-200 rounded-2xl p-3.5 sm:p-4 shadow-xs flex flex-col sm:flex-row gap-3 sm:gap-0 items-start sm:items-center justify-between">
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 text-base sm:text-lg shrink-0">
                    📄
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-slate-900 truncate">
                      {fileInfo.name} <span className="text-xs font-normal text-slate-500">({fileInfo.size})</span>
                    </h3>
                    <p className="text-xs text-slate-500 truncate">
                      Processed at {fileInfo.extractedAt} • {fileInfo.totalParsed} records parsed
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setActiveTab('records')}
                  className="w-full sm:w-auto px-3.5 py-1.5 text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg transition text-center shrink-0"
                >
                  View in Explorer →
                </button>
              </div>
            )}

            {/* Error Banner */}
            {error && (
              <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-2xl p-3.5 sm:p-4 text-xs sm:text-sm flex items-center justify-between">
                <span>⚠️ {error}</span>
                <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700 font-bold ml-4">
                  ✕
                </button>
              </div>
            )}

            {/* Drag and Drop Upload Card */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-4 sm:p-8">
              <div className="max-w-2xl mx-auto text-center">
                <h2 className="text-lg sm:text-xl font-bold text-slate-900">Upload Ticket Export File</h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Ingest Confluence HTML tables or Word DOCX documents with automated SLA calculation.
                </p>

                {/* Drop Zone Box */}
                <div
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                  onDrop={onDrop}
                  onClick={() => document.getElementById('file-upload-input').click()}
                  className={`mt-5 sm:mt-6 border-2 border-dashed rounded-2xl p-5 sm:p-8 cursor-pointer transition-all duration-200 ${
                    isDragging
                      ? 'border-indigo-500 bg-indigo-50/80 scale-[1.01]'
                      : 'border-indigo-200 hover:border-indigo-400 bg-indigo-50/30 hover:bg-indigo-50/60'
                  }`}
                >
                  <input
                    type="file"
                    id="file-upload-input"
                    accept=".html,.htm,.docx"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        handleFileUpload(e.target.files[0]);
                      }
                    }}
                    className="hidden"
                  />

                  <div className="flex flex-col items-center pointer-events-none">
                    <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-white shadow-xs border border-indigo-100 flex items-center justify-center text-indigo-600 text-xl sm:text-2xl">
                      ☁️
                    </div>
                    <p className="mt-3 sm:mt-4 text-sm sm:text-base font-semibold text-slate-800">
                      Drag & drop Confluence HTML or Word DOCX here, or <span className="text-indigo-600 underline">browse</span>
                    </p>
                    <p className="text-xs text-slate-400 mt-1">Single-file upload up to 25 MB</p>

                    <div className="flex flex-wrap justify-center items-center gap-2 mt-3 sm:mt-4">
                      <span className="px-2.5 py-1 text-xs font-medium rounded-md bg-white border border-slate-200 text-slate-600">
                        HTML (.html, .htm)
                      </span>
                      <span className="px-2.5 py-1 text-xs font-medium rounded-md bg-white border border-slate-200 text-slate-600">
                        Word (.docx)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Upload Spinner */}
                {loading && (
                  <div className="mt-6 flex flex-col items-center justify-center">
                    <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-sm font-medium text-slate-700 mt-2">Parsing tickets & calculating SLA metrics...</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 2: SLA RECORDS EXPLORER                                  */}
        {/* ============================================================ */}
        {activeTab === 'records' && (
          <div className="space-y-5">
            {/* Filter Toolbar */}
            <div className="bg-white border border-slate-200 rounded-2xl p-3.5 sm:p-4 shadow-xs flex flex-col lg:flex-row gap-3.5 items-stretch lg:items-center justify-between">
              <div className="flex flex-col sm:flex-row flex-wrap gap-2.5 sm:gap-3 items-stretch sm:items-center flex-1">
                {/* Search Bar */}
                <input
                  type="text"
                  placeholder="Search by ticket key, summary, team..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="px-3.5 py-2 text-xs border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full sm:w-64 md:w-72"
                />

                {/* Priority Filter */}
                <select
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  className="px-3 py-2 text-xs border border-slate-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full sm:w-auto"
                >
                  <option value="ALL">All Priorities</option>
                  <option value="P1">P1 (1 day)</option>
                  <option value="P2">P2 (2 days)</option>
                  <option value="P3">P3 (5 days)</option>
                  <option value="P4">P4 (10 days)</option>
                  <option value="P5">P5 (15 days)</option>
                </select>

                {/* Severity Filter */}
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="px-3 py-2 text-xs border border-slate-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full sm:w-auto"
                >
                  <option value="ALL">All Severities</option>
                  <option value="OK">OK (Compliant)</option>
                  <option value="WARNING">WARNING (&gt;= 80%)</option>
                  <option value="BREACHED">BREACHED</option>
                  <option value="CRITICAL">CRITICAL (&gt; 3 days)</option>
                </select>

                {/* Breached Only Checkbox */}
                <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer py-1 px-1">
                  <input
                    type="checkbox"
                    checked={breachedOnly}
                    onChange={(e) => setBreachedOnly(e.target.checked)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="whitespace-nowrap font-medium">Breached Only</span>
                </label>
              </div>

              {/* Reset button & count */}
              <div className="flex items-center justify-between lg:justify-end space-x-3 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-100">
                <span className="text-xs text-slate-500 whitespace-nowrap">
                  Showing <b>{filteredRecords.length}</b> of {records.length} records
                </span>
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setPriorityFilter('ALL');
                    setSeverityFilter('ALL');
                    setBreachedOnly(false);
                  }}
                  className="px-2.5 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg hover:bg-slate-50 transition whitespace-nowrap"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Records Data Table */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
              {filteredRecords.length === 0 ? (
                <div className="p-8 sm:p-12 text-center text-slate-400">
                  <p className="text-3xl mb-2">📋</p>
                  <p className="font-semibold text-slate-700">No records found</p>
                  <p className="text-xs mt-1">Upload a file or adjust your search filters to display tickets.</p>
                </div>
              ) : (
                <div>
                  <div className="sm:hidden px-4 py-2 bg-slate-50/70 border-b border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-medium">
                    <span>👉 Swipe horizontally for all columns</span>
                    <span className="font-mono text-slate-400">9 cols</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[760px] text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase">
                        <tr>
                          <th className="py-3 px-4 whitespace-nowrap">Key</th>
                          <th className="py-3 px-4">Summary</th>
                          <th className="py-3 px-4 whitespace-nowrap">Team</th>
                          <th className="py-3 px-4 whitespace-nowrap">Priority</th>
                          <th className="py-3 px-4 whitespace-nowrap">Target</th>
                          <th className="py-3 px-4 whitespace-nowrap">Elapsed</th>
                          <th className="py-3 px-4 whitespace-nowrap">Overdue</th>
                          <th className="py-3 px-4 whitespace-nowrap">Severity</th>
                          <th className="py-3 px-4 text-right whitespace-nowrap">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {filteredRecords.map((r, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/80 transition">
                            <td className="py-3 px-4 font-mono font-bold text-indigo-600 whitespace-nowrap">{r.key}</td>
                            <td className="py-3 px-4 font-medium text-slate-900 max-w-[200px] sm:max-w-xs truncate" title={r.summary}>
                              {r.summary || '—'}
                            </td>
                            <td className="py-3 px-4 text-slate-600 whitespace-nowrap">{r.team || 'Unassigned'}</td>
                            <td className="py-3 px-4 whitespace-nowrap">
                              <span className="px-2 py-0.5 rounded font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                                {r.priority || '—'}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                              {r.sla_target_days != null ? `${r.sla_target_days}d` : '—'}
                            </td>
                            <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                              {r.elapsed_days != null ? `${r.elapsed_days}d` : '—'}
                            </td>
                            <td className="py-3 px-4 font-mono font-bold whitespace-nowrap">
                              {r.overdue_days != null && r.overdue_days > 0 ? (
                                <span className="text-rose-600">+{r.overdue_days}d</span>
                              ) : (
                                <span className="text-slate-400">0d</span>
                              )}
                            </td>
                            <td className="py-3 px-4 whitespace-nowrap">
                              <span className={`px-2 py-0.5 rounded-full font-bold border text-[11px] ${getSeverityBadge(r.severity)}`}>
                                {r.severity}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right whitespace-nowrap">
                              <button
                                onClick={() => setSelectedRecord(r)}
                                className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold underline"
                              >
                                Details
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 3: VISUAL ANALYTICS                                      */}
        {/* ============================================================ */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            {!analytics ? (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 sm:p-12 text-center text-slate-400">
                <p className="text-3xl sm:text-4xl mb-2">📊</p>
                <p className="text-sm sm:text-base font-semibold text-slate-700">No Analytics Loaded</p>
                <p className="text-xs mt-1">Upload a ticket export file in the Upload tab to generate charts and distributions.</p>
                <button
                  onClick={() => setActiveTab('upload')}
                  className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-700 transition"
                >
                  Go to Upload Tab
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                {/* Severity Breakdown */}
                <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-6 shadow-xs space-y-4">
                  <h3 className="text-xs sm:text-sm font-bold text-slate-900 uppercase tracking-wider">Severity Breakdown</h3>
                  <div className="space-y-3">
                    {Object.entries(analytics.severity_distribution || {}).map(([sev, count]) => {
                      const total = records.length || 1;
                      const pct = ((count / total) * 100).toFixed(1);
                      return (
                        <div key={sev} className="space-y-1">
                          <div className="flex justify-between text-xs font-medium">
                            <span>{sev}</span>
                            <span className="font-bold text-slate-700">{count} ({pct}%)</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                sev === 'CRITICAL'
                                  ? 'bg-orange-500'
                                  : sev === 'BREACHED'
                                  ? 'bg-rose-500'
                                  : sev === 'WARNING'
                                  ? 'bg-amber-400'
                                  : 'bg-emerald-500'
                              }`}
                              style={{ width: `${pct}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Overdue Duration Distribution */}
                <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-6 shadow-xs space-y-4">
                  <h3 className="text-xs sm:text-sm font-bold text-slate-900 uppercase tracking-wider">Overdue Duration Buckets</h3>
                  <div className="space-y-3">
                    {Object.entries(analytics.overdue_distribution || {}).map(([bin, count]) => {
                      const totalBreached = (metrics && metrics.breached_count) || 1;
                      const pct = ((count / totalBreached) * 100).toFixed(1);
                      return (
                        <div key={bin} className="space-y-1">
                          <div className="flex justify-between text-xs font-medium">
                            <span className="font-mono">{bin} overdue</span>
                            <span className="font-bold text-slate-700">{count} tickets</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                            <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.min(100, pct)}%` }}></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Team Breach Leaderboard */}
                <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-6 shadow-xs space-y-4 lg:col-span-2">
                  <h3 className="text-xs sm:text-sm font-bold text-slate-900 uppercase tracking-wider">Team SLA Compliance Rankings</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[500px] text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase">
                        <tr>
                          <th className="py-2.5 px-3">Team Name</th>
                          <th className="py-2.5 px-3">Total Tickets</th>
                          <th className="py-2.5 px-3">Compliant</th>
                          <th className="py-2.5 px-3">Breached</th>
                          <th className="py-2.5 px-3">Breach Rate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {(analytics.team_rankings || []).map((t, idx) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="py-2.5 px-3 font-semibold text-slate-800">{t.team}</td>
                            <td className="py-2.5 px-3 text-slate-600">{t.total}</td>
                            <td className="py-2.5 px-3 text-emerald-600 font-medium">{t.compliant}</td>
                            <td className="py-2.5 px-3 text-rose-600 font-bold">{t.breached}</td>
                            <td className="py-2.5 px-3 font-mono font-bold">
                              <span className={t.breach_rate_pct > 0 ? 'text-rose-600' : 'text-emerald-600'}>
                                {t.breach_rate_pct}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 4: SLA RULES & SETTINGS                                  */}
        {/* ============================================================ */}
        {activeTab === 'rules' && (
          <div className="space-y-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-6 shadow-xs space-y-5">
              <div>
                <h3 className="text-sm sm:text-base font-bold text-slate-900">Active Priority SLA Targets</h3>
                <p className="text-xs text-slate-500 mt-1">Resolution time limits associated with each ticket priority level.</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
                {[
                  { priority: 'P1 / Blocker', days: '1.0 day (24h)', color: 'border-rose-200 bg-rose-50/50' },
                  { priority: 'P2 / Critical', days: '2.0 days (48h)', color: 'border-orange-200 bg-orange-50/50' },
                  { priority: 'P3 / Major', days: '5.0 days (120h)', color: 'border-amber-200 bg-amber-50/50' },
                  { priority: 'P4 / Minor', days: '10.0 days (240h)', color: 'border-blue-200 bg-blue-50/50' },
                  { priority: 'P5 / Trivial', days: '15.0 days (360h)', color: 'border-slate-200 bg-slate-50/50' },
                ].map((item, idx) => (
                  <div key={idx} className={`p-3.5 sm:p-4 rounded-xl border ${item.color}`}>
                    <p className="text-xs font-bold text-slate-700">{item.priority}</p>
                    <p className="text-base sm:text-lg font-extrabold text-slate-900 mt-1">{item.days}</p>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-slate-100 text-xs text-slate-500 space-y-1">
                <p>• <b>Warning Threshold:</b> Triggers at 80% elapsed SLA target window.</p>
                <p>• <b>Breached Threshold:</b> Triggers when overdue resolution days &gt; 0.0.</p>
                <p>• <b>Critical Severity:</b> Triggers when overdue resolution days &gt;= 3.0 days.</p>
                <p>• <b>Allowed Formats:</b> Confluence HTML export (.html, .htm) and Word document (.docx).</p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ------------------------------------------------------------- */}
      {/* 3. TICKET DETAILS MODAL                                       */}
      {/* ------------------------------------------------------------- */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-3 sm:p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-4 sm:p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3 gap-2">
              <div className="min-w-0">
                <span className="font-mono text-xs font-bold text-indigo-600 block">{selectedRecord.key}</span>
                <h3 className="text-sm sm:text-base font-bold text-slate-900 break-words">{selectedRecord.summary || 'Ticket Details'}</h3>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold p-1 shrink-0"
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-400 font-semibold block">Team</span>
                <span className="font-bold text-slate-800 break-words">{selectedRecord.team || 'Unassigned'}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Status</span>
                <span className="font-bold text-slate-800 break-words">{selectedRecord.status || 'Open'}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Priority</span>
                <span className="font-bold text-slate-800">{selectedRecord.priority || '—'}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Severity</span>
                <span className={`inline-block px-2 py-0.5 rounded font-bold ${getSeverityBadge(selectedRecord.severity)}`}>
                  {selectedRecord.severity}
                </span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Created Date</span>
                <span className="text-slate-700">{selectedRecord.created_date ? new Date(selectedRecord.created_date).toLocaleString() : '—'}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Resolved Date</span>
                <span className="text-slate-700">{selectedRecord.resolved_date ? new Date(selectedRecord.resolved_date).toLocaleString() : 'Active (Unresolved)'}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Elapsed Days</span>
                <span className="font-bold text-slate-800">{selectedRecord.elapsed_days != null ? `${selectedRecord.elapsed_days}d` : '—'}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Overdue Days</span>
                <span className="font-bold text-rose-600">{selectedRecord.overdue_days != null ? `+${selectedRecord.overdue_days}d` : '0d'}</span>
              </div>
            </div>

            {/* Raw Fields JSON */}
            {selectedRecord.raw_fields && (
              <div className="pt-2">
                <span className="text-xs font-semibold text-slate-500 block mb-1">Unmapped Extracted Fields</span>
                <pre className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-[11px] font-mono text-slate-700 overflow-x-auto max-h-36 whitespace-pre-wrap break-all">
                  {JSON.stringify(selectedRecord.raw_fields, null, 2)}
                </pre>
              </div>
            )}

            <div className="text-right pt-2 border-t border-slate-100">
              <button
                onClick={() => setSelectedRecord(null)}
                className="w-full sm:w-auto px-4 py-2 bg-slate-100 text-slate-700 font-semibold text-xs rounded-xl hover:bg-slate-200 transition text-center"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
