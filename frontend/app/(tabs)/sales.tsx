import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Text,
  View,
  StyleSheet,
  Pressable,
  ScrollView,
  TouchableOpacity,
  Alert,
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import { API_URL } from "../../constants/Config";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SaleItem {
  id: string;
  name: string;
  category: string;
  costPrice: number;
  salePrice: number;
  status: "Paid" | "Unpaid";
}

interface ReportItem {
  id: string;
  title: string;
  subtitle: string;
  generatedAt: string;
  days: 1 | 7 | 28 | 30;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_STATS = {
  7: { profit: 567, revenue: 2450, profitChange: 12, revenueChange: 12 },
  14: { profit: 1230, revenue: 5800, profitChange: 8, revenueChange: 9 },
  28: { profit: 3100, revenue: 14200, profitChange: 5, revenueChange: 7 },
};

const MOCK_ITEMS: SaleItem[] = [
  {
    id: "1",
    name: "Organic Honey (500g)",
    category: "GROCERIES",
    costPrice: 850,
    salePrice: 1200,
    status: "Paid",
  },
  {
    id: "2",
    name: "Raw Almonds (1kg)",
    category: "GROCERIES",
    costPrice: 1200,
    salePrice: 2125,
    status: "Paid",
  },
  {
    id: "3",
    name: "Green Tea Box",
    category: "GROCERIES",
    costPrice: 95,
    salePrice: 145,
    status: "Paid",
  },
  {
    id: "4",
    name: "Organic Honey (500g)",
    category: "GROCERIES",
    costPrice: 60,
    salePrice: 95,
    status: "Paid",
  },
];

const MOCK_REPORTS: ReportItem[] = [
  {
    id: "1",
    title: "Daily Report",
    subtitle: "Last 1 day",
    generatedAt: "Generated yesterday",
    days: 1,
  },
  {
    id: "2",
    title: "Weekly Report",
    subtitle: "Last 7 days",
    generatedAt: "Generated yesterday",
    days: 7,
  },
  {
    id: "3",
    title: "Monthly Report",
    subtitle: "Last 28 days",
    generatedAt: "Generated yesterday",
    days: 28,
  },
  {
    id: "4",
    title: "Monthly Report",
    subtitle: "Last 30 days",
    generatedAt: "Generated a week ago",
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
  return (
    <View style={styles.statCard}>
      <View style={styles.statCardHeader}>
        {/* Trend icon placeholder */}
        <Text style={styles.statIcon}>↗</Text>
        <Text style={styles.statLabel}>{label}</Text>
      </View>
      <Text style={styles.statValue}>Rs {value.toLocaleString()}</Text>
      <Text style={styles.statChange}>
        <Text style={styles.statChangePercent}>{change}%</Text> {changeLabel}
      </Text>
    </View>
  );
}

function SaleItemRow({ item }: { item: SaleItem }) {
  return (
    <View style={styles.itemRow}>
      <View style={styles.itemLeft}>
        <Text style={styles.itemName}>{item.name}</Text>
        <Text style={styles.itemCategory}>
          {item.category} Rs {item.costPrice}
        </Text>
      </View>
      <View style={styles.itemRight}>
        <Text style={styles.itemPrice}>
          Rs {item.salePrice.toLocaleString()}
        </Text>
        <Text style={styles.itemStatus}>{item.status}</Text>
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
    <View style={styles.reportRow}>
      <View style={styles.reportIcon}>
        <Text style={styles.reportIconText}>📄</Text>
      </View>
      <View style={styles.reportInfo}>
        <Text style={styles.reportTitle}>{report.title}</Text>
        <Text style={styles.reportSubtitle}>{report.subtitle}</Text>
        <Text style={styles.reportGenerated}>{report.generatedAt}</Text>
      </View>
      <TouchableOpacity
        style={styles.downloadBtn}
        disabled={loading}
        onPress={() => onDownload(report)}
      >
        <Text style={styles.downloadBtnText}>
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

  const stats = MOCK_STATS[timeFilter];

  const timeFilterLabel: Record<TimeFilter, string> = {
    7: "Last Day",
    14: "Last Week",
    28: "Last Month",
  };

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Title */}
        <Text style={styles.title}>SALES</Text>

        {/* Main Segmented Control */}
        <View style={styles.segmentContainer}>
          {(["Daily Sales", "Report"] as MainTab[]).map((tab) => (
            <Pressable
              key={tab}
              onPress={() => setActiveTab(tab)}
              style={[
                styles.segmentButton,
                activeTab === tab && styles.activeSegment,
              ]}
            >
              <Text
                style={[
                  styles.segmentText,
                  activeTab === tab && styles.activeText,
                ]}
              >
                {tab}
              </Text>
            </Pressable>
          ))}
        </View>

        {/* Time Filter Pills */}
        <View style={styles.timeFilterRow}>
          {([7, 14, 28] as TimeFilter[]).map((days) => (
            <Pressable
              key={days}
              onPress={() => setTimeFilter(days)}
              style={[
                styles.timePill,
                timeFilter === days && styles.timePillActive,
              ]}
            >
              <Text
                style={[
                  styles.timePillText,
                  timeFilter === days && styles.timePillTextActive,
                ]}
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
            <View style={styles.statsRow}>
              <StatCard
                label="Profit"
                value={stats.profit}
                change={stats.profitChange}
                changeLabel="Today"
              />
              <StatCard
                label="Revenue"
                value={stats.revenue}
                change={stats.revenueChange}
                changeLabel="Today"
              />
            </View>

            {/* Item List Header */}
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Item lists</Text>
              <TouchableOpacity
                onPress={() => Alert.alert("View All", "Showing all items")}
              >
                <Text style={styles.viewAll}>View All</Text>
              </TouchableOpacity>
            </View>

            {/* Items */}
            {MOCK_ITEMS.map((item) => (
              <SaleItemRow key={item.id} item={item} />
            ))}
          </>
        )}

        {/* ── REPORT TAB ── */}
        {activeTab === "Report" && (
          <>
            {/* Stock Alert Header */}
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Stock Alert</Text>
              <TouchableOpacity
                onPress={() => Alert.alert("View All", "Showing all alerts")}
              >
                <Text style={styles.viewAll}>View All</Text>
              </TouchableOpacity>
            </View>

            {/* Reports */}
            {MOCK_REPORTS.map((report) => (
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

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#F0F4F8",
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 56,
    paddingBottom: 32,
  },

  // Title
  title: {
    fontSize: 28,
    fontWeight: "800",
    color: "#0F172A",
    marginBottom: 16,
    letterSpacing: 0.5,
  },

  // Segmented Control
  segmentContainer: {
    flexDirection: "row",
    backgroundColor: "#E2E8F0",
    borderRadius: 12,
    padding: 4,
    marginBottom: 16,
  },
  segmentButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: 10,
  },
  activeSegment: {
    backgroundColor: "#fff",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  segmentText: {
    fontSize: 15,
    color: "#64748B",
    fontWeight: "500",
  },
  activeText: {
    color: "#7C3AED",
    fontWeight: "700",
  },

  // Time Filter
  timeFilterRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 20,
  },
  timePill: {
    paddingVertical: 7,
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: "#E2E8F0",
  },
  timePillActive: {
    backgroundColor: "#1E293B",
  },
  timePillText: {
    fontSize: 13,
    color: "#64748B",
    fontWeight: "500",
  },
  timePillTextActive: {
    color: "#fff",
    fontWeight: "600",
  },

  // Stat Cards
  statsRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  statCardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 6,
  },
  statIcon: {
    fontSize: 14,
    color: "#7C3AED",
  },
  statLabel: {
    fontSize: 13,
    color: "#64748B",
    fontWeight: "500",
  },
  statValue: {
    fontSize: 22,
    fontWeight: "800",
    color: "#0F172A",
    marginBottom: 4,
  },
  statChange: {
    fontSize: 12,
    color: "#64748B",
  },
  statChangePercent: {
    color: "#22C55E",
    fontWeight: "700",
  },

  // Section Header
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0F172A",
  },
  viewAll: {
    fontSize: 13,
    color: "#64748B",
    fontWeight: "500",
  },

  // Sale Item Row
  itemRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  itemLeft: {
    flex: 1,
  },
  itemName: {
    fontSize: 14,
    fontWeight: "600",
    color: "#0F172A",
    marginBottom: 3,
  },
  itemCategory: {
    fontSize: 12,
    color: "#94A3B8",
    fontWeight: "400",
  },
  itemRight: {
    alignItems: "flex-end",
  },
  itemPrice: {
    fontSize: 14,
    fontWeight: "700",
    color: "#0F172A",
    marginBottom: 2,
  },
  itemStatus: {
    fontSize: 12,
    color: "#22C55E",
    fontWeight: "600",
  },

  // Report Row
  reportRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
    gap: 12,
  },
  reportIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: "#EDE9FE",
    alignItems: "center",
    justifyContent: "center",
  },
  reportIconText: {
    fontSize: 18,
  },
  reportInfo: {
    flex: 1,
  },
  reportTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#0F172A",
  },
  reportSubtitle: {
    fontSize: 13,
    color: "#475569",
    marginTop: 1,
  },
  reportGenerated: {
    fontSize: 11,
    color: "#94A3B8",
    marginTop: 2,
  },
  downloadBtn: {
    paddingVertical: 7,
    paddingHorizontal: 14,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: "#7C3AED",
  },
  downloadBtnText: {
    fontSize: 13,
    color: "#7C3AED",
    fontWeight: "600",
  },
});
