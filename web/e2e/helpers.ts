import { expect, type Page } from "@playwright/test";

export const USERS = {
  admin: "admin@uotp.local",
  akim: "akim@uotp.local",
  operator: "operator@uotp.local",
  spec: "spec_gkh@uotp.local",
  contractor: "con_clean@uotp.local",
} as const;

/** Логин демо-пользователя (все с паролем demo123) и ожидание дашборда. */
export async function login(page: Page, email: string, password = "demo123") {
  await page.goto("/");
  const inputs = page.locator("input");
  await inputs.nth(0).fill(email);
  await inputs.nth(1).fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
  // Дашборд отрисовал приветствие.
  await expect(page.getByText(/Добрый|Кабинет/).first()).toBeVisible();
}
