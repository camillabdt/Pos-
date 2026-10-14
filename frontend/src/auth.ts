/**
 * Dois modos:
 *  - dev: a pessoa escolhe "ver como" (coordenação, um docente, um discente) na barra superior.
 *         O backend precisa estar com PERCURSO_AUTH=dev. Nunca use em produção.
 *  - firebase: login por e-mail/senha no Firebase Auth; o token vai no cabeçalho Authorization.
 */
import type { Auth, User } from "firebase/auth";

export const MODO_AUTH = ((import.meta.env.VITE_AUTH as string | undefined) ?? "dev") as "dev" | "firebase";

export interface IdentidadeDev { papel: "coordenacao" | "docente" | "discente"; id?: string; rotulo: string }

const CHAVE = "percurso.dev";

export function identidadeDev(): IdentidadeDev | null {
  if (MODO_AUTH !== "dev") return null;
  try {
    const v = localStorage.getItem(CHAVE);
    if (v) return JSON.parse(v) as IdentidadeDev;
  } catch { /* armazenamento indisponível: segue como coordenação */ }
  return { papel: "coordenacao", rotulo: "Coordenação" };
}

export function definirIdentidadeDev(i: IdentidadeDev) {
  try { localStorage.setItem(CHAVE, JSON.stringify(i)); } catch { /* ignora */ }
}

let authFirebase: Auth | null = null;

async function obterAuth(): Promise<Auth> {
  if (authFirebase) return authFirebase;
  const { initializeApp } = await import("firebase/app");
  const { getAuth } = await import("firebase/auth");
  const app = initializeApp({
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  });
  authFirebase = getAuth(app);
  return authFirebase;
}

export async function tokenAtual(): Promise<string | null> {
  if (MODO_AUTH !== "firebase") return null;
  const auth = await obterAuth();
  return auth.currentUser ? auth.currentUser.getIdToken() : null;
}

export async function entrar(email: string, senha: string) {
  const { signInWithEmailAndPassword } = await import("firebase/auth");
  await signInWithEmailAndPassword(await obterAuth(), email, senha);
}

export async function sair() {
  const { signOut } = await import("firebase/auth");
  await signOut(await obterAuth());
}

export async function observarLogin(cb: (u: User | null) => void) {
  const { onAuthStateChanged } = await import("firebase/auth");
  return onAuthStateChanged(await obterAuth(), cb);
}
