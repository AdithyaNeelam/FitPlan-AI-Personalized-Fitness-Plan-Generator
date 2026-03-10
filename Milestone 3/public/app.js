const tabLogin = document.getElementById("tabLogin");
const tabRegister = document.getElementById("tabRegister");
const loginPanel = document.getElementById("loginPanel");
const registerPanel = document.getElementById("registerPanel");

const googleLoginBtn = document.getElementById("googleLoginBtn");
const loginForm = document.getElementById("loginForm");
const loginVerifyForm = document.getElementById("loginVerifyForm");
const registerSendOtpForm = document.getElementById("registerSendOtpForm");
const registerVerifyForm = document.getElementById("registerVerifyForm");

const loginEmail = document.getElementById("loginEmail");
const loginPassword = document.getElementById("loginPassword");
const loginOtp = document.getElementById("loginOtp");

const registerName = document.getElementById("registerName");
const registerAge = document.getElementById("registerAge");
const registerGender = document.getElementById("registerGender");
const registerGoal = document.getElementById("registerGoal");
const registerHeight = document.getElementById("registerHeight");
const registerWeight = document.getElementById("registerWeight");
const registerActivity = document.getElementById("registerActivity");
const registerEmail = document.getElementById("registerEmail");
const registerPassword = document.getElementById("registerPassword");
const registerOtp = document.getElementById("registerOtp");
const statusEl = document.getElementById("status");

const registerDraftKey = "fitplan_register_draft";
const registerInputs = [
  registerName,
  registerAge,
  registerGender,
  registerGoal,
  registerHeight,
  registerWeight,
  registerActivity,
  registerEmail,
  registerPassword,
  registerOtp
];

function setStatus(message, type = "info") {
  statusEl.textContent = message;
  statusEl.classList.remove("error", "success");
  if (type === "error") {
    statusEl.classList.add("error");
  }
  if (type === "success") {
    statusEl.classList.add("success");
  }
}

function showTab(tab) {
  const loginActive = tab === "login";
  tabLogin.classList.toggle("active", loginActive);
  tabRegister.classList.toggle("active", !loginActive);
  loginPanel.classList.toggle("hidden", !loginActive);
  registerPanel.classList.toggle("hidden", loginActive);
  if (!loginActive) {
    loginVerifyForm.classList.add("hidden");
  }
  setStatus("");
}

function saveRegisterDraft() {
  const draft = {
    name: registerName.value,
    age: registerAge.value,
    gender: registerGender.value,
    goal: registerGoal.value,
    heightCm: registerHeight.value,
    weightKg: registerWeight.value,
    activityLevel: registerActivity.value,
    email: registerEmail.value,
    password: registerPassword.value,
    otp: registerOtp.value,
    otpVisible: !registerVerifyForm.classList.contains("hidden")
  };
  localStorage.setItem(registerDraftKey, JSON.stringify(draft));
}

function restoreRegisterDraft() {
  const raw = localStorage.getItem(registerDraftKey);
  if (!raw) {
    return;
  }

  try {
    const draft = JSON.parse(raw);
    registerName.value = draft.name || "";
    registerAge.value = draft.age || "";
    registerGender.value = draft.gender || "";
    registerGoal.value = draft.goal || "";
    registerHeight.value = draft.heightCm || "";
    registerWeight.value = draft.weightKg || "";
    registerActivity.value = draft.activityLevel || "";
    registerEmail.value = draft.email || "";
    registerPassword.value = draft.password || "";
    registerOtp.value = draft.otp || "";

    if (draft.otpVisible) {
      registerVerifyForm.classList.remove("hidden");
    }
  } catch (error) {
    localStorage.removeItem(registerDraftKey);
  }
}

function clearRegisterDraft() {
  localStorage.removeItem(registerDraftKey);
}

function getRegistrationPayload() {
  return {
    name: registerName.value.trim(),
    age: Number(registerAge.value),
    gender: registerGender.value,
    goal: registerGoal.value,
    heightCm: Number(registerHeight.value),
    weightKg: Number(registerWeight.value),
    activityLevel: registerActivity.value,
    email: registerEmail.value.trim().toLowerCase(),
    password: registerPassword.value
  };
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await response.json().catch(() => ({ ok: false, message: "Unexpected server response." }));

  if (!response.ok) {
    throw new Error(data.message || "Request failed.");
  }

  return data;
}

tabLogin.addEventListener("click", () => showTab("login"));
tabRegister.addEventListener("click", () => showTab("register"));

googleLoginBtn.addEventListener("click", () => {
  window.location.href = "/auth/google";
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = loginEmail.value.trim().toLowerCase();
  const password = loginPassword.value;

  try {
    setStatus("Checking credentials and sending OTP...");
    const data = await postJson("/api/login", { email, password });
    loginVerifyForm.classList.remove("hidden");
    loginOtp.value = "";
    setStatus(data.message, "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

loginVerifyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = loginEmail.value.trim().toLowerCase();
  const otp = loginOtp.value.trim();

  try {
    setStatus("Verifying login OTP...");
    const data = await postJson("/api/login/verify-otp", { email, otp });
    localStorage.setItem("fitplan_token", data.token);
    localStorage.setItem("fitplan_email", data.email);
    if (data.profile) {
      localStorage.setItem("fitplan_profile", JSON.stringify(data.profile));
    }
    setStatus(`Logged in as ${data.email}`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

registerSendOtpForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = getRegistrationPayload();

  try {
    setStatus("Sending registration OTP...");
    await postJson("/api/register/send-otp", payload);
    registerVerifyForm.classList.remove("hidden");
    saveRegisterDraft();
    setStatus("OTP sent to your email. Enter it to finish registration.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

registerVerifyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = registerEmail.value.trim().toLowerCase();
  const otp = registerOtp.value.trim();

  try {
    setStatus("Verifying OTP...");
    const data = await postJson("/api/register/verify-otp", { email, otp });
    clearRegisterDraft();
    if (data.profile) {
      localStorage.setItem("fitplan_profile", JSON.stringify(data.profile));
    }
    setStatus(`${data.message} You can now sign in.`, "success");
    showTab("login");
    loginEmail.value = email;
    loginPassword.value = "";
    registerSendOtpForm.reset();
    registerVerifyForm.classList.add("hidden");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

for (const input of registerInputs) {
  input.addEventListener("input", saveRegisterDraft);
  input.addEventListener("change", saveRegisterDraft);
}

showTab("login");
restoreRegisterDraft();

const params = new URLSearchParams(window.location.search);
const authState = params.get("auth");
const authEmail = params.get("email");

if (authState === "google_not_configured") {
  setStatus("Google login is not configured on server yet.", "error");
}

if (authState === "google_failed") {
  setStatus("Google login failed. Please try again.", "error");
}

if (authState === "google_success") {
  if (authEmail) {
    localStorage.setItem("fitplan_email", authEmail);
  }
  setStatus(`Google login successful${authEmail ? `: ${authEmail}` : ""}`, "success");
}
