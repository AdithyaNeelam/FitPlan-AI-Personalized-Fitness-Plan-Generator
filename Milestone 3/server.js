require("dotenv").config();

const crypto = require("crypto");
const path = require("path");
const express = require("express");
const session = require("express-session");
const nodemailer = require("nodemailer");
const passport = require("passport");
const GoogleStrategy = require("passport-google-oauth20").Strategy;
const { connectToDatabase } = require("./db");
const { ensureUserIndexes, findUserByEmail, createUser } = require("./models/User");

const app = express();

const PORT = Number(process.env.PORT || 3000);
const OTP_SECRET = process.env.OTP_SECRET || "change-me";
const OTP_LENGTH = Number(process.env.OTP_LENGTH || 6);
const OTP_TTL_MINUTES = Number(process.env.OTP_TTL_MINUTES || 5);
const MAX_VERIFY_ATTEMPTS = Number(process.env.MAX_VERIFY_ATTEMPTS || 5);
const MIN_SECONDS_BETWEEN_SENDS = Number(process.env.MIN_SECONDS_BETWEEN_SENDS || 45);
const SESSION_SECRET = process.env.SESSION_SECRET || "fitplan-session-secret-change-me";
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || "";
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || "";
const GOOGLE_CALLBACK_URL = process.env.GOOGLE_CALLBACK_URL || `http://localhost:${PORT}/auth/google/callback`;
const googleOAuthEnabled = Boolean(GOOGLE_CLIENT_ID && GOOGLE_CLIENT_SECRET);

const registerOtpStore = new Map();
const loginOtpStore = new Map();

app.use(express.json());
app.use(
  session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { httpOnly: true, sameSite: "lax" }
  })
);
app.use(passport.initialize());
app.use(passport.session());
app.use(express.static(path.join(__dirname, "public")));

passport.serializeUser((user, done) => {
  done(null, user);
});

passport.deserializeUser((user, done) => {
  done(null, user);
});

if (googleOAuthEnabled) {
  passport.use(
    new GoogleStrategy(
      {
        clientID: GOOGLE_CLIENT_ID,
        clientSecret: GOOGLE_CLIENT_SECRET,
        callbackURL: GOOGLE_CALLBACK_URL
      },
      async (accessToken, refreshToken, profile, done) => {
        const email = String(profile?.emails?.[0]?.value || "").trim().toLowerCase();
        if (!email || !isValidEmail(email)) {
          return done(new Error("Google account has no valid email."));
        }

        try {
          const existingUser = await findUserByEmail(email);
          if (!existingUser) {
            await createUser({
              email,
              passwordHash: null,
              profile: null,
              provider: "google",
              createdAt: new Date().toISOString()
            });
          }

          return done(null, { email, provider: "google" });
        } catch (error) {
          return done(error);
        }
      }
    )
  );
}

function isValidEmail(email) {
  return /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email);
}

function generateOtp(length) {
  let out = "";
  for (let i = 0; i < length; i += 1) {
    out += crypto.randomInt(0, 10);
  }
  return out;
}

function hashOtp(otp) {
  return crypto.createHash("sha256").update(`${OTP_SECRET}:${otp}`).digest("hex");
}

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}

function verifyPassword(password, saltedHash) {
  const [salt, savedHash] = String(saltedHash || "").split(":");
  if (!salt || !savedHash) {
    return false;
  }
  const testHash = crypto.scryptSync(password, salt, 64).toString("hex");
  return crypto.timingSafeEqual(Buffer.from(savedHash, "hex"), Buffer.from(testHash, "hex"));
}

function toPositiveNumber(value) {
  const num = Number(value);
  if (!Number.isFinite(num) || num <= 0) {
    return null;
  }
  return num;
}

function validateRegistrationInput(payload) {
  const email = String(payload?.email || "").trim().toLowerCase();
  const password = String(payload?.password || "");
  const name = String(payload?.name || "").trim();
  const age = toPositiveNumber(payload?.age);
  const heightCm = toPositiveNumber(payload?.heightCm);
  const weightKg = toPositiveNumber(payload?.weightKg);
  const gender = String(payload?.gender || "").trim();
  const goal = String(payload?.goal || "").trim();
  const activityLevel = String(payload?.activityLevel || "").trim();

  if (!isValidEmail(email)) {
    return { ok: false, message: "Use a valid email address for registration." };
  }

  if (password.length < 8) {
    return { ok: false, message: "Password must be at least 8 characters." };
  }

  if (!name || name.length < 2) {
    return { ok: false, message: "Full name must be at least 2 characters." };
  }

  if (!age || age < 13 || age > 80) {
    return { ok: false, message: "Age must be between 13 and 80." };
  }

  if (!heightCm || heightCm < 100 || heightCm > 250) {
    return { ok: false, message: "Height must be between 100 and 250 cm." };
  }

  if (!weightKg || weightKg < 30 || weightKg > 250) {
    return { ok: false, message: "Weight must be between 30 and 250 kg." };
  }

  if (!gender || !goal || !activityLevel) {
    return { ok: false, message: "Please complete all registration fields." };
  }

  return {
    ok: true,
    data: {
      email,
      password,
      profile: {
        name,
        age,
        gender,
        goal,
        heightCm,
        weightKg,
        activityLevel
      }
    }
  };
}

function getTransporter() {
  const host = process.env.SMTP_HOST;
  const port = Number(process.env.SMTP_PORT || 587);
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASS;
  const secure = String(process.env.SMTP_SECURE || "false").toLowerCase() === "true";

  if (!host || !user || !pass) {
    throw new Error("Missing SMTP configuration. Check your .env file.");
  }

  return nodemailer.createTransport({
    host,
    port,
    secure,
    auth: { user, pass }
  });
}

async function sendOtpEmail(email, otp, purpose = "login") {
  const from = process.env.SMTP_FROM || process.env.SMTP_USER;
  const transporter = getTransporter();
  const purposeLabel = purpose === "registration" ? "Registration" : "Login";

  await transporter.sendMail({
    from,
    to: email,
    subject: `Your FitPlan AI ${purposeLabel} OTP`,
    text: `Your ${purposeLabel.toLowerCase()} OTP is ${otp}. It expires in ${OTP_TTL_MINUTES} minutes.`
  });
}

function getMailErrorMessage(error) {
  const message = String(error?.message || "");
  const code = String(error?.code || "");

  if (message.includes("535-5.7.8") || code === "EAUTH") {
    return "Email service authentication failed. Please contact support.";
  }

  if (code === "ECONNECTION" || code === "ETIMEDOUT") {
    return "Email service is temporarily unavailable. Please try again.";
  }

  return "Could not send OTP at the moment. Please try again.";
}

app.get("/auth/google", (req, res, next) => {
  if (!googleOAuthEnabled) {
    return res.redirect("/?auth=google_not_configured");
  }
  return passport.authenticate("google", { scope: ["profile", "email"] })(req, res, next);
});

app.get("/auth/google/callback", (req, res, next) => {
  if (!googleOAuthEnabled) {
    return res.redirect("/?auth=google_not_configured");
  }

  return passport.authenticate("google", { failureRedirect: "/?auth=google_failed" })(req, res, () => {
    const email = encodeURIComponent(String(req.user?.email || ""));
    return res.redirect(`/?auth=google_success&email=${email}`);
  });
});

app.post("/api/login", async (req, res) => {
  const email = String(req.body?.email || "").trim().toLowerCase();
  const password = String(req.body?.password || "");

  if (!isValidEmail(email)) {
    return res.status(400).json({ ok: false, message: "Use a valid email address." });
  }

  if (!password || password.length < 8) {
    return res.status(400).json({ ok: false, message: "Password must be at least 8 characters." });
  }

  try {
    const user = await findUserByEmail(email);
    if (!user) {
      return res.status(404).json({ ok: false, message: "User not found. Register first." });
    }

    if (user.provider === "google" && !user.passwordHash) {
      return res.status(400).json({ ok: false, message: "This account uses Google login. Continue with Google." });
    }

    if (!verifyPassword(password, user.passwordHash)) {
      return res.status(401).json({ ok: false, message: "Invalid email or password." });
    }

    const existing = loginOtpStore.get(email);
    if (existing && Date.now() - existing.lastSentAt < MIN_SECONDS_BETWEEN_SENDS * 1000) {
      return res.status(429).json({ ok: false, message: `Wait ${MIN_SECONDS_BETWEEN_SENDS}s before requesting another OTP.` });
    }

    const otp = generateOtp(OTP_LENGTH);
    await sendOtpEmail(email, otp, "login");

    loginOtpStore.set(email, {
      otpHash: hashOtp(otp),
      expiresAt: Date.now() + OTP_TTL_MINUTES * 60 * 1000,
      attempts: 0,
      lastSentAt: Date.now(),
      profile: user.profile || null
    });

    return res.json({ ok: true, message: "Login OTP sent to your email.", requiresOtp: true, email });
  } catch (error) {
    const message = /mongodb|database/i.test(String(error?.message || ""))
      ? "Database error while logging in. Please try again."
      : getMailErrorMessage(error);
    return res.status(500).json({ ok: false, message });
  }
});

app.post("/api/login/verify-otp", (req, res) => {
  const email = String(req.body?.email || "").trim().toLowerCase();
  const otp = String(req.body?.otp || "").trim();

  if (!isValidEmail(email)) {
    return res.status(400).json({ ok: false, message: "Use a valid email address." });
  }

  if (!/^\d+$/.test(otp) || otp.length !== OTP_LENGTH) {
    return res.status(400).json({ ok: false, message: `OTP must be a ${OTP_LENGTH}-digit number.` });
  }

  const record = loginOtpStore.get(email);
  if (!record) {
    return res.status(400).json({ ok: false, message: "No login OTP request found. Sign in first." });
  }

  if (Date.now() > record.expiresAt) {
    loginOtpStore.delete(email);
    return res.status(400).json({ ok: false, message: "OTP expired. Sign in again to request a new OTP." });
  }

  if (record.attempts >= MAX_VERIFY_ATTEMPTS) {
    loginOtpStore.delete(email);
    return res.status(429).json({ ok: false, message: "Too many wrong attempts. Sign in again to request a new OTP." });
  }

  if (hashOtp(otp) !== record.otpHash) {
    record.attempts += 1;
    loginOtpStore.set(email, record);
    const left = Math.max(0, MAX_VERIFY_ATTEMPTS - record.attempts);
    return res.status(401).json({ ok: false, message: `Invalid OTP. Attempts left: ${left}.` });
  }

  loginOtpStore.delete(email);
  const sessionToken = crypto.randomBytes(24).toString("hex");
  return res.json({
    ok: true,
    message: "Login successful.",
    token: sessionToken,
    email,
    profile: record.profile || null
  });
});

app.post("/api/register/send-otp", async (req, res) => {
  try {
    const validation = validateRegistrationInput(req.body);
    if (!validation.ok) {
      return res.status(400).json({ ok: false, message: validation.message });
    }
    const { email, password, profile } = validation.data;

    const existingUser = await findUserByEmail(email);
    if (existingUser) {
      return res.status(409).json({ ok: false, message: "User already exists. Please sign in." });
    }

    const existing = registerOtpStore.get(email);
    if (existing && Date.now() - existing.lastSentAt < MIN_SECONDS_BETWEEN_SENDS * 1000) {
      return res.status(429).json({ ok: false, message: `Wait ${MIN_SECONDS_BETWEEN_SENDS}s before requesting another OTP.` });
    }

    const otp = generateOtp(OTP_LENGTH);
    await sendOtpEmail(email, otp, "registration");

    registerOtpStore.set(email, {
      otpHash: hashOtp(otp),
      passwordHash: hashPassword(password),
      profile,
      expiresAt: Date.now() + OTP_TTL_MINUTES * 60 * 1000,
      attempts: 0,
      lastSentAt: Date.now()
    });

    return res.json({ ok: true, message: "OTP sent to your email." });
  } catch (error) {
    const message = /mongodb|database/i.test(String(error?.message || ""))
      ? "Database error while checking account. Please try again."
      : getMailErrorMessage(error);
    return res.status(500).json({ ok: false, message });
  }
});

app.post("/api/register/verify-otp", async (req, res) => {
  const email = String(req.body?.email || "").trim().toLowerCase();
  const otp = String(req.body?.otp || "").trim();

  if (!isValidEmail(email)) {
    return res.status(400).json({ ok: false, message: "Use a valid email address." });
  }

  if (!/^\d+$/.test(otp) || otp.length !== OTP_LENGTH) {
    return res.status(400).json({ ok: false, message: `OTP must be a ${OTP_LENGTH}-digit number.` });
  }

  const record = registerOtpStore.get(email);
  if (!record) {
    return res.status(400).json({ ok: false, message: "No OTP request found. Send OTP first." });
  }

  if (Date.now() > record.expiresAt) {
    registerOtpStore.delete(email);
    return res.status(400).json({ ok: false, message: "OTP expired. Request a new OTP." });
  }

  if (record.attempts >= MAX_VERIFY_ATTEMPTS) {
    registerOtpStore.delete(email);
    return res.status(429).json({ ok: false, message: "Too many wrong attempts. Request a new OTP." });
  }

  if (hashOtp(otp) !== record.otpHash) {
    record.attempts += 1;
    registerOtpStore.set(email, record);
    const left = Math.max(0, MAX_VERIFY_ATTEMPTS - record.attempts);
    return res.status(401).json({ ok: false, message: `Invalid OTP. Attempts left: ${left}.` });
  }

  try {
    await createUser({
      email,
      passwordHash: record.passwordHash,
      profile: record.profile || null,
      provider: "password",
      createdAt: new Date().toISOString()
    });
  } catch (error) {
    if (error?.code === 11000) {
      registerOtpStore.delete(email);
      return res.status(409).json({ ok: false, message: "User already exists. Please sign in." });
    }
    return res.status(500).json({ ok: false, message: "Database error while saving your account. Please try again." });
  }

  registerOtpStore.delete(email);
  return res.json({ ok: true, message: "Registration successful.", profile: record.profile || null });
});

async function startServer() {
  try {
    await connectToDatabase();
    await ensureUserIndexes();
    app.listen(PORT, () => {
      // eslint-disable-next-line no-console
      console.log(`FitPlan AI auth app running on http://localhost:${PORT}`);
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Failed to connect to MongoDB. Check MONGODB_URI and MONGODB_DB_NAME.", error);
    process.exit(1);
  }
}

startServer();
