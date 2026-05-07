const statusBox = document.getElementById("runtimeStatus");

async function req(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function initStatus() {
  try {
    await req("/healthz");
    statusBox.textContent = "服务在线，选择模块开始占卜";
    statusBox.classList.add("ok");
  } catch (err) {
    statusBox.textContent = "服务不可用: " + err.message;
    statusBox.classList.add("bad");
  }
}

initStatus();
