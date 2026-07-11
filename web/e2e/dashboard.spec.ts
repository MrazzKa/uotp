import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Ролевые дашборды — каждой роли своя работа", () => {
  test("оператор видит очередь «Нераспределённые», без графиков", async ({ page }) => {
    await login(page, USERS.operator);
    await expect(page.getByRole("heading", { name: "Нераспределённые" })).toBeVisible();
    await expect(page.getByText("По статусам")).toHaveCount(0);
  });

  test("специалист видит «Мои задачи», без графиков", async ({ page }) => {
    await login(page, USERS.spec);
    await expect(page.getByRole("heading", { name: "Мои задачи" })).toBeVisible();
    await expect(page.getByText("По статусам")).toHaveCount(0);
  });

  test("аким видит мониторинг по округам и личный контроль", async ({ page }) => {
    await login(page, USERS.akim);
    await expect(page.getByText("Мониторинг по сельским округам")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Мой контроль" })).toBeVisible();
  });
});
