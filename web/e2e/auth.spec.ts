import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Аутентификация", () => {
  test("форма логина пустая, без демо-кнопок и пред-заполнения", async ({ page }) => {
    await page.goto("/");
    const inputs = page.locator("input");
    await expect(inputs.nth(0)).toHaveValue("");
    await expect(inputs.nth(1)).toHaveValue("");
    // На публично мониторимом домене не должно быть демо-ролей/кнопок быстрого входа.
    await expect(page.getByRole("button", { name: /Аким|Оператор|демо|demo/i })).toHaveCount(0);
  });

  test("неверные учётные данные не пускают", async ({ page }) => {
    await page.goto("/");
    await page.locator("input").nth(0).fill("nobody@uotp.local");
    await page.locator("input").nth(1).fill("wrongpass");
    await page.getByRole("button", { name: "Войти" }).click();
    // Остаёмся на логине (дашборд не появился).
    await expect(page.getByText(/Добрый|Кабинет/)).toHaveCount(0);
  });

  test("успешный вход акима", async ({ page }) => {
    await login(page, USERS.akim);
    await expect(page.getByText("Кабинет акима")).toBeVisible();
  });
});
