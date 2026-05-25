(function () {
  const form = document.getElementById("gateForm");
  const passwordInput = document.getElementById("gatePassword");
  const errorBox = document.getElementById("gateError");
  const submitBtn = document.getElementById("gateSubmit");

  function showError(message) {
    errorBox.hidden = false;
    errorBox.textContent = message;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    submitBtn.disabled = true;

    try {
      const response = await fetch("/api/v1/site-gate/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: passwordInput.value }),
      });

      if (!response.ok) {
        showError("口令不正确");
        return;
      }

      window.location.replace("/home");
    } catch {
      showError("无法连接服务，请稍后重试");
    } finally {
      submitBtn.disabled = false;
    }
  });
})();
