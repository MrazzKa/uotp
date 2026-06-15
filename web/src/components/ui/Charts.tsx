import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { chartPalette } from "../../lib/design";

type ChartDatum = Record<string, string | number>;

function axisColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--text-muted").trim();
}

function gridColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--border").trim();
}

export function SoftLineChart({ data, xKey, yKey }: { data: ChartDatum[]; xKey: string; yKey: string }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="lineFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={chartPalette[0]} stopOpacity={0.22} />
            <stop offset="100%" stopColor={chartPalette[0]} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={gridColor()} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xKey} axisLine={false} tickLine={false} tick={{ fill: axisColor(), fontSize: 12 }} />
        <YAxis axisLine={false} tickLine={false} tick={{ fill: axisColor(), fontSize: 12 }} width={32} />
        <Tooltip contentStyle={{ borderRadius: 12, borderColor: "var(--border)", background: "var(--surface)" }} />
        <Area type="monotone" dataKey={yKey} stroke={chartPalette[0]} strokeWidth={2} fill="url(#lineFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function SoftBarChart({ data, xKey, yKey }: { data: ChartDatum[]; xKey: string; yKey: string }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
        <CartesianGrid stroke={gridColor()} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xKey} axisLine={false} tickLine={false} tick={{ fill: axisColor(), fontSize: 12 }} />
        <YAxis axisLine={false} tickLine={false} tick={{ fill: axisColor(), fontSize: 12 }} width={32} />
        <Tooltip contentStyle={{ borderRadius: 12, borderColor: "var(--border)", background: "var(--surface)" }} />
        <Bar dataKey={yKey} fill={chartPalette[2]} radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function SoftDonutChart({ data, nameKey, valueKey }: { data: ChartDatum[]; nameKey: string; valueKey: string }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Tooltip contentStyle={{ borderRadius: 12, borderColor: "var(--border)", background: "var(--surface)" }} />
        <Pie data={data} dataKey={valueKey} nameKey={nameKey} innerRadius={58} outerRadius={86} paddingAngle={3}>
          {data.map((_, index) => (
            <Cell key={index} fill={chartPalette[index % chartPalette.length]} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
}
