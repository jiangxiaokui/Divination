const loginState = document.getElementById("loginState");
const runtimeBox = document.getElementById("runtimeBox");
const recordsBox = document.getElementById("recordsBox");
const STORAGE_KEY = "admin_token";

function getToken() {
  return localStorage.getItem(STORAGE_KEY);
}

function setToken(token) {
  localStorage.setItem(STORAGE_KEY, token);
}

function clearToken() {
  localStorage.removeItem(STORAGE_KEY);
}

function updateLoginState() {
  if (getToken()) {
    loginState.textContent = "已登录";
  } else {
    loginState.textContent = "未登录";
  }
}

async function adminReq(url, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${JSON.stringify(data)}`);
  }
  return data;
}

document.getElementById("adminLoginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    const data = await adminReq("/api/v1/admin/login", {
      method: "POST",
      body: JSON.stringify({
        username: form.username.value.trim(),
        password: form.password.value,
      }),
    });
    setToken(data.access_token);
    updateLoginState();
    runtimeBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    runtimeBox.textContent = String(err);
  }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  try {
    if (getToken()) {
      await adminReq("/api/v1/admin/logout", { method: "POST" });
    }
  } catch (err) {
    // ignore logout errors
  }
  clearToken();
  updateLoginState();
  runtimeBox.textContent = "已退出登录";
  recordsBox.textContent = "请先登录后加载记录...";
});

document.getElementById("runtimeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await adminReq("/api/v1/admin/runtime", { method: "GET" });
    runtimeBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    runtimeBox.textContent = String(err);
  }
});

document.getElementById("recordsForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    const limit = Number(form.limit.value || 50);
    const data = await adminReq(`/api/v1/admin/records?limit=${limit}&offset=0`, {
      method: "GET",
    });
    recordsBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    recordsBox.textContent = String(err);
  }
});

updateLoginState();
