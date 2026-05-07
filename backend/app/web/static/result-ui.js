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

function setSubmitting(btn, loading, text) {
  btn.disabled = loading;
  if (text) btn.textContent = text;
  if (loading) btn.classList.add("loading");
  else btn.classList.remove("loading");
}

function renderLoading(container) {
  container.innerHTML = `
    <article class="result-card muted">
      <h3>占卜中\u2026</h3>
      <p>正在推演，请稍候。</p>
    </article>
  `;
}

function renderCards(container, data) {
  const cards = [];

  cards.push(`
    <article class="result-card headline">
      <h3>${escapeHtml(data.headline || "占卜结果")}</h3>
      <p>${normalizeMultiline(data.summary || "")}</p>
      <span class="badge">\u6a21\u5757: ${escapeHtml(data.module || "unknown")}</span>
    </article>
  `);

  if (Array.isArray(data.cards)) {
    for (const item of data.cards) {
      const tone = item.tone || "neutral";
      cards.push(`
        <article class="result-card tone-${escapeHtml(tone)}">
          <h3>${escapeHtml(item.title || "\u89e3\u8bfb")}</h3>
          <p>${normalizeMultiline(item.content || "")}</p>
        </article>
      `);
    }
  }

  if (data.lot) {
    cards.push(`
      <article class="result-card lot-card">
        <h3>\u7b7e\u53f7: \u7b2c${escapeHtml(data.lot.lot_no)}\u7b7e \u00b7 ${escapeHtml(data.lot.title)}</h3>
        <p><strong>\u7b7e\u8bd7</strong><br />${normalizeMultiline(data.lot.poem || "")}</p>
        <p><strong>\u89e3\u7b7e</strong><br />${normalizeMultiline(data.lot.meaning || "")}</p>
      </article>
    `);
  }

  container.innerHTML = cards.join("\n");
}

function renderError(container, title, err) {
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${JSON.stringify(data)}`);
  }

  return data;
}
