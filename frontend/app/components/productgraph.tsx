import { ChevronDown } from "lucide-react-native";
import { useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Modal,
  Pressable,
  ScrollView,
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
const PADDING = { top: 18, right: 18, bottom: 44, left: 36 };
const ABSOLUTE_FILL = { position: "absolute" as const, top: 0, right: 0, bottom: 0, left: 0 };

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
  title = "Product Stock",
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
    <View className="bg-white pt-[12px] pb-0">
      <View className="mb-0 flex-row items-center justify-between">
        <Text className="text-2xl font-bold text-black">{title}</Text>

        <Pressable
          onPress={openPicker}
          disabled={!products.length || loading}
          className={`min-w-[80px] flex-row items-center justify-between gap-2 rounded-full bg-[#E5EBF4] px-[18px] py-3 ${
            !products.length || loading ? "opacity-60" : ""
          }`}
          style={({ pressed }) =>
            pressed && products.length > 0 && !loading ? { opacity: 0.82 } : null
          }
        >
          <Text numberOfLines={1} className="max-w-[126px] text-sm font-bold text-[#475569]">
            {selectedProductName}
          </Text>
          <ChevronDown color="#475569" size={20} strokeWidth={2.2} />
        </Pressable>
      </View>

      {loading ? (
        <View className="items-center justify-center gap-2.5 -mt-4" style={{ height }}>
          <ActivityIndicator size="large" color="#007566" />
          <Text className="text-sm font-medium text-[#5B5F68]">Loading product data...</Text>
        </View>
      ) : error ? (
        <View className="items-center justify-center gap-2.5" style={{ height }}>
          <Text className="px-6 text-center text-sm font-semibold text-[#B42318]">{error}</Text>
        </View>
      ) : !products.length ? (
        <View className="items-center justify-center gap-2.5" style={{ height }}>
          <Text className="text-sm font-medium text-[#5B5F68]">No products found yet.</Text>
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
        <View className="flex-1 justify-end">
          <Pressable className="absolute inset-0" onPress={closePicker}>
            <Animated.View
              style={[ABSOLUTE_FILL, { opacity: backdropOpacity, backgroundColor: "#000000" }]}
            />
          </Pressable>

          <Animated.View
            className="w-full min-h-[90%] max-h-[90%]"
            style={[
              {
                transform: [{ translateY: sheetTranslateY }],
              },
            ]}
          >
            <View className="flex-1 rounded-t-[30px] bg-white px-5 pt-[14px] pb-7">
              <View className="mb-[26px] h-2 w-28 self-center rounded-full bg-black" />
              <Text className="mb-[22px] text-[28px] font-bold text-black">
                Select the option below
              </Text>

              <ScrollView showsVerticalScrollIndicator={false}>
                <View className="pb-3">
                  {products.map((product) => {
                    const isSelected = product.id === selectedProductId;

                    return (
                      <Pressable
                        key={product.id}
                        className="mb-[8px] min-h-[54px] flex-row items-center gap-4 px-[18px] bg-[#007566]/10 rounded-2xl"
                        onPress={() => handleSelectProduct(product)}
                      >
                        <View
                          className={`h-7 w-7 items-center justify-center rounded-full border ${
                            isSelected ? "border-[#0F766E]" : "border-[#111111]"
                          }`}
                        >
                          <View
                            className={`h-3 w-3 rounded-full ${
                              isSelected ? "bg-[#0F766E]" : ""
                            }`}
                          />
                        </View>
                        <Text className="flex-shrink text-lg font-medium text-black">
                          {product.name}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>
              </ScrollView>
            </View>
          </Animated.View>
        </View>
      </Modal>
    </View>
  );
}
