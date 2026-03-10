# FitPlan AI Auth System

## Overview
This project implements the Milestone 3 authentication flow for FitPlan AI using a Node.js backend, MongoDB database storage, and OTP verification over email.

The application includes:
- User signup with email and password
- User details stored in MongoDB
- Login with email and password validation from the database
- A 6-digit OTP generated after successful login
- OTP delivery to the user's registered email
- OTP verification before access is granted
- Google sign-in support when OAuth credentials are configured
- A responsive branded authentication UI

## Tech stack
- Node.js
- Express
- MongoDB
- Nodemailer
- Passport Google OAuth
- HTML, CSS, JavaScript

## Project files
- `server.js` -> main backend server and auth routes
- `db.js` -> MongoDB connection
- `models/User.js` -> user database helpers
- `public/index.html` -> UI markup
- `public/styles.css` -> page styling
- `public/app.js` -> frontend auth logic
- `.env.example` -> environment template
- `package.json` -> Node dependency source of truth
- `requirements.txt` -> dependency reference list for submission

## What was implemented
### Signup
- Users can register with profile fields, email, and password.
- Registration sends a 6-digit OTP to the entered email.
- The account is created only after OTP verification.

### Login
- Users log in with email and password.
- After credentials are validated, a fresh 6-digit login OTP is generated.
- The user receives the OTP by email.
- The user gets access only after login OTP verification succeeds.

### Database
- Registered users are stored in MongoDB.
- User profile information is saved with the account.

### Access control
- Access is intentionally blocked until OTP verification is complete.
- Login no longer returns final access immediately after password validation.

## Requirements
- Node.js 18 or later
- npm
- MongoDB running locally or a MongoDB Atlas connection string
- SMTP sender email account for OTP delivery

## How to extract and run the project from ZIP
1. Extract the ZIP file to a folder such as `C:\FitPlanAi`.
2. Open PowerShell in the extracted folder.
3. Install dependencies:

```powershell
npm install
```

4. Create `.env` from `.env.example`:

```powershell
Copy-Item .env.example .env
```

5. Update the values inside `.env`.
6. Make sure MongoDB is running and reachable.
7. Start the application:

```powershell
node server.js
```

8. Open the application in a browser:

```text
http://localhost:3000
```

## Environment configuration
Use this template in `.env`:

```env
PORT=3000
OTP_SECRET=replace-with-a-random-secret
OTP_LENGTH=6
OTP_TTL_MINUTES=5
MAX_VERIFY_ATTEMPTS=5
MIN_SECONDS_BETWEEN_SENDS=45
SESSION_SECRET=replace-with-a-long-random-session-secret

MONGODB_URI=mongodb://127.0.0.1:27017
MONGODB_DB_NAME=fitplanai

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-16-char-google-app-password
SMTP_FROM=FitPlan AI <your-email@gmail.com>
SMTP_SECURE=false

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_CALLBACK_URL=http://localhost:3000/auth/google/callback
```

## Gmail App Password setup for OTP email
If you are using Gmail to send OTP messages, use an App Password instead of your normal Gmail password.

1. Sign in to the Gmail account that will send OTP emails.
2. Open Google Account Security:
   `https://myaccount.google.com/security`
3. Enable `2-Step Verification`.
4. After 2-Step Verification is active, open `App passwords`.
5. Create a new App Password for Mail.
6. Copy the generated 16-character password.
7. Paste it into `.env` as `SMTP_PASS`.

### Detailed steps to create a Gmail App Password
1. Go to `https://myaccount.google.com/`.
2. Click `Security` in the left menu.
3. Under `How you sign in to Google`, turn on `2-Step Verification` if it is not already enabled.
4. After that is enabled, return to the `Security` page.
5. Under `How you sign in to Google`, click `App passwords`.
6. Google may ask you to sign in again.
7. In the app password page:
   Select app: choose `Mail`
   Select device: choose `Other` and enter a name such as `FitPlan AI`
8. Click `Generate`.
9. Google will show a 16-character password.
10. Copy that password and place it in `.env` as:

```env
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-16-character-app-password
SMTP_FROM=FitPlan AI <your-email@gmail.com>
```

11. Restart the app after updating `.env`:

```powershell
node server.js
```

Important:
- Do not use your normal Gmail password in `SMTP_PASS`.
- `SMTP_USER` and the Gmail account that created the App Password must be the same account.
- If Google shows the password in grouped format like `abcd efgh ijkl mnop`, remove the spaces before saving it.

## Optional Google login setup
Google login is optional. If you want it to work:

1. Create OAuth credentials in Google Cloud Console.
2. Set the authorized redirect URI to:

```text
http://localhost:3000/auth/google/callback
```

3. Add these values to `.env`:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_CALLBACK_URL`

## API routes
- `POST /api/register/send-otp`
- `POST /api/register/verify-otp`
- `POST /api/login`
- `POST /api/login/verify-otp`
- `GET /auth/google`
- `GET /auth/google/callback`

## Notes
- Registered users are stored in MongoDB.
- Pending OTP requests are stored in memory and will reset if the server restarts.
- `.env` must never be committed to GitHub.
- `node_modules` should not be shared in ZIP submissions.

## Troubleshooting
### Email service authentication failed
- Check `SMTP_USER`, `SMTP_PASS`, and `SMTP_FROM`.
- If using Gmail, confirm that 2-Step Verification is enabled and `SMTP_PASS` is a valid App Password.

### OTP email not received
- Check spam or junk folder.
- Confirm SMTP settings are valid.
- Confirm the sender email account is allowed to send mail.

### User not found during login
- Complete signup and OTP verification first.
- Check that MongoDB is running and the database connection is correct.
