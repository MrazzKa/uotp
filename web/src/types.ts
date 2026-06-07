export type RoleCode = "ADMIN" | "DISPATCHER" | "EXECUTOR" | "AKIM" | "INSPECTOR";

export type User = {
  id: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  language: string;
  role: { id: string; code: RoleCode; name_ru: string; name_kk: string; permissions: Record<string, unknown> };
  tenant: { id: string; code: string; name_ru: string; name_kk: string; timezone: string; locale_default: string };
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};
