# StackPilot Frontend

Clean, minimal React + Tailwind frontend for StackPilot auth.

## Stack
- React 18 (JSX) + Vite
- Tailwind CSS
- React Router
- Axios

## Structure
```
src/
  api/axios.js        # axios instance + token interceptor
  components/AuthShell.jsx
  pages/Login.jsx
  pages/Register.jsx
  pages/Dashboard.jsx
  App.jsx             # routes
  main.jsx
```

## Run
```bash
npm install
npm run dev
```

Backend expected at `http://127.0.0.1:8000`:
- `POST /auth/register` `{ name, email, password, otp }`
- `POST /auth/login` `{ email, password }`
- `POST /auth/send-otp` `{ email }`
