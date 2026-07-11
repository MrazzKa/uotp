import { Ionicons } from "@expo/vector-icons";
import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { fetchMe, login } from "../src/lib/api";
import { radii, spacing } from "../src/theme/tokens";
import { useTheme } from "../src/theme/store";

export default function LoginScreen() {
  const { t, i18n } = useTranslation();
  const { colors, toggleTheme } = useTheme();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: async () => {
      await login(identifier, password);
      await fetchMe();
    },
    onSuccess: () => router.replace("/home")
  });

  function toggleLanguage() {
    i18n.changeLanguage(i18n.language === "ru" ? "kk" : "ru");
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.topActions}>
        <Pressable style={[styles.iconButton, { backgroundColor: colors.surface, borderColor: colors.border }]} onPress={toggleLanguage}>
          <Text style={[styles.iconText, { color: colors.text }]}>{i18n.language === "ru" ? "RU" : "KK"}</Text>
        </Pressable>
        <Pressable style={[styles.iconButton, { backgroundColor: colors.surface, borderColor: colors.border }]} onPress={toggleTheme}>
          <Ionicons name="contrast-outline" size={20} color={colors.text} />
        </Pressable>
      </View>
      <View style={[styles.panel, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={[styles.logo, { backgroundColor: colors.primarySoft }]}>
          <Ionicons name="lock-closed-outline" size={28} color={colors.primary} />
        </View>
        <Text style={[styles.title, { color: colors.text }]}>UOTP</Text>
        <Text style={[styles.subtitle, { color: colors.mutedText }]}>{t("signIn")}</Text>

        <TextInput
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          placeholder={t("identifier")}
          placeholderTextColor={colors.mutedText}
          style={[styles.input, { borderColor: colors.border, color: colors.text, backgroundColor: colors.surface2 }]}
          value={identifier}
          onChangeText={setIdentifier}
        />
        <TextInput
          placeholder={t("password")}
          placeholderTextColor={colors.mutedText}
          secureTextEntry
          style={[styles.input, { borderColor: colors.border, color: colors.text, backgroundColor: colors.surface2 }]}
          value={password}
          onChangeText={setPassword}
        />
        <Pressable
          disabled={mutation.isPending || !identifier || !password}
          style={[styles.primaryButton, { backgroundColor: colors.primary, opacity: !identifier || !password ? 0.5 : 1 }]}
          onPress={() => mutation.mutate()}
        >
          <Ionicons name="log-in-outline" size={22} color="#FFFFFF" />
          <Text style={styles.primaryText}>{mutation.isPending ? "..." : t("signIn")}</Text>
        </Pressable>
        {mutation.isError ? (
          <Text style={{ color: colors.danger, fontFamily: "Inter_400Regular", fontSize: 13 }}>
            {(mutation.error as Error)?.message ?? "error"}
          </Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: spacing.xl },
  topActions: { position: "absolute", right: spacing.xl, top: 56, flexDirection: "row", gap: spacing.sm },
  iconButton: { minHeight: 44, minWidth: 44, alignItems: "center", justifyContent: "center", borderWidth: 1, borderRadius: radii.control },
  iconText: { fontFamily: "Inter_600SemiBold", fontSize: 13 },
  panel: { borderWidth: 1, borderRadius: radii.card, padding: spacing.xl, gap: spacing.md },
  logo: { width: 56, height: 56, borderRadius: radii.control, alignItems: "center", justifyContent: "center" },
  title: { fontFamily: "Inter_600SemiBold", fontSize: 28 },
  subtitle: { fontFamily: "Inter_400Regular", fontSize: 15, marginBottom: spacing.sm },
  input: { minHeight: 54, borderWidth: 1, borderRadius: radii.control, paddingHorizontal: spacing.lg, fontFamily: "Inter_400Regular", fontSize: 16 },
  primaryButton: { minHeight: 56, borderRadius: radii.control, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  primaryText: { color: "#FFFFFF", fontFamily: "Inter_600SemiBold", fontSize: 16 }
});
