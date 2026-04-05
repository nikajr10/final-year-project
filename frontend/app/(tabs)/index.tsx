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
import ProfitGraph from "../components/profitgraph";
import ProductGraph from "../components/productgraph";

const Microphone = require("../../assets/images/Microphone.svg");
const Sales = require("../../assets/images/revenue.svg");
const Inventory = require("../../assets/images/inventory.svg");
const Alertimg = require("../../assets/images/Alert-Danger.svg");

const GENERAL_GREETINGS = [
  "Welcome Back",
  "Hello",
  "Hi There",
  "Greetings",
  "Welcome",
  "Hello Again",
  "All Set",
  "Let's Roll",
  "Stay Sharp",
];
const SESSION_GREETING_KEY = "session_greeting";

function getTimeBasedGreeting(date = new Date()) {
  const hour = date.getHours();

  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  return "Good Evening";
}

function getRandomGreeting() {
  const greetingPool = [...GENERAL_GREETINGS, getTimeBasedGreeting()];
  const randomIndex = Math.floor(Math.random() * greetingPool.length);
  return greetingPool[randomIndex];
}

function getGreetingName(value: string | null) {
  const raw = value?.trim();
  if (!raw) return "User";

  if (raw.includes("@")) {
    return "User";
  }

  const firstChunk = raw
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean)[0];

  if (!firstChunk) return "User";

  return firstChunk.charAt(0).toUpperCase() + firstChunk.slice(1);
}

export default function HomeScreen() {
  const [name, setName] = useState("User");
  const [greeting, setGreeting] = useState("Welcome Back");
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalUnits: 0,
    inventoryCount: 0,
    lowStockItems: [],
  });
  const fetchInFlight = useRef(false);

  useFocusEffect(
    useCallback(() => {
      loadSessionGreeting();
      loadUserName();
      fetchDashboardData();
    }, []),
  );

  const loadSessionGreeting = async () => {
    try {
      const storedGreeting = await AsyncStorage.getItem(SESSION_GREETING_KEY);
      if (storedGreeting?.trim()) {
        setGreeting(storedGreeting);
        return;
      }

      const nextGreeting = getRandomGreeting();
      setGreeting(nextGreeting);
      await AsyncStorage.setItem(SESSION_GREETING_KEY, nextGreeting);
    } catch {
      setGreeting("Welcome Back");
    }
  };

  const loadUserName = async () => {
    try {
      const storedName = await AsyncStorage.getItem("user_name");
      setName(getGreetingName(storedName));
    } catch {
      setName("User");
    }
  };

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
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      clearTimeout(timer);
      const data = await response.json();

      if (response.ok && data.status === "success") {
        const products = data.inventory;

        // Calculate Stats
        const lowStock = products.filter((p: any) => p.current_stock < 10);
        const totalItems = products.length;
        const totalPhysicalUnits = products.reduce(
          (sum: number, p: any) => sum + (p.current_stock || 0),
          0,
        );

        setStats({
          totalUnits: totalPhysicalUnits,
          inventoryCount: totalItems,
          lowStockItems: lowStock,
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
            {greeting}, {name}!
          </Text>
        </View>

        <View className="flex-row justify-between gap-4">
          <View className="flex-1 border-2 py-4 pl-4 border-slate-300 rounded-lg bg-white">
            <View className="flex-row items-center gap-2 mb-2">
              <Image source={Sales} style={{ width: 18, height: 18 }} />
              <Text className="text-sm font-bold text-slate-400">
                Total Stock
              </Text>
            </View>
            <Text className="text-xl font-bold mb-1 text-zinc-900">
              {stats.totalUnits.toLocaleString()}
            </Text>
            <Text className="text-xs font-bold text-[#007566]">
              Physical Units
            </Text>
          </View>

          <View className="flex-1 border-2 py-4 pl-4 border-slate-300 rounded-lg bg-white">
            <View className="flex-row items-center gap-2 mb-2">
              <Image source={Inventory} style={{ width: 18, height: 18 }} />
              <Text className="text-sm font-bold text-slate-400">
                Inventory
              </Text>
            </View>
            <Text className="text-xl font-bold mb-1 text-zinc-900">
              {stats.inventoryCount}
            </Text>
            <Text className="text-xs font-bold text-slate-400">
              Unique Items
            </Text>
          </View>
        </View>

        <Pressable
          className="items-center justify-center pt-8 bg-[#007566]/10 rounded-2xl mt-8"
          onPress={() => router.push("/(screens)/voice")}
        >
          <View className="w-full items-center justify-center mb-10">
            <Image
              source={Microphone}
              style={{ width: 100, height: 100 }}
              contentFit="contain"
            />
          </View>
          <View className="w-full">
            <View className="mx-6 rounded-xl bg-[#007566] rounded-2xl py-5 items-center mb-6">
              <Text className="font-bold text-white text-base">
                Tap to Speak
              </Text>
            </View>
          </View>
        </Pressable>

        <View className="mt-6">
          <View className="flex-row justify-between items-center mb-4">
            <Text className="font-semibold text-lg text-slate-600">
              Stock Alert
            </Text>
            <Pressable className="rounded-3xl bg-slate-200 px-4 py-1">
              <Text className="text-slate-600 font-bold text-xs">
                {stats.lowStockItems.length} View All
              </Text>
            </Pressable>
          </View>

          {loading ? (
            <ActivityIndicator
              size="large"
              color="#007566"
              style={{ marginTop: 20 }}
            />
          ) : stats.lowStockItems.length === 0 ? (
            <View className="p-4 rounded-xl">
              <Text className="text-[#007566] text-center font-bold">
                All Stock Levels Good! ✅
              </Text>
            </View>
          ) : (
            stats.lowStockItems.map((item: any, index: number) => (
              <View
                key={index}
                className="bg-red-100 rounded-xl my-2 p-4 flex-row items-center gap-4"
              >
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

<View>
  <ProfitGraph />
</View>

<View className="mt-6">
  <ProductGraph />
</View>

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  titleContainer: { flexDirection: "row", alignItems: "center", gap: 8 },
});
