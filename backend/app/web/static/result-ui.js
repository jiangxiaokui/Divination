function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeMultiline(text) {
  return escapeHtml(text).replaceAll("\n", "<br />");
}

const resultStateStore = new WeakMap();
let drawerRoot = null;
let drawerBackdrop = null;
let activeDrawerContainer = null;
let activeDrawerIndex = null;
const pageStatePrefix = "xj_page_state_v1:";

function getPageStateKey(pageKey) {
  return `${pageStatePrefix}${pageKey}`;
}

function syncModeButtons(form) {
  const readingMode = form?.elements?.readingMode?.value;
  if (!readingMode) {
    return;
  }

  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === readingMode);
  });
}

function serializeFormState(form) {
  const data = {};
  if (!form?.elements) {
    return data;
  }

  for (const field of form.elements) {
    if (!field.name || field.disabled) {
      continue;
    }

    if (field.type === "radio") {
      if (field.checked) {
        data[field.name] = field.value;
      }
      continue;
    }

    if (field.type === "checkbox") {
      data[field.name] = Boolean(field.checked);
      continue;
    }

    if (field.tagName === "SELECT" && field.multiple) {
      data[field.name] = Array.from(field.selectedOptions).map((opt) => opt.value);
      continue;
    }

    data[field.name] = field.value;
  }

  return data;
}

function applyFormState(form, data) {
  if (!form?.elements || !data || typeof data !== "object") {
    return;
  }

  for (const [name, value] of Object.entries(data)) {
    const fields = form.querySelectorAll(`[name="${CSS.escape(name)}"]`);
    if (!fields.length) {
      continue;
    }

    fields.forEach((field) => {
      if (field.type === "radio") {
        field.checked = field.value === value;
        return;
      }

      if (field.type === "checkbox") {
        field.checked = Boolean(value);
        return;
      }

      if (field.tagName === "SELECT" && field.multiple && Array.isArray(value)) {
        Array.from(field.options).forEach((opt) => {
          opt.selected = value.includes(opt.value);
        });
        return;
      }

      field.value = value ?? "";
    });
  }
}

function initPageState(options) {
  const pageKey = options?.pageKey;
  const form = options?.form;
  const resultContainer = options?.resultContainer;

  if (!pageKey || !form || !resultContainer || typeof sessionStorage === "undefined") {
    return {
      saveNow() {},
      clear() {},
    };
  }

  const storageKey = getPageStateKey(pageKey);
  const readStored = () => {
    const raw = sessionStorage.getItem(storageKey);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw);
    } catch {
      sessionStorage.removeItem(storageKey);
      return null;
    }
  };

  const saveNow = () => {
    const payload = {
      form: serializeFormState(form),
      resultHtml: resultContainer.innerHTML,
      savedAt: Date.now(),
    };
    sessionStorage.setItem(storageKey, JSON.stringify(payload));
  };

  const clear = () => {
    sessionStorage.removeItem(storageKey);
  };

  const stored = readStored();
  if (stored?.form) {
    applyFormState(form, stored.form);
  }
  syncModeButtons(form);
  if (stored?.resultHtml) {
    resultContainer.innerHTML = stored.resultHtml;
  }

  const onFieldChange = () => {
    syncModeButtons(form);
    saveNow();
  };

  form.addEventListener("input", onFieldChange);
  form.addEventListener("change", onFieldChange);

  const observer = new MutationObserver(() => {
    saveNow();
  });
  observer.observe(resultContainer, {
    childList: true,
    subtree: true,
    characterData: true,
  });

  window.addEventListener("beforeunload", saveNow);

  return {
    saveNow,
    clear,
  };
}

window.initPageState = initPageState;

function getResultState(container) {
  if (!resultStateStore.has(container)) {
    resultStateStore.set(container, {
      data: null,
      timeline: [],
    });
  }
  return resultStateStore.get(container);
}

function updateResultState(container, patch) {
  const prev = getResultState(container);
  const next = {
    ...prev,
    ...patch,
  };
  resultStateStore.set(container, next);
  if (activeDrawerContainer === container && drawerRoot?.classList.contains("open")) {
    renderDrawerContent(container, activeDrawerIndex);
  }
  return next;
}

function ensureDrawer() {
  if (drawerRoot && drawerBackdrop) {
    return;
  }

  drawerBackdrop = document.createElement("div");
  drawerBackdrop.className = "result-drawer-backdrop";
  drawerBackdrop.addEventListener("click", closeResultDrawer);

  drawerRoot = document.createElement("aside");
  drawerRoot.className = "result-drawer";
  drawerRoot.innerHTML = `
    <div class="drawer-header">
      <div>
        <p class="drawer-eyebrow">Result Drawer</p>
        <h3>推演详情</h3>
      </div>
      <button type="button" class="ghost drawer-close" data-close-result-drawer>关闭</button>
    </div>
    <div class="drawer-content">
      <section class="drawer-section">
        <h4>主结论</h4>
        <div class="drawer-summary" data-drawer-summary></div>
      </section>
      <section class="drawer-section">
        <h4>卡片详情</h4>
        <div class="drawer-card" data-drawer-card></div>
      </section>
      <section class="drawer-section">
        <h4>推演轨迹</h4>
        <div class="drawer-timeline" data-drawer-timeline></div>
      </section>
    </div>
  `;

  drawerRoot.querySelector("[data-close-result-drawer]").addEventListener("click", closeResultDrawer);
  document.body.append(drawerBackdrop, drawerRoot);
}

function renderDrawerContent(container, cardIndex = null) {
  ensureDrawer();
  const state = getResultState(container);
  const data = state.data;
  const summaryNode = drawerRoot.querySelector("[data-drawer-summary]");
  const cardNode = drawerRoot.querySelector("[data-drawer-card]");
  const timelineNode = drawerRoot.querySelector("[data-drawer-timeline]");

  if (!data) {
    summaryNode.innerHTML = `<p class="drawer-empty">暂无结果，提交后这里会显示完整推演。</p>`;
    cardNode.innerHTML = `<p class="drawer-empty">还没有可展开的卡片。</p>`;
  } else {
    summaryNode.innerHTML = `
      <article class="drawer-summary-card">
        <h5>${escapeHtml(data.headline || "占卜结果")}</h5>
        <p>${normalizeMultiline(data.summary || "")}</p>
        <span class="badge">模块: ${escapeHtml(data.module || "unknown")}</span>
      </article>
    `;

    const cards = Array.isArray(data.cards) ? data.cards : [];
    const safeIndex = Number.isInteger(cardIndex) ? cardIndex : Math.max(cards.length - 1, 0);
    const selectedCard = cards[safeIndex];

    if (selectedCard) {
      cardNode.innerHTML = `
        <article class="drawer-detail-card tone-${escapeHtml(selectedCard.tone || "neutral")}">
          <h5>${escapeHtml(selectedCard.title || "解读")}</h5>
          <p>${normalizeMultiline(selectedCard.content || "")}</p>
        </article>
      `;
      activeDrawerIndex = safeIndex;
    } else {
      cardNode.innerHTML = `<p class="drawer-empty">当前结果没有明细卡片。</p>`;
      activeDrawerIndex = null;
    }
  }

  const timeline = state.timeline || [];
  if (!timeline.length) {
    timelineNode.innerHTML = `<p class="drawer-empty">暂无推演轨迹。</p>`;
    return;
  }

  timelineNode.innerHTML = timeline
    .map(
      (item, index) => `
        <article class="timeline-item timeline-${escapeHtml(item.kind || "info")}">
          <span class="timeline-index">${index + 1}</span>
          <div>
            <h5>${escapeHtml(item.label || "状态更新")}</h5>
            <p>${normalizeMultiline(item.detail || "")}</p>
          </div>
        </article>
      `,
    )
    .join("\n");
}

function openResultDrawer(container, cardIndex = null) {
  ensureDrawer();
  activeDrawerContainer = container;
  renderDrawerContent(container, cardIndex);
  drawerBackdrop.classList.add("open");
  drawerRoot.classList.add("open");
  document.body.classList.add("drawer-open");
}

function closeResultDrawer() {
  if (!drawerRoot || !drawerBackdrop) {
    return;
  }
  drawerBackdrop.classList.remove("open");
  drawerRoot.classList.remove("open");
  document.body.classList.remove("drawer-open");
}

function appendTimeline(container, entry) {
  const state = getResultState(container);
  const timeline = [...state.timeline, entry].slice(-12);
  updateResultState(container, { timeline });
}

function buildCardAction(container, label, index = "") {
  return `<button type="button" class="card-action" data-open-result-drawer="true" data-card-index="${escapeHtml(index)}">${escapeHtml(label)}</button>`;
}

function setSubmitting(btn, loading, text) {
  btn.disabled = loading;
  if (text) btn.textContent = text;
  if (loading) btn.classList.add("loading");
  else btn.classList.remove("loading");
}

function renderLoading(container) {
  updateResultState(container, {
    data: null,
    timeline: [{ label: "已发送请求", detail: "正在建立流式连接并准备推演。", kind: "pending" }],
  });
  container.innerHTML = `
    <article class="result-card muted">
      <h3>占卜中\u2026</h3>
      <p>正在推演，请稍候。若服务支持流式输出，卡片会逐步出现。</p>
    </article>
  `;
}

function renderCards(container, data) {
  const state = getResultState(container);
  updateResultState(container, { data, timeline: state.timeline });
  const cards = [];

  cards.push(`
    <article class="result-card headline">
      <div class="result-card-headline-row">
        <h3>${escapeHtml(data.headline || "占卜结果")}</h3>
        ${buildCardAction(container, "结果抽屉")}
      </div>
      <p>${normalizeMultiline(data.summary || "")}</p>
      <span class="badge">\u6a21\u5757: ${escapeHtml(data.module || "unknown")}</span>
    </article>
  `);

  if (Array.isArray(data.cards)) {
    for (const [index, item] of data.cards.entries()) {
      const tone = item.tone || "neutral";
      cards.push(`
        <article class="result-card tone-${escapeHtml(tone)}">
          <div class="result-card-headline-row">
            <h3>${escapeHtml(item.title || "\u89e3\u8bfb")}</h3>
            ${buildCardAction(container, "展开", index)}
          </div>
          <p>${normalizeMultiline(item.content || "")}</p>
        </article>
      `);
    }
  }

  if (data.lot) {
    cards.push(`
      <article class="result-card lot-card">
        <div class="result-card-headline-row">
          <h3>\u7b7e\u53f7: \u7b2c${escapeHtml(data.lot.lot_no)}\u7b7e \u00b7 ${escapeHtml(data.lot.title)}</h3>
          ${buildCardAction(container, "结果抽屉")}
        </div>
        <p><strong>\u7b7e\u8bd7</strong><br />${normalizeMultiline(data.lot.poem || "")}</p>
        <p><strong>\u89e3\u7b7e</strong><br />${normalizeMultiline(data.lot.meaning || "")}</p>
      </article>
    `);
  }

  container.innerHTML = cards.join("\n");
}

function renderError(container, title, err) {
  appendTimeline(container, { label: title, detail: String(err), kind: "danger" });
  container.innerHTML = `
    <article class="result-card tone-danger">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(String(err))}</p>
    </article>
  `;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(window.userAuth?.getAuthHeaders?.() || {}),
    },
    body: JSON.stringify(payload),
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${JSON.stringify(data)}`);
  }

  return data;
}

async function streamReading(url, payload, container) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(window.userAuth?.getAuthHeaders?.() || {}),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    throw new Error(`${response.status} ${response.statusText}: ${JSON.stringify(data)}`);
  }

  if (!response.body) {
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    renderCards(container, data);
    return data;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult = null;

  function handleEventBlock(block) {
    let eventName = "message";
    const dataLines = [];

    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    if (!dataLines.length) {
      return;
    }

    const payloadData = JSON.parse(dataLines.join("\n"));
    if (eventName === "stage") {
      appendTimeline(container, {
        label: payloadData.message || "状态更新",
        detail: payloadData.detail || "",
        kind: "info",
      });
      return;
    }

    if (eventName === "card") {
      appendTimeline(container, {
        label: `已生成第 ${payloadData.step || 0} 步`,
        detail: payloadData.summary || "",
        kind: "progress",
      });
      renderCards(container, payloadData);
      return;
    }

    if (eventName === "result") {
      finalResult = payloadData;
      appendTimeline(container, {
        label: "推演完成",
        detail: payloadData.summary || "",
        kind: "success",
      });
      renderCards(container, payloadData);
      return;
    }

    if (eventName === "error") {
      throw new Error(payloadData.message || "流式请求失败");
    }
  }

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done }).replaceAll("\r", "");

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);
      if (block) {
        handleEventBlock(block);
      }
      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      if (buffer.trim()) {
        handleEventBlock(buffer.trim());
      }
      break;
    }
  }

  return finalResult;
}

document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-open-result-drawer]");
  if (trigger) {
    const container = trigger.closest(".result-panel")?.querySelector("#resultCards, .cards-wrap") || trigger.closest("#resultCards, .cards-wrap");
    if (container) {
      const rawIndex = trigger.getAttribute("data-card-index");
      const cardIndex = rawIndex === "" ? null : Number(rawIndex);
      openResultDrawer(container, Number.isNaN(cardIndex) ? null : cardIndex);
    }
  }

  if (event.target.closest("[data-close-result-drawer]")) {
    closeResultDrawer();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeResultDrawer();
  }
});
