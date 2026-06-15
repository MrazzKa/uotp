import { useQuery } from "@tanstack/react-query";
import maplibregl, { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { AlertTriangle, Layers, MapPinned, Thermometer, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/Button";
import { statusHex } from "../../lib/design";
import {
  fetchCatalogs,
  fetchMapClusters,
  fetchMapDistricts,
  fetchMapHeatmap,
  fetchMapIssues
} from "../../lib/api";
import type { IssueStatus } from "../../types";
import { useThemeStore } from "../../theme/store";

const CENTER: [number, number] = [69.15, 54.8666];
const DEFAULT_BBOX = "69.05,54.80,69.25,54.94";
const TILE_STYLE = import.meta.env.VITE_MAP_STYLE_URL ?? "https://tiles.openfreemap.org/styles/liberty";

const ALL_STATUSES: IssueStatus[] = [
  "NEW", "QUALIFICATION", "ASSIGNED", "ACCEPTED", "IN_PROGRESS",
  "COMPLETED", "INSPECTION", "CLOSED", "REJECTED", "RETURNED", "DUPLICATE"
];

type Filters = {
  status: string;
  category: string;
  district: string;
  priority: string;
  assigned_to: string;
  is_overdue: string;
};

export function MapPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { theme } = useThemeStore();
  const mapRef = useRef<MapLibreMap | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const [bbox, setBbox] = useState(DEFAULT_BBOX);
  const [zoom, setZoom] = useState(12);
  const [districtsVisible, setDistrictsVisible] = useState(true);
  const [heatmapVisible, setHeatmapVisible] = useState(false);
  const [filters, setFilters] = useState<Filters>({ status: "", category: "", district: "", priority: "", assigned_to: "", is_overdue: "" });
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const mapParams = useMemo(
    () => ({
      bbox,
      zoom: String(Math.round(zoom)),
      status: filters.status || undefined,
      category: filters.category || undefined,
      district: filters.district || undefined,
      priority: filters.priority || undefined,
      assigned_to: filters.assigned_to || undefined,
      is_overdue: filters.is_overdue || undefined
    }),
    [bbox, zoom, filters]
  );
  const issues = useQuery({ queryKey: ["map-issues", mapParams], queryFn: () => fetchMapIssues(mapParams), enabled: zoom >= 12 });
  const clusters = useQuery({ queryKey: ["map-clusters", mapParams], queryFn: () => fetchMapClusters(mapParams), enabled: zoom < 12 });
  const heatmap = useQuery({ queryKey: ["map-heatmap", mapParams], queryFn: () => fetchMapHeatmap(mapParams), enabled: heatmapVisible });
  const districts = useQuery({ queryKey: ["map-districts"], queryFn: fetchMapDistricts });

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: TILE_STYLE,
      center: CENTER,
      zoom: 12
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
    map.on("moveend", () => {
      const bounds = map.getBounds();
      setBbox(`${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`);
      setZoom(map.getZoom());
    });
    mapRef.current = map;
    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const applyData = () => {
      syncSource(map, "districts", districts.data ?? emptyFeatureCollection());
      syncSource(map, "issues", issues.data ?? emptyFeatureCollection());
      syncSource(map, "clusters", clustersToFeatures(clusters.data ?? []));
      syncSource(map, "heatmap", heatmapToFeatures(heatmap.data ?? []));
      ensureLayers(map, theme);
      setLayerVisibility(map, "district-fill", districtsVisible);
      setLayerVisibility(map, "district-line", districtsVisible);
      setLayerVisibility(map, "heatmap-layer", heatmapVisible);
      setLayerVisibility(map, "issue-points", zoom >= 12);
      setLayerVisibility(map, "cluster-points", zoom < 12);
      setLayerVisibility(map, "cluster-counts", zoom < 12);
    };
    if (map.isStyleLoaded()) applyData();
    else map.once("load", applyData);
  }, [districts.data, issues.data, clusters.data, heatmap.data, districtsVisible, heatmapVisible, zoom, theme]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const handler = (event: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      const feature = event.features?.[0];
      if (!feature) return;
      const props = feature.properties as Record<string, string | boolean>;
      popupRef.current?.remove();
      const overdue = props.is_overdue === "true" || props.is_overdue === true;
      const html = `<div class="uotp-popup"><strong>${props.public_number}</strong><br/>${props.status}${overdue ? ` - ${t("overdue")}` : ""}<br/>${props.category ?? ""}<br/>${props.address ?? ""}<br/><button data-issue="${props.id}">${t("open")}</button></div>`;
      const popup = new maplibregl.Popup({ closeButton: true }).setLngLat(event.lngLat).setHTML(html).addTo(map);
      popup.getElement().querySelector("button")?.addEventListener("click", () => {
        navigate(`/issues/${props.id}`);
      });
      popupRef.current = popup;
    };
    map.on("click", "issue-points", handler);
    return () => {
      map.off("click", "issue-points", handler);
    };
  }, [t, navigate]);

  return (
    <main className="h-[calc(100vh-112px)] overflow-hidden rounded-panel border border-border bg-surface text-foreground shadow-card">
      <div className="grid h-full grid-cols-1 md:grid-cols-[320px_1fr]">
        <aside className="z-10 border-r border-border bg-surface p-4">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-xl font-semibold">{t("map")}</h1>
            <Button variant="muted" className="w-10 px-0" onClick={() => navigate("/issues")}><X size={18} /></Button>
          </div>
          <div className="grid gap-3">
            <Select value={filters.status} onChange={(status) => setFilters({ ...filters, status })} label={t("status")} items={["NEW", "QUALIFICATION", "ASSIGNED", "ACCEPTED", "IN_PROGRESS", "COMPLETED", "INSPECTION", "CLOSED"].map((value) => ({ value, label: value }))} />
            <Select value={filters.category} onChange={(category) => setFilters({ ...filters, category })} label={t("category")} items={(catalogs.data?.categories ?? []).map((item) => ({ value: item.id, label: i18n.language === "kk" ? item.name_kk : item.name_ru }))} />
            <Select value={filters.district} onChange={(district) => setFilters({ ...filters, district })} label={t("district")} items={(catalogs.data?.districts ?? []).map((item) => ({ value: item.id, label: i18n.language === "kk" ? item.name_kk : item.name_ru }))} />
            <Select value={filters.priority} onChange={(priority) => setFilters({ ...filters, priority })} label={t("priority")} items={["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => ({ value, label: value }))} />
            <Button variant={filters.is_overdue ? "accent" : "muted"} onClick={() => setFilters({ ...filters, is_overdue: filters.is_overdue ? "" : "true" })}><AlertTriangle size={18} />{t("onlyOverdue")}</Button>
            <Button variant={districtsVisible ? "default" : "muted"} onClick={() => setDistrictsVisible(!districtsVisible)}><Layers size={18} />{t("districtsLayer")}</Button>
            <Button variant={heatmapVisible ? "default" : "muted"} onClick={() => setHeatmapVisible(!heatmapVisible)}><Thermometer size={18} />{t("heatmap")}</Button>
            <Button variant="accent" onClick={() => mapRef.current?.flyTo({ center: CENTER, zoom: 12 })}><MapPinned size={18} />{t("petropavlovsk")}</Button>
          </div>
        </aside>
        <div ref={containerRef} className="min-h-[70vh] md:min-h-0" />
      </div>
    </main>
  );
}

function Select({ value, onChange, label, items }: { value: string; onChange: (value: string) => void; label: string; items: Array<{ value: string; label: string }> }) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-mutedText">{label}</span>
      <select className="h-10 rounded-control border border-border bg-surface px-3 shadow-base" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">{label}</option>
        {items.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
      </select>
    </label>
  );
}

function emptyFeatureCollection(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

function clustersToFeatures(items: Array<{ longitude: number; latitude: number; count: number; dominant_status: string }>): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: items.map((item) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [item.longitude, item.latitude] },
      properties: { count: item.count, dominant_status: item.dominant_status, color: statusHex(item.dominant_status) }
    }))
  };
}

function heatmapToFeatures(items: Array<{ longitude: number; latitude: number; weight: number }>): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: items.map((item) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [item.longitude, item.latitude] },
      properties: { weight: item.weight }
    }))
  };
}

function syncSource(map: MapLibreMap, id: string, data: GeoJSON.FeatureCollection) {
  const source = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
  if (source) source.setData(data);
  else map.addSource(id, { type: "geojson", data });
}

function ensureLayers(map: MapLibreMap, theme: string) {
  if (!map.getLayer("district-fill")) {
    map.addLayer({ id: "district-fill", type: "fill", source: "districts", paint: { "fill-color": theme === "dark" ? "#22d3ee" : "#0891b2", "fill-opacity": 0.12 } });
    map.addLayer({ id: "district-line", type: "line", source: "districts", paint: { "line-color": theme === "dark" ? "#67e8f9" : "#0e7490", "line-width": 2 } });
  }
  if (!map.getLayer("heatmap-layer")) {
    map.addLayer({ id: "heatmap-layer", type: "heatmap", source: "heatmap", paint: { "heatmap-weight": ["get", "weight"], "heatmap-radius": 28, "heatmap-opacity": 0.7 } });
  }
  if (!map.getLayer("cluster-points")) {
    map.addLayer({ id: "cluster-points", type: "circle", source: "clusters", paint: { "circle-radius": ["+", 12, ["*", 1.5, ["ln", ["get", "count"]]]], "circle-color": ["get", "color"], "circle-opacity": 0.85 } });
    map.addLayer({ id: "cluster-counts", type: "symbol", source: "clusters", layout: { "text-field": ["to-string", ["get", "count"]], "text-size": 12 }, paint: { "text-color": "#fff" } });
  }
  if (!map.getLayer("issue-points")) {
    const statusColorPairs = ALL_STATUSES.flatMap((status) => [status, statusHex(status)]);
    const colorExpression = ["match", ["get", "status"], ...statusColorPairs, "#94A3B8"] as unknown as maplibregl.ExpressionSpecification;
    map.addLayer({
      id: "issue-points",
      type: "circle",
      source: "issues",
      paint: {
        "circle-radius": ["case", ["==", ["get", "is_overdue"], true], 10, 7],
        "circle-color": colorExpression,
        "circle-stroke-color": ["case", ["==", ["get", "is_overdue"], true], "#dc2626", "#fff"],
        "circle-stroke-width": ["case", ["==", ["get", "is_overdue"], true], 4, 2]
      }
    });
  }
}

function setLayerVisibility(map: MapLibreMap, id: string, visible: boolean) {
  if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
}
