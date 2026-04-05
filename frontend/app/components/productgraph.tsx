import { ChevronDown } from "lucide-react-native";
import { useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Svg, { Circle, Line, Path, Text as SvgText } from "react-native-svg";
import { API_URL, FETCH_TIMEOUT_MS } from "../../constants/Config";

type ProductOption = {
  id: number;
  name: string;
  nameNepali?: string;
  unit?: string;
  currentStock?: number;
};

type ProductPoint = {
  date?: string;
  label: string;
  value: number;
};

type ProductGraphProps = {
  title?: string;
  days?: 7 | 14 | 28 | 30;
  maxValue?: number;
  height?: number;
};

const SVG_WIDTH = 420;
const SVG_HEIGHT = 320;
const PADDING = { top: 18, right: 18, bottom: 44, left: 54 };

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

export default function ProductGraph({
  title = "Products",
  days = 7,
  maxValue,
  height = 340,
}: ProductGraphProps) {
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [selectedProductName, setSelectedProductName] = useState("Select item");
  const [data, setData] = useState<ProductPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pickerVisible, setPickerVisible] = useState(false);

  const selectedProductIdRef = useRef<number | null>(null);
  const activeControllerRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sheetProgress = useRef(new Animated.Value(0)).current;

  const cleanupPendingRequest = useCallback(() => {
    activeControllerRef.current?.abort();
    activeControllerRef.current = null;

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const loadProductSeries = useCallback(
    async (productId?: number | null) => {
      cleanupPendingRequest();

      const controller = new AbortController();
      let didTimeout = false;
      activeControllerRef.current = controller;
      timeoutRef.current = setTimeout(() => {
        didTimeout = true;
        controller.abort();
      }, FETCH_TIMEOUT_MS);

      setLoading(true);
      setError(null);

      try {
        const query = new URLSearchParams({ days: String(days) });
        if (productId) {
          query.append("product_id", String(productId));
        }

        const response = await fetch(`${API_URL}/api/reports/product-series?${query.toString()}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to load product series (${response.status})`);
        }

        const payload = await response.json();
        const nextProducts: ProductOption[] = Array.isArray(payload.products)
          ? payload.products.map((product: ProductOption) => ({
              id: Number(product.id),
              name: product.name,
              nameNepali: product.nameNepali,
              unit: product.unit,
              currentStock: Number(product.currentStock ?? 0),
            }))
          : [];
        const nextSelected = payload.selectedProduct
          ? {
              id: Number(payload.selectedProduct.id),
              name: payload.selectedProduct.name,
              nameNepali: payload.selectedProduct.nameNepali,
              unit: payload.selectedProduct.unit,
              currentStock: Number(payload.selectedProduct.currentStock ?? 0),
            }
          : null;
        const nextSeries: ProductPoint[] = Array.isArray(payload.series)
          ? payload.series.map((point: ProductPoint) => ({
              date: point.date,
              label: point.label,
              value: Number(point.value ?? 0),
            }))
          : [];

        setProducts(nextProducts);
        setData(nextSeries);
        setSelectedProductId(nextSelected?.id ?? null);
        setSelectedProductName(nextSelected?.name ?? "Select item");
        selectedProductIdRef.current = nextSelected?.id ?? null;
      } catch (fetchError: any) {
        if (fetchError?.name === "AbortError" && !didTimeout) {
          return;
        }

        setError(
          fetchError?.name === "AbortError"
            ? "Product data request timed out."
            : "Unable to load product data.",
        );
      } finally {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }

        if (activeControllerRef.current === controller) {
          activeControllerRef.current = null;
        }

        if (!(controller.signal.aborted && !didTimeout)) {
          setLoading(false);
        }
      }
    },
    [cleanupPendingRequest, days],
  );

  useFocusEffect(
    useCallback(() => {
      loadProductSeries(selectedProductIdRef.current);

      return () => {
        cleanupPendingRequest();
      };
    }, [cleanupPendingRequest, loadProductSeries]),
  );

  const openPicker = useCallback(() => {
    if (!products.length) return;

    setPickerVisible(true);
    sheetProgress.setValue(0);
    Animated.timing(sheetProgress, {
      toValue: 1,
      duration: 240,
      useNativeDriver: true,
    }).start();
  }, [products.length, sheetProgress]);

  const closePicker = useCallback(() => {
    Animated.timing(sheetProgress, {
      toValue: 0,
      duration: 220,
      useNativeDriver: true,
    }).start(({ finished }) => {
      if (finished) {
        setPickerVisible(false);
      }
    });
  }, [sheetProgress]);

  const handleSelectProduct = useCallback(
    (product: ProductOption) => {
      if (product.id === selectedProductIdRef.current) {
        closePicker();
        return;
      }

      selectedProductIdRef.current = product.id;
      setSelectedProductId(product.id);
      setSelectedProductName(product.name);
      closePicker();
      loadProductSeries(product.id);
    },
    [closePicker, loadProductSeries],
  );

  const fallbackSeries = useMemo<ProductPoint[]>(
    () =>
      Array.from({ length: days }, (_, index) => ({
        label: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][index] ?? `${index + 1}`,
        value: 0,
      })),
    [days],
  );

  const safeData = data.length > 0 ? data : fallbackSeries;
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

  const sheetTranslateY = sheetProgress.interpolate({
    inputRange: [0, 1],
    outputRange: [520, 0],
  });

  const backdropOpacity = sheetProgress.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 0.28],
  });

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{title}</Text>

        <Pressable
          onPress={openPicker}
          disabled={!products.length || loading}
          style={({ pressed }) => [
            styles.selectorButton,
            (!products.length || loading) && styles.selectorDisabled,
            pressed && products.length > 0 && !loading ? styles.selectorPressed : null,
          ]}
        >
          <Text numberOfLines={1} style={styles.selectorText}>
            {selectedProductName}
          </Text>
          <ChevronDown color="#475569" size={26} strokeWidth={2.2} />
        </Pressable>
      </View>

      {loading ? (
        <View style={[styles.feedback, { height }]}>
          <ActivityIndicator size="large" color="#007566" />
          <Text style={styles.feedbackText}>Loading product data...</Text>
        </View>
      ) : error ? (
        <View style={[styles.feedback, { height }]}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : !products.length ? (
        <View style={[styles.feedback, { height }]}>
          <Text style={styles.feedbackText}>No products found yet.</Text>
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

      <Modal
        animationType="none"
        transparent
        visible={pickerVisible}
        onRequestClose={closePicker}
        statusBarTranslucent
      >
        <View style={styles.modalRoot}>
          <Pressable style={StyleSheet.absoluteFill} onPress={closePicker}>
            <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]} />
          </Pressable>

          <Animated.View
            style={[
              styles.sheet,
              {
                transform: [{ translateY: sheetTranslateY }],
              },
            ]}
          >
            <View style={styles.sheetHandle} />
            <Text style={styles.sheetTitle}>Select the option below</Text>

            <ScrollView
              showsVerticalScrollIndicator={false}
              contentContainerStyle={styles.sheetList}
            >
              {products.map((product) => {
                const isSelected = product.id === selectedProductId;

                return (
                  <Pressable
                    key={product.id}
                    style={styles.optionRow}
                    onPress={() => handleSelectProduct(product)}
                  >
                    <View style={[styles.radioOuter, isSelected ? styles.radioOuterSelected : null]}>
                      <View style={[styles.radioInner, isSelected ? styles.radioInnerSelected : null]} />
                    </View>
                    <Text style={styles.optionText}>{product.name}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </Animated.View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 16,
    paddingTop: 18,
    paddingBottom: 8,
  },
  headerRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  title: {
    color: "#000000",
    fontSize: 24,
    fontWeight: "700",
  },
  selectorButton: {
    alignItems: "center",
    backgroundColor: "#E5EBF4",
    borderRadius: 28,
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
    minWidth: 148,
    paddingHorizontal: 18,
    paddingVertical: 12,
  },
  selectorDisabled: {
    opacity: 0.6,
  },
  selectorPressed: {
    opacity: 0.82,
  },
  selectorText: {
    color: "#475569",
    fontSize: 18,
    fontWeight: "700",
    maxWidth: 126,
  },
  feedback: {
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
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
    paddingHorizontal: 24,
    textAlign: "center",
  },
  modalRoot: {
    flex: 1,
    justifyContent: "flex-end",
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "#000000",
  },
  sheet: {
    backgroundColor: "#FFFFFF",
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    maxHeight: "72%",
    minHeight: "62%",
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 28,
  },
  sheetHandle: {
    alignSelf: "center",
    backgroundColor: "#000000",
    borderRadius: 999,
    height: 8,
    marginBottom: 26,
    width: 112,
  },
  sheetTitle: {
    color: "#000000",
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 22,
  },
  sheetList: {
    paddingBottom: 12,
  },
  optionRow: {
    alignItems: "center",
    borderColor: "#1F2937",
    borderWidth: 1.5,
    flexDirection: "row",
    gap: 16,
    marginBottom: 18,
    minHeight: 78,
    paddingHorizontal: 18,
  },
  radioOuter: {
    alignItems: "center",
    borderColor: "#111111",
    borderRadius: 999,
    borderWidth: 3,
    height: 28,
    justifyContent: "center",
    width: 28,
  },
  radioOuterSelected: {
    borderColor: "#0F766E",
  },
  radioInner: {
    borderRadius: 999,
    height: 12,
    width: 12,
  },
  radioInnerSelected: {
    backgroundColor: "#0F766E",
  },
  optionText: {
    color: "#000000",
    flexShrink: 1,
    fontSize: 18,
    fontWeight: "500",
  },
});
