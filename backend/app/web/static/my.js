const userCenterStatus = document.getElementById("userCenterStatus");
const authForm = document.getElementById("authForm");
const authSubmitBtn = document.getElementById("authSubmitBtn");
const logoutUserBtn = document.getElementById("logoutUserBtn");
const authGuestView = document.getElementById("authGuestView");
const authSignedView = document.getElementById("authSignedView");
const authSignedSummary = document.getElementById("authSignedSummary");
const refreshProfileBtn = document.getElementById("refreshProfileBtn");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const saveProfileBtn = document.getElementById("saveProfileBtn");
const profileCards = document.getElementById("profileCards");
const historyCards = document.getElementById("historyCards");
const profileForm = document.getElementById("profileForm");
const registerOnlyFields = Array.from(document.querySelectorAll("[data-register-only]"));
let authMode = "login";
const historyExpandedSessions = new Set();
let latestHistoryData = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeProfilePayload(profile) {
  const source = profile || {};
  const tags = Array.isArray(source.tags)
    ? source.tags.filter(Boolean)
    : String(source.tags || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

  return {
    city: source.city || "",
    gender: source.gender || "",
    birth_year: source.birth_year || "",
    relationship_status: source.relationship_status || "",
    tags,
    bio: source.bio || "",
    notes: source.notes || "",
  };
}

function formatGenderLabel(value) {
  const mapping = {
    male: "男",
    female: "女",
    other: "其他",
  };
  return mapping[value] || value || "";
}

function buildRegisterProfilePayload(form) {
  const tags = form.registerTags.value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const payload = {
    city: form.registerCity.value.trim() || null,
    gender: form.registerGender.value || null,
    relationship_status: form.registerRelationshipStatus.value.trim() || null,
    tags,
    bio: form.registerBio.value.trim() || null,
  };

  const normalized = Object.fromEntries(Object.entries(payload).filter(([, value]) => {
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return value !== null && value !== "";
  }));

  return Object.keys(normalized).length ? normalized : null;
}

function renderAuthPanel(user) {
  const loggedIn = Boolean(user);
  authGuestView.hidden = loggedIn;
  authSignedView.hidden = !loggedIn;

  if (!loggedIn) {
    authSignedSummary.innerHTML = '<article class="result-card tone-info"><h3>未登录</h3><p>登录后这里会显示当前账号概览。</p></article>';
    return;
  }

  const profile = normalizeProfilePayload(user.profile_payload);
  const summary = [
    profile.city ? `城市: ${profile.city}` : null,
    profile.relationship_status ? `情感状态: ${profile.relationship_status}` : null,
    profile.tags.length ? `标签: ${profile.tags.join("、")}` : null,
  ].filter(Boolean);

  authSignedSummary.innerHTML = `
    <article class="result-card tone-info">
      <h3>${escapeHtml(user.nickname)}</h3>
      <p>用户名: ${escapeHtml(user.username)}</p>
      <p>${escapeHtml(summary.join(" | ") || "已登录，可直接查看档案与历史记录。")}</p>
    </article>
  `;
}

function setProfileFormEnabled(enabled) {
  Array.from(profileForm.elements).forEach((element) => {
    element.disabled = !enabled;
  });
  saveProfileBtn.disabled = !enabled;
}

function fillProfileForm(user) {
  if (!user) {
    profileForm.reset();
    setProfileFormEnabled(false);
    return;
  }

  const profile = normalizeProfilePayload(user.profile_payload);
  profileForm.nickname.value = user.nickname || "";
  profileForm.city.value = profile.city;
  profileForm.gender.value = profile.gender;
  profileForm.birthYear.value = profile.birth_year || "";
  profileForm.relationshipStatus.value = profile.relationship_status;
  profileForm.tags.value = profile.tags.join(", ");
  profileForm.bio.value = profile.bio;
  profileForm.notes.value = profile.notes;
  setProfileFormEnabled(true);
}

function setAuthMode(nextMode) {
  authMode = nextMode;
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.authMode === nextMode);
  });
  registerOnlyFields.forEach((field) => {
    const visible = nextMode === "register";
    field.hidden = !visible;
    field.style.display = visible ? "" : "none";
    field.querySelectorAll("input, textarea, select").forEach((input) => {
      input.required = visible && input.name === "nickname";
      if (!visible) {
        input.setCustomValidity("");
      }
    });
  });
  authSubmitBtn.textContent = nextMode === "register" ? "注册并登录" : "登录";
}

function renderProfile(user) {
  if (!user) {
    renderAuthPanel(null);
    profileCards.innerHTML = '<article class="result-card muted"><h3>未登录</h3><p>登录后可查看并维护个人档案信息。</p></article>';
    fillProfileForm(null);
    return;
  }

  renderAuthPanel(user);

  const profile = normalizeProfilePayload(user.profile_payload);
  const facts = [
    profile.city ? `城市: ${profile.city}` : null,
    profile.gender ? `性别: ${formatGenderLabel(profile.gender)}` : null,
    profile.birth_year ? `出生年份: ${profile.birth_year}` : null,
    profile.relationship_status ? `情感状态: ${profile.relationship_status}` : null,
  ].filter(Boolean);

  profileCards.innerHTML = `
    <article class="result-card headline">
      <h3>${escapeHtml(user.nickname)}</h3>
      <p>用户名: ${escapeHtml(user.username)}</p>
      <span class="badge">用户 ID: ${escapeHtml(user.id)}</span>
    </article>
    <article class="result-card tone-info">
      <h3>档案摘要</h3>
      <p>${escapeHtml(facts.join(" | ") || "你还没有填写结构化档案信息。")}</p>
      <p>${escapeHtml(profile.bio || "暂无个人简介")}</p>
      <p>${escapeHtml(profile.tags.length ? `标签: ${profile.tags.join("、")}` : "暂无兴趣标签")}</p>
    </article>
  `;
  fillProfileForm(user);
}

function renderHistory(data) {
  latestHistoryData = data;
  const sessions = data?.sessions || [];
  if (!sessions.length) {
    historyCards.innerHTML = '<article class="result-card muted"><h3>暂无历史</h3><p>登录后产生的占卜记录会显示在这里。</p></article>';
    return;
  }

  historyCards.innerHTML = sessions
    .map((session) => {
      const expanded = historyExpandedSessions.has(session.session_id);
      const recordsText = session.records
        .map((record) => `${record.module} #${record.record_id}`)
        .join(" / ");
      const detailHtml = expanded
        ? session.records
            .map((record) => `
              <div class="history-detail-item">
                <div class="result-card-headline-row">
                  <h4>${escapeHtml(record.module)} · #${escapeHtml(record.record_id)}</h4>
                  <button type="button" class="card-action" data-open-history-detail="${escapeHtml(record.record_id)}" data-session-id="${escapeHtml(session.session_id)}">查看详情</button>
                </div>
                <p>时间: ${escapeHtml(new Date(record.created_at).toLocaleString("zh-CN"))}</p>
                <p>${escapeHtml(record.final_text || "暂无总结")}</p>
              </div>
            `)
            .join("")
        : "";
      return `
        <article class="result-card tone-neutral">
          <div class="result-card-headline-row">
            <h3>${escapeHtml(session.category)} · 会话 #${escapeHtml(session.session_id)}</h3>
            <button type="button" class="card-action" data-toggle-history-session="${escapeHtml(session.session_id)}">${expanded ? "收起" : "展开"}</button>
          </div>
          <p>问题: ${escapeHtml(session.question || "未填写")}</p>
          <p>时间: ${escapeHtml(new Date(session.created_at).toLocaleString("zh-CN"))}</p>
          <p>记录: ${escapeHtml(recordsText || "无")}</p>
          ${expanded ? `<div class="history-detail-list">${detailHtml}</div>` : ""}
        </article>
      `;
    })
    .join("\n");
}

function openRecordDetail(record) {
  const detailWindow = document.createElement("div");
  detailWindow.className = "result-drawer-backdrop open";
  detailWindow.innerHTML = `
    <aside class="result-drawer open history-detail-drawer">
      <div class="drawer-header">
        <div>
          <p class="drawer-eyebrow">History Detail</p>
          <h3>${escapeHtml(record.module)} · #${escapeHtml(record.record_id)}</h3>
        </div>
        <button type="button" class="ghost" data-close-history-detail>关闭</button>
      </div>
      <div class="drawer-content">
        <section class="drawer-section">
          <h4>结果摘要</h4>
          <pre>${escapeHtml(record.final_text || "暂无")}</pre>
        </section>
        <section class="drawer-section">
          <h4>输入参数</h4>
          <pre>${escapeHtml(JSON.stringify(record.input_payload || {}, null, 2))}</pre>
        </section>
        <section class="drawer-section">
          <h4>计算结果</h4>
          <pre>${escapeHtml(JSON.stringify(record.calc_result || {}, null, 2))}</pre>
        </section>
      </div>
    </aside>
  `;
  detailWindow.addEventListener("click", (event) => {
    if (event.target === detailWindow || event.target.closest("[data-close-history-detail]")) {
      detailWindow.remove();
    }
  });
  document.body.appendChild(detailWindow);
}

async function refreshUserCenter() {
  const session = window.userAuth.getUserSession();
  if (!session?.access_token) {
    userCenterStatus.textContent = "未登录，可直接体验游客模式";
    userCenterStatus.className = "status warn";
    latestHistoryData = null;
    historyExpandedSessions.clear();
    renderProfile(null);
    renderHistory(null);
    return;
  }

  try {
    const [user, history] = await Promise.all([
      window.userAuth.userReq("/api/v1/users/me", { method: "GET" }),
      window.userAuth.userReq("/api/v1/users/me/history", { method: "GET" }),
    ]);
    userCenterStatus.textContent = `已登录: ${user.nickname}`;
    userCenterStatus.className = "status ok";
    renderProfile(user);
    renderHistory(history);
  } catch (err) {
    window.userAuth.clearUserSession();
    userCenterStatus.textContent = `登录态失效: ${String(err)}`;
    userCenterStatus.className = "status bad";
    renderProfile(null);
    renderHistory(null);
  }
}

function buildProfilePayload() {
  const tags = profileForm.tags.value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const payload = {
    city: profileForm.city.value.trim() || null,
    gender: profileForm.gender.value || null,
    birth_year: profileForm.birthYear.value ? Number(profileForm.birthYear.value) : null,
    relationship_status: profileForm.relationshipStatus.value.trim() || null,
    tags,
    bio: profileForm.bio.value.trim() || null,
    notes: profileForm.notes.value.trim() || null,
  };

  return Object.fromEntries(Object.entries(payload).filter(([, value]) => {
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return value !== null && value !== "";
  }));
}

document.querySelectorAll("[data-auth-mode]").forEach((button) => {
  button.addEventListener("click", () => setAuthMode(button.dataset.authMode));
});

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const payload = {
      username: form.username.value.trim(),
      password: form.password.value,
    };
    if (authMode === "register") {
      payload.nickname = form.nickname.value.trim();
      payload.profile_payload = buildRegisterProfilePayload(form);
    }

    const data = await window.userAuth.userReq(
      authMode === "register" ? "/api/v1/users/register" : "/api/v1/users/login",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
    window.userAuth.setUserSession(data);
    await refreshUserCenter();
  } catch (err) {
    userCenterStatus.textContent = `操作失败: ${String(err)}`;
    userCenterStatus.className = "status bad";
  }
});

logoutUserBtn.addEventListener("click", async () => {
  try {
    const session = window.userAuth.getUserSession();
    if (session?.access_token) {
      await window.userAuth.userReq("/api/v1/users/logout", { method: "POST" });
    }
  } catch {
    // ignore logout failures
  }
  window.userAuth.clearUserSession();
  await refreshUserCenter();
});

refreshProfileBtn.addEventListener("click", refreshUserCenter);
refreshHistoryBtn.addEventListener("click", refreshUserCenter);
saveProfileBtn.addEventListener("click", () => profileForm.requestSubmit());

historyCards.addEventListener("click", (event) => {
  const toggle = event.target.closest("[data-toggle-history-session]");
  if (toggle) {
    const sessionId = Number(toggle.dataset.toggleHistorySession);
    if (historyExpandedSessions.has(sessionId)) {
      historyExpandedSessions.delete(sessionId);
    } else {
      historyExpandedSessions.add(sessionId);
    }
    renderHistory(latestHistoryData);
    return;
  }

  const detailButton = event.target.closest("[data-open-history-detail]");
  if (detailButton) {
    const sessionId = Number(detailButton.dataset.sessionId);
    const recordId = Number(detailButton.dataset.openHistoryDetail);
    const record = latestHistoryData?.sessions
      ?.find((session) => session.session_id === sessionId)
      ?.records?.find((item) => item.record_id === recordId);
    if (record) {
      openRecordDetail(record);
    }
  }
});

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const session = window.userAuth.getUserSession();
  if (!session?.access_token) {
    userCenterStatus.textContent = "请先登录后再修改个人档案";
    userCenterStatus.className = "status warn";
    return;
  }

  try {
    const updated = await window.userAuth.userReq("/api/v1/users/me", {
      method: "PATCH",
      body: JSON.stringify({
        nickname: profileForm.nickname.value.trim(),
        profile_payload: buildProfilePayload(),
      }),
    });
    userCenterStatus.textContent = `档案已更新: ${updated.nickname}`;
    userCenterStatus.className = "status ok";
    renderProfile(updated);
  } catch (err) {
    userCenterStatus.textContent = `档案保存失败: ${String(err)}`;
    userCenterStatus.className = "status bad";
  }
});

setAuthMode("login");
refreshUserCenter();