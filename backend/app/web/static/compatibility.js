document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach((item) => item.classList.remove("active"));
    btn.classList.add("active");
    document.querySelector('[name="readingMode"]').value = btn.dataset.mode;
  });
});

const resultCards = document.getElementById("resultCards");
const submitBtn = document.getElementById("submitBtn");
const compatibilityForm = document.getElementById("compatibilityForm");

initPageState({
  pageKey: "compatibility",
  form: compatibilityForm,
  resultContainer: resultCards,
});

function resetResult() {
  resultCards.innerHTML =
    '<article class="result-card muted"><h3>等待合盘</h3><p>提交关系信息后，这里会逐步显示缘分走势与建议。</p></article>';
}

compatibilityForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;

  renderLoading(resultCards);
  setSubmitting(submitBtn, true, "合盘中…");

  try {
    await streamReading("/api/v1/readings/compatibility/stream", {
      user_id: null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", page: "compatibility" },
      reading_mode: form.readingMode.value,
      input_payload: {
        person_a: form.personA.value.trim(),
        person_b: form.personB.value.trim(),
        focus: form.focus.value,
        relation_stage: form.relationStage.value,
      },
    }, resultCards);
  } catch (err) {
    renderError(resultCards, "姻缘合盘失败", err);
  } finally {
    setSubmitting(submitBtn, false, "开始合盘");
  }
});

document.getElementById("clearResult").addEventListener("click", resetResult);