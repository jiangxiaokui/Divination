const statusBox = document.getElementById("runtimeStatus");
const introRoot = document.getElementById("bookIntro");
const bookShell = document.getElementById("bookShell");
const bookOpenBtn = document.getElementById("bookOpenBtn");
const bookSkip = document.getElementById("bookSkip");
const introDoneKey = "xj_intro_seen";
let introSeenMemory = "0";

function readIntroSeen() {
  try {
    return sessionStorage.getItem(introDoneKey) || introSeenMemory;
  } catch {
    return introSeenMemory;
  }
}

function writeIntroSeen(value) {
  introSeenMemory = value;
  try {
    sessionStorage.setItem(introDoneKey, value);
  } catch {
    // ignore storage failures in private/blocked contexts
  }
}

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

function unlockPortal(withAnimation = true) {
  if (!introRoot) {
    return;
  }

  document.body.classList.remove("portal-revealed", "portal-settled");

  if (withAnimation) {
    document.body.classList.add("portal-unsealing");
    introRoot.classList.add("opening");
    window.XJImmersive?.playBookOpen?.();
    bookShell?.setAttribute("aria-disabled", "true");
    window.setTimeout(() => {
      introRoot.classList.add("done");
      document.body.classList.remove("portal-locked");
      document.body.classList.remove("portal-unsealing");
      document.body.classList.add("portal-revealed");
      window.setTimeout(() => {
        document.body.classList.add("portal-settled");
      }, 180);
    }, 1150);
  } else {
    introRoot.classList.add("done");
    document.body.classList.remove("portal-locked");
    document.body.classList.add("portal-revealed");
    document.body.classList.add("portal-settled");
  }
}

function bindBookIntro() {
  if (!introRoot || !bookShell) {
    document.body.classList.remove("portal-locked");
    return;
  }

  if (readIntroSeen() === "1") {
    unlockPortal(false);
    return;
  }

  const openBook = () => {
    if (introRoot.classList.contains("opening") || introRoot.classList.contains("done")) {
      return;
    }
    writeIntroSeen("1");
    unlockPortal(true);
  };

  bookShell.addEventListener("click", openBook);
  introRoot.addEventListener("click", (event) => {
    if (event.target.closest("#bookSkip")) {
      return;
    }
    if (event.target.closest("#bookShell") || event.target.closest("#bookOpenBtn")) {
      openBook();
    }
  });
  bookShell.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openBook();
    }
  });
  bookOpenBtn?.addEventListener("click", (event) => {
    event.stopPropagation();
    openBook();
  });

  bookSkip?.addEventListener("click", () => {
    writeIntroSeen("1");
    unlockPortal(false);
  });
}

bindBookIntro();
initStatus();
