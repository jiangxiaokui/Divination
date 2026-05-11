const loginState = document.getElementById("loginState");
const runtimeSummary = document.getElementById("runtimeSummary");
const runtimeMeta = document.getElementById("runtimeMeta");
const recordsSummary = document.getElementById("recordsSummary");
const moduleSummary = document.getElementById("moduleSummary");
const recordsTableHeadRow = document.querySelector(".admin-table thead tr");
const recordsTableBody = document.getElementById("recordsTableBody");
const recordsEmpty = document.getElementById("recordsEmpty");
const recordDetail = document.getElementById("recordDetail");
const recordsForm = document.getElementById("recordsForm");
const queryModeSelect = recordsForm.queryMode;
const API_BASE = "/api/v1/admin";
const STORAGE_KEY = "admin_token";
const state = {
  records: [],
  selectedRecordId: null,
  advancedQueryEnabled: false,
};
const QUERY_MODE_LABELS = {
  all: "默认查询: 最近全部",
  has_name: "非默认查询: 已填写姓名/对象",
  has_question: "非默认查询: 已填写问题",
  has_name_or_question: "非默认查询: 姓名或问题任一已填",
  has_name_and_question: "非默认查询: 姓名和问题都已填",
};

function getToken() {
  return localStorage.getItem(STORAGE_KEY);
}

function setToken(token) {
  localStorage.setItem(STORAGE_KEY, token);
}

function clearToken() {
  localStorage.removeItem(STORAGE_KEY);
}

function updateLoginState() {
  if (getToken()) {
    loginState.textContent = "已登录";
  } else {
    loginState.textContent = "未登录";
  }
}

function applyQueryPermission() {
  queryModeSelect.hidden = !state.advancedQueryEnabled;
  queryModeSelect.disabled = !state.advancedQueryEnabled;
  if (!state.advancedQueryEnabled) {
    queryModeSelect.value = "all";
  }
}

function renderTableHead() {
  recordsTableHeadRow.innerHTML = state.advancedQueryEnabled
    ? `
        <th>记录</th>
        <th>模块</th>
        <th>姓名/对象</th>
        <th>问题</th>
        <th>用户</th>
        <th>置信度</th>
        <th>LLM</th>
        <th>时间</th>
        <th>详情</th>
      `
    : `
        <th>记录</th>
        <th>模块</th>
        <th>用户</th>
        <th>置信度</th>
        <th>LLM</th>
        <th>时间</th>
        <th>详情</th>
      `;
}

function resetRuntime(text) {
  runtimeSummary.innerHTML = `<div class="admin-empty">${text}</div>`;
  runtimeMeta.innerHTML = "";
}

function resetRecords(text) {
  recordsSummary.innerHTML = `<div class="admin-empty">${text}</div>`;
  moduleSummary.innerHTML = "";
  recordsTableBody.innerHTML = "";
  recordsEmpty.textContent = text;
  recordsEmpty.hidden = false;
  recordDetail.innerHTML = '<p class="admin-detail-placeholder">选择一条记录后，可查看入库详情、输入参数和原始结果。</p>';
  state.records = [];
  state.selectedRecordId = null;
  state.advancedQueryEnabled = false;
  applyQueryPermission();
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function shortenText(value, maxLength = 40) {
  if (!value) {
    return "-";
  }

  const normalized = String(value).replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength)}...`;
}

function stringifyJson(value) {
  if (value == null) {
    return "暂无";
  }
  return JSON.stringify(value, null, 2);
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setBlockText(container, title, value) {
  const block = document.createElement("section");
  block.className = "admin-detail-block";

  const heading = document.createElement("h3");
  heading.textContent = title;

  const pre = document.createElement("pre");
  pre.textContent = value || "暂无";

  block.append(heading, pre);
  container.appendChild(block);
}

function appendDetailItem(container, label, value) {
  const item = document.createElement("div");
  item.className = "admin-detail-item";

  const labelEl = document.createElement("span");
  labelEl.className = "admin-detail-label";
  labelEl.textContent = label;

  const valueEl = document.createElement("strong");
  valueEl.textContent = value || "-";

  item.append(labelEl, valueEl);
  container.appendChild(item);
}

function renderRuntime(data) {
  state.advancedQueryEnabled = Boolean(data.advanced_query_enabled);
  applyQueryPermission();

  runtimeSummary.innerHTML = `
    <article class="admin-metric-card">
      <span class="admin-metric-label">运行环境</span>
      <strong class="admin-metric-value">${escapeHtml(data.app_env || "unknown")}</strong>
      <span class="admin-metric-hint">当前服务环境</span>
    </article>
    <article class="admin-metric-card">
      <span class="admin-metric-label">数据库持久化</span>
      <strong class="admin-metric-value ${data.db_persistence_enabled ? "is-good" : "is-bad"}">${data.db_persistence_enabled ? "已开启" : "未开启"}</strong>
      <span class="admin-metric-hint">管理记录读取依赖此配置</span>
    </article>
    <article class="admin-metric-card">
      <span class="admin-metric-label">本地登录状态</span>
      <strong class="admin-metric-value">${getToken() ? "令牌有效" : "未登录"}</strong>
      <span class="admin-metric-hint">基于浏览器本地令牌判断</span>
    </article>
  `;

  runtimeMeta.innerHTML = "";
  [
    `接口时间: ${new Date().toLocaleString("zh-CN")}`,
    `数据源: ${API_BASE}/runtime`,
  ].forEach((text) => {
    const chip = document.createElement("span");
    chip.className = "admin-chip";
    chip.textContent = text;
    runtimeMeta.appendChild(chip);
  });
}

function renderRecordDetail(record) {
  if (!record) {
    recordDetail.innerHTML = '<p class="admin-detail-placeholder">选择一条记录后，可查看入库详情、输入参数和原始结果。</p>';
    return;
  }

  recordDetail.innerHTML = "";

  const header = document.createElement("div");
  header.className = "admin-detail-head";

  const titleWrap = document.createElement("div");
  const title = document.createElement("h2");
  title.textContent = `${record.module} · 记录 #${record.record_id}`;
  const subtitle = document.createElement("p");
  subtitle.className = "subtitle";
  subtitle.textContent = shortenText(record.question || "未填写问题", 90);
  titleWrap.append(title, subtitle);

  const badgeWrap = document.createElement("div");
  badgeWrap.className = "admin-chip-row";
  [
    `分类 ${record.category}`,
    `会话 ${record.session_id}`,
    record.has_random_trace ? "含随机轨迹" : "无随机轨迹",
    record.has_calc_result ? "含计算结果" : "无计算结果",
  ].forEach((text) => {
    const chip = document.createElement("span");
    chip.className = "admin-chip";
    chip.textContent = text;
    badgeWrap.appendChild(chip);
  });

  header.append(titleWrap, badgeWrap);
  recordDetail.appendChild(header);

  const grid = document.createElement("div");
  grid.className = "admin-detail-grid";
  appendDetailItem(grid, "记录时间", formatDateTime(record.created_at));
  appendDetailItem(grid, "会话时间", formatDateTime(record.session_created_at));
  appendDetailItem(grid, "用户", record.has_user ? `用户 #${record.user_id}` : "匿名");
  appendDetailItem(grid, "姓名/对象", record.display_name || "未填写");
  appendDetailItem(grid, "置信度", record.confidence_level || "未标注");
  appendDetailItem(grid, "LLM 调用", `${record.llm_call_count} 次`);
  appendDetailItem(grid, "问题", record.question || "未填写");
  recordDetail.appendChild(grid);

  setBlockText(recordDetail, "结论文本", record.final_text || "暂无");
  setBlockText(recordDetail, "输入参数", stringifyJson(record.input_payload));
  setBlockText(recordDetail, "计算结果", stringifyJson(record.calc_result));
  setBlockText(recordDetail, "客户端信息", stringifyJson(record.client_meta));
}

function renderRecords(data) {
  const summary = data.summary || {};
  const metricCards = [
    `
      <article class="admin-metric-card">
        <span class="admin-metric-label">数据库总记录</span>
        <strong class="admin-metric-value">${summary.total_records ?? data.total ?? 0}</strong>
        <span class="admin-metric-hint">当前数据库累计条数</span>
      </article>
    `,
    `
      <article class="admin-metric-card">
        <span class="admin-metric-label">筛选命中</span>
        <strong class="admin-metric-value">${summary.filtered_records ?? data.total ?? 0}</strong>
        <span class="admin-metric-hint">${escapeHtml(QUERY_MODE_LABELS[summary.query_mode || "all"] || QUERY_MODE_LABELS.all)}</span>
      </article>
    `,
    `
      <article class="admin-metric-card">
        <span class="admin-metric-label">本次加载</span>
        <strong class="admin-metric-value">${summary.returned_records ?? data.items.length}</strong>
        <span class="admin-metric-hint">limit=${data.limit}，offset=${data.offset}</span>
      </article>
    `,
  ];

  if (state.advancedQueryEnabled) {
    metricCards.push(`
      <article class="admin-metric-card">
        <span class="admin-metric-label">已填姓名/对象</span>
        <strong class="admin-metric-value">${summary.with_name_count ?? 0}</strong>
        <span class="admin-metric-hint">从 input_payload 中提取</span>
      </article>
    `);
    metricCards.push(`
      <article class="admin-metric-card">
        <span class="admin-metric-label">已填问题</span>
        <strong class="admin-metric-value">${summary.with_question_count ?? 0}</strong>
        <span class="admin-metric-hint">session.question 非空</span>
      </article>
    `);
  }

  recordsSummary.innerHTML = metricCards.join("");
  renderTableHead();

  moduleSummary.innerHTML = "";
  const modules = summary.modules || [];
  if (modules.length) {
    modules.forEach((item) => {
      const chip = document.createElement("span");
      chip.className = "admin-chip";
      chip.textContent = `${item.module} ${item.count}`;
      moduleSummary.appendChild(chip);
    });
  }

  state.records = data.items;
  if (!data.items.length) {
    recordsTableBody.innerHTML = "";
    recordsEmpty.textContent = "当前条件下没有记录。";
    recordsEmpty.hidden = false;
    renderRecordDetail(null);
    return;
  }

  const activeId = state.records.some((item) => item.record_id === state.selectedRecordId)
    ? state.selectedRecordId
    : data.items[0].record_id;

  state.selectedRecordId = activeId;
  recordsTableBody.innerHTML = data.items
    .map((item) => {
      const isActive = item.record_id === activeId;
      const cells = [
        `
          <td>
            <strong>#${item.record_id}</strong>
            <div class="admin-cell-sub">会话 #${item.session_id}</div>
          </td>
        `,
        `
          <td>
            <strong>${escapeHtml(item.module)}</strong>
            <div class="admin-cell-sub">${escapeHtml(item.category)}</div>
          </td>
        `,
      ];

      if (state.advancedQueryEnabled) {
        cells.push(`<td>${escapeHtml(item.display_name || "未填写")}</td>`);
        cells.push(`<td title="${escapeHtml(item.question || "未填写")}">${escapeHtml(shortenText(item.question || "未填写", 28))}</td>`);
      }

      cells.push(`<td>${escapeHtml(item.has_user ? `#${item.user_id}` : "匿名")}</td>`);
      cells.push(`<td>${escapeHtml(item.confidence_level || "-")}</td>`);
      cells.push(`<td>${item.llm_call_count}</td>`);
      cells.push(`<td>${escapeHtml(formatDateTime(item.created_at))}</td>`);
      cells.push(`<td><button type="button" class="ghost admin-record-button" data-record-id="${item.record_id}">查看</button></td>`);

      return `
        <tr class="${isActive ? "is-active" : ""}" data-record-id="${item.record_id}">
          ${cells.join("")}
        </tr>
      `;
    })
    .join("");

  recordsEmpty.hidden = true;
  renderRecordDetail(state.records.find((item) => item.record_id === activeId));
}

async function loadRuntime() {
  try {
    const data = await adminReq(`${API_BASE}/runtime`, { method: "GET" });
    renderRuntime(data);
  } catch (err) {
    resetRuntime(String(err));
  }
}

async function loadRecords() {
  const limit = Number(recordsForm.limit.value || 50);
  const queryMode = state.advancedQueryEnabled ? (queryModeSelect.value || "all") : "all";
  try {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: "0",
      query_mode: queryMode,
    });
    const data = await adminReq(`${API_BASE}/records?${params.toString()}`, {
      method: "GET",
    });
    renderRecords(data);
  } catch (err) {
    if (String(err).includes("403")) {
      state.advancedQueryEnabled = false;
      applyQueryPermission();
    }
    resetRecords(String(err));
  }
}

async function adminReq(url, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });
  const text = await res.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${JSON.stringify(data)}`);
  }
  return data;
}

document.getElementById("adminLoginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    const data = await adminReq(`${API_BASE}/login`, {
      method: "POST",
      body: JSON.stringify({
        username: form.username.value.trim(),
        password: form.password.value,
      }),
    });
    setToken(data.access_token);
    state.advancedQueryEnabled = Boolean(data.advanced_query_enabled);
    applyQueryPermission();
    updateLoginState();
    await loadRuntime();
    await loadRecords();
  } catch (err) {
    resetRuntime(String(err));
  }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  try {
    if (getToken()) {
      await adminReq(`${API_BASE}/logout`, { method: "POST" });
    }
  } catch (err) {
    // ignore logout errors
  }
  clearToken();
  updateLoginState();
  resetRuntime("已退出登录");
  resetRecords("请先登录后加载记录...");
});

document.getElementById("runtimeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  await loadRuntime();
});

recordsForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  await loadRecords();
});

recordsTableBody.addEventListener("click", (e) => {
  const button = e.target.closest("button[data-record-id]");
  if (!button) {
    return;
  }

  const recordId = Number(button.dataset.recordId);
  state.selectedRecordId = recordId;

  Array.from(recordsTableBody.querySelectorAll("tr")).forEach((row) => {
    row.classList.toggle("is-active", Number(row.dataset.recordId) === recordId);
  });

  renderRecordDetail(state.records.find((item) => item.record_id === recordId));
});

updateLoginState();

applyQueryPermission();
renderTableHead();

if (getToken()) {
  loadRuntime();
  loadRecords();
} else {
  resetRuntime("请先登录后查看...");
  resetRecords("请先登录后加载记录...");
}

if (getToken()) {
  loadRuntime();
  loadRecords();
} else {
  resetRuntime("请先登录后查看...");
  resetRecords("请先登录后加载记录...");
}
