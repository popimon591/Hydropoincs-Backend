# Firebase phone authentication

Hydro uses Firebase Authentication to send and verify phone OTPs. The frontend
sends the SMS with the Firebase client SDK; Django never generates or exposes
an OTP. After the user enters the code, the frontend sends the resulting
Firebase ID token to Hydro, which verifies the token and returns Hydro JWTs.

## Firebase setup

1. Create or select a Firebase project and enable **Authentication >
   Sign-in method > Phone**.
2. Add the frontend's development and production hostnames to **Authentication
   > Settings > Authorized domains**.
3. Set `FIREBASE_PROJECT_ID=agromonitoringapp` in Hydro's environment. The
   Android App ID (`1:750505557021:android:c9137cf8f3c53d7cafdaf4`) belongs to
   the Android client configuration; it is not used by this Django backend.
4. Give the Hydro server a service account identity with permission to verify
   Firebase Authentication ID tokens. The supplied development service account
   is configured using `FIREBASE_CREDENTIALS` in the ignored local `.env`.
   Docker Compose mounts the file read-only at
   `/run/secrets/firebase-service-account.json`; set
   `FIREBASE_CREDENTIALS_HOST_PATH` in `.env` to the file's host path when
   deploying elsewhere. On hosted environments, prefer the platform's
   Application Default Credentials or secret manager instead of a downloaded
   key. Never commit or share the service-account file.

## Client flow

The Capacitor Android client uses
`@capacitor-firebase/authentication`. Its sign-in screen requests the code
through Firebase, confirms the entered code, gets the Firebase ID token, and
sends that token to Hydro. After changing the client, run `yarn build` followed
by `yarn cap sync android`, then rebuild and install the Android app. The
Android app's `google-services.json` must match its package name and Firebase
project, and its SHA fingerprints must be registered in Firebase.

The send-OTP endpoints normalize the phone number and check whether the request
is eligible before the client contacts Firebase. Login requires an active
existing Hydro account; registration requires that the phone number is not
already registered. The verification endpoints repeat the relevant database
checks after Firebase verifies the OTP so account state changes during
verification cannot bypass validation.

For a Firebase test phone number, enter the exact configured country code and
number and use the configured test verification code; Firebase will not send a
real SMS for that number.

The app also calls Hydro before requesting Firebase verification. Ensure
`REACT_APP_BACKEND_URL` points to a running Hydro server reachable from the
Android device, including its port (for example, `http://192.168.1.20:8000`).
Do not use `localhost` for a physical Android device; it refers to the device
itself.

For a web client, initialize the Firebase Web SDK with the web app configuration.
Render a reCAPTCHA container and use
`signInWithPhoneNumber(auth, phoneNumber, recaptchaVerifier)`. The phone number
must be in E.164 format (for example, `+14155552671`). Confirm the code with
the returned confirmation result, then call `result.user.getIdToken()`.

Call Hydro's registration preflight before starting Firebase verification. It
validates the submitted name and phone number format and rejects numbers
already registered in Hydro, without creating an account:

```http
POST /api/v1/user/register/send-otp
Content-Type: application/json

{"full_name":"Ada Lovelace","phone_number":"+14155552671"}
```

After Firebase confirms the code, complete registration:

```http
POST /api/v1/user/register/verify-otp
Content-Type: application/json

{
  "full_name":"Ada Lovelace",
  "phone_number":"+14155552671",
  "firebase_id_token":"<Firebase ID token>"
}
```

For login, preflight with `POST /api/v1/user/login/send-otp` and
`{"phone_number":"+14155552671"}`. Hydro rejects missing or inactive accounts
before the client requests an OTP. After confirming the Firebase code, call
`POST /api/v1/user/login/verify-otp` with `phone_number` and
`firebase_id_token`. Hydro verifies the Firebase token and rechecks that the
phone belongs to an active Hydro account.

The send-OTP endpoints check whether the phone number can proceed; Firebase's
client SDK sends and verifies the OTP. Successful verification returns the
existing Hydro response envelope with user details and `token.access` /
`token.refresh` JWTs. Firebase credentials are server-only; the Firebase web
app configuration is intended for the client and should be protected with
Firebase's domain restrictions and API-key restrictions.

In development, the Android client logs elapsed auth-stage timings to the
console, and Hydro logs phone normalization, database lookup, Firebase token
verification, account creation, and endpoint durations without logging phone
numbers or tokens. To enable client timing logs in a production build, set
`REACT_APP_AUTH_TIMINGS=true` when building the frontend.
