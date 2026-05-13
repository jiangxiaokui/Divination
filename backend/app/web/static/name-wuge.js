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
const nameForm = document.getElementById("nameForm");

initPageState({
  pageKey: "name_wuge",
  form: nameForm,
  resultContainer: resultCards,
});

function resetResult() {
  resultCards.innerHTML =
    '<article class="result-card muted"><h3>等待分析</h3><p>提交后这里会显示最终结果。</p></article>';
}

nameForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;

  renderLoading(resultCards);
  setSubmitting(submitBtn, true, "分析中…");

  try {
    await streamReading("/api/v1/readings/name_wuge/stream", {
      user_id: null,
      question: form.question.value.trim() || null,
      client_meta: { from: "web-ui", page: "name_wuge" },
      reading_mode: form.readingMode.value,
      input_payload: {
        full_name: form.fullName.value.trim(),
        script_type: form.scriptType.value,
        gender: form.gender.value,
      },
    }, resultCards);
  } catch (err) {
    renderError(resultCards, "姓名学分析失败", err);
  } finally {
    setSubmitting(submitBtn, false, "开始分析");
  }
});

document.getElementById("clearResult").addEventListener("click", resetResult);
