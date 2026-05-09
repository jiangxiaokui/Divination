// ── 填充年份 ──
const yearSel = document.querySelector('[name="birthYear"]');
const curYear = new Date().getFullYear();
for (let y = curYear - 10; y >= 1920; y--) {
  yearSel.insertAdjacentHTML("beforeend", `<option value="${y}">${y} 年</option>`);
}

// ── 填充月份 ──
const monthSel = document.querySelector('[name="birthMonth"]');
const MONTH_NAMES = ["一","二","三","四","五","六","七","八","九","十","十一","十二"];
MONTH_NAMES.forEach((m, i) => {
  monthSel.insertAdjacentHTML("beforeend", `<option value="${i+1}">${i+1} 月（${m}月）</option>`);
});

// ── 动态填充日（基于年月）──
const daySel = document.querySelector('[name="birthDay"]');
function updateDays() {
  const y = Number(yearSel.value) || 2000;
  const m = Number(monthSel.value) || 1;
  const prev = daySel.value;
  const maxDay = new Date(y, m, 0).getDate();
  daySel.innerHTML = '<option value="">日</option>';
  for (let d = 1; d <= maxDay; d++) {
    daySel.insertAdjacentHTML("beforeend",
      `<option value="${d}"${String(d) === prev ? " selected" : ""}>${d} 日</option>`);
  }
}
yearSel.addEventListener("change", updateDays);
monthSel.addEventListener("change", updateDays);
updateDays();

// ── 填充时辰 ──
const hourSel = document.querySelector('[name="birthHour"]');
const SHIZHI = [
  ["子时", "0", "0~1 时"],["丑时", "1", "1~3 时"],["寅时", "3", "3~5 时"],
  ["卯时", "5", "5~7 时"],["辰时", "7", "7~9 时"],["巳时", "9", "9~11 时"],
  ["午时", "11", "11~13 时"],["未时", "13", "13~15 时"],["申时", "15", "15~17 时"],
  ["酉时", "17", "17~19 时"],["戌时", "19", "19~21 时"],["亥时", "21", "21~23 时"],
  ["不清楚", "12", ""],
];
SHIZHI.forEach(([name, val, range]) => {
  hourSel.insertAdjacentHTML("beforeend",
    `<option value="${val}">${name}${range ? "（" + range + "）" : ""}</option>`);
});

// ── 模式切换 ──
document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelector('[name="readingMode"]').value = btn.dataset.mode;
  });
});

// ── 表单提交 ──
const resultCards = document.getElementById("resultCards");
const submitBtn   = document.getElementById("submitBtn");

function resetResult() {
  resultCards.innerHTML =
    '<article class="result-card muted"><h3>等待占卜</h3><p>提交后这里会显示最终结果。</p></article>';
}

document.getElementById("baziForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;

  const year  = form.birthYear.value;
  const month = String(form.birthMonth.value).padStart(2, "0");
  const day   = String(form.birthDay.value).padStart(2, "0");
  const hour  = String(form.birthHour.value || "12").padStart(2, "0");
  const birthDatetime = `${year}-${month}-${day}T${hour}:00`;

  renderLoading(resultCards);
  setSubmitting(submitBtn, true, "测算中…");

  try {
    await streamReading("/api/v1/readings/bazi/stream", {
      user_id: null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", page: "bazi" },
      reading_mode: form.readingMode.value,
      input_payload: {
        birth_datetime: birthDatetime,
        birth_place: form.birthPlace.value.trim() || null,
        gender: form.gender.value,
      },
    });
  } catch (err) {
    renderError(resultCards, "八字测算失败", err);
  } finally {
    setSubmitting(submitBtn, false, "开始测算");
  }
});

document.getElementById("clearResult").addEventListener("click", resetResult);
