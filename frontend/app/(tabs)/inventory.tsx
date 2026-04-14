import React, { useState, useRef } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  View,
  Text,
  TextInput,
  FlatList,
  ActivityIndicator,
  Pressable,
  RefreshControl,
} from "react-native";
import { useFocusEffect } from "expo-router";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL, FETCH_TIMEOUT_MS, LOW_STOCK_THRESHOLD } from "../../constants/Config";
import Dougnut from "../components/dougnut";

// FIX 3: Match the exact schema your Swagger just showed us
interface Product {
  item: string;
  item_nepali: string;
  current_stock: number;
  unit: string;
}

export default function InventoryScreen() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchInFlight = useRef(false);

  const normalizeSearchValue = (value: string) =>
    value
      .normalize("NFC")
      .trim()
      .toLocaleLowerCase()
      .replace(/\s+/g, " ");

  const matchesSearch = (product: Product, query: string) => {
    const normalizedQuery = normalizeSearchValue(query);

    if (!normalizedQuery) return true;

    const englishName = normalizeSearchValue(product.item || "");
    const nepaliName = normalizeSearchValue(product.item_nepali || "");

    return (
      englishName.includes(normalizedQuery) ||
      nepaliName.includes(normalizedQuery)
    );
  };

  const fetchProducts = async (isRefresh = false) => {
    if (fetchInFlight.current) return;
    fetchInFlight.current = true;

    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

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

      const data = await response.json();

      if (response.ok && data.status === "success") {
        // FIX 2: Extract data.inventory
        const inventoryList = data.inventory;
        setProducts(inventoryList);
        setFilteredProducts(
          search.trim()
            ? inventoryList.filter((product: Product) =>
                matchesSearch(product, search),
              )
            : inventoryList,
        );
      } else {
        setError("Failed to load inventory.");
      }
    } catch (err: any) {
      clearTimeout(timer);
      if (err?.name === "AbortError") {
        setError("Request timed out. Is the backend running?");
      } else {
        setError("Cannot connect to server.");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
      fetchInFlight.current = false;
    }
  };

  useFocusEffect(
    React.useCallback(() => {
      fetchProducts();
    }, []),
  );

  const handleSearch = (text: string) => {
    setSearch(text);
    setFilteredProducts(
      text.trim()
        ? products.filter((product) => matchesSearch(product, text))
        : products,
    );
  };

  const renderItem = ({ item }: { item: Product }) => {
    const isLowStock = item.current_stock < LOW_STOCK_THRESHOLD;
    const stockColor = isLowStock ? "#B91C1C" : "#15803D";

    return (
      <View className="bg-slate-200 rounded-lg p-4 mb-4">
        <View className="flex-row justify-between items-center">
          <View>
            {/* FIX 3: Render the correct keys */}
            <Text className="font-bold text-lg text-slate-800">
              {item.item}
            </Text>
            <Text className="text-sm font-medium text-slate-500">
              {item.item_nepali}
            </Text>
          </View>
          <Text
            style={{ color: stockColor }}
            className="font-extrabold text-xl"
          >
            {item.current_stock} {item.unit}
          </Text>
        </View>
      </View>
    );
  };

  const listHeader = (
    <>
      <View className="mb-4 flex-row items-center">
        <Dougnut />
      </View>

      <View className="mb-4 flex-row items-center justify-between">
        <Text className="text-lg font-semibold text-slate-600">
          Items ({filteredProducts.length})
        </Text>
        <Pressable
          onPress={() => fetchProducts(false)}
          className="rounded-full bg-[#007566]/10 px-4 py-1"
        >
          <Text className="text-xs font-bold text-[#007566]">Refresh</Text>
        </Pressable>
      </View>
    </>
  );

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-[#fff] mt-14 px-4"
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View className="mt-4">
        <Text className="font-inter text-3xl font-bold uppercase text-slate-900">
          Inventory
        </Text>
      </View>

      <TextInput
        value={search}
        onChangeText={handleSearch}
        placeholder="Search by name (English or Nepali)"
        className="bg-slate-100 border border-slate-300 rounded-xl px-4 py-4 my-6 text-base"
      />

      {loading ? (
        <View className="flex-1 justify-center items-center">
          <ActivityIndicator size="large" color="#007566" />
          <Text className="mt-2 text-slate-400">Loading Inventory...</Text>
        </View>
      ) : error ? (
        <View className="flex-1 justify-center items-center px-4">
          <Text className="text-red-600 text-center font-semibold">{error}</Text>
          <Pressable
            onPress={() => fetchProducts()}
            className="mt-4 bg-[#007566] px-6 py-3 rounded-xl"
          >
            <Text className="text-white font-bold">Retry</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={filteredProducts}
          keyExtractor={(_, index) => index.toString()}
          renderItem={renderItem}
          ListHeaderComponent={listHeader}
          showsHorizontalScrollIndicator={false}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingBottom: 100 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                fetchProducts();
              }}
            />
          }
          ListEmptyComponent={
            <Text className="text-center text-slate-400 mt-10">
              No items found.
            </Text>
          }
        />
      )}
    </KeyboardAvoidingView>
  );
}
