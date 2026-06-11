import AsyncStorage from "@react-native-async-storage/async-storage";
import { useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";
import Svg, { Circle, Path, Text as SvgText } from "react-native-svg";
import { API_URL, FETCH_TIMEOUT_MS } from "../../constants/Config";
import { readApiResponse } from "../../utils/apiResponse";

type InventoryItem = {
  current_stock: number | string;
  item: string;
  item_nepali?: string;
  unit?: string;
};

type StockSlice = {
  color: string;
  name: string;
  percentage: number;
  value: number;
};

type SegmentLabelAnchor = "start" | "middle" | "end";

const CHART_COLORS = [
  "#6E5423",
  "#6D9AE5",
  "#98A5BD",
  "#E87484",
  "#A279E6",
  "#D96BAF",
  "#67C8B8",
  "#FFD447",
  "#7F85E7",
  "#4BA545",
  "#CC2FF2",
  "#F59E0B",
];

const DONUT_REFRESH_INTERVAL_MS = 7000;
const SVG_WIDTH = 390;
const SVG_HEIGHT = 330;
const CENTER_X = 195;
const CENTER_Y = 152;
const OUTER_RADIUS = 116;
const INNER_RADIUS = 70;
const LABEL_RADIUS = 146;
const START_ANGLE = -50;

function polarToCartesian(
  centerX: number,
  centerY: number,
  radius: number,
  angleInDegrees: number,
) {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180;

  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  };
}

function describeDonutArc(
  centerX: number,
  centerY: number,
  outerRadius: number,
  innerRadius: number,
  startAngle: number,
  endAngle: number,
) {
  const startOuter = polarToCartesian(centerX, centerY, outerRadius, startAngle);
  const endOuter = polarToCartesian(centerX, centerY, outerRadius, endAngle);
  const startInner = polarToCartesian(centerX, centerY, innerRadius, startAngle);
  const endInner = polarToCartesian(centerX, centerY, innerRadius, endAngle);
  const largeArcFlag = endAngle - startAngle > 180 ? "1" : "0";

  return [
    `M ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${endInner.x} ${endInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${startInner.x} ${startInner.y}`,
    "Z",
  ].join(" ");
}

export default function Dougnut() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeControllerRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const requestInFlightRef = useRef(false);

  const cleanupPendingRequest = useCallback(() => {
    activeControllerRef.current?.abort();
    activeControllerRef.current = null;

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const loadInventory = useCallback(async (showLoader: boolean) => {
    if (requestInFlightRef.current) {
      return;
    }

    const controller = new AbortController();
    let didTimeout = false;
    requestInFlightRef.current = true;
    activeControllerRef.current = controller;
    timeoutRef.current = setTimeout(() => {
      didTimeout = true;
      controller.abort();
    }, FETCH_TIMEOUT_MS);

    if (showLoader) {
      setLoading(true);
    }
    setError(null);

    try {
      const token = await AsyncStorage.getItem("access_token");
      const response = await fetch(`${API_URL}/stock`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal: controller.signal,
      });

      const payload = await readApiResponse(response);

      if (!response.ok || payload.status !== "success" || !Array.isArray(payload.inventory)) {
        throw new Error("Unable to load stock distribution.");
      }

      setItems(
        payload.inventory.map((item: InventoryItem) => ({
          current_stock: Number(item.current_stock ?? 0),
          item: item.item,
          item_nepali: item.item_nepali,
          unit: item.unit,
        })),
      );
    } catch (fetchError: any) {
      if (fetchError?.name === "AbortError" && !didTimeout) {
        return;
      }

      setItems([]);
      setError(
        fetchError?.name === "AbortError"
          ? "Stock distribution request timed out."
          : "Unable to load stock distribution.",
      );
    } finally {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      if (activeControllerRef.current === controller) {
        activeControllerRef.current = null;
      }
      requestInFlightRef.current = false;

      if (!(controller.signal.aborted && !didTimeout)) {
        setLoading(false);
      }
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadInventory(true);
      intervalRef.current = setInterval(() => {
        loadInventory(false);
      }, DONUT_REFRESH_INTERVAL_MS);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        cleanupPendingRequest();
      };
    }, [cleanupPendingRequest, loadInventory]),
  );

  const slices = useMemo<StockSlice[]>(() => {
    const normalizedItems = items
      .map((item) => ({
        name: item.item?.trim() || "Unnamed Item",
        value: Number(item.current_stock ?? 0),
      }))
      .filter((item) => Number.isFinite(item.value) && item.value > 0)
      .sort((left, right) => right.value - left.value);

    const total = normalizedItems.reduce((sum, item) => sum + item.value, 0);
    if (total <= 0) {
      return [];
    }

    return normalizedItems.map((item, index) => ({
      color: CHART_COLORS[index % CHART_COLORS.length],
      name: item.name,
      percentage: (item.value / total) * 100,
      value: item.value,
    }));
  }, [items]);

  const chartSegments = useMemo(() => {
    let currentAngle = START_ANGLE;

    return slices.map((slice) => {
      const sweepAngle = Math.min((slice.percentage / 100) * 360, 359.999);
      const startAngle = currentAngle;
      const endAngle = currentAngle + sweepAngle;
      const midAngle = startAngle + sweepAngle / 2;
      currentAngle = endAngle;

      const labelPosition = polarToCartesian(
        CENTER_X,
        CENTER_Y,
        LABEL_RADIUS,
        midAngle,
      );

      const labelAnchor: SegmentLabelAnchor =
        labelPosition.x < CENTER_X - 12 ? "end" :
        labelPosition.x > CENTER_X + 12 ? "start" :
        "middle";

      return {
        ...slice,
        labelAnchor,
        labelPosition,
        showLabel: slice.percentage >= 4,
        labelText: `${Math.max(1, Math.round(slice.percentage))}%`,
        path: describeDonutArc(
          CENTER_X,
          CENTER_Y,
          OUTER_RADIUS,
          INNER_RADIUS,
          startAngle,
          endAngle,
        ),
      };
    });
  }, [slices]);

  return (
    <View className="bg-white px-2 pt-0 pb-0">
      {loading ? (
        <View className="h-[500px] items-center justify-center gap-3">
          <ActivityIndicator size="large" color="#007566" />
          <Text className="text-sm font-medium text-[#5B5F68]">
            Loading stock distribution...
          </Text>
        </View>
      ) : error ? (
        <View className="h-[520px] items-center justify-center px-6">
          <Text className="text-center text-sm font-semibold text-[#B42318]">
            {error}
          </Text>
        </View>
      ) : chartSegments.length === 0 ? (
        <View className="h-[520px] items-center justify-center px-6">
          <Text className="text-center text-sm font-semibold text-[#007566]">
            No stock data available yet.
          </Text>
        </View>
      ) : (
        <>
          <View className="items-center">
            <Svg
              width="100%"
              height={SVG_HEIGHT}
              viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
            >
              {chartSegments.map((segment) => (
                <Path key={segment.name} d={segment.path} fill={segment.color} />
              ))}

              <Circle cx={CENTER_X} cy={CENTER_Y} fill="#FFFFFF" r={INNER_RADIUS - 1} />

              {chartSegments
                .filter((segment) => segment.showLabel)
                .map((segment) => (
                <SvgText
                  key={`${segment.name}-label`}
                  x={segment.labelPosition.x}
                  y={segment.labelPosition.y}
                  fill="#111111"
                  fontSize={13}
                  fontWeight="700"
                  textAnchor={segment.labelAnchor}
                  alignmentBaseline="middle"
                >
                  {segment.labelText}
                </SvgText>
              ))}

              <SvgText
                x={CENTER_X}
                y={CENTER_Y + 3}
                fill="#111111"
                fontSize={18}
                fontWeight="700"
                textAnchor="middle"
                alignmentBaseline="middle"
              >
                Items
              </SvgText>
            </Svg>
          </View>

          <View className="mt-0 flex-row flex-wrap justify-center gap-x-5 gap-y-6 px-4">
            {chartSegments.map((segment) => (
              <View key={`${segment.name}-legend`} className="flex-row items-center gap-3">
                <View
                  className="h-[18px] w-[18px] rounded-full"
                  style={{ backgroundColor: segment.color }}
                />
                <Text className="text-[15px] font-bold text-[#556173]">
                  {segment.name}
                </Text>
              </View>
            ))}
          </View>
        </>
      )}
    </View>
  );
}
