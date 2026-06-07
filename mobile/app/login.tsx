import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { fetchMe, login } from "../src/lib/api";
import { useThemeStore } from "../src/theme/store";

export default function LoginScreen() {
  const { t } = useTranslation();
  const colors = useThemeStore((state) => state.colors);
  const [identifier, setIdentifier] = useState("executor@uotp.local");
  const [password, setPassword] = useState("demo123");
  const mutation = useMutation({
    mutationFn: async () => {
      await login(identifier, password);
      await fetchMe();
    },
    onSuccess: () => router.replace("/home")
  });

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={[styles.panel, { borderColor: colors.border }]}>
        <Text style={[styles.title, { color: colors.text }]}>UOTP</Text>
        <TextInput style={[styles.input, { borderColor: colors.border, color: colors.text }]} value={identifier} onChangeText={setIdentifier} placeholder={t("identifier")} placeholderTextColor={colors.mutedText} autoCapitalize="none" />
        <TextInput style={[styles.input, { borderColor: colors.border, color: colors.text }]} value={password} onChangeText={setPassword} placeholder={t("password")} placeholderTextColor={colors.mutedText} secureTextEntry />
        <Pressable style={[styles.button, { backgroundColor: colors.primary }]} onPress={() => mutation.mutate()}>
          <Text style={styles.buttonText}>{t("signIn")}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 20 },
  panel: { borderWidth: 1, borderRadius: 8, padding: 20, gap: 14 },
  title: { fontSize: 26, fontWeight: "700" },
  input: { height: 46, borderWidth: 1, borderRadius: 8, paddingHorizontal: 12 },
  button: { height: 46, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  buttonText: { color: "#fff", fontWeight: "700" }
});
