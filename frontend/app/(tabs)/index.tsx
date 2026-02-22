import { Image } from "expo-image";
import { router, useFocusEffect } from "expo-router"; // useFocusEffect helps refresh data when you come back
import React, { useState, useCallback } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  ActivityIndicator,
  Alert
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

// ✅ YOUR IP ADDRESS
const API_URL = "http://192.168.1.95:8000";

// Assets
const Microphone = require("../../assets/images/Microphone.png");
const Sales = require("../../assets/images/Sales.png");
const Inventory = require("../../assets/images/inventory.png");
const Alertimg = require("../../assets/images/Alert-Danger.png");

export default function HomeScreen() {
  const [name, setName] = useState("User");
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<{
    revenue: number;
    inventoryCount: number;
    lowStockItems: Array<{ id: string | number; name_english: string; name_nepali: string; quantity: number; unit: string }>;
  }>({
    revenue: 0,
    inventoryCount: 0,
    lowStockItems: []
  });

  // ✅ Refresh data every time the screen comes into focus
  useFocusEffect(
    useCallback(() => {
      fetchDashboardData();
    }, [])
  );

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      // 1. Get User Name
      const storedName = await AsyncStorage.getItem("user_name");
      if (storedName) setName(storedName);

      // 2. Fetch Products to calculate stats
      const response = await fetch(`${API_URL}/products`);
      const products = await response.json();

      if (response.ok) {
        // --- Calculate Stats Locally ---
        
        // A. Low Stock (Less than 10 units)
        const lowStock = products.filter((p: { quantity: number }) => p.quantity < 10);

        // B. Total Unique Items
        const totalItems = products.length;

        // C. (Optional) Total Stock Value (Instead of Revenue for now)
        const totalValue = products.reduce((sum: number, p: { quantity: number; cost_price: number }) => sum + (p.quantity * p.cost_price), 0);

        setStats({
          revenue: totalValue, // Showing "Stock Value" as Revenue for now
          inventoryCount: totalItems,
          lowStockItems: lowStock
        });
      }
    } catch (error) {
      console.error("Error fetching dashboard:", error);
      // Don't alert constantly, just log it
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white mt-14"
      behavior={Platform.select({ ios: "padding", android: undefined })}
    >
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 100 }}>
        
        {/* Header */}
        <View style={styles.titleContainer}>
          <Text className="text-2xl font-semibold mb-6 text-zinc-800">
            Good morning, {name}!
          </Text>
        </View>

        {/* Stats Grid */}
        <View className="flex-row justify-between gap-4">
          
          {/* Revenue / Stock Value Card */}
          <View className="flex-1 border-2 py-4 pl-4 border-slate-300 rounded-lg bg-white">
            <View className="flex-row items-center gap-2 mb-2">
              <Image source={Sales} style={{ width: 18, height: 18 }} />
              <Text className="text-sm font-bold text-slate-400">Stock Value</Text>
            </View>
            <Text className="text-xl font-bold mb-1 text-zinc-900">
              Rs {stats.revenue.toLocaleString()}
            </Text>
            <Text className="text-xs font-bold text-green-700">Total Asset</Text>
          </View>

          {/* Inventory Count Card */}
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

        {/* Mic Section */}
        <Pressable
          className="items-center justify-center pt-8 bg-slate-200 rounded-2xl mt-8"
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
            <View className="mx-6 rounded-xl bg-purple-700 py-5 items-center mb-6">
              <Text className="font-bold text-white text-base">
                Tap to Speak
              </Text>
            </View>
          </View>
        </Pressable>

        {/* Stock Alert Section */}
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

          {/* Dynamic Alert Cards */}
          {loading ? (
            <ActivityIndicator size="small" color="#7E22CE" />
          ) : stats.lowStockItems.length === 0 ? (
            <View className="p-4 bg-green-100 rounded-xl">
              <Text className="text-green-800 text-center font-bold">All Stock Levels Good! ✅</Text>
            </View>
          ) : (
            stats.lowStockItems.map((item) => (
              <View key={item.id} className="bg-red-100 rounded-xl my-2 p-4 flex-row items-center gap-4">
                <Image source={Alertimg} style={{ width: 24, height: 24 }} />
                <View>
                  <Text className="text-base font-bold text-zinc-800">
                    {item.name_english} ({item.name_nepali})
                  </Text>
                  <Text className="text-xs font-bold text-red-700">
                    ONLY {item.quantity} {item.unit} LEFT IN STOCK
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
  titleContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
});