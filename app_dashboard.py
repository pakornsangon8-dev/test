"""
=============================================================================
Dashboard พนักงานเจ้าหน้าที่ตาม พ.ร.บ. ไซเบอร์ฯ / คอมพิวเตอร์ฯ (Python Standalone App)
=============================================================================
"""

import http.server
import socketserver
import webbrowser
import os
import json
import pandas as pd

PORT = 8501

html_template = """<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard พนักงานเจ้าหน้าที่ตาม พ.ร.บ. ไซเบอร์ฯ / คอมพิวเตอร์ฯ</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Sarabun', sans-serif; }
    .badge { display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
    .badge-expired { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-warning { background-color: rgba(245, 158, 11, 0.15); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-active { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-duplicate { background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.3); }
  </style>
</head>
<body class="bg-gray-50 text-gray-800 antialiased min-h-screen p-4 md:p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div class="flex items-center gap-2 mb-1">
          <span class="inline-block w-3 h-3 rounded-full bg-blue-500 animate-pulse"></span>
          <span class="text-xs font-semibold uppercase tracking-wider text-blue-500">Cybersecurity Officer Management Dashboard</span>
        </div>
        <h1 class="text-2xl md:text-3xl font-bold text-gray-900">Dashboard พนักงานเจ้าหน้าที่แยกตามระดับ & ติดตามสถานะการแต่งตั้ง</h1>
        <p class="text-sm text-gray-500 mt-1">ระบบวิเคราะห์สถานะการหมดอายุ (Expired Timestamps), การเสนอชื่อซ้ำ/ตั้งซ้ำ/ต่ออายุ</p>
      </div>
      <button onclick="resetFilters()" class="px-4 py-2 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">🔄 ล้างตัวกรอง</button>
    </div>

    <!-- KPI Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <div class="text-xs font-medium text-gray-500">เจ้าหน้าที่ทั้งหมด</div>
        <div class="text-3xl font-extrabold mt-2 text-gray-900" id="kpi-total">0</div>
        <div class="text-xs text-gray-500 mt-1" id="kpi-unique">0 บุคคล</div>
      </div>
      <div class="bg-white border border-red-200 rounded-xl p-5 shadow-sm bg-red-50/50">
        <div class="text-xs font-medium text-red-600">หมดอายุแล้ว (Expired)</div>
        <div class="text-3xl font-extrabold mt-2 text-red-600" id="kpi-expired">0</div>
        <div class="text-xs text-red-500 mt-1" id="kpi-expired-pct">0% ของทั้งหมด</div>
      </div>
      <div class="bg-white border border-amber-200 rounded-xl p-5 shadow-sm bg-amber-50/50">
        <div class="text-xs font-medium text-amber-600">ใกล้หมดอายุ (ภายใน 90 วัน)</div>
        <div class="text-3xl font-extrabold mt-2 text-amber-600" id="kpi-warning">0</div>
        <div class="text-xs text-amber-500 mt-1">ต้องเตรียมต่ออายุ</div>
      </div>
      <div class="bg-white border border-emerald-200 rounded-xl p-5 shadow-sm bg-emerald-50/50">
        <div class="text-xs font-medium text-emerald-600">ยังมีผลใช้งาน (Active)</div>
        <div class="text-3xl font-extrabold mt-2 text-emerald-600" id="kpi-active">0</div>
        <div class="text-xs text-emerald-500 mt-1">ยังไม่หมดอายุ</div>
      </div>
      <div class="bg-white border border-purple-200 rounded-xl p-5 shadow-sm bg-purple-50/50">
        <div class="text-xs font-medium text-purple-600">เสนอชื่อซ้ำ / ต่ออายุ</div>
        <div class="text-3xl font-extrabold mt-2 text-purple-600" id="kpi-renewals">0</div>
        <div class="text-xs text-purple-500 mt-1">แต่งตั้ง > 1 ประกาศ</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="border-b border-gray-200 flex gap-2 overflow-x-auto pb-1">
      <button onclick="switchTab('tab-overview')" id="btn-tab-overview" class="px-5 py-2.5 font-semibold text-sm rounded-t-lg border-b-2 border-blue-600 text-blue-600 bg-white">📊 สรุปภาพรวม & กราฟสถิติ</button>
      <button onclick="switchTab('tab-expiration')" id="btn-tab-expiration" class="px-5 py-2.5 font-semibold text-sm rounded-t-lg text-gray-500 hover:text-gray-700">⏳ วิเคราะห์สถานะหมดอายุ & Timestamp</button>
      <button onclick="switchTab('tab-renewals')" id="btn-tab-renewals" class="px-5 py-2.5 font-semibold text-sm rounded-t-lg text-gray-500 hover:text-gray-700">🔄 เสนอชื่อซ้ำ / ต่ออายุบัตร</button>
      <button onclick="switchTab('tab-table')" id="btn-tab-table" class="px-5 py-2.5 font-semibold text-sm rounded-t-lg text-gray-500 hover:text-gray-700">📋 ตารางค้นหาข้อมูลทั้งหมด</button>
    </div>

    <!-- Global Filter Bar -->
    <div class="bg-white border border-gray-200 rounded-xl p-4 shadow-sm grid grid-cols-1 sm:grid-cols-2 md:grid-cols-6 gap-3 text-xs">
      <div>
        <label class="block font-medium mb-1 text-gray-600">🔍 ค้นหา (ชื่อ/ตำแหน่ง/หน่วยงาน)</label>
        <input type="text" id="filter-search" oninput="applyFilters()" placeholder="พิมพ์ชื่อ, สังกัด..." class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
      </div>
      <div>
        <label class="block font-medium mb-1 text-gray-600">📌 สถานะการหมดอายุ</label>
        <select id="filter-status" onchange="applyFilters()" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
          <option value="ALL">ทั้งหมด</option>
          <option value="EXPIRED">หมดอายุแล้ว (Expired)</option>
          <option value="WARNING">ใกล้หมดอายุ (ภายใน 90 วัน)</option>
          <option value="ACTIVE">ปกติ (ยังไม่หมดอายุ)</option>
          <option value="DUPLICATE">เฉพาะผู้แต่งตั้งซ้ำ/ต่ออายุ</option>
        </select>
      </div>
      <div>
        <label class="block font-medium mb-1 text-gray-600">🏛️ ประกาศฉบับที่</label>
        <select id="filter-announcement" onchange="applyFilters()" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
          <option value="ALL">ทุกฉบับประกาศ</option>
        </select>
      </div>
      <div>
        <label class="block font-medium mb-1 text-gray-600">🗺️ ภาค / พื้นที่</label>
        <select id="filter-region" onchange="applyFilters()" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
          <option value="ALL">ทุกภาค</option>
        </select>
      </div>
      <div>
        <label class="block font-medium mb-1 text-gray-600">📍 จังหวัด</label>
        <select id="filter-province" onchange="applyFilters()" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
          <option value="ALL">ทุกจังหวัด</option>
        </select>
      </div>
      <div>
        <label class="block font-medium mb-1 text-gray-600">🏢 หน่วยงาน</label>
        <select id="filter-agency" onchange="applyFilters()" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
          <option value="ALL">ทุกหน่วยงาน</option>
        </select>
      </div>
    </div>

    <!-- TAB 1: OVERVIEW -->
    <div id="tab-overview" class="space-y-6 tab-content">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h3 class="font-semibold text-base mb-4">🎯 สัดส่วนสถานะบัตรพนักงานเจ้าหน้าที่</h3>
          <div class="relative h-64"><canvas id="chart-status"></canvas></div>
        </div>
        <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h3 class="font-semibold text-base mb-4">🗺️ จำนวนพนักงานเจ้าหน้าที่แยกตามภาค (แนวนอน)</h3>
          <div class="relative h-64"><canvas id="chart-region"></canvas></div>
        </div>
        <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h3 class="font-semibold text-base mb-4">✍️ การแต่งตั้งแยกตามรัฐมนตรีผู้ลงนาม (แนวนอน)</h3>
          <div class="relative h-64"><canvas id="chart-minister"></canvas></div>
        </div>
        <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h3 class="font-semibold text-base mb-4">🏢 Top 10 หน่วยงานที่มีพนักงานเจ้าหน้าที่มากที่สุด (แนวนอน)</h3>
          <div class="relative h-64"><canvas id="chart-agency"></canvas></div>
        </div>
      </div>
    </div>

    <!-- TAB 2: EXPIRATION (Replaced 'สถานะและระยะเวลา' with 'รัฐมนตรี (minister)') -->
    <div id="tab-expiration" class="space-y-6 tab-content hidden">
      <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <h3 class="font-bold text-lg text-red-600 mb-2">⏳ ตารางวิเคราะห์ Timestamp และระยะเวลาหมดอายุ</h3>
        <p class="text-xs text-gray-500 mb-4">เรียงลำดับจากรายการที่ **หมดอายุไปแล้วนานที่สุด** (<span class="text-red-600 font-bold">🔴 สีแดง = หมดอายุแล้ว</span> | <span class="text-amber-600 font-bold">🟡 สีเหลือง = ใกล้หมดอายุ <= 90 วัน</span> | <span class="text-emerald-600 font-bold">🟢 สีเขียว = ยังไม่หมดอายุ</span>)</p>
        <div class="overflow-x-auto border border-gray-200 rounded-lg">
          <table class="w-full text-xs text-left">
            <thead class="bg-gray-100 uppercase font-semibold text-gray-600 border-b">
              <tr>
                <th class="px-3 py-3">ลำดับ</th><th class="px-3 py-3">ชื่อ-นามสกุล</th><th class="px-3 py-3">หน่วยงาน</th><th class="px-3 py-3">จังหวัด</th><th class="px-3 py-3">ฉบับที่</th><th class="px-3 py-3">วันเริ่มแต่งตั้ง</th><th class="px-3 py-3">วันหมดอายุบัตร</th><th class="px-3 py-3">ระยะเวลา (วัน)</th><th class="px-3 py-3">รัฐมนตรี (Minister)</th>
              </tr>
            </thead>
            <tbody id="table-expiration-body" class="divide-y border-gray-200"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 3: RENEWALS -->
    <div id="tab-renewals" class="space-y-6 tab-content hidden">
      <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <h3 class="font-bold text-lg text-purple-600 mb-2">🔄 รายชื่อเสนอชื่อซ้ำ / แต่งตั้งซ้ำ / ต่ออายุ</h3>
        <div id="duplicates-container" class="space-y-4 mt-4"></div>
      </div>
    </div>

    <!-- TAB 4: TABLE -->
    <div id="tab-table" class="space-y-6 tab-content hidden">
      <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <div class="flex justify-between items-center mb-4">
          <h3 class="font-bold text-lg">📋 ตารางพนักงานเจ้าหน้าที่ทั้งหมด</h3>
          <button onclick="exportToCSV()" class="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700">📥 Export CSV</button>
        </div>
        <div class="overflow-x-auto border border-gray-200 rounded-lg">
          <table class="w-full text-xs text-left">
            <thead class="bg-gray-100 uppercase font-semibold text-gray-600 border-b">
              <tr>
                <th class="px-3 py-3">ลำดับรวม</th><th class="px-3 py-3">ฉบับที่</th><th class="px-3 py-3">คำนำหน้า</th><th class="px-3 py-3">ชื่อ-นามสกุล</th><th class="px-3 py-3">เพศ</th><th class="px-3 py-3">หน่วยงาน</th><th class="px-3 py-3">จังหวัด/ภาค</th><th class="px-3 py-3">เริ่มแต่งตั้ง</th><th class="px-3 py-3">หมดอายุ</th><th class="px-3 py-3">สถานะ</th><th class="px-3 py-3">รัฐมนตรี</th>
              </tr>
            </thead>
            <tbody id="table-main-body" class="divide-y border-gray-200"></tbody>
          </table>
        </div>
        <div class="flex justify-between items-center mt-4 text-xs">
          <div text-gray-500 id="page-info"></div>
          <div class="flex gap-2">
            <button id="btn-prev" onclick="changePage(-1)" class="px-3 py-1.5 border rounded-lg hover:bg-gray-50">ย้อนกลับ</button>
            <button id="btn-next" onclick="changePage(1)" class="px-3 py-1.5 border rounded-lg hover:bg-gray-50">ถัดไป</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const allData = __DATA_JSON__;
    let filteredData = [...allData];
    let currentPage = 1, pageSize = 25, charts = {};

    allData.forEach(item => {
      const days = item['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ'];
      if (days !== null && days !== undefined) {
        if (days < 0) item.statusType = 'EXPIRED';
        else if (days <= 90) item.statusType = 'WARNING';
        else item.statusType = 'ACTIVE';
      } else item.statusType = 'UNKNOWN';
    });

    const nameCounts = {};
    allData.forEach(item => {
      const fullName = (item['ชื่อ'] || '').trim() + ' ' + (item['นามสกุล'] || '').trim();
      item.cleanFullName = fullName;
      nameCounts[fullName] = (nameCounts[fullName] || 0) + 1;
    });

    allData.forEach(item => {
      item.isDuplicate = nameCounts[item.cleanFullName] > 1;
      item.dupCount = nameCounts[item.cleanFullName];
    });

    document.addEventListener("DOMContentLoaded", () => {
      populateDropdowns();
      applyFilters();
      renderRenewalsTracker();
    });

    function populateDropdowns() {
      const anns = [...new Set(allData.map(d => d['ประกาศฉบับที่']))].sort((a,b) => a - b);
      const annSelect = document.getElementById('filter-announcement');
      anns.forEach(ann => {
        if (ann) {
          const opt = document.createElement('option');
          opt.value = ann; opt.textContent = `ฉบับที่ ${ann}`;
          annSelect.appendChild(opt);
        }
      });
      
      const regs = [...new Set(allData.map(d => d['ภาค']))].filter(Boolean).sort();
      const regSelect = document.getElementById('filter-region');
      regs.forEach(reg => {
        const opt = document.createElement('option');
        opt.value = reg; opt.textContent = reg;
        regSelect.appendChild(opt);
      });

      const provs = [...new Set(allData.map(d => d['จังหวัด']))].filter(Boolean).sort();
      const provSelect = document.getElementById('filter-province');
      provs.forEach(prov => {
        const opt = document.createElement('option');
        opt.value = prov; opt.textContent = prov;
        provSelect.appendChild(opt);
      });

      const agencies = [...new Set(allData.map(d => d['หน่วยงาน']))].filter(Boolean).sort();
      const agencySelect = document.getElementById('filter-agency');
      agencies.forEach(ag => {
        const opt = document.createElement('option');
        opt.value = ag; opt.textContent = ag;
        agencySelect.appendChild(opt);
      });
    }

    function applyFilters() {
      const search = document.getElementById('filter-search').value.toLowerCase().trim();
      const status = document.getElementById('filter-status').value;
      const ann = document.getElementById('filter-announcement').value;
      const reg = document.getElementById('filter-region').value;
      const prov = document.getElementById('filter-province').value;
      const agency = document.getElementById('filter-agency').value;

      filteredData = allData.filter(d => {
        if (search) {
          const matchName = (d['ชื่อ-นามสกุล'] || '').toLowerCase().includes(search);
          const matchDept = (d['หน่วยงาน'] || '').toLowerCase().includes(search);
          if (!matchName && !matchDept) return false;
        }
        if (status === 'EXPIRED' && d.statusType !== 'EXPIRED') return false;
        if (status === 'WARNING' && d.statusType !== 'WARNING') return false;
        if (status === 'ACTIVE' && d.statusType !== 'ACTIVE') return false;
        if (status === 'DUPLICATE' && !d.isDuplicate) return false;
        if (ann !== 'ALL' && String(d['ประกาศฉบับที่']) !== String(ann)) return false;
        if (reg !== 'ALL' && d['ภาค'] !== reg) return false;
        if (prov !== 'ALL' && d['จังหวัด'] !== prov) return false;
        if (agency !== 'ALL' && d['หน่วยงาน'] !== agency) return false;
        return true;
      });

      currentPage = 1;
      updateKPIs();
      renderOverviewCharts();
      renderExpirationTable();
      renderMainTable();
    }

    function resetFilters() {
      document.getElementById('filter-search').value = '';
      document.getElementById('filter-status').value = 'ALL';
      document.getElementById('filter-announcement').value = 'ALL';
      document.getElementById('filter-region').value = 'ALL';
      document.getElementById('filter-province').value = 'ALL';
      document.getElementById('filter-agency').value = 'ALL';
      applyFilters();
    }

    function updateKPIs() {
      const total = filteredData.length;
      const expired = filteredData.filter(d => d.statusType === 'EXPIRED').length;
      const warning = filteredData.filter(d => d.statusType === 'WARNING').length;
      const active = filteredData.filter(d => d.statusType === 'ACTIVE').length;
      const uniqueNames = new Set(filteredData.map(d => d.cleanFullName)).size;
      const duplicates = filteredData.filter(d => d.isDuplicate).length;

      document.getElementById('kpi-total').textContent = total.toLocaleString();
      document.getElementById('kpi-unique').textContent = `${uniqueNames.toLocaleString()} บุคคล (${duplicates} แต่งตั้งซ้ำ)`;
      document.getElementById('kpi-expired').textContent = expired.toLocaleString();
      document.getElementById('kpi-expired-pct').textContent = total > 0 ? `${((expired/total)*100).toFixed(1)}%` : '0%';
      document.getElementById('kpi-warning').textContent = warning.toLocaleString();
      document.getElementById('kpi-active').textContent = active.toLocaleString();
      document.getElementById('kpi-renewals').textContent = `${duplicates} รายการ`;
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.getElementById(tabId).classList.remove('hidden');
      ['overview', 'expiration', 'renewals', 'table'].forEach(t => {
        const btn = document.getElementById(`btn-tab-${t}`);
        if (`tab-${t}` === tabId) btn.className = "px-5 py-2.5 font-semibold text-sm rounded-t-lg border-b-2 border-blue-600 text-blue-600 bg-white";
        else btn.className = "px-5 py-2.5 font-semibold text-sm rounded-t-lg text-gray-500 hover:text-gray-700";
      });
    }

    function renderOverviewCharts() {
      const statusCounts = {
        'ยังไม่หมดอายุ': filteredData.filter(d => d.statusType === 'ACTIVE').length,
        'ใกล้หมดอายุ': filteredData.filter(d => d.statusType === 'WARNING').length,
        'หมดอายุแล้ว': filteredData.filter(d => d.statusType === 'EXPIRED').length,
      };
      if (charts.status) charts.status.destroy();
      charts.status = new Chart(document.getElementById('chart-status'), {
        type: 'bar',
        data: { labels: Object.keys(statusCounts), datasets: [{ label: 'จำนวน', data: Object.values(statusCounts), backgroundColor: ['#10b981', '#f59e0b', '#ef4444'] }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
      });

      const regionMap = {};
      filteredData.forEach(d => { const r = d['ภาค'] || 'ไม่ระบุ'; regionMap[r] = (regionMap[r] || 0) + 1; });
      if (charts.region) charts.region.destroy();
      charts.region = new Chart(document.getElementById('chart-region'), {
        type: 'bar',
        data: { labels: Object.keys(regionMap), datasets: [{ label: 'จำนวนเจ้าหน้าที่', data: Object.values(regionMap), backgroundColor: '#3b82f6' }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
      });

      const minMap = {};
      filteredData.forEach(d => { const m = d['รัฐมนตรี (minister)'] || 'ไม่ระบุ'; minMap[m] = (minMap[m] || 0) + 1; });
      if (charts.minister) charts.minister.destroy();
      charts.minister = new Chart(document.getElementById('chart-minister'), {
        type: 'bar',
        data: { labels: Object.keys(minMap), datasets: [{ label: 'จำนวน', data: Object.values(minMap), backgroundColor: ['#8b5cf6', '#ec4899', '#06b6d4', '#f97316'] }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
      });

      const agencyMap = {};
      filteredData.forEach(d => { const a = d['หน่วยงาน'] || 'ไม่ระบุ'; agencyMap[a] = (agencyMap[a] || 0) + 1; });
      const sortedAgencies = Object.entries(agencyMap).sort((a,b) => b[1] - a[1]).slice(0, 10);
      if (charts.agency) charts.agency.destroy();
      charts.agency = new Chart(document.getElementById('chart-agency'), {
        type: 'bar',
        data: { labels: sortedAgencies.map(a => a[0].length > 25 ? a[0].substring(0, 25) + '...' : a[0]), datasets: [{ label: 'จำนวน', data: sortedAgencies.map(a => a[1]), backgroundColor: '#06b6d4' }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
      });
    }

    function renderExpirationTable() {
      const container = document.getElementById('table-expiration-body');
      container.innerHTML = '';
      const sortedItems = [...filteredData].sort((a,b) => (a['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ'] ?? 99999) - (b['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ'] ?? 99999));
      sortedItems.forEach((item, idx) => {
        const days = item['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ'];
        let daysBadge = '';
        if (days < 0) {
          daysBadge = `<span class="text-red-600 font-bold bg-red-100 px-2 py-0.5 rounded">${days} วัน</span>`;
        } else if (days <= 90) {
          daysBadge = `<span class="text-amber-600 font-bold bg-amber-100 px-2 py-0.5 rounded">+${days} วัน</span>`;
        } else {
          daysBadge = `<span class="text-emerald-600 font-bold bg-emerald-100 px-2 py-0.5 rounded">+${days} วัน</span>`;
        }
        
        const tr = document.createElement('tr');
        tr.className = "hover:bg-gray-50";
        tr.innerHTML = `
          <td class="px-3 py-2.5">${idx + 1}</td>
          <td class="px-3 py-2.5 font-semibold">${item['ชื่อ-นามสกุล'] || '-'}</td>
          <td class="px-3 py-2.5 text-gray-600">${item['หน่วยงาน'] || '-'}</td>
          <td class="px-3 py-2.5 text-gray-500">${item['จังหวัด'] || '-'}</td>
          <td class="px-3 py-2.5">ฉบับที่ ${item['ประกาศฉบับที่'] || '-'}</td>
          <td class="px-3 py-2.5">${item['วันที่เริ่ม (announcement_date)'] || '-'}</td>
          <td class="px-3 py-2.5 font-medium">${item['วันหมดอายุบัตร (ค.ศ.)'] || '-'}</td>
          <td class="px-3 py-2.5">${daysBadge}</td>
          <td class="px-3 py-2.5 text-gray-600">${item['รัฐมนตรี (minister)'] || '-'}</td>
        `;
        container.appendChild(tr);
      });
    }

    function renderRenewalsTracker() {
      const container = document.getElementById('duplicates-container');
      container.innerHTML = '';
      const dupGroups = {};
      allData.filter(d => d.isDuplicate).forEach(d => {
        const name = d.cleanFullName;
        if (!dupGroups[name]) dupGroups[name] = [];
        dupGroups[name].push(d);
      });
      Object.keys(dupGroups).forEach(name => {
        const records = dupGroups[name].sort((a,b) => (a['ประกาศฉบับที่'] || 0) - (b['ประกาศฉบับที่'] || 0));
        const card = document.createElement('div');
        card.className = "border border-purple-200 bg-purple-50/50 rounded-xl p-4 space-y-3";
        let html = `
          <div class="border-b border-purple-200 pb-2">
            <span class="badge badge-duplicate mb-1">🔄 มีประวัติแต่งตั้งซ้ำ / ต่ออายุ (${records.length} ฉบับประกาศ)</span>
            <h4 class="text-base font-bold text-gray-900">${name}</h4>
            <p class="text-xs text-gray-500">สังกัด: ${records[0]['หน่วยงาน'] || '-'} | จังหวัด: ${records[0]['จังหวัด'] || '-'}</p>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-${Math.min(records.length, 3)} gap-3">
        `;
        records.forEach((rec, idx) => {
          const days = rec['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ'];
          let statusText = days < 0 ? `<span class="text-red-600 font-bold">🔴 หมดอายุแล้ว (${days} วัน)</span>` : days <= 90 ? `<span class="text-amber-600 font-bold">🟡 ใกล้หมดอายุ (เหลือ ${days} วัน)</span>` : `<span class="text-emerald-600 font-bold">🟢 ปกติ (เหลือ ${days} วัน)</span>`;
          html += `
            <div class="bg-white border rounded-lg p-3 space-y-1">
              <div class="text-xs font-bold text-purple-600">ประกาศฉบับที่ ${rec['ประกาศฉบับที่']}</div>
              <div class="text-xs">📅 เริ่ม: ${rec['วันที่เริ่ม (announcement_date)'] || '-'}</div>
              <div class="text-xs">📅 หมดอายุ: ${rec['วันหมดอายุบัตร (ค.ศ.)'] || '-'}</div>
              <div class="text-xs">✍️ รัฐมนตรี: ${rec['รัฐมนตรี (minister)'] || '-'}</div>
              <div class="text-xs pt-1">${statusText}</div>
            </div>
          `;
        });
        html += `</div>`;
        card.innerHTML = html;
        container.appendChild(card);
      });
    }

    function renderMainTable() {
      const container = document.getElementById('table-main-body');
      container.innerHTML = '';
      const total = filteredData.length;
      const start = (currentPage - 1) * pageSize;
      const end = Math.min(start + pageSize, total);
      const pageData = filteredData.slice(start, end);
      document.getElementById('page-info').textContent = `กำลังแสดง ${total > 0 ? start + 1 : 0} - ${end} จาก ${total.toLocaleString()} รายการ`;
      document.getElementById('btn-prev').disabled = currentPage === 1;
      document.getElementById('btn-next').disabled = end >= total;

      pageData.forEach(item => {
        let statusBadge = item.statusType === 'EXPIRED' ? `<span class="badge badge-expired">หมดอายุ</span>` : item.statusType === 'WARNING' ? `<span class="badge badge-warning">ใกล้หมดอายุ</span>` : `<span class="badge badge-active">ปกติ</span>`;
        const dupBadge = item.isDuplicate ? `<span class="badge badge-duplicate ml-1">🔄 ซ้ำ</span>` : '';
        const tr = document.createElement('tr');
        tr.className = "hover:bg-gray-50";
        tr.innerHTML = `
          <td class="px-3 py-2.5">${item['ลำดับรวม'] || '-'}</td>
          <td class="px-3 py-2.5 font-bold text-blue-600">ฉบับที่ ${item['ประกาศฉบับที่'] || '-'}</td>
          <td class="px-3 py-2.5 text-gray-500">${item['คำนำหน้าชื่อ'] || '-'}</td>
          <td class="px-3 py-2.5 font-semibold">${item['ชื่อ-นามสกุล'] || '-'} ${dupBadge}</td>
          <td class="px-3 py-2.5">${item['เพศ'] || '-'}</td>
          <td class="px-3 py-2.5">${item['หน่วยงาน'] || '-'}</td>
          <td class="px-3 py-2.5 text-gray-500">${item['จังหวัด'] || '-'} (${item['ภาค'] || '-'})</td>
          <td class="px-3 py-2.5">${item['วันที่เริ่ม (announcement_date)'] || '-'}</td>
          <td class="px-3 py-2.5 font-medium">${item['วันหมดอายุบัตร (ค.ศ.)'] || '-'}</td>
          <td class="px-3 py-2.5">${statusBadge}</td>
          <td class="px-3 py-2.5 text-gray-500">${item['รัฐมนตรี (minister)'] || '-'}</td>
        `;
        container.appendChild(tr);
      });
    }

    function changePage(delta) { currentPage += delta; renderMainTable(); }

    function exportToCSV() {
      if (filteredData.length === 0) return alert('ไม่มีข้อมูล');
      const keys = Object.keys(filteredData[0]).filter(k => typeof filteredData[0][k] !== 'object');
      let csv = '\\uFEFF' + keys.join(',') + '\\n';
      filteredData.forEach(row => {
        const vals = keys.map(k => `"${String(row[k] ?? '').replace(/"/g, '""')}"`);
        csv += vals.join(',') + '\\n';
      });
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url); link.setAttribute('download', 'officers_export.csv');
      document.body.appendChild(link); link.click(); document.body.removeChild(link);
    }
  </script>
</body>
</html>
"""

final_html = html_template.replace("__DATA_JSON__", json_data_str)

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(final_html.encode("utf-8"))

print(f"🚀 กำลังเปิด Web App Dashboard บน พอร์ต {PORT}...")
webbrowser.open(f"http://localhost:{PORT}")

with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    print(f"✅ Web App Server ทำงานแล้วที่ http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 ปิดการทำงานเรียบร้อยแล้ว")
