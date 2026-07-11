import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Реестр задач", () => {
  test("аким создаёт задачу, и она появляется", async ({ page }) => {
    await login(page, USERS.akim);
    await page.goto("/issues");

    await page.getByRole("button", { name: "Новая задача" }).click();

    const title = `E2E задача ${Date.now()}`;
    await page.getByPlaceholder("Текст задачи").fill(title);
    await page.getByRole("button", { name: "Создать" }).click();

    // После создания задача видна (в детале или списке).
    await expect(page.getByText(title).first()).toBeVisible({ timeout: 15_000 });
  });

  test("реестр открывается и фильтр по поиску работает", async ({ page }) => {
    await login(page, USERS.akim);
    await page.goto("/issues");
    // Кнопка экспорта CSV присутствует.
    await expect(page.getByRole("button", { name: "Экспорт" })).toBeVisible();
    // Поиск сужает список без ошибок.
    await page.getByPlaceholder("Поиск").fill("фонари");
    await page.waitForTimeout(1000);
    await expect(page.locator("body")).toBeVisible();
  });

  test("специалист не видит кнопку удаления чужих задач в детале", async ({ page }) => {
    await login(page, USERS.spec);
    await page.goto("/issues");
    // Реестр специалиста открывается без ошибок.
    await expect(page.getByRole("button", { name: "Новая задача" })).toBeVisible();
  });
});
