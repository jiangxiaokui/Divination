document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach((item) => item.classList.remove("active"));
    btn.classList.add("active");
    document.querySelector('[name="readingMode"]').value = btn.dataset.mode;
  });
});

const resultCards = document.getElementById("resultCards");
const submitBtn = document.getElementById("submitBtn");

function resetResult() {
  resultCards.innerHTML =
    '<article class="result-card muted"><h3>等待解析</h3><p>提交梦境后，这里会逐步显示推演结果。</p></article>';
}

document.getElementById("dreamForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;

  renderLoading(resultCards);
  setSubmitting(submitBtn, true, "解析中…");

  try {
    await streamReading("/api/v1/readings/dream/stream", {
      user_id: null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", page: "dream" },
      reading_mode: form.readingMode.value,
      input_payload: {
        dream_text: form.dreamText.value.trim(),
        emotion: form.emotion.value,
        recent_focus: form.recentFocus.value,
        symbols: form.symbols.value.trim(),
      },
    }, resultCards);
  } catch (err) {
    renderError(resultCards, "梦境解析失败", err);
  } finally {
    setSubmitting(submitBtn, false, "开始解梦");
  }
});

document.getElementById("clearResult").addEventListener("click", resetResult);