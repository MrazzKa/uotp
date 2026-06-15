import { Ionicons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import * as ExpoNotifications from "expo-notifications";
import { Redirect } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
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
  createIssue,
  fetchCatalogs,
  fetchIssue,
  fetchIssues,
  fetchMapIssues,
  fetchNotifications,
  fetchUnreadCount,
  logout as logoutApi,
  markAllNotificationsRead,
  markNotificationRead,
  registerDevice,
  transitionIssue,
  unregisterDevice,
  uploadIssuePhoto
} from "../src/lib/api";
import { getExpoPushToken, notificationPlatform } from "../src/lib/notifications";
import { useAuthStore } from "../src/store/auth";
import { radii, spacing, statusColor, ThemeColors } from "../src/theme/tokens";
import { useTheme } from "../src/theme/store";
import type { Issue, NotificationItem, RoleCode } from "../src/types";

type Screen = "list" | "new" | "detail" | "map" | "notifications" | "profile";
type Filter = "all" | "overdue";
type MapIssueFeature = {
  id: string;
  geometry: { coordinates: [number, number] };
  properties: Record<string, string | boolean | null>;
};

const progressByStatus: Record<string, number> = {
  NEW: 0,
  QUALIFICATION: 10,
  ASSIGNED: 25,
  ACCEPTED: 40,
  IN_PROGRESS: 60,
  COMPLETED: 85,
  INSPECTION: 95,
  CLOSED: 100
};

export default function HomeScreen() {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const { colors, toggleTheme } = useTheme();
  const [screen, setScreen] = useState<Screen>("list");
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
  if (screen === "new") return t("newIssue");
  if (screen === "map") return t("map");
  if (screen === "notifications") return t("notifications");
  if (screen === "profile") return t("profile");
  return t("myIssues");
}

function BottomTabs({ screen, onChange }: { screen: Screen; onChange: (screen: Screen) => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const unread = useQuery({ queryKey: ["notifications", "unread-count"], queryFn: fetchUnreadCount, refetchInterval: 30000 });
  const tabs: Array<{ key: Screen; label: string; icon: keyof typeof Ionicons.glyphMap }> = [
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
  const { colors } = useTheme();
  const tone = statusColor(status, overdue, colors);
  return (
    <View style={[styles.statusPill, { backgroundColor: tone.soft }]}>
      <View style={[styles.statusDot, { backgroundColor: tone.bg }]} />
      <Text style={[styles.statusText, { color: tone.text }]}>{status}</Text>
    </View>
  );
}

function slaLabel(issue: Issue, overdueLabel: string) {
  if (issue.is_overdue) return overdueLabel;
  if (!issue.sla_due_at) return "";
  const minutes = Math.ceil((new Date(issue.sla_due_at).getTime() - Date.now()) / 60000);
  if (minutes < 0) return overdueLabel;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return hours > 0 ? `${hours}h ${rest}m` : `${rest}m`;
}

function IssueList({ onOpen }: { onOpen: (issue: Issue) => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [filter, setFilter] = useState<Filter>("all");
  const issues = useQuery({ queryKey: ["issues"], queryFn: fetchIssues });
  const visible = useMemo(() => (issues.data ?? []).filter((issue) => filter === "all" || issue.is_overdue), [issues.data, filter]);

  return (
    <ScrollView
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={issues.isFetching} onRefresh={() => issues.refetch()} tintColor={colors.primary} />}
    >
      <View style={styles.filterRow}>
        <Pill label={t("all")} active={filter === "all"} onPress={() => setFilter("all")} />
        <Pill label={t("overdueOnly")} active={filter === "overdue"} onPress={() => setFilter("overdue")} />
      </View>
      {visible.length ? visible.map((issue) => <IssueCard key={issue.id} issue={issue} onPress={() => onOpen(issue)} />) : <EmptyState />}
    </ScrollView>
  );
}

function IssueCard({ issue, onPress }: { issue: Issue; onPress: () => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const name = issue.category?.name_ru ?? issue.priority;
  return (
    <Pressable style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]} onPress={onPress}>
      <View style={styles.cardHeader}>
        <Text style={[styles.cardNumber, { color: colors.text }]}>{issue.public_number}</Text>
        <StatusPill status={issue.status} overdue={issue.is_overdue} />
      </View>
      <Text style={[styles.cardTitle, { color: colors.text }]}>{issue.title}</Text>
      <Text style={[styles.metaText, { color: colors.mutedText }]}>{name}</Text>
      <View style={styles.cardFooter}>
        <Text style={[styles.metaText, { color: colors.mutedText }]}>{issue.address ?? issue.district?.name_ru ?? ""}</Text>
        <View style={[styles.slaPill, { backgroundColor: issue.is_overdue ? colors.danger : colors.primarySoft }]}>
          <Text style={[styles.slaText, { color: issue.is_overdue ? "#FFFFFF" : colors.primary }]}>
            {slaLabel(issue, t("overdue")) || "-"}
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
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [coords, setCoords] = useState<{ latitude: number; longitude: number } | null>(null);
  const category = catalogs.data?.find((item) => item.id === categoryId) ?? catalogs.data?.[0];
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
        title,
        description,
        address,
        primary_category_id: category?.id,
        latitude: location?.latitude,
        longitude: location?.longitude,
        priority: category?.default_priority ?? "MEDIUM"
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
        <TextInput style={[styles.input, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]} placeholder={t("title")} placeholderTextColor={colors.mutedText} value={title} onChangeText={setTitle} />
        <TextInput style={[styles.input, styles.multiline, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]} placeholder={t("description")} placeholderTextColor={colors.mutedText} value={description} onChangeText={setDescription} multiline />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryRow}>
          {(catalogs.data ?? []).map((item) => <Pill key={item.id} label={item.name_ru} active={(category?.id ?? "") === item.id} onPress={() => setCategoryId(item.id)} />)}
        </ScrollView>
        <TextInput style={[styles.input, { backgroundColor: colors.surface2, borderColor: colors.border, color: colors.text }]} placeholder={t("address")} placeholderTextColor={colors.mutedText} value={address} onChangeText={setAddress} />
        <View style={styles.twoColumns}>
          <SecondaryButton label={photoUri ? t("photo") : t("addPhoto")} icon="camera-outline" onPress={pickPhoto} />
          <SecondaryButton label={coords ? t("gps") : t("myLocation")} icon="location-outline" onPress={captureLocation} />
        </View>
        {photoUri ? <Image source={{ uri: photoUri }} style={styles.photo} /> : null}
        <PrimaryButton label={t("submit")} icon="send-outline" disabled={mutation.isPending} onPress={() => mutation.mutate()} />
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
  const mutation = useMutation({
    mutationFn: (status: string) => transitionIssue(issueId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["issue", issueId] });
      queryClient.invalidateQueries({ queryKey: ["issues"] });
    }
  });
  const data = issue.data;
  const action = data && user ? primaryAction(user.role.code, data.status) : null;
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
              <Text style={[styles.cardNumber, { color: colors.text }]}>{data.public_number}</Text>
              <StatusPill status={data.status} overdue={data.is_overdue} />
            </View>
            <Text style={[styles.detailTitle, { color: colors.text }]}>{data.title}</Text>
            <Text style={[styles.metaText, { color: colors.mutedText }]}>{data.priority} · {data.category?.name_ru ?? ""}</Text>
            {data.attachments?.[0] ? <Image source={{ uri: data.attachments[0].thumbnail_url ?? data.attachments[0].file_url }} style={styles.photo} /> : null}
            <Text style={[styles.body, { color: colors.text }]}>{data.description}</Text>
          </View>
          <SmartCard issue={data} />
          <Deadlines issue={data} />
          <Timeline issue={data} />
          <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            {action ? <PrimaryButton label={t(action.label)} icon="checkmark-circle-outline" onPress={() => mutation.mutate(action.status)} /> : <Text style={[styles.metaText, { color: colors.mutedText }]}>{t("emptyState")}</Text>}
          </View>
        </>
      ) : null}
    </ScrollView>
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
        <Text style={[styles.sectionTitle, { color: colors.text }]}>{t("smartCard")}</Text>
        <View style={[styles.slaPill, { backgroundColor: riskColor }]}>
          <Text style={[styles.slaText, { color: "#FFFFFF" }]}>{riskLabel}</Text>
        </View>
      </View>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { backgroundColor: colors.primary, width: `${progress}%` }]} />
      </View>
      <Text style={[styles.metaText, { color: colors.mutedText }]}>{t("progress")}: {progress}%</Text>
      <Text style={[styles.metaText, { color: colors.mutedText }]}>{t("aiSummary")}</Text>
    </View>
  );
}

function Deadlines({ issue }: { issue: Issue }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.sectionTitle, { color: colors.text }]}>{t("deadlines")}</Text>
      <Deadline label={t("reactionDue")} value={issue.reaction_due_at} />
      <Deadline label={t("executionDue")} value={issue.sla_due_at} highlight={issue.is_overdue} />
      <Deadline label={t("inspectionDue")} value={issue.inspection_due_at} />
    </View>
  );
}

function Deadline({ label, value, highlight }: { label: string; value?: string | null; highlight?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={styles.deadlineRow}>
      <Text style={[styles.metaText, { color: colors.mutedText }]}>{label}</Text>
      <Text style={[styles.deadlineValue, { color: highlight ? colors.danger : colors.text }]}>{value ? new Date(value).toLocaleString() : "-"}</Text>
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
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.detailTitle, { color: colors.text }]}>{user?.full_name}</Text>
      <Text style={[styles.metaText, { color: colors.mutedText }]}>{user?.role.code}</Text>
      <SecondaryButton label={t("theme")} icon="contrast-outline" onPress={toggleTheme} />
      <SecondaryButton label={t("language")} icon="language-outline" onPress={() => i18n.changeLanguage(i18n.language === "ru" ? "kk" : "ru")} />
      <PrimaryButton label={t("signOut")} icon="log-out-outline" onPress={onLogout} />
    </View>
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

function primaryAction(role: RoleCode, status: string) {
  if (role === "EXECUTOR" && status === "ASSIGNED") return { status: "ACCEPTED", label: "accept" };
  if (role === "EXECUTOR" && status === "ACCEPTED") return { status: "IN_PROGRESS", label: "onSite" };
  if (role === "EXECUTOR" && status === "IN_PROGRESS") return { status: "COMPLETED", label: "complete" };
  if (role === "ADMIN" && status === "ASSIGNED") return { status: "ACCEPTED", label: "accept" };
  if (role === "ADMIN" && status === "ACCEPTED") return { status: "IN_PROGRESS", label: "onSite" };
  if (role === "ADMIN" && status === "IN_PROGRESS") return { status: "COMPLETED", label: "complete" };
  return null;
}

function riskLevel(issue: Issue) {
  if (issue.is_overdue) return "high";
  if (!issue.sla_due_at) return "low";
  const created = new Date(issue.created_at).getTime();
  const due = new Date(issue.sla_due_at).getTime();
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
  pill: { minHeight: 38, borderRadius: radii.chip, borderWidth: 1, paddingHorizontal: spacing.lg, alignItems: "center", justifyContent: "center" },
  pillText: { fontFamily: "Inter_600SemiBold", fontSize: 13 },
  card: { borderWidth: 1, borderRadius: radii.card, padding: spacing.lg, marginBottom: spacing.md },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md, alignItems: "center", marginBottom: spacing.sm },
  cardNumber: { fontFamily: "Inter_600SemiBold", fontSize: 15 },
  cardTitle: { fontFamily: "Inter_500Medium", fontSize: 16, marginBottom: spacing.xs },
  detailTitle: { fontFamily: "Inter_600SemiBold", fontSize: 22, marginBottom: spacing.xs },
  sectionTitle: { fontFamily: "Inter_600SemiBold", fontSize: 17, marginBottom: spacing.md },
  metaText: { fontFamily: "Inter_400Regular", fontSize: 14 },
  body: { fontFamily: "Inter_400Regular", fontSize: 15, lineHeight: 22, marginTop: spacing.md },
  cardFooter: { marginTop: spacing.md, flexDirection: "row", justifyContent: "space-between", gap: spacing.sm, alignItems: "center" },
  statusPill: { minHeight: 28, borderRadius: radii.chip, paddingHorizontal: spacing.sm, flexDirection: "row", alignItems: "center", gap: 6 },
  statusDot: { width: 7, height: 7, borderRadius: radii.chip },
  statusText: { fontFamily: "Inter_600SemiBold", fontSize: 11 },
  unreadDot: { width: 9, height: 9, borderRadius: 5 },
  slaPill: { borderRadius: radii.chip, paddingHorizontal: spacing.sm, paddingVertical: 5 },
  slaText: { fontFamily: "Inter_600SemiBold", fontSize: 12 },
  input: { minHeight: 54, borderWidth: 1, borderRadius: radii.control, paddingHorizontal: spacing.lg, marginBottom: spacing.md, fontFamily: "Inter_400Regular", fontSize: 16 },
  multiline: { minHeight: 118, paddingTop: spacing.md },
  categoryRow: { marginBottom: spacing.md },
  twoColumns: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  primaryButton: { minHeight: 56, borderRadius: radii.control, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: spacing.sm },
  primaryText: { color: "#FFFFFF", fontFamily: "Inter_600SemiBold", fontSize: 16 },
  secondaryButton: { flex: 1, minHeight: 52, borderRadius: radii.control, borderWidth: 1, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: spacing.sm, paddingHorizontal: spacing.md, marginBottom: spacing.sm },
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
  empty: { textAlign: "center", marginTop: spacing.xxl, fontFamily: "Inter_400Regular" }
});
