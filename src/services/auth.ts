import { useFinanceStore } from '@/store/useFinanceStore';
import { genId } from '@/utils/id';

// Local stand-in for /auth/register, /auth/login, /auth/refresh (spec
// section 5.1). There's no backend yet, so this just establishes session
// state in the persisted store. Response shapes match the spec so the
// real Firebase-Auth-backed JWT endpoints can drop in later.

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  user: { id: string; name: string; email: string };
}

function fakeToken(prefix: string) {
  return `${prefix}.${genId('tok')}.${Date.now()}`;
}

export async function register(email: string, password: string, name: string): Promise<AuthResponse> {
  if (!email || !password || !name) {
    throw new Error('email, password and name are required');
  }
  const { login, user } = useFinanceStore.getState();
  login(email, name);
  return {
    accessToken: fakeToken('access'),
    refreshToken: fakeToken('refresh'),
    user: { id: user.id, name, email },
  };
}

export async function loginRequest(email: string, password: string): Promise<AuthResponse> {
  if (!email || !password) {
    throw new Error('email and password are required');
  }
  const { login, user } = useFinanceStore.getState();
  login(email);
  return {
    accessToken: fakeToken('access'),
    refreshToken: fakeToken('refresh'),
    user: { id: user.id, name: user.name, email },
  };
}

export function logoutRequest() {
  useFinanceStore.getState().logout();
}
