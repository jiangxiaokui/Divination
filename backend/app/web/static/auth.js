(function () {
  const STORAGE_KEY = "user_session";

  function getUserSession() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
  }

  function setUserSession(session) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }

  function clearUserSession() {
    localStorage.removeItem(STORAGE_KEY);
  }

  function getAuthHeaders() {
    const session = getUserSession();
    if (!session?.access_token) {
      return {};
    }
    return { Authorization: `Bearer ${session.access_token}` };
  }

  async function userReq(url, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...(options.headers || {}),
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    const text = await response.text();
    let data = {};
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text };
      }
    }

    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}: ${JSON.stringify(data)}`);
    }

    return data;
  }

  window.userAuth = {
    getUserSession,
    setUserSession,
    clearUserSession,
    getAuthHeaders,
    userReq,
  };
})();