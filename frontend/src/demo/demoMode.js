export const DEMO_TOKEN = "demo-token";
export const isDemo = () => localStorage.getItem("token") === DEMO_TOKEN;