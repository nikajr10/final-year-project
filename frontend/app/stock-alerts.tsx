import { Image } from "expo-image";
import { ArrowLeft } from "lucide-react-native";
import { router, Stack, useFocusEffect } from "expo-router";
import React, { useCallback, useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL, FETCH_TIMEOUT_MS } from "../constants/Config";

const Alertimg = require("../assets/images/Alert-Danger.svg");

type LowStockItem = {
  item: string;
  item_nepali: string;
  current_stock: number;
  unit: string;
};

export default function StockAlertsScreen() {
  const [loading, setLoading] = useState(true);
  const [lowStockItems, setLowStockItems] = useState<LowStockItem[]>([]);
  const fetchInFlight = useRef(false);

  const fetchLowStockItems = useCallback(async () => {
    if (fetchInFlight.current) return;
    fetchInFlight.current = true;
    setLoading(true);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

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

      clearTimeout(timer);
      const data = await response.json();

      if (response.ok && data.status === "success") {
        const products = Array.isArray(data.inventory) ? data.inventory : [];
        setLowStockItems(products.filter((product: LowStockItem) => product.current_stock < 10));
      } else {
        setLowStockItems([]);
      }
    } catch {
      clearTimeout(timer);
      setLowStockItems([]);
    } finally {
      setLoading(false);
      fetchInFlight.current = false;
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchLowStockItems();
    }, [fetchLowStockItems]),
  );

  return (
    <>
    <KeyboardAvoidingView
          className="flex-1 bg-[#fff] mt-14 px-0"
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
      <Stack.Screen
        options={{
          headerShown: false,
        }}
      />

      <View className="flex-1 bg-white">
        <ScrollView
          className="flex-1"
          contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 32 }}
        >
          <Pressable
              accessibilityLabel="Go back"
              accessibilityRole="button"
              className="mr-2 h-11 w-11 items-center justify-center rounded-full bg-zinc-100 transition duration-200 hover:bg-zinc-70"
              hitSlop={8}
              onPress={() => router.back()}
              style={({ pressed }) => (pressed ? { opacity: 0.8 } : null)}
            >
              <ArrowLeft color="#111827" size={22} strokeWidth={2.4} />
            </Pressable>
          <View className="mb-4 flex-row items-center">

            <Text className="text-2xl justify-items-center mx-auto font-bold text-zinc-900">
              Stock Alert
            </Text> 
          </View>

          {loading ? (
            <ActivityIndicator
              size="large"
              color="#007566"
              style={{ marginTop: 20 }}
            />
          ) : lowStockItems.length === 0 ? (
            <View className="rounded-xl p-4">
              <Text className="text-center font-bold text-[#007566]">
                All Stock Levels Good! ✅
              </Text>
            </View>
          ) : (
            lowStockItems.map((item, index) => (
              <View
                key={`${item.item}-${index}`}
                className="my-2 flex-row items-center gap-4 rounded-xl bg-red-100 p-4"
              >
                <Image source={Alertimg} style={{ width: 24, height: 24 }} />
                <View className="flex-1">
                  <Text className="text-base font-bold text-zinc-800">
                    {item.item} ({item.item_nepali})
                  </Text>
                  <Text className="text-xs font-bold text-red-700">
                    ONLY {item.current_stock} {item.unit} LEFT IN STOCK
                  </Text>
                </View>
              </View>
            ))
          )}
        </ScrollView>
      </View>
      </KeyboardAvoidingView>
    </>
  );
}
