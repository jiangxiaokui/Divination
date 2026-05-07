const resultCards = document.getElementById("resultCards");
const statusBox = document.getElementById("runtimeStatus");

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

function renderCards(data) {
  const cards = [];
  cards.push(`
    <article class="result-card headline">
      <h3>${escapeHtml(data.headline || "占卜结果")}</h3>
      <p>${normalizeMultiline(data.summary || "")}</p>
      <span class="badge">模块: ${escapeHtml(data.module || "unknown")}</span>
    </article>
  `);

  if (Array.isArray(data.cards)) {
    for (const item of data.cards) {
      const tone = item.tone || "neutral";
      cards.push(`
        <article class="result-card tone-${escapeHtml(tone)}">
          <h3>${escapeHtml(item.title || "解读")}</h3>
          <p>${normalizeMultiline(item.content || "")}</p>
        </article>
      `);
    }
  }

  if (data.lot) {
    cards.push(`
      <article class="result-card lot-card">
        <h3>签号: 第${escapeHtml(data.lot.lot_no)}签 · ${escapeHtml(data.lot.title)}</h3>
        <p><strong>签诗</strong><br />${normalizeMultiline(data.lot.poem || "")}</p>
        <p><strong>解签</strong><br />${normalizeMultiline(data.lot.meaning || "")}</p>
      </article>
    `);
  }

  cards.push(`
    <article class="result-card muted">
      <h3>追踪信息</h3>
      <p>session_id: ${escapeHtml(data.session_id)}<br />record_id: ${escapeHtml(data.record_id)}</p>
    </article>
  `);

  resultCards.innerHTML = cards.join("\n");
}

function showError(title, err) {
  resultCards.innerHTML = `
    <article class="result-card tone-danger">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(String(err))}</p>
    </article>
  `;
}

function safeJson(text, fallback) {
  if (!text || !text.trim()) return fallback;
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error("JSON 格式有误: " + err.message);
  }
}

async function req(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${JSON.stringify(data)}`);
  }
  return data;
}

async function initStatus() {
  try {
    await req("/healthz", { method: "GET" });
    statusBox.textContent = "服务在线，可直接使用占卜功能";
    statusBox.classList.add("ok");
  } catch (err) {
    statusBox.textContent = "服务状态检测失败: " + err.message;
    statusBox.classList.add("bad");
  }
}

document.getElementById("userForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    const payload = {
      nickname: form.nickname.value.trim(),
      profile_payload: safeJson(form.profile.value, null),
    };
    const data = await req("/api/v1/users", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderCards({
      module: "user",
      headline: "用户创建成功",
      summary: `用户ID: ${data.id}，昵称: ${data.nickname}`,
      cards: [
        {
          title: "说明",
          content: "该用户可在后续占卜表单里使用 user_id 关联历史记录。",
          tone: "info",
        },
      ],
      session_id: "-",
      record_id: "-",
    });
  } catch (err) {
    showError("用户创建失败", err);
  }
});

async function submitReading(module, payload) {
  const data = await req(`/api/v1/readings/${module}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  renderCards(data);
}

document.getElementById("baziForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    await submitReading("bazi", {
      user_id: form.userId.value ? Number(form.userId.value) : null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", form: "bazi" },
      input_payload: {
        birth_datetime: form.birthDatetime.value,
        birth_place: form.birthPlace.value.trim() || null,
        gender: form.gender.value,
      },
    });
  } catch (err) {
    showError("八字请求失败", err);
  }
});

document.getElementById("liuyaoForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    const lineValues = form.lineValues.value
      .split(",")
      .map((v) => Number(v.trim()))
      .filter((v) => [6, 7, 8, 9].includes(v));

    await submitReading("liuyao", {
      user_id: form.userId.value ? Number(form.userId.value) : null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", form: "liuyao" },
      input_payload: {
        question_type: form.questionType.value,
        casting_method: form.castingMethod.value,
        line_values: lineValues,
      },
    });
  } catch (err) {
    showError("六爻请求失败", err);
  }
});

document.getElementById("nameForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    await submitReading("name_wuge", {
      user_id: form.userId.value ? Number(form.userId.value) : null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", form: "name_wuge" },
      input_payload: {
        full_name: form.fullName.value.trim(),
        script_type: form.scriptType.value,
        gender: form.gender.value,
      },
    });
  } catch (err) {
    showError("姓名学请求失败", err);
  }
});

document.getElementById("tarotForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    await submitReading("tarot", {
      user_id: form.userId.value ? Number(form.userId.value) : null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", form: "tarot" },
      input_payload: {
        question_type: form.questionType.value,
        spread: form.spread.value,
        allow_reversed: form.allowReversed.value === "true",
      },
    });
  } catch (err) {
    showError("塔罗请求失败", err);
  }
});

document.getElementById("lotForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    const payload = {
      user_id: form.userId.value ? Number(form.userId.value) : null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui" },
      input_payload: {},
      seed: form.seed.value ? Number(form.seed.value) : null,
    };
    const lotType = form.lotType.value;
    const data = await req(`/api/v1/lots/${lotType}/reading`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderCards(data);
  } catch (err) {
    showError("抽签失败", err);
  }
});

document.getElementById("clearResult").addEventListener("click", () => {
  resultCards.innerHTML = `
    <article class="result-card muted">
      <h3>等待占卜</h3>
      <p>填写任意模块并提交后，这里会显示结构化结果卡片。</p>
    </article>
  `;
});

initStatus();
