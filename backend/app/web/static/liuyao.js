// Mode toggle
document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelector('[name="readingMode"]').value = btn.dataset.mode;
  });
});

const resultCards = document.getElementById("resultCards");
const submitBtn   = document.getElementById("submitBtn");
const liuyaoForm = document.getElementById("liuyaoForm");
const castingMethod = document.querySelector('[name="castingMethod"]');
const lineValuesInput = document.querySelector('[name="lineValues"]');

const pageState = initPageState({
  pageKey: "liuyao",
  form: liuyaoForm,
  resultContainer: resultCards,
});

function syncLineValuesHint() {
  if (!castingMethod || !lineValuesInput) {
    return;
  }

  if (castingMethod.value === "manual") {
    lineValuesInput.placeholder = "7,8,7,9,8,7";
    lineValuesInput.title = "手动录入需填写 6 个爻值（仅限 6/7/8/9，逗号分隔）";
  } else {
    lineValuesInput.placeholder = "可留空，系统将按问题自动模拟起卦";
    lineValuesInput.title = "铜钱法可留空，系统会自动生成六爻";
  }
}

function resetResult() {
  resultCards.innerHTML =
    '<article class="result-card muted"><h3>等待占卜</h3><p>提交后这里会显示最终结果。</p></article>';
}

function buildCoinFace(result) {
  return result === 3 ? "乾" : "坤";
}

function renderCoinCasting(container, method) {
  const methodLabel = method === "manual" ? "手动爻值已就绪，正在归盘" : "铜钱起卦中";
  container.innerHTML = `
    <article class="result-card headline coin-casting altar-casting ${method === "coin" ? "is-random" : "is-manual"}">
      <div class="casting-backdrop"></div>
      <h3>${methodLabel}</h3>
      <p class="casting-subline">法坛已启，逐爻推演正在展开。每一轮都会落下一爻，再汇总成卦。</p>
      <div class="coin-stage" aria-hidden="true">
        <span class="coin coin-1"><span class="coin-face">乾</span></span>
        <span class="coin coin-2"><span class="coin-face">坤</span></span>
        <span class="coin coin-3"><span class="coin-face">乾</span></span>
      </div>
      <div class="hex-progress" aria-hidden="true" data-casting-progress>
        <span></span><span></span><span></span><span></span><span></span><span></span>
      </div>
      <div class="casting-lines" data-casting-lines>
        <div class="casting-line-slot"><span>初爻</span><strong>待定</strong></div>
        <div class="casting-line-slot"><span>二爻</span><strong>待定</strong></div>
        <div class="casting-line-slot"><span>三爻</span><strong>待定</strong></div>
        <div class="casting-line-slot"><span>四爻</span><strong>待定</strong></div>
        <div class="casting-line-slot"><span>五爻</span><strong>待定</strong></div>
        <div class="casting-line-slot"><span>上爻</span><strong>待定</strong></div>
      </div>
      <div class="casting-journal" data-casting-journal>法器就位，准备落下第一爻。</div>
    </article>
  `;
}

function buildLineLabel(lineValue) {
  if (lineValue === 6) return "老阴";
  if (lineValue === 7) return "少阳";
  if (lineValue === 8) return "少阴";
  return "老阳";
}

function setCoinFaces(container, tosses) {
  container.querySelectorAll(".coin").forEach((coinNode, index) => {
    const toss = tosses[index] ?? 3;
    const face = coinNode.querySelector(".coin-face");
    if (face) {
      face.textContent = buildCoinFace(toss);
    }
    coinNode.classList.remove("coin-burst");
    void coinNode.offsetWidth;
    coinNode.classList.add("coin-burst");
  });
}

function updateCastingLine(container, lineIndex, lineValue, tosses) {
  const slot = container.querySelectorAll(".casting-line-slot")[lineIndex];
  if (!slot) {
    return;
  }

  const strong = slot.querySelector("strong");
  slot.classList.add("is-done");
  strong.textContent = `${buildLineLabel(lineValue)} · ${lineValue}`;
  slot.style.setProperty("--line-width", lineValue === 7 || lineValue === 9 ? "100%" : "42%");
  slot.dataset.toss = tosses.join("/");
}

function updateCastingProgress(container, completedCount, detailText) {
  const bars = container.querySelectorAll("[data-casting-progress] span");
  bars.forEach((bar, index) => {
    bar.classList.toggle("is-filled", index < completedCount);
  });

  const journal = container.querySelector("[data-casting-journal]");
  if (journal) {
    journal.textContent = detailText;
  }
}

function randomCoinTosses() {
  return Array.from({ length: 3 }, () => (Math.random() > 0.5 ? 3 : 2));
}

function lineValueFromTosses(tosses) {
  return tosses.reduce((sum, value) => sum + value, 0);
}

async function playCastingAnimation(container, method, presetLines = []) {
  renderCoinCasting(container, method);
  const lines = [];

  for (let index = 0; index < 6; index += 1) {
    const tosses = method === "coin"
      ? randomCoinTosses()
      : Array.from({ length: 3 }, (_, tossIndex) => ((presetLines[index] ?? 7) + tossIndex) % 2 === 0 ? 2 : 3);
    const lineValue = method === "coin" ? lineValueFromTosses(tosses) : (presetLines[index] ?? 7);
    lines.push(lineValue);
    setCoinFaces(container, tosses);
    window.XJImmersive?.playCoin?.();
    updateCastingProgress(container, index, `第 ${index + 1} 轮铜钱落盘中，正在校准卦气。`);
    await new Promise((resolve) => window.setTimeout(resolve, 620));
    updateCastingLine(container, index, lineValue, tosses);
    updateCastingProgress(container, index + 1, `第 ${index + 1} 爻已定为 ${buildLineLabel(lineValue)}（${lineValue}），继续推演下一爻。`);
    await new Promise((resolve) => window.setTimeout(resolve, 320));
  }

  updateCastingProgress(container, 6, "六爻已成，正在归藏卦象并接入推算结果。\n");
  window.XJImmersive?.playReveal?.();
  await new Promise((resolve) => window.setTimeout(resolve, 780));
  return lines;
}

syncLineValuesHint();
castingMethod?.addEventListener("change", syncLineValuesHint);

liuyaoForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;

  const lineValues = form.lineValues.value
    .split(",")
    .map((v) => Number(v.trim()))
    .filter((v) => [6, 7, 8, 9].includes(v));

  if (form.castingMethod.value === "manual" && lineValues.length !== 6) {
    renderError(resultCards, "六爻占卜失败", new Error("手动录入模式下，请填写 6 个有效爻值（6/7/8/9）。"));
    return;
  }

  setSubmitting(submitBtn, true, "占卜中…");

  try {
    const resolvedLines = await playCastingAnimation(resultCards, form.castingMethod.value, lineValues);
    form.lineValues.value = resolvedLines.join(",");
    form.lineValues.dispatchEvent(new Event("input", { bubbles: true }));
    pageState.saveNow();
    renderLoading(resultCards);
    await streamReading("/api/v1/readings/liuyao/stream", {
      user_id: null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", page: "liuyao" },
      reading_mode: form.readingMode.value,
      input_payload: {
        question_type: form.questionType.value,
        casting_method: form.castingMethod.value,
        line_values: resolvedLines,
      },
    }, resultCards);
  } catch (err) {
    renderError(resultCards, "六爻占卜失败", err);
  } finally {
    setSubmitting(submitBtn, false, "开始占卜");
  }
});

document.getElementById("clearResult").addEventListener("click", resetResult);
