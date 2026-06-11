import React, { useState, useEffect, useRef } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Text,
  View,
  Pressable,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Linking,
} from "react-native";
import { API_URL, FETCH_TIMEOUT_MS } from "../../constants/Config";
import { getApiErrorMessage, readApiResponse } from "../../utils/apiResponse";
import { ArrowUpRight } from "lucide-react-native";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SaleItem {
  id: string;
  name: string;
  category: string;
  costPrice: number;
  salePrice: number;
  quantity?: number;
  unit?: string;
  status: "Paid" | "Unpaid";
  date?: string;
}

interface ReportItem {
  id: string;
  title: string;
  subtitle: string;
  generatedAt: string;
  days: 1 | 7 | 28 | 30;
}

// ─── Mock Reports ─────────────────────────────────────────────────────────────

const REPORTS: Omit<ReportItem, "generatedAt">[] = [
  {
    id: "1",
    title: "Daily Report",
    subtitle: "Last 1 day",
    days: 1,
  },
  {
    id: "2",
    title: "Weekly Report",
    subtitle: "Last 7 days",
    days: 7,
  },
  {
    id: "3",
    title: "Monthly Report",
    subtitle: "Last 28 days",
    days: 28,
  },
  {
    id: "4",
    title: "30-Day Report",
    subtitle: "Last 30 days",
    days: 30,
  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  change,
  changeLabel,
}: {
  label: string;
  value: number;
  change: number;
  changeLabel: string;
}) {
  const isPositive = change >= 0;
  return (
    <View className="flex-1 rounded-2xl border border-slate-200 bg-white p-4">
      <View className="mb-1.5 flex-row items-center gap-1.5">
        <ArrowUpRight size={14} color="#007566" style={{ opacity: isPositive ? 1 : 0.5 }} />
        <Text className="text-[13px] font-medium text-slate-500">{label}</Text>
      </View>
      <Text className="mb-1 text-[22px] font-extrabold text-slate-900">
        Rs {value.toLocaleString()}
      </Text>
      <Text className="text-xs text-slate-500">
        <Text className={`font-bold ${isPositive ? 'text-[#007566]' : 'text-red-500'}`}>
          {isPositive ? '+' : ''}{change}%
        </Text>{" "}
        {changeLabel}
      </Text>
    </View>
  );
}

function SaleItemRow({ item }: { item: SaleItem }) {
  const quantityLabel = item.quantity ? `${item.quantity} ${item.unit ?? ""}`.trim() : null;

  return (
    <View className="mb-2.5 flex-row items-center justify-between rounded-xl border border-slate-300 bg-transparent p-3.5">
      <View className="flex-1">
        <Text className="mb-1 text-[14px] font-semibold text-slate-900">
          {item.name}
        </Text>
        <Text className="text-[12px] font-normal text-slate-400">
          {item.category} {quantityLabel ? `• ${quantityLabel} • ` : "• "}Rs {item.costPrice}/unit
        </Text>
      </View>
      <View className="items-end">
        <Text className="mb-0.5 text-[14px] font-bold text-slate-900">
          Rs {item.salePrice.toLocaleString()}
        </Text>
        <Text className="text-[12px] font-semibold text-[#007566]">
          {item.status}
        </Text>
      </View>
    </View>
  );
}

function ReportRow({
  report,
  onDownload,
  loading,
}: {
  report: ReportItem;
  onDownload: (report: ReportItem) => void;
  loading: boolean;
}) {
  return (
    <View className="mb-2.5 flex-row items-center gap-3 rounded-xl border border-slate-200 bg-white p-3.5">
      <View className="h-10 w-10 items-center justify-center rounded-lg bg-[#007566]">
        <Text className="text-lg">📄</Text>
      </View>
      <View className="flex-1">
        <Text className="text-[14px] font-bold text-slate-900">
          {report.title}
        </Text>
        <Text className="mt-0.5 text-[13px] text-slate-600">
          {report.subtitle}
        </Text>
        <Text className="mt-0.5 text-[11px] text-slate-400">
          {report.generatedAt}
        </Text>
      </View>
      <TouchableOpacity
        className="rounded-full border-[1.5px] border-green-600 px-3.5 py-2"
        disabled={loading}
        style={{ opacity: loading ? 0.5 : 1 }}
        onPress={() => onDownload(report)}
      >
        <Text className="text-[13px] font-semibold text-[#007566]">
          {loading ? "Opening..." : "Download"}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

// ─── Main Screen ──────────────────────────────────────────────────────────────

type MainTab = "Daily Sales" | "Report";
type TimeFilter = 7 | 14 | 28;

export default function SalesScreen() {
  const [activeTab, setActiveTab] = useState<MainTab>("Daily Sales");
  const [timeFilter, setTimeFilter] = useState<TimeFilter>(7);
  const [downloadingReportId, setDownloadingReportId] = useState<string | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [stats, setStats] = useState({ profit: 0, revenue: 0, profitChange: 0, revenueChange: 0 });
  const [items, setItems] = useState<SaleItem[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const fetchInFlight = useRef(false);

  const fetchSalesData = async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (fetchInFlight.current) return;
    fetchInFlight.current = true;
    setLoading(true);
    setFetchError(false);

    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      const res = await fetch(
        `${API_URL}/api/reports/sales-data?days=${timeFilter}`,
        { signal: controller.signal },
      );
      clearTimeout(timer);
      const data = await readApiResponse(res);
      if (!res.ok) throw new Error(getApiErrorMessage(data, `Server error ${res.status}`));
      setStats(data.stats);
      setItems(data.items);
    } catch (err: any) {
      clearTimeout(timer);
      if (err?.name !== "AbortError") {
        console.error("Error fetching sales data:", err);
        setFetchError(true);
      }
    } finally {
      fetchInFlight.current = false;
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "Daily Sales") fetchSalesData();
    return () => { abortRef.current?.abort(); fetchInFlight.current = false; };
  }, [timeFilter, activeTab]);

  const handleDownloadReport = async (report: ReportItem) => {
    const url = `${API_URL}/api/reports/sales-pdf?days=${report.days}`;
    setDownloadingReportId(report.id);

    try {
      const supported = await Linking.canOpenURL(url);
      if (!supported) {
        throw new Error(`Cannot open URL: ${url}`);
      }
      await Linking.openURL(url);
    } catch (error) {
      console.error("Failed to open sales report:", error);
      Alert.alert(
        "Download Failed",
        "Could not open the sales report. Check backend server and network.",
      );
    } finally {
      setDownloadingReportId(null);
    }
  };

  const timeFilterLabel: Record<TimeFilter, string> = {
    7: "Last Week",
    14: "Last 14 Days",
    28: "Last Month",
  };

  const reports: ReportItem[] = REPORTS.map((report) => ({
    ...report,
    generatedAt: report.days === 1 ? "Generate today's report" : `Generate last ${report.days} days`,
  }));

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-slate-100"
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 56, paddingBottom: 32 }}
      >
        {/* Title */}
        <Text className="mb-4 text-[28px] font-extrabold tracking-wide text-slate-900">
          SALES
        </Text>

        {/* Main Segmented Control */}
        <View className="mb-4 flex-row rounded-xl bg-slate-200 p-1">
          {(["Daily Sales", "Report"] as MainTab[]).map((tab) => (
            <Pressable
              key={tab}
              onPress={() => setActiveTab(tab)}
              className={`flex-1 items-center rounded-lg py-2.5 ${activeTab === tab ? "border border-slate-300 bg-[#007566]" : ""
                }`}
            >
              <Text
                className={`text-[15px] ${activeTab === tab
                    ? "font-bold text-white"
                    : "font-medium text-slate-500"
                  }`}
              >
                {tab}
              </Text>
            </Pressable>
          ))}
        </View>

        {activeTab === "Daily Sales" && (
          <View className="mb-5 flex-row gap-2">
            {([7, 14, 28] as TimeFilter[]).map((days) => (
              <Pressable
                key={days}
                onPress={() => setTimeFilter(days)}
                className={`rounded-full px-4 py-2 ${timeFilter === days ? "bg-slate-800" : "bg-slate-200"
                  }`}
              >
                <Text
                  className={`text-[13px] ${timeFilter === days
                      ? "font-semibold text-white"
                      : "font-medium text-slate-500"
                    }`}
                >
                  {timeFilterLabel[days]}
                </Text>
              </Pressable>
            ))}
          </View>
        )}

        {/* ── DAILY SALES TAB ── */}
        {activeTab === "Daily Sales" && (
          <>
            {/* Stat Cards */}
            <View className="mb-6 flex-row gap-3">
              <StatCard
                label="Profit"
                value={stats.profit}
                change={stats.profitChange}
                changeLabel="vs last period"
              />
              <StatCard
                label="Revenue"
                value={stats.revenue}
                change={stats.revenueChange}
                changeLabel="vs last period"
              />
            </View>

            {/* Item List Header */}
            <View className="mb-3 flex-row items-center justify-between">
              <Text className="text-[16px] font-bold text-slate-900">Item lists</Text>
              <TouchableOpacity
                onPress={() => Alert.alert("View All", "Showing all items")}
              >
                <Text className="text-[13px] font-medium text-slate-500">View All</Text>
              </TouchableOpacity>
            </View>

            {/* Items */}
            {loading ? (
              <ActivityIndicator size="large" color="#007566" className="my-8" />
            ) : fetchError ? (
              <View className="my-8 items-center gap-3">
                <Text className="text-center text-slate-500">Could not load sales data.</Text>
                <Pressable
                  onPress={fetchSalesData}
                  className="rounded-full bg-[#007566] px-5 py-2"
                >
                  <Text className="text-sm font-semibold text-white">Retry</Text>
                </Pressable>
              </View>
            ) : items.length > 0 ? (
              items.map((item) => (
                <SaleItemRow key={item.id} item={item} />
              ))
            ) : (
              <Text className="my-4 text-center text-slate-500">No items found.</Text>
            )}
          </>
        )}

        {/* ── REPORT TAB ── */}
        {activeTab === "Report" && (
          <>
            {/* Stock Alert Header */}
            <View className="mb-3 flex-row items-center justify-between">
              <Text className="text-[16px] font-bold text-slate-900">Reports</Text>
              <TouchableOpacity
                onPress={() => Alert.alert("View All", "Showing all reports")}
              >
                <Text className="text-[13px] font-medium text-slate-500">View All</Text>
              </TouchableOpacity>
            </View>

            {/* Reports */}
            {reports.map((report) => (
              <ReportRow
                key={report.id}
                report={report}
                onDownload={handleDownloadReport}
                loading={downloadingReportId === report.id}
              />
            ))}
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
