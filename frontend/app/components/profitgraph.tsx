import { useFocusEffect } from "expo-router";
import React, { useCallback, useRef, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Line, Path, Text as SvgText } from "react-native-svg";
import { API_URL, FETCH_TIMEOUT_MS } from "../../constants/Config";
import { getApiErrorMessage, readApiResponse } from "../../utils/apiResponse";

type ProfitPoint = {
  date?: string;
  label: string;
  value: number;
};

type ProfitGraphProps = {
  title?: string;
  days?: 7 | 14 | 28 | 30;
  maxValue?: number;
  height?: number;
};

const SVG_WIDTH = 420;
const SVG_HEIGHT = 320;
const PADDING = { top: 18, right: 16, bottom: 44, left: 36 };
const PROFIT_REFRESH_INTERVAL_MS = 5000;

function buildYAxisTicks(values: number[], forcedMaxValue?: number) {
  if (forcedMaxValue) {
    const step = forcedMaxValue / 4;
    return Array.from({ length: 5 }, (_, index) => Math.round(index * step));
  }

  const minValue = Math.min(...values, 0);
  const maxValue = Math.max(...values, 0);

  if (minValue === 0 && maxValue === 0) {
    return [0, 100, 200, 300, 400];
  }

  const range = Math.max(maxValue - minValue, 1);
  const roughStep = range / 4;
  const magnitude = 10 ** Math.floor(Math.log10(roughStep));
  const normalizedStep = roughStep / magnitude;
  const niceStep =
    normalizedStep <= 1 ? 1 :
    normalizedStep <= 2 ? 2 :
    normalizedStep <= 5 ? 5 : 10;
  const step = niceStep * magnitude;
  const lowerBound = minValue >= 0 ? 0 : Math.floor(minValue / step) * step;
  const upperBound = Math.ceil(maxValue / step) * step;

  const ticks: number[] = [];
  for (let value = lowerBound; value <= upperBound + step / 2; value += step) {
    ticks.push(Number(value.toFixed(2)));
  }

  return ticks.length >= 2 ? ticks : [lowerBound, lowerBound + step];
}

export default function ProfitGraph({
  title = "Daily Profit",
  days = 7,
  maxValue,
  height = 340,
}: ProfitGraphProps) {
  const [data, setData] = useState<ProfitPoint[]>([]);
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

  const loadProfitSeries = useCallback(
    async (showLoader: boolean) => {
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
        const response = await fetch(`${API_URL}/api/reports/profit-series?days=${days}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          const errorPayload = await readApiResponse(response);
          throw new Error(getApiErrorMessage(errorPayload, `Failed to load profit series (${response.status})`));
        }

        const payload = await readApiResponse(response);
        setData(
          Array.isArray(payload.series)
            ? payload.series.map((point: ProfitPoint) => ({
                date: point.date,
                label: point.label,
                value: Number(point.value ?? 0),
              }))
            : [],
        );
      } catch (fetchError: any) {
        if (fetchError?.name === "AbortError" && !didTimeout) {
          return;
        }

        setError(
          fetchError?.name === "AbortError"
            ? "Profit data request timed out."
            : "Unable to load profit data.",
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
    },
    [days],
  );

  useFocusEffect(
    useCallback(() => {
      loadProfitSeries(true);
      intervalRef.current = setInterval(() => {
        loadProfitSeries(false);
      }, PROFIT_REFRESH_INTERVAL_MS);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        cleanupPendingRequest();
      };
    }, [cleanupPendingRequest, loadProfitSeries]),
  );

  const safeData: ProfitPoint[] = data.length > 0 ? data : Array.from({ length: days }, (_, index) => ({
    label: `${index + 1}`,
    value: 0,
  }));
  const yTicks = buildYAxisTicks(safeData.map((point) => point.value), maxValue);
  const chartMinValue = yTicks[0];
  const chartMaxValue = yTicks[yTicks.length - 1];
  const chartRange = Math.max(chartMaxValue - chartMinValue, 1);
  const chartWidth = SVG_WIDTH - PADDING.left - PADDING.right;
  const chartHeight = SVG_HEIGHT - PADDING.top - PADDING.bottom;
  const stepX = safeData.length > 1 ? chartWidth / (safeData.length - 1) : 0;

  const getX = (index: number) => PADDING.left + index * stepX;
  const getY = (value: number) =>
    PADDING.top + chartHeight - ((value - chartMinValue) / chartRange) * chartHeight;

  const linePath = safeData
    .map((point, index) => `${index === 0 ? "M" : "L"} ${getX(index)} ${getY(point.value)}`)
    .join(" ");

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>

      {loading ? (
        <View style={[styles.feedback, { height }]}>
          <ActivityIndicator size="large" color="#007566" />
          <Text style={styles.feedbackText}>Loading profit data...</Text>
        </View>
      ) : error ? (
        <View style={[styles.feedback, { height }]}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : (
        <Svg
          width="100%"
          height={height}
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        >
          {yTicks
            .filter((tick) => tick !== chartMinValue)
            .map((tick) => {
              const y = getY(tick);

              return (
                <React.Fragment key={tick}>
                  <Line
                    x1={PADDING.left}
                    y1={y}
                    x2={SVG_WIDTH - PADDING.right}
                    y2={y}
                    stroke="#D6D9DF"
                    strokeWidth={1.2}
                  />
                  <SvgText
                    x={PADDING.left - 12}
                    y={y}
                    fill="#5B5F68"
                    fontSize={12}
                    textAnchor="end"
                    alignmentBaseline="middle"
                  >
                    {tick}
                  </SvgText>
                </React.Fragment>
              );
            })}

          <Line
            x1={PADDING.left}
            y1={PADDING.top + chartHeight}
            x2={SVG_WIDTH - PADDING.right}
            y2={PADDING.top + chartHeight}
            stroke="#61656D"
            strokeWidth={1.4}
          />

          <SvgText
            x={PADDING.left - 12}
            y={PADDING.top + chartHeight}
            fill="#5B5F68"
            fontSize={12}
            textAnchor="end"
            alignmentBaseline="middle"
          >
            {chartMinValue}
          </SvgText>

          <Path
            d={linePath}
            fill="none"
            stroke="#000000"
            strokeWidth={2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {safeData.map((point, index) => (
            <React.Fragment key={`${point.label}-${point.date ?? index}`}>
              <Circle
                cx={getX(index)}
                cy={getY(point.value)}
                r={4.2}
                fill="#666666"
              />
              <Line
                x1={getX(index)}
                y1={PADDING.top + chartHeight}
                x2={getX(index)}
                y2={PADDING.top + chartHeight + 6}
                stroke="#61656D"
                strokeWidth={1.4}
              />
              <SvgText
                x={getX(index)}
                y={PADDING.top + chartHeight + 18}
                fill="#5B5F68"
                fontSize={12}
                textAnchor="middle"
              >
                {point.label}
              </SvgText>
            </React.Fragment>
          ))}
        </Svg>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 0,
    paddingTop: 12,
    paddingBottom: 8,
  },
  title: {
    color: "#000000",
    fontSize: 24,
    fontWeight: "700",
    marginBottom: 10,
  },
  feedback: {
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  feedbackText: {
    color: "#5B5F68",
    fontSize: 14,
    fontWeight: "500",
  },
  errorText: {
    color: "#B42318",
    fontSize: 14,
    fontWeight: "600",
    textAlign: "center",
    paddingHorizontal: 24,
  },
});
