import React, { useState, useEffect } from "react";
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
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import { API_URL } from "../../constants/Config";
import { ArrowUpRight } from "lucide-react-native";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SaleItem {
  id: string;
  name: string;
  category: string;
  costPrice: number;
  salePrice: number;
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

const REPORTS: ReportItem[] = [
  {
    id: "1",
    title: "Daily Report",
    subtitle: "Last 1 day",
    generatedAt: "Generated today",
    days: 1,
  },
  {
    id: "2",
    title: "Weekly Report",
    subtitle: "Last 7 days",
    generatedAt: "Generated fresh",
    days: 7,
  },
  {
    id: "3",
    title: "Monthly Report",
    subtitle: "Last 28 days",
    generatedAt: "Generated fresh",
    days: 28,
  },
  {
    id: "4",
    title: "Monthly Report",
    subtitle: "Last 30 days",
    generatedAt: "Generated fresh",
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
    <View className="flex-1 rounded-2xl bg-white p-4 shadow-sm elevation-2">
      <View className="mb-1.5 flex-row items-center gap-1.5">
        <ArrowUpRight size={14} color="#7C3AED" className={isPositive ? "" : "opacity-50"} />
        <Text className="text-[13px] font-medium text-slate-500">{label}</Text>
      </View>
      <Text className="mb-1 text-[22px] font-extrabold text-slate-900">
        Rs {value.toLocaleString()}
      </Text>
      <Text className="text-xs text-slate-500">
        <Text className={`font-bold ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
          {isPositive ? '+' : ''}{change}%
        </Text>{" "}
        {changeLabel}
      </Text>
    </View>
  );
}

function SaleItemRow({ item }: { item: SaleItem }) {
  return (
    <View className="mb-2.5 flex-row items-center justify-between rounded-xl bg-white p-3.5 shadow-sm elevation-1">
      <View className="flex-1">
        <Text className="mb-1 text-[14px] font-semibold text-slate-900">
          {item.name}
        </Text>
        <Text className="text-[12px] font-normal text-slate-400">
          {item.category} Rs {item.costPrice}
        </Text>
      </View>
      <View className="items-end">
        <Text className="mb-0.5 text-[14px] font-bold text-slate-900">
          Rs {item.salePrice.toLocaleString()}
        </Text>
        <Text className="text-[12px] font-semibold text-green-500">
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
    <View className="mb-2.5 flex-row items-center gap-3 rounded-xl bg-white p-3.5 shadow-sm elevation-1">
      <View className="h-10 w-10 items-center justify-center rounded-lg bg-purple-100">
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
        className="rounded-full border-[1.5px] border-purple-600 px-3.5 py-2 opacity-100 disabled:opacity-50"
        disabled={loading}
        onPress={() => onDownload(report)}
      >
        <Text className="text-[13px] font-semibold text-purple-600">
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
  const [stats, setStats] = useState({ profit: 0, revenue: 0, profitChange: 0, revenueChange: 0 });
  const [items, setItems] = useState<SaleItem[]>([]);

  useEffect(() => {
    const fetchSalesData = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/reports/sales-data?days=${timeFilter}`);
        if (!res.ok) throw new Error("Failed to fetch");
        const data = await res.json();
        setStats(data.stats);
        setItems(data.items);
      } catch (err) {
        console.error("Error fetching sales data:", err);
      } finally {
        setLoading(false);
      }
    };

    if (activeTab === "Daily Sales") {
      fetchSalesData();
    }
  }, [timeFilter, activeTab]);

  const handleDownloadReport = async (report: ReportItem) => {
    const url = `${API_URL}/api/reports/sales-pdf?days=${report.days}`;
    setDownloadingReportId(report.id);

    try {
      await WebBrowser.openBrowserAsync(url);
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
              className={`flex-1 items-center rounded-lg py-2.5 ${activeTab === tab ? "bg-white shadow-sm elevation-2" : ""
                }`}
            >
              <Text
                className={`text-[15px] ${activeTab === tab
                    ? "font-bold text-purple-600"
                    : "font-medium text-slate-500"
                  }`}
              >
                {tab}
              </Text>
            </Pressable>
          ))}
        </View>

        {/* Time Filter Pills */}
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
              <ActivityIndicator size="large" color="#7C3AED" className="my-8" />
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
            {REPORTS.map((report) => (
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
