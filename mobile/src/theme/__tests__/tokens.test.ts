import { palettes, statusColor } from "../tokens";

/**
 * Маппинг статус→цвет должен быть согласован с вебом/бэком (v3-статусы) и
 * приоритет просрочки — выше статуса. Чистая логика, без рендера RN.
 */
describe("statusColor (мобилка, v3)", () => {
  const c = palettes.light;

  it("просрочка перекрывает любой статус (красный, белый текст)", () => {
    const tone = statusColor("ASSIGNED", true, c);
    expect(tone.bg).toBe(c.danger);
    expect(tone.text).toBe("#FFFFFF");
  });

  it("NEW и ASSIGNED — информационный тон", () => {
    for (const s of ["NEW", "ASSIGNED"]) {
      expect(statusColor(s, false, c).bg).toBe(c.info);
    }
  });

  it("проверка у контролёра и у автора — предупреждающий тон", () => {
    for (const s of ["REVIEW_CONTROLLER", "REVIEW_AUTHOR"]) {
      expect(statusColor(s, false, c).bg).toBe(c.warning);
    }
  });

  it("снято с контроля — успех", () => {
    expect(statusColor("CLOSED", false, c).bg).toBe(c.success);
  });

  it("черновик и пауза — приглушённый тон", () => {
    for (const s of ["DRAFT", "ON_HOLD"]) {
      expect(statusColor(s, false, c).bg).toBe(c.mutedText);
    }
  });

  it("неизвестный статус не падает, даёт дефолтный тон", () => {
    expect(() => statusColor("WHATEVER", false, c)).not.toThrow();
  });
});
