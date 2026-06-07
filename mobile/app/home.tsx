import { Redirect } from "expo-router";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useAuthStore } from "../src/store/auth";
import { useThemeStore } from "../src/theme/store";
import type { RoleCode } from "../src/types";

const titles: Record<RoleCode, string> = {
  ADMIN: "admin",
  DISPATCHER: "dispatcher",
  EXECUTOR: "executor",
  AKIM: "akim",
  INSPECTOR: "inspector"
};

const subtitles: Record<RoleCode, string> = {
  ADMIN: "people",
  DISPATCHER: "queue",
  EXECUTOR: "nextTask",
  AKIM: "briefing",
  INSPECTOR: "checks"
};

export default function HomeScreen() {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { colors, toggleTheme } = useThemeStore();

  if (!user) {
    return <Redirect href="/login" />;
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.tenant, { color: colors.mutedText }]}>{user.tenant.name_ru}</Text>
      <Text style={[styles.title, { color: colors.text }]}>{t(titles[user.role.code])}</Text>
      <View style={[styles.card, { borderColor: colors.border }]}>
        <Text style={[styles.cardTitle, { color: colors.text }]}>{t(subtitles[user.role.code])}</Text>
        <Text style={{ color: colors.mutedText }}>Foundation placeholder</Text>
      </View>
      <View style={styles.actions}>
        <Pressable style={[styles.button, { backgroundColor: colors.primary }]} onPress={toggleTheme}>
          <Text style={styles.buttonText}>{t("theme")}</Text>
        </Pressable>
        <Pressable style={[styles.button, { backgroundColor: colors.accent }]} onPress={() => i18n.changeLanguage(i18n.language === "ru" ? "kk" : "ru")}>
          <Text style={styles.buttonText}>{t("language")}</Text>
        </Pressable>
        <Pressable style={[styles.button, { backgroundColor: colors.muted }]} onPress={logout}>
          <Text style={[styles.buttonText, { color: colors.text }]}>{t("signOut")}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, paddingTop: 70 },
  tenant: { fontSize: 14 },
  title: { fontSize: 28, fontWeight: "700", marginTop: 4 },
  card: { borderWidth: 1, borderRadius: 8, padding: 18, marginTop: 24 },
  cardTitle: { fontSize: 18, fontWeight: "700", marginBottom: 8 },
  actions: { gap: 10, marginTop: 24 },
  button: { height: 44, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  buttonText: { color: "#fff", fontWeight: "700" }
});
