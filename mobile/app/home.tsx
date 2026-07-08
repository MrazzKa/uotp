import { Ionicons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import * as ExpoNotifications from "expo-notifications";
import { RecordingPresets, requestRecordingPermissionsAsync, setAudioModeAsync, useAudioRecorder } from "expo-audio";
import { Redirect } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View
} from "react-native";
import MapView, { Callout, Marker, Region } from "react-native-maps";

import {
  changePassword,
  createIssue,
  fetchDashboardSummary,
  fetchIssue,
  fetchIssues,
  fetchMapIssues,
  fetchNotifications,
  fetchSpheres,
  fetchUnreadCount,
  fetchUsers,
  logout as logoutApi,
  markAllNotificationsRead,
  markNotificationRead,
  parseVoice,
  registerDevice,
  setPersonalControl,
  submitIssue,
  transitionIssue,
  unregisterDevice,
  updateIssue,
  uploadIssuePhoto
} from "../src/lib/api";
import { getExpoPushToken, notificationPlatform } from "../src/lib/notifications";
import { useAuthStore } from "../src/store/auth";
import { radii, spacing, statusColor } from "../src/theme/tokens";
import { useTheme } from "../src/theme/store";
import type { DashboardSummary, Issue, NotificationItem, User } from "../src/types";

type Screen = "summary" | "list" | "new" | "detail" | "map" | "notifications" | "profile";
type Filter = "all" | "mine" | "personal" | "overdue";
type MapIssueFeature = {
  id: string;
  geometry: { coordinates: [number, number] };
  properties: Record<string, string | boolean | null>;
};

const LEADERSHIP: string[] = ["AKIM", "DEPUTY", "APPARAT", "ADMIN"];

const progressByStatus: Record<string, number> = {
  DRAFT: 5,
  NEW: 15,
  ASSIGNED: 40,
  REVIEW_CONTROLLER: 70,
  REVIEW_AUTHOR: 85,
  CLOSED: 100,
  ON_HOLD: 30
};

function impLabel(value: string) {
  return value === "URGENT" ? "Срочно" : value === "IMPORTANT" ? "Важно" : "Обычная";
}

type TaskAction = { kind: "submit" | "transition"; status?: string; label: string; danger?: boolean };

function taskActions(user: User, issue: Issue): TaskAction[] {
  const acts: TaskAction[] = [];
  const uid = user.id;
  const isAuthor = issue.created_by?.id === uid;
  const isController = issue.controller?.id === uid;
  const isExecutor = issue.assigned_to?.id === uid;
  const isAdmin = user.role.code === "ADMIN";
  if (isExecutor && issue.status === "ASSIGNED") {
    acts.push({ kind: "submit", label: "markDone" });
  }
  if (issue.status === "REVIEW_CONTROLLER" && (isController || isAuthor || isAdmin)) {
    acts.push({ kind: "transition", status: "CLOSED", label: "removeFromControl" });
    if (isController || isAdmin) acts.push({ kind: "transition", status: "REVIEW_AUTHOR", label: "toAuthor" });
    acts.push({ kind: "transition", status: "ASSIGNED", label: "notAccept", danger: true });
  }
  if (issue.status === "REVIEW_AUTHOR" && (isAuthor || isAdmin)) {
    acts.push({ kind: "transition", status: "CLOSED", label: "removeFromControl" });
    acts.push({ kind: "transition", status: "ASSIGNED", label: "notAccept", danger: true });
  }
  return acts;
}

export default function HomeScreen() {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const { colors, toggleTheme } = useTheme();
  const [screen, setScreen] = useState<Screen>(user && LEADERSHIP.includes(user.role.code) ? "summary" : "list");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pushToken, setPushToken] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    getExpoPushToken().then(async (token) => {
      if (!mounted || !token) return;
      setPushToken(token);
      await registerDevice(token, notificationPlatform());
    });
    const subscription = ExpoNotifications.addNotificationResponseReceivedListener((response) => {
      const issueId = response.notification.request.content.data?.issue_id;
      if (typeof issueId === "string") {
        setSelectedId(issueId);
        setScreen("detail");
      }
    });
    return () => {
      mounted = false;
      subscription.remove();
    };
  }, []);

  async function handleLogout() {
    if (pushToken) await unregisterDevice(pushToken);
    await logoutApi();
  }

  if (!user) return <Redirect href="/login" />;

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.header}>
        <View>
          <Text style={[styles.tenant, { color: colors.mutedText }]}>{user.tenant.name_ru}</Text>
          <Text style={[styles.title, { color: colors.text }]}>{screenTitle(screen, t)}</Text>
        </View>
        <Pressable style={[styles.roundButton, { backgroundColor: colors.surface, borderColor: colors.border }]} onPress={toggleTheme}>
          <Ionicons name="contrast-outline" size={22} color={colors.text} />
        </Pressable>
      </View>

      <View style={styles.content}>
        {screen === "summary" ? <Summary onOpen={(id) => { setSelectedId(id); setScreen("detail"); }} /> : null}
        {screen === "list" ? (
          <IssueList
            onOpen={(issue) => {
              setSelectedId(issue.id);
              setScreen("detail");
            }}
          />
        ) : null}
        {screen === "new" ? <IssueCreate onCreated={(id) => { setSelectedId(id); setScreen("detail"); }} /> : null}
        {screen === "detail" && selectedId ? <IssueDetail issueId={selectedId} onBack={() => setScreen("list")} /> : null}
        {screen === "map" ? <IssueMap onOpen={(id) => { setSelectedId(id); setScreen("detail"); }} /> : null}
        {screen === "notifications" ? <NotificationsList onOpen={(id) => { setSelectedId(id); setScreen("detail"); }} /> : null}
        {screen === "profile" ? <Profile onLogout={handleLogout} /> : null}
      </View>

      <BottomTabs screen={screen} onChange={(next) => setScreen(next)} />
    </View>
  );
}

function screenTitle(screen: Screen, t: (key: string) => string) {
  if (screen === "summary") return t("summaryTab");
  if (screen === "new") return t("newIssue");
  if (screen === "map") return t("map");
  if (screen === "notifications") return t("notifications");
  if (screen === "profile") return t("profile");
  return t("myIssues");
}

function BottomTabs({ screen, onChange }: { screen: Screen; onChange: (screen: Screen) => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const user = useAuthStore((state) => state.user);
  const leader = user ? LEADERSHIP.includes(user.role.code) : false;
  const unread = useQuery({ queryKey: ["notifications", "unread-count"], queryFn: fetchUnreadCount, refetchInterval: 30000 });
  const tabs: Array<{ key: Screen; label: string; icon: keyof typeof Ionicons.glyphMap }> = leader
    ? [
        { key: "summary", label: t("summaryTab"), icon: "grid-outline" },
        { key: "list", label: t("issues"), icon: "list-outline" },
        { key: "new", label: t("createTab"), icon: "add-circle-outline" },
        { key: "notifications", label: t("notificationsTab"), icon: "notifications-outline" },
        { key: "profile", label: t("profile"), icon: "person-outline" }
      ]
    : [
        { key: "list", label: t("issues"), icon: "list-outline" },
        { key: "map", label: t("map"), icon: "map-outline" },
        { key: "new", label: t("createTab"), icon: "add-circle-outline" },
        { key: "notifications", label: t("notificationsTab"), icon: "notifications-outline" },
        { key: "profile", label: t("profile"), icon: "person-outline" }
      ];
  return (
    <View style={[styles.tabs, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      {tabs.map((tab) => {
        const active = screen === tab.key || (screen === "detail" && tab.key === "list");
        return (
          <Pressable key={tab.key} style={styles.tab} onPress={() => onChange(tab.key)}>
            <View>
              <Ionicons name={tab.icon} size={24} color={active ? colors.primary : colors.mutedText} />
              {tab.key === "notifications" && (unread.data ?? 0) > 0 ? (
                <View style={[styles.badge, { backgroundColor: colors.danger }]}>
                  <Text style={styles.badgeText}>{Math.min(unread.data ?? 0, 99)}</Text>
                </View>
              ) : null}
            </View>
            <Text style={[styles.tabText, { color: active ? colors.primary : colors.mutedText }]}>{tab.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function okrugTone(pct: number, colors: { success: string; warning: string; danger: string }) {
  if (pct >= 85) return colors.success;
  if (pct >= 65) return colors.warning;
  return colors.danger;
}

function KpiCard({ label, value, color }: { label: string; value: number; color: string }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.kpiCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.kpiValue, { color }]}>{value}</Text>
      <Text style={[styles.kpiLabel, { color: colors.mutedText }]}>{label}</Text>
    </View>
  );
}

function Summary({ onOpen }: { onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const summary = useQuery({ queryKey: ["dashboard-summary"], queryFn: fetchDashboardSummary });
  const personal = useQuery({ queryKey: ["issues", { personal: "true" }], queryFn: () => fetchIssues({ personal: "true", limit: "20" }) });
  const counts = summary.data?.counts;
  const okrug = summary.data?.okrug_monitoring ?? [];
  const personalItems = personal.data ?? [];

  return (
    <ScrollView
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={summary.isFetching} onRefresh={() => { summary.refetch(); personal.refetch(); }} tintColor={colors.primary} />}
    >
      {counts ? (
        <View style={styles.kpiRow}>
          <KpiCard label={t("inProgress")} value={counts.in_progress} color={colors.primary} />
          <KpiCard label={t("overdue")} value={counts.overdue} color={colors.danger} />
          <KpiCard label={t("onReview")} value={counts.on_review} color={colors.warning} />
          <KpiCard label={t("newTasks")} value={counts.new} color={colors.info} />
        </View>
      ) : null}

      <Text style={[styles.sectionTitle, { color: colors.text, marginTop: spacing.md }]}>{t("onlyPersonal")}</Text>
      {personalItems.length ? personalItems.map((issue) => <IssueCard key={issue.id} issue={issue} onPress={() => onOpen(issue.id)} />) : <EmptyState />}

      {okrug.length ? (
        <>
          <Text style={[styles.sectionTitle, { color: colors.text, marginTop: spacing.md }]}>{t("okrugMonitoring")}</Text>
          {okrug.map((zone) => {
            const tone = okrugTone(zone.pct, colors);
            return (
              <View key={zone.name} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
                <View style={styles.cardHeader}>
                  <View style={styles.flexOne}>
                    <Text style={[styles.cardNumber, { color: colors.text }]}>{zone.name}</Text>
                    <Text style={[styles.metaText, { color: colors.mutedText }]}>{zone.done} {t("ofTasks")} {zone.total}</Text>
                  </View>
                  <Text style={[styles.okrugPct, { color: tone }]}>{zone.pct}%</Text>
                </View>
                <View style={styles.progressTrack}>
                  <View style={[styles.progressFill, { backgroundColor: tone, width: `${zone.pct}%` }]} />
                </View>
              </View>
            );
          })}
        </>
      ) : null}
    </ScrollView>
  );
}

function NotificationsList({ onOpen }: { onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { colors } = useTheme();
  const notifications = useQuery({
    queryKey: ["notifications", "list"],
    queryFn: fetchNotifications,
    refetchInterval: 30000
  });
  const readOne = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    }
  });
  const readAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    }
  });

  async function handleOpen(item: NotificationItem) {
    if (!item.is_read) await readOne.mutateAsync(item.id);
    if (item.issue_id) onOpen(item.issue_id);
  }

  return (
    <ScrollView
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={notifications.isFetching} onRefresh={() => notifications.refetch()} tintColor={colors.primary} />}
    >
      <View style={styles.filterRow}>
        <SecondaryButton label={t("markAllRead")} icon="checkmark-done-outline" onPress={() => readAll.mutate()} />
      </View>
      {(notifications.data ?? []).length ? (
        notifications.data?.map((item) => (
          <Pressable
            key={item.id}
            style={[
              styles.card,
              { backgroundColor: item.is_read ? colors.surface : colors.primarySoft, borderColor: colors.border }
            ]}
            onPress={() => handleOpen(item)}
          >
            <View style={styles.cardHeader}>
              <Text style={[styles.cardNumber, { color: colors.text }]}>{item.title}</Text>
              {!item.is_read ? <View style={[styles.unreadDot, { backgroundColor: colors.primary }]} /> : null}
            </View>
            <Text style={[styles.cardTitle, { color: colors.text }]}>{item.body}</Text>
            <Text style={[styles.metaText, { color: colors.mutedText }]}>{new Date(item.created_at).toLocaleString()}</Text>
          </Pressable>
        ))
      ) : (
        <EmptyState />
      )}
    </ScrollView>
  );
}

function Pill({ label, active, onPress }: { label: string; active?: boolean; onPress?: () => void }) {
  const { colors } = useTheme();
  return (
    <Pressable
      style={[styles.pill, { backgroundColor: active ? colors.primarySoft : colors.surface, borderColor: active ? colors.primary : colors.border }]}
      onPress={onPress}
    >
      <Text style={[styles.pillText, { color: active ? colors.primary : colors.mutedText }]}>{label}</Text>
    </Pressable>
  );
}

function StatusPill({ status, overdue }: { status: string; overdue?: boolean }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const tone = statusColor(status, overdue, colors);
  return (
    <View style={[styles.statusPill, { backgroundColor: tone.soft }]}>
      <View style={[styles.statusDot, { backgroundColor: tone.bg }]} />
      <Text style={[styles.statusText, { color: tone.text }]}>{t(`st_${status}`, status)}</Text>
    </View>
  );
}

function dueLabel(issue: Issue, overdueLabel: string) {
  if (issue.is_overdue) return overdueLabel;
  if (!issue.due_at) return "";
  const minutes = Math.ceil((new Date(issue.due_at).getTime() - Date.now()) / 60000);
  if (minutes < 0) return overdueLabel;
  const hours = Math.floor(minutes / 60);
  if (hours >= 24) return `${Math.floor(hours / 24)}д`;
  const rest = minutes % 60;
  return hours > 0 ? `${hours}ч ${rest}м` : `${rest}м`;
}

function IssueList({ onOpen }: { onOpen: (issue: Issue) => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const user = useAuthStore((state) => state.user);
  const [filter, setFilter] = useState<Filter>("all");
  const params = useMemo(
    () => ({
      is_overdue: filter === "overdue" ? "true" : undefined,
      personal: filter === "personal" ? "true" : undefined,
      assigned_to: filter === "mine" ? user?.id : undefined
    }),
    [filter, user?.id]
  );
  const issues = useQuery({ queryKey: ["issues", params], queryFn: () => fetchIssues(params) });
  const visible = issues.data ?? [];

  return (
    <ScrollView
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={issues.isFetching} onRefresh={() => issues.refetch()} tintColor={colors.primary} />}
    >
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterRow}>
        <Pill label={t("all")} active={filter === "all"} onPress={() => setFilter("all")} />
        <Pill label={t("mine")} active={filter === "mine"} onPress={() => setFilter("mine")} />
        <Pill label={t("onlyPersonal")} active={filter === "personal"} onPress={() => setFilter("personal")} />
        <Pill label={t("overdueOnly")} active={filter === "overdue"} onPress={() => setFilter("overdue")} />
      </ScrollView>
      {visible.length ? visible.map((issue) => <IssueCard key={issue.id} issue={issue} onPress={() => onOpen(issue)} />) : <EmptyState />}
    </ScrollView>
  );
}

function IssueCard({ issue, onPress }: { issue: Issue; onPress: () => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const meta = [issue.sphere?.name_ru, impLabel(issue.importance)].filter(Boolean).join(" · ");
  return (
    <Pressable style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]} onPress={onPress}>
      <View style={styles.cardHeader}>
        <View style={styles.rowGap}>
          <Text style={[styles.cardNumber, { color: colors.text }]}>{issue.public_number}</Text>
          {issue.on_personal_control ? <Ionicons name="star" size={14} color={colors.warning} /> : null}
        </View>
        <StatusPill status={issue.status} overdue={issue.is_overdue} />
      </View>
      <Text style={[styles.cardTitle, { color: colors.text }]}>{issue.title}</Text>
      <Text style={[styles.metaText, { color: colors.mutedText }]}>{meta}</Text>
      <View style={styles.cardFooter}>
        <Text style={[styles.metaText, { color: colors.mutedText }]}>{issue.assigned_to?.full_name ?? issue.address ?? ""}</Text>
        <View style={[styles.slaPill, { backgroundColor: issue.is_overdue ? colors.danger : colors.primarySoft }]}>
          <Text style={[styles.slaText, { color: issue.is_overdue ? "#FFFFFF" : colors.primary }]}>
            {dueLabel(issue, t("overdue")) || "-"}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

function IssueCreate({ onCreated }: { onCreated: (id: string) => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { colors } = useTheme();
  const spheres = useQuery({ queryKey: ["spheres"], queryFn: fetchSpheres });
  const users = useQuery({ queryKey: ["users"], queryFn: fetchUsers });
  const [title, setTitle] = useState("");
  const [importance, setImportance] = useState("NORMAL");
  const [taskType, setTaskType] = useState("TASK");
  const [executorId, setExecutorId] = useState("");
  const [coExec, setCoExec] = useState<string[]>([]);
  const [sphereId, setSphereId] = useState("");
  const [address, setAddress] = useState("");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [coords, setCoords] = useState<{ latitude: number; longitude: number } | null>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [recording, setRecording] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);

  async function toggleVoice() {
    if (voiceBusy) return;
    if (recording) {
      setRecording(false);
      try {
        await recorder.stop();
        const uri = recorder.uri;
        if (!uri) return;
        setVoiceBusy(true);
        const draft = await parseVoice(uri);
        if (draft.title) setTitle(draft.title);
        if (draft.importance) setImportance(draft.importance);
        if (draft.sphere_id) setSphereId(draft.sphere_id);
        if (draft.executor_id) setExecutorId(draft.executor_id);
      } catch (error) {
        const status = (error as { response?: { status?: number } })?.response?.status;
        Alert.alert(t("voiceInput"), status === 503 ? t("voiceNotConfigured") : t("voiceError"));
      } finally {
        setVoiceBusy(false);
      }
      return;
    }
    const permission = await requestRecordingPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(t("voiceInput"), t("voiceNoPermission"));
      return;
    }
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    await recorder.prepareToRecordAsync();
    recorder.record();
    setRecording(true);
  }

  const mutation = useMutation({
    mutationFn: async () => {
      let location = coords;
      if (!location) {
        const permission = await Location.requestForegroundPermissionsAsync();
        if (permission.granted) {
          const current = await Location.getCurrentPositionAsync({});
          location = { latitude: current.coords.latitude, longitude: current.coords.longitude };
        }
      }
      const issue = await createIssue({
        source: "app",
        task_type: taskType,
        title,
        importance,
        sphere_id: sphereId || undefined,
        executor_ids: executorId ? [executorId] : [],
        co_executor_ids: coExec.filter((id) => id !== executorId),
        address: address || undefined,
        latitude: location?.latitude,
        longitude: location?.longitude
      });
      if (photoUri) await uploadIssuePhoto(issue.id, photoUri, "before", location?.latitude, location?.longitude);
      return issue;
    },
    onSuccess: (issue) => {
      queryClient.invalidateQueries({ queryKey: ["issues"] });
      onCreated(issue.id);
    }
  });

  async function pickPhoto() {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    const result = permission.granted
      ? await ImagePicker.launchCameraAsync({ quality: 0.7 })
      : await ImagePicker.launchImageLibraryAsync({ quality: 0.7 });
    if (!result.canceled) setPhotoUri(result.assets[0].uri);
  }

  async function captureLocation() {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (!permission.granted) return;
    const current = await Location.getCurrentPositionAsync({});
    setCoords({ latitude: current.coords.latitude, longitude: current.coords.longitude });
  }

  return (
    <ScrollView showsVerticalScrollIndicator={false}>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Pressable
          style={[styles.voiceButton, { borderColor: recording ? colors.danger : colors.primary, backgroundColor: recording ? colors.danger : colors.primarySoft }]}
          onPress={toggleVoice}
          disabled={voiceBusy}
        >
          <Ionicons name={recording ? "stop-circle-outline" : "mic-outline"} size={22} color={recording ? "#FFFFFF" : colors.primary} />
          <Text style={[styles.voiceText, { color: recording ? "#FFFFFF" : colors.primary }]}>
            {voiceBusy ? t("voiceProcessing") : recording ? t("voiceStop") : t("voiceInput")}
          </Text>
        </Pressable>
        <View style={styles.filterRow}>
          <Pill label={t("typeTask")} active={taskType === "TASK"} onPress={() => setTaskType("TASK")} />
          <Pill label={t("typeEvent")} active={taskType === "EVENT"} onPress={() => setTaskType("EVENT")} />
        </View>
        <TextInput style={[styles.input, styles.multiline, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]} placeholder={t("taskText")} placeholderTextColor={colors.mutedText} value={title} onChangeText={setTitle} multiline />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryRow}>
          {["URGENT", "IMPORTANT", "NORMAL"].map((item) => <Pill key={item} label={impLabel(item)} active={importance === item} onPress={() => setImportance(item)} />)}
        </ScrollView>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryRow}>
          {(spheres.data ?? []).map((item) => <Pill key={item.id} label={item.name_ru} active={sphereId === item.id} onPress={() => setSphereId(item.id)} />)}
        </ScrollView>
        <Text style={[styles.fieldLabel, { color: colors.mutedText }]}>{t("assignee")}</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryRow}>
          {(users.data ?? []).map((u) => <Pill key={u.id} label={u.full_name} active={executorId === u.id} onPress={() => setExecutorId(executorId === u.id ? "" : u.id)} />)}
        </ScrollView>
        <Text style={[styles.fieldLabel, { color: colors.mutedText }]}>{t("coExecutors")}</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryRow}>
          {(users.data ?? []).filter((u) => u.id !== executorId).map((u) => (
            <Pill
              key={u.id}
              label={u.full_name}
              active={coExec.includes(u.id)}
              onPress={() => setCoExec((prev) => (prev.includes(u.id) ? prev.filter((x) => x !== u.id) : [...prev, u.id]))}
            />
          ))}
        </ScrollView>
        <TextInput style={[styles.input, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]} placeholder={t("address")} placeholderTextColor={colors.mutedText} value={address} onChangeText={setAddress} />
        <View style={styles.twoColumns}>
          <SecondaryButton label={photoUri ? t("photo") : t("addPhoto")} icon="camera-outline" onPress={pickPhoto} />
          <SecondaryButton label={coords ? t("gps") : t("myLocation")} icon="location-outline" onPress={captureLocation} />
        </View>
        {photoUri ? <Image source={{ uri: photoUri }} style={styles.photo} /> : null}
        <PrimaryButton label={t("submit")} icon="send-outline" disabled={mutation.isPending || title.length < 3} onPress={() => mutation.mutate()} />
      </View>
    </ScrollView>
  );
}

function IssueDetail({ issueId, onBack }: { issueId: string; onBack: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const { colors } = useTheme();
  const issue = useQuery({ queryKey: ["issue", issueId], queryFn: () => fetchIssue(issueId) });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["issue", issueId] });
    queryClient.invalidateQueries({ queryKey: ["issues"] });
  };
  const transition = useMutation({ mutationFn: (status: string) => transitionIssue(issueId, status), onSuccess: invalidate });
  const submit = useMutation({ mutationFn: (report?: string) => submitIssue(issueId, report), onSuccess: invalidate });
  const personal = useMutation({
    mutationFn: (on: boolean) => setPersonalControl(issueId, on, issue.data?.importance ?? "NORMAL"),
    onSuccess: invalidate
  });
  const update = useMutation({ mutationFn: (payload: Record<string, unknown>) => updateIssue(issueId, payload), onSuccess: invalidate });
  const [report, setReport] = useState("");
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editImp, setEditImp] = useState("NORMAL");
  const data = issue.data;
  const actions = data && user ? taskActions(user, data) : [];
  const canPersonal = user ? LEADERSHIP.includes(user.role.code) : false;
  const hasSubmit = actions.some((action) => action.kind === "submit");
  const canEdit = !!(data && user && data.created_by?.id === user.id && ["DRAFT", "NEW", "ASSIGNED"].includes(data.status));

  function runAction(action: TaskAction) {
    if (action.kind === "submit") submit.mutate(report || undefined);
    else if (action.status) transition.mutate(action.status);
  }

  return (
    <ScrollView showsVerticalScrollIndicator={false}>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Ionicons name="chevron-back-outline" size={22} color={colors.primary} />
        <Text style={[styles.backText, { color: colors.primary }]}>{t("back")}</Text>
      </Pressable>
      {data ? (
        <>
          <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={styles.cardHeader}>
              <View style={styles.rowGap}>
                <Text style={[styles.cardNumber, { color: colors.text }]}>{data.public_number}</Text>
                {data.on_personal_control ? <Ionicons name="star" size={15} color={colors.warning} /> : null}
              </View>
              <StatusPill status={data.status} overdue={data.is_overdue} />
            </View>
            <Text style={[styles.detailTitle, { color: colors.text }]}>{data.title}</Text>
            <Text style={[styles.metaText, { color: colors.mutedText }]}>{impLabel(data.importance)}{data.sphere ? ` · ${data.sphere.name_ru}` : ""}</Text>
            {data.attachments?.[0] ? <Image source={{ uri: data.attachments[0].thumbnail_url ?? data.attachments[0].file_url }} style={styles.photo} /> : null}
            {data.description && data.description !== data.title ? <Text style={[styles.body, { color: colors.text }]}>{data.description}</Text> : null}
            <View style={styles.metaGrid}>
              <MetaRow label={t("assignee")} value={data.assigned_to?.full_name} />
              <MetaRow label={t("controller")} value={data.controller?.full_name} />
            </View>
          </View>
          {canEdit ? (
            editing ? (
              <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
                <TextInput
                  style={[styles.input, styles.multiline, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]}
                  value={editTitle}
                  onChangeText={setEditTitle}
                  multiline
                />
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryRow}>
                  {["URGENT", "IMPORTANT", "NORMAL"].map((item) => (
                    <Pill key={item} label={impLabel(item)} active={editImp === item} onPress={() => setEditImp(item)} />
                  ))}
                </ScrollView>
                <PrimaryButton label={t("save")} icon="save-outline" onPress={() => { update.mutate({ title: editTitle, importance: editImp }); setEditing(false); }} />
                <SecondaryButton label={t("back")} icon="close-outline" onPress={() => setEditing(false)} />
              </View>
            ) : (
              <SecondaryButton label={t("edit")} icon="create-outline" onPress={() => { setEditTitle(data.title); setEditImp(data.importance); setEditing(true); }} />
            )
          ) : null}
          <SmartCard issue={data} />
          <Deadlines issue={data} />
          <Timeline issue={data} />
          <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            {hasSubmit ? (
              <TextInput
                style={[styles.input, styles.multiline, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]}
                placeholder={t("reportHint")}
                placeholderTextColor={colors.mutedText}
                value={report}
                onChangeText={setReport}
                multiline
              />
            ) : null}
            {actions.length ? (
              actions.map((action, index) =>
                index === 0 ? (
                  <PrimaryButton key={action.label} label={t(action.label)} icon="checkmark-circle-outline" onPress={() => runAction(action)} />
                ) : (
                  <SecondaryButton key={action.label} label={t(action.label)} icon={action.danger ? "close-outline" : "arrow-forward-outline"} onPress={() => runAction(action)} />
                )
              )
            ) : (
              <Text style={[styles.metaText, { color: colors.mutedText }]}>{t("emptyState")}</Text>
            )}
            {canPersonal ? (
              <SecondaryButton
                label={t(data.on_personal_control ? "personalControlOff" : "personalControlOn")}
                icon={data.on_personal_control ? "star" : "star-outline"}
                onPress={() => personal.mutate(!data.on_personal_control)}
              />
            ) : null}
          </View>
        </>
      ) : null}
    </ScrollView>
  );
}

function MetaRow({ label, value }: { label: string; value?: string | null }) {
  const { colors } = useTheme();
  return (
    <View style={styles.deadlineRow}>
      <Text style={[styles.metaText, { color: colors.mutedText }]}>{label}</Text>
      <Text style={[styles.deadlineValue, { color: colors.text }]}>{value || "-"}</Text>
    </View>
  );
}

function SmartCard({ issue }: { issue: Issue }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const progress = progressByStatus[issue.status] ?? 0;
  const risk = riskLevel(issue);
  const riskLabel = risk === "high" ? t("riskHigh") : risk === "medium" ? t("riskMedium") : t("riskLow");
  const riskColor = risk === "high" ? colors.danger : risk === "medium" ? colors.warning : colors.success;
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <Text style={[styles.sectionTitle, { color: colors.text }]}>{t("progress")}</Text>
        <View style={[styles.slaPill, { backgroundColor: riskColor }]}>
          <Text style={[styles.slaText, { color: "#FFFFFF" }]}>{riskLabel}</Text>
        </View>
      </View>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { backgroundColor: colors.primary, width: `${progress}%` }]} />
      </View>
      <Text style={[styles.metaText, { color: colors.mutedText }]}>{progress}%</Text>
    </View>
  );
}

function Deadlines({ issue }: { issue: Issue }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.sectionTitle, { color: colors.text }]}>{t("dueDate")}</Text>
      <View style={styles.deadlineRow}>
        <Text style={[styles.metaText, { color: colors.mutedText }]}>{t("dueDate")}</Text>
        <Text style={[styles.deadlineValue, { color: issue.is_overdue ? colors.danger : colors.text }]}>
          {issue.due_at ? new Date(issue.due_at).toLocaleString() : "-"}
        </Text>
      </View>
    </View>
  );
}

function Timeline({ issue }: { issue: Issue }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.sectionTitle, { color: colors.text }]}>{t("timeline")}</Text>
      {(issue.history ?? []).slice(0, 6).map((event) => (
        <View key={event.id} style={[styles.timelineItem, { borderLeftColor: colors.primary }]}>
          <Text style={[styles.cardNumber, { color: colors.text }]}>{event.action}</Text>
          <Text style={[styles.metaText, { color: colors.mutedText }]}>{new Date(event.created_at).toLocaleString()}</Text>
        </View>
      ))}
    </View>
  );
}

function IssueMap({ onOpen }: { onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [region, setRegion] = useState<Region>({ latitude: 54.8666, longitude: 69.15, latitudeDelta: 0.11, longitudeDelta: 0.18 });
  const bbox = `${region.longitude - region.longitudeDelta / 2},${region.latitude - region.latitudeDelta / 2},${region.longitude + region.longitudeDelta / 2},${region.latitude + region.latitudeDelta / 2}`;
  const markers = useQuery({ queryKey: ["map-issues", bbox], queryFn: () => fetchMapIssues(bbox) });

  async function centerOnMe() {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (!permission.granted) return;
    const current = await Location.getCurrentPositionAsync({});
    setRegion({ latitude: current.coords.latitude, longitude: current.coords.longitude, latitudeDelta: 0.04, longitudeDelta: 0.06 });
  }

  return (
    <View style={[styles.mapWrap, { borderColor: colors.border }]}>
      <MapView style={styles.map} region={region} onRegionChangeComplete={setRegion}>
        {((markers.data ?? []) as MapIssueFeature[]).map((feature) => {
          const [longitude, latitude] = feature.geometry.coordinates;
          const overdue = feature.properties.is_overdue === true || feature.properties.is_overdue === "true";
          const status = String(feature.properties.status ?? "NEW");
          return (
            <Marker key={feature.id} coordinate={{ latitude, longitude }} pinColor={overdue ? colors.danger : statusColor(status, false, colors).bg}>
              <Callout onPress={() => onOpen(String(feature.properties.id))}>
                <View style={styles.callout}>
                  <Text style={styles.calloutTitle}>{feature.properties.public_number}</Text>
                  <Text>{status}{overdue ? ` - ${t("overdue")}` : ""}</Text>
                  <Text>{feature.properties.address}</Text>
                  <Text>{t("open")}</Text>
                </View>
              </Callout>
            </Marker>
          );
        })}
      </MapView>
      <Pressable style={[styles.locationButton, { backgroundColor: colors.primary }]} onPress={centerOnMe}>
        <Ionicons name="navigate-outline" size={22} color="#FFFFFF" />
      </Pressable>
    </View>
  );
}

function Profile({ onLogout }: { onLogout: () => void }) {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const { colors, toggleTheme } = useTheme();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const pass = useMutation({
    mutationFn: () => changePassword(current, next),
    onSuccess: () => { setCurrent(""); setNext(""); Alert.alert(t("changePassword"), t("passwordChanged")); },
    onError: () => Alert.alert(t("changePassword"), t("passwordError"))
  });
  return (
    <ScrollView showsVerticalScrollIndicator={false}>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.detailTitle, { color: colors.text }]}>{user?.full_name}</Text>
        <Text style={[styles.metaText, { color: colors.mutedText }]}>{user?.role.name_ru ?? user?.role.code}</Text>
        <SecondaryButton label={t("theme")} icon="contrast-outline" onPress={toggleTheme} />
        <SecondaryButton label={t("language")} icon="language-outline" onPress={() => i18n.changeLanguage(i18n.language === "ru" ? "kk" : "ru")} />
      </View>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.sectionTitle, { color: colors.text }]}>{t("changePassword")}</Text>
        <TextInput style={[styles.input, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]} placeholder={t("currentPassword")} placeholderTextColor={colors.mutedText} secureTextEntry value={current} onChangeText={setCurrent} />
        <TextInput style={[styles.input, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]} placeholder={t("newPassword")} placeholderTextColor={colors.mutedText} secureTextEntry value={next} onChangeText={setNext} />
        <PrimaryButton label={t("save")} icon="key-outline" disabled={pass.isPending || current.length < 1 || next.length < 6} onPress={() => pass.mutate()} />
      </View>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <PrimaryButton label={t("signOut")} icon="log-out-outline" onPress={onLogout} />
      </View>
    </ScrollView>
  );
}

function EmptyState() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return <Text style={[styles.empty, { color: colors.mutedText }]}>{t("emptyState")}</Text>;
}

function PrimaryButton({ label, icon, disabled, onPress }: { label: string; icon: keyof typeof Ionicons.glyphMap; disabled?: boolean; onPress: () => void }) {
  const { colors } = useTheme();
  return (
    <Pressable disabled={disabled} style={[styles.primaryButton, { backgroundColor: colors.primary, opacity: disabled ? 0.55 : 1 }]} onPress={onPress}>
      <Ionicons name={icon} size={22} color="#FFFFFF" />
      <Text style={styles.primaryText}>{label}</Text>
    </Pressable>
  );
}

function SecondaryButton({ label, icon, onPress }: { label: string; icon: keyof typeof Ionicons.glyphMap; onPress: () => void }) {
  const { colors } = useTheme();
  return (
    <Pressable style={[styles.secondaryButton, { backgroundColor: colors.surface2, borderColor: colors.border }]} onPress={onPress}>
      <Ionicons name={icon} size={20} color={colors.primary} />
      <Text style={[styles.secondaryText, { color: colors.text }]}>{label}</Text>
    </Pressable>
  );
}

function riskLevel(issue: Issue) {
  if (issue.is_overdue) return "high";
  if (!issue.due_at) return "low";
  const created = new Date(issue.created_at).getTime();
  const due = new Date(issue.due_at).getTime();
  const remaining = due - Date.now();
  const total = Math.max(due - created, 1);
  return remaining / total < 0.2 ? "medium" : "low";
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 56 },
  header: { paddingHorizontal: spacing.xl, paddingBottom: spacing.md, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  tenant: { fontFamily: "Inter_400Regular", fontSize: 13 },
  title: { fontFamily: "Inter_600SemiBold", fontSize: 28 },
  roundButton: { width: 46, height: 46, borderRadius: radii.control, borderWidth: 1, alignItems: "center", justifyContent: "center" },
  content: { flex: 1, paddingHorizontal: spacing.lg },
  tabs: { minHeight: 76, borderTopWidth: 1, flexDirection: "row", paddingBottom: spacing.sm, paddingTop: spacing.sm },
  tab: { flex: 1, alignItems: "center", justifyContent: "center", gap: 2 },
  tabText: { fontFamily: "Inter_500Medium", fontSize: 12 },
  badge: { position: "absolute", right: -10, top: -8, minWidth: 18, height: 18, borderRadius: 9, alignItems: "center", justifyContent: "center", paddingHorizontal: 4 },
  badgeText: { color: "#FFFFFF", fontFamily: "Inter_600SemiBold", fontSize: 10 },
  filterRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  rowGap: { flexDirection: "row", alignItems: "center", gap: 6 },
  pill: { minHeight: 38, borderRadius: radii.chip, borderWidth: 1, paddingHorizontal: spacing.lg, alignItems: "center", justifyContent: "center", marginRight: spacing.sm },
  pillText: { fontFamily: "Inter_600SemiBold", fontSize: 13 },
  card: { borderWidth: 1, borderRadius: radii.card, padding: spacing.lg, marginBottom: spacing.md },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md, alignItems: "center", marginBottom: spacing.sm },
  cardNumber: { fontFamily: "Inter_600SemiBold", fontSize: 15 },
  cardTitle: { fontFamily: "Inter_500Medium", fontSize: 16, marginBottom: spacing.xs },
  detailTitle: { fontFamily: "Inter_600SemiBold", fontSize: 22, marginBottom: spacing.xs },
  sectionTitle: { fontFamily: "Inter_600SemiBold", fontSize: 17, marginBottom: spacing.md },
  metaText: { fontFamily: "Inter_400Regular", fontSize: 14 },
  metaGrid: { marginTop: spacing.md },
  body: { fontFamily: "Inter_400Regular", fontSize: 15, lineHeight: 22, marginTop: spacing.md },
  cardFooter: { marginTop: spacing.md, flexDirection: "row", justifyContent: "space-between", gap: spacing.sm, alignItems: "center" },
  statusPill: { minHeight: 28, borderRadius: radii.chip, paddingHorizontal: spacing.sm, flexDirection: "row", alignItems: "center", gap: 6 },
  statusDot: { width: 7, height: 7, borderRadius: radii.chip },
  statusText: { fontFamily: "Inter_600SemiBold", fontSize: 11 },
  unreadDot: { width: 9, height: 9, borderRadius: 5 },
  slaPill: { borderRadius: radii.chip, paddingHorizontal: spacing.sm, paddingVertical: 5 },
  slaText: { fontFamily: "Inter_600SemiBold", fontSize: 12 },
  voiceButton: { minHeight: 52, borderRadius: radii.control, borderWidth: 1, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  voiceText: { fontFamily: "Inter_600SemiBold", fontSize: 15 },
  input: { minHeight: 54, borderWidth: 1, borderRadius: radii.control, paddingHorizontal: spacing.lg, marginBottom: spacing.md, fontFamily: "Inter_400Regular", fontSize: 16 },
  multiline: { minHeight: 118, paddingTop: spacing.md },
  categoryRow: { marginBottom: spacing.md },
  fieldLabel: { fontFamily: "Inter_500Medium", fontSize: 13, marginBottom: spacing.sm },
  twoColumns: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  primaryButton: { minHeight: 56, borderRadius: radii.control, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: spacing.sm },
  primaryText: { color: "#FFFFFF", fontFamily: "Inter_600SemiBold", fontSize: 16 },
  secondaryButton: { minHeight: 52, borderRadius: radii.control, borderWidth: 1, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: spacing.sm, paddingHorizontal: spacing.md, marginTop: spacing.sm },
  secondaryText: { fontFamily: "Inter_600SemiBold", fontSize: 14 },
  photo: { width: "100%", height: 210, borderRadius: radii.card, marginTop: spacing.md },
  progressTrack: { height: 8, borderRadius: radii.chip, backgroundColor: "rgba(148,163,184,0.22)", overflow: "hidden", marginBottom: spacing.sm },
  progressFill: { height: "100%", borderRadius: radii.chip },
  deadlineRow: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md, paddingVertical: spacing.sm },
  deadlineValue: { flex: 1, textAlign: "right", fontFamily: "Inter_500Medium", fontSize: 13 },
  timelineItem: { borderLeftWidth: 2, paddingLeft: spacing.md, marginBottom: spacing.md },
  backButton: { flexDirection: "row", alignItems: "center", gap: 4, minHeight: 44, marginBottom: spacing.sm },
  backText: { fontFamily: "Inter_600SemiBold", fontSize: 15 },
  mapWrap: { flex: 1, minHeight: 520, borderWidth: 1, borderRadius: radii.card, overflow: "hidden" },
  map: { flex: 1 },
  locationButton: { position: "absolute", right: spacing.md, top: spacing.md, width: 48, height: 48, borderRadius: radii.control, alignItems: "center", justifyContent: "center" },
  callout: { width: 190, gap: 3 },
  calloutTitle: { fontFamily: "Inter_600SemiBold" },
  empty: { textAlign: "center", marginTop: spacing.xxl, fontFamily: "Inter_400Regular" },
  flexOne: { flex: 1 },
  kpiRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginBottom: spacing.sm },
  kpiCard: { flexGrow: 1, minWidth: "45%", borderWidth: 1, borderRadius: radii.card, padding: spacing.md },
  kpiValue: { fontFamily: "Inter_600SemiBold", fontSize: 26 },
  kpiLabel: { fontFamily: "Inter_400Regular", fontSize: 13, marginTop: 2 },
  okrugPct: { fontFamily: "Inter_600SemiBold", fontSize: 18 }
});
