import { Image } from "expo-image";
import { router, useFocusEffect } from "expo-router";
import React, { useState, useCallback, useRef } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  ActivityIndicator,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL, FETCH_TIMEOUT_MS } from "../../constants/Config";

const Microphone = require("../../assets/images/Microphone.png");
const Sales = require("../../assets/images/Sales.png");
const Inventory = require("../../assets/images/inventory.png");
const Alertimg = require("../../assets/images/Alert-Danger.png");

export default function HomeScreen() {
  const [name] = useState("Admin");
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalUnits: 0,
    inventoryCount: 0,
    lowStockItems: [] as any[],
  });
  const fetchInFlight = useRef(false);

  useFocusEffect(
    useCallback(() => {
      fetchDashboardData();
    }, [])
  );

  const fetchDashboardData = async () => {
    if (fetchInFlight.current) return;
    fetchInFlight.current = true;
    setLoading(true);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    try {
      const token = await AsyncStorage.getItem("access_token");
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(`${API_URL}/stock`, {
        method: "GET",
        headers,
        signal: controller.signal,
      });

      clearTimeout(timer);
      const data = await response.json();

      if (response.ok && data.status === "success") {
        const products = data.inventory;
        setStats({
          totalUnits: products.reduce((sum: number, p: any) => sum + (p.current_stock || 0), 0),
          inventoryCount: products.length,
          lowStockItems: products.filter((p: any) => p.current_stock < 10),
        });
      }
    } catch {
      clearTimeout(timer);
      // Fail silently — dashboard shows zeros, user can still navigate
    } finally {
      setLoading(false);
      fetchInFlight.current = false;
    }
  };

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white mt-14"
      behavior={Platform.select({ ios: "padding", android: undefined })}
    >
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 100 }}>
        
        <View style={styles.titleContainer}>
          <Text className="text-2xl font-semibold mb-6 text-zinc-800">
            Good morning, {name}!
          </Text>
        </View>

        <View className="flex-row justify-between gap-4">
          <View className="flex-1 border-2 py-4 pl-4 border-slate-300 rounded-lg bg-white">
            <View className="flex-row items-center gap-2 mb-2">
              <Image source={Sales} style={{ width: 18, height: 18 }} />
              <Text className="text-sm font-bold text-slate-400">Total Stock</Text>
            </View>
            <Text className="text-xl font-bold mb-1 text-zinc-900">
              {stats.totalUnits.toLocaleString()}
            </Text>
            <Text className="text-xs font-bold text-green-700">Physical Units</Text>
          </View>

          <View className="flex-1 border-2 py-4 pl-4 border-slate-300 rounded-lg bg-white">
            <View className="flex-row items-center gap-2 mb-2">
              <Image source={Inventory} style={{ width: 18, height: 18 }} />
              <Text className="text-sm font-bold text-slate-400">Inventory</Text>
            </View>
            <Text className="text-xl font-bold mb-1 text-zinc-900">
              {stats.inventoryCount}
            </Text>
            <Text className="text-xs font-bold text-slate-400">Unique Items</Text>
          </View>
        </View>

        <Pressable
          className="items-center justify-center pt-8 bg-slate-200 rounded-2xl mt-8"
          onPress={() => router.push("/(screens)/voice")}
        >
          <View className="w-full items-center justify-center mb-10">
            <Image source={Microphone} style={{ width: 100, height: 100 }} contentFit="contain" />
          </View>
          <View className="w-full">
            <View className="mx-6 rounded-xl bg-purple-700 py-5 items-center mb-6">
              <Text className="font-bold text-white text-base">Tap to Speak</Text>
            </View>
          </View>
        </Pressable>

        <View className="mt-6">
          <View className="flex-row justify-between items-center mb-4">
            <Text className="font-semibold text-lg text-slate-600">Stock Alert</Text>
            <Pressable className="rounded-3xl bg-slate-200 px-4 py-1">
              <Text className="text-slate-600 font-bold text-xs">{stats.lowStockItems.length} View All</Text>
            </Pressable>
          </View>

          {loading ? (
            <ActivityIndicator size="large" color="#7E22CE" style={{ marginTop: 20 }} />
          ) : stats.lowStockItems.length === 0 ? (
            <View className="p-4 bg-green-100 rounded-xl">
              <Text className="text-green-800 text-center font-bold">All Stock Levels Good! ✅</Text>
            </View>
          ) : (
            stats.lowStockItems.map((item: any, index: number) => (
              <View key={index} className="bg-red-100 rounded-xl my-2 p-4 flex-row items-center gap-4">
                <Image source={Alertimg} style={{ width: 24, height: 24 }} />
                <View>
                  {/* FIX 3: Use item.item and item.item_nepali */}
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
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  titleContainer: { flexDirection: "row", alignItems: "center", gap: 8 },
});