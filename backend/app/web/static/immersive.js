(function () {
  const SOUND_PREF_KEY = "xj_sound_enabled";
  let overlay;
  let audioContext = null;
  let masterGain = null;
  let ambientGain = null;
  let ambientStarted = false;
  let chimeTimer = null;
  let soundButton = null;
  let soundEnabled = readStoredSoundPref();

  function readStoredSoundPref() {
    try {
      const stored = localStorage.getItem(SOUND_PREF_KEY);
      return stored == null ? true : stored === "1";
    } catch {
      return true;
    }
  }

  function writeStoredSoundPref(value) {
    soundEnabled = value;
    try {
      localStorage.setItem(SOUND_PREF_KEY, value ? "1" : "0");
    } catch {
      // ignore storage failures
    }
    updateSoundButton();
  }

  function updateSoundButton() {
    if (!soundButton) {
      return;
    }
    soundButton.textContent = soundEnabled ? "音景 开" : "音景 关";
    soundButton.classList.toggle("is-muted", !soundEnabled);
  }

  function ensureAudioGraph() {
    if (audioContext) {
      return;
    }

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) {
      return;
    }

    audioContext = new AudioCtx();
    masterGain = audioContext.createGain();
    ambientGain = audioContext.createGain();
    masterGain.gain.value = 0.18;
    ambientGain.gain.value = 0;
    ambientGain.connect(masterGain);
    masterGain.connect(audioContext.destination);
  }

  function resumeAudioContext() {
    ensureAudioGraph();
    if (!audioContext) {
      return;
    }
    if (audioContext.state === "suspended") {
      audioContext.resume().catch(() => {});
    }
  }

  function startAmbient() {
    if (!soundEnabled) {
      return;
    }

    resumeAudioContext();
    if (!audioContext || ambientStarted) {
      return;
    }

    ambientStarted = true;
    const now = audioContext.currentTime;
    const droneA = audioContext.createOscillator();
    const droneB = audioContext.createOscillator();
    const shimmer = audioContext.createOscillator();
    const lfo = audioContext.createOscillator();
    const lfoGain = audioContext.createGain();
    const filter = audioContext.createBiquadFilter();

    droneA.type = "triangle";
    droneB.type = "sine";
    shimmer.type = "triangle";
    lfo.type = "sine";

    droneA.frequency.value = 146.83;
    droneB.frequency.value = 220;
    shimmer.frequency.value = 587.33;
    lfo.frequency.value = 0.11;
    lfoGain.gain.value = 18;
    filter.type = "lowpass";
    filter.frequency.value = 920;

    lfo.connect(lfoGain);
    lfoGain.connect(filter.frequency);

    const mixA = audioContext.createGain();
    const mixB = audioContext.createGain();
    const mixC = audioContext.createGain();
    mixA.gain.value = 0.18;
    mixB.gain.value = 0.12;
    mixC.gain.value = 0.018;

    droneA.connect(mixA);
    droneB.connect(mixB);
    shimmer.connect(mixC);
    mixA.connect(filter);
    mixB.connect(filter);
    mixC.connect(filter);
    filter.connect(ambientGain);

    ambientGain.gain.cancelScheduledValues(now);
    ambientGain.gain.setValueAtTime(0.0001, now);
    ambientGain.gain.exponentialRampToValueAtTime(0.18, now + 2.8);

    droneA.start();
    droneB.start();
    shimmer.start();
    lfo.start();

    chimeTimer = window.setInterval(() => {
      if (!soundEnabled) {
        return;
      }
      playTone({
        frequency: 783.99,
        duration: 1.8,
        type: "sine",
        gain: 0.018,
        attack: 0.02,
        release: 1.6,
      });
    }, 9000);
  }

  function stopAmbient() {
    if (!ambientGain || !audioContext) {
      return;
    }
    const now = audioContext.currentTime;
    ambientGain.gain.cancelScheduledValues(now);
    ambientGain.gain.setTargetAtTime(0.0001, now, 0.25);
    if (chimeTimer) {
      window.clearInterval(chimeTimer);
      chimeTimer = null;
    }
  }

  function playTone(options) {
    if (!soundEnabled) {
      return;
    }

    resumeAudioContext();
    if (!audioContext || !masterGain) {
      return;
    }

    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    const filter = audioContext.createBiquadFilter();
    const startAt = audioContext.currentTime;
    const duration = options.duration ?? 0.5;
    const attack = options.attack ?? 0.01;
    const release = options.release ?? Math.max(duration - attack, 0.08);

    oscillator.type = options.type || "sine";
    oscillator.frequency.setValueAtTime(options.frequency || 440, startAt);
    if (options.detune) {
      oscillator.detune.setValueAtTime(options.detune, startAt);
    }

    filter.type = options.filterType || "lowpass";
    filter.frequency.value = options.filterFrequency || 1800;
    gain.gain.setValueAtTime(0.0001, startAt);
    gain.gain.exponentialRampToValueAtTime(options.gain || 0.04, startAt + attack);
    gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration + release);

    oscillator.connect(filter);
    filter.connect(gain);
    gain.connect(masterGain);

    oscillator.start(startAt);
    oscillator.stop(startAt + duration + release + 0.04);
  }

  function playBookOpen() {
    playTone({ frequency: 261.63, duration: 0.45, gain: 0.06, type: "triangle", filterFrequency: 1400 });
    window.setTimeout(() => {
      playTone({ frequency: 392, duration: 0.9, gain: 0.04, type: "sine", filterFrequency: 1800, release: 1.1 });
    }, 80);
  }

  function playCoin() {
    playTone({ frequency: 1180, duration: 0.12, gain: 0.03, type: "triangle", filterFrequency: 2400, release: 0.22 });
    window.setTimeout(() => {
      playTone({ frequency: 860, duration: 0.1, gain: 0.018, type: "sine", filterFrequency: 2200, release: 0.16 });
    }, 45);
  }

  function playReveal() {
    playTone({ frequency: 523.25, duration: 0.32, gain: 0.04, type: "sine", filterFrequency: 1600, release: 0.42 });
    window.setTimeout(() => {
      playTone({ frequency: 783.99, duration: 0.55, gain: 0.03, type: "triangle", filterFrequency: 2200, release: 0.62 });
    }, 65);
  }

  function ensureOverlay() {
    if (overlay) {
      return overlay;
    }

    overlay = document.createElement("div");
    overlay.className = "page-transition-overlay";
    overlay.innerHTML = `
      <div class="page-transition-ring"></div>
      <div class="page-transition-copy">天机流转中</div>
    `;
    document.body.appendChild(overlay);
    return overlay;
  }

  function enterPageTransition() {
    const node = ensureOverlay();
    node.classList.add("is-active");
    window.setTimeout(() => node.classList.add("is-settled"), 24);
  }

  function leavePageTransition() {
    const node = ensureOverlay();
    node.classList.remove("is-active", "is-settled");
  }

  function bindPageTransitions() {
    ensureOverlay();
    document.body.classList.add("page-transition-ready");
    window.setTimeout(() => document.body.classList.add("page-transition-entered"), 32);

    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link) {
        return;
      }

      const href = link.getAttribute("href");
      if (!href || href.startsWith("#") || link.target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || url.pathname === window.location.pathname) {
        return;
      }

      event.preventDefault();
      enterPageTransition();
      playReveal();
      window.setTimeout(() => {
        window.location.href = url.href;
      }, 520);
    });

    window.addEventListener("pageshow", leavePageTransition);
  }

  function bindSoundToggle() {
    const nav = document.querySelector(".top-nav");
    if (!nav) {
      return;
    }

    soundButton = document.createElement("button");
    soundButton.type = "button";
    soundButton.className = "ghost sound-toggle";
    soundButton.addEventListener("click", () => {
      writeStoredSoundPref(!soundEnabled);
      if (soundEnabled) {
        startAmbient();
      } else {
        stopAmbient();
      }
    });
    updateSoundButton();
    nav.appendChild(soundButton);
  }

  function bindFirstInteraction() {
    const resumeOnce = () => {
      if (soundEnabled) {
        startAmbient();
      } else {
        resumeAudioContext();
      }
      document.removeEventListener("pointerdown", resumeOnce);
      document.removeEventListener("keydown", resumeOnce);
    };

    document.addEventListener("pointerdown", resumeOnce, { once: true });
    document.addEventListener("keydown", resumeOnce, { once: true });
  }

  bindPageTransitions();
  bindSoundToggle();
  bindFirstInteraction();

  window.XJImmersive = {
    playBookOpen,
    playCoin,
    playReveal,
    startAmbient,
    stopAmbient,
  };
})();