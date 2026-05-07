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

function resetResult() {
  resultCards.innerHTML =
    '<article class="result-card muted"><h3>等待占卜</h3><p>提交后这里会显示最终结果。</p></article>';
}

document.getElementById("liuyaoForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;

  const lineValues = form.lineValues.value
    .split(",")
    .map((v) => Number(v.trim()))
    .filter((v) => [6, 7, 8, 9].includes(v));

  renderLoading(resultCards);
  setSubmitting(submitBtn, true, "占卜中…");

  try {
    const data = await postJson("/api/v1/readings/liuyao", {
      user_id: null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", page: "liuyao" },
      reading_mode: form.readingMode.value,
      input_payload: {
        question_type: form.questionType.value,
        casting_method: form.castingMethod.value,
        line_values: lineValues,
      },
    });
    renderCards(resultCards, data);
  } catch (err) {
    renderError(resultCards, "六爻占卜失败", err);
  } finally {
    setSubmitting(submitBtn, false, "开始占卜");
  }
});

document.getElementById("clearResult").addEventListener("click", resetResult);
