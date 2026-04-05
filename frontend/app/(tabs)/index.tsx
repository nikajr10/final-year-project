import { Image } from "expo-image";
import { router, useFocusEffect } from "expo-router";
import React, { useState, useCallback, useRef } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  View,
  ActivityIndicator,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL, FETCH_TIMEOUT_MS, LOW_STOCK_THRESHOLD } from "../../constants/Config";
import Graphs from "../components/graphs";
import StockAlertButton from "../components/stockalertbutton";

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
        const lowStock = products.filter((p: any) => p.current_stock < LOW_STOCK_THRESHOLD);
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

  const openStockAlerts = () => {
    router.push("/stock-alerts");
  };

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white mt-14"
      behavior={Platform.select({ ios: "padding", android: undefined })}
    >
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 100 }}>
        <View className="mb-4 flex-row items-start justify-between gap-4">
          <Text className="flex-1 pt-2 text-2xl font-semibold text-zinc-800">
            {greeting}, {name}!
          </Text>
          <StockAlertButton count={stats.lowStockItems.length} onPress={openStockAlerts} />
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
          className="items-center justify-center pt-2 bg-[#007566]/10 rounded-2xl mt-8"
          onPress={() => router.push("/(screens)/voice")}
        >
          <View className="w-full items-center justify-center mb-6">
            <Image
              source={Microphone}
              style={{ width: 100, height: 100 }}
              contentFit="contain"
            />
          </View>
          <View className="w-full">
            <View className="mx-6 rounded-xl bg-[#007566] rounded-2xl py-5 items-center mb-4">
              <Text className="font-bold text-white text-base">
                Tap to Speak
              </Text>
            </View>
          </View>
        </Pressable>

<Graphs />

      </ScrollView>
    </KeyboardAvoidingView>
  );
}
