import React, { useEffect, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  View,
  Text,
  TextInput,
  FlatList,
  ActivityIndicator,
  Pressable,
  RefreshControl
} from "react-native";
import { useFocusEffect } from "expo-router"; // Use this to auto-refresh when you open the tab

// ✅ YOUR IP ADDRESS
const API_URL = "http://192.168.1.95:8000"; // your local backend IP


interface Product {
  id: number;
  name_english: string;
  name_nepali: string;
  quantity: number;
  unit: string;
  cost_price: number;
  selling_price: number;
}

export default function InventoryScreen() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // 1. Function to Fetch Data
  const fetchProducts = async () => {
    try {
      const response = await fetch(`${API_URL}/products`);
      const data = await response.json();
      
      if (response.ok) {
        setProducts(data);
        setFilteredProducts(data); // Initially, show everything
      }
    } catch (error) {
      console.error("Error fetching inventory:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // 2. Auto-fetch when screen opens
  useFocusEffect(
    React.useCallback(() => {
      fetchProducts();
    }, [])
  );

  // 3. Handle Search
  const handleSearch = (text: string) => {
    setSearch(text);
    if (text) {
      const newData = products.filter((item) => {
        const itemData = item.name_english ? item.name_english.toUpperCase() : "".toUpperCase();
        const itemDataNepali = item.name_nepali ? item.name_nepali : "";
        const textData = text.toUpperCase();
        
        return itemData.indexOf(textData) > -1 || itemDataNepali.indexOf(textData) > -1;
      });
      setFilteredProducts(newData);
    } else {
      setFilteredProducts(products);
    }
  };

  // 4. Render Single Item
  const renderItem = ({ item }: { item: Product }) => {
    // Logic: Red if quantity is less than 10, Green otherwise
    const isLowStock = item.quantity < 10;
    const stockColor = isLowStock ? "#B91C1C" : "#15803D"; // Red : Green

    return (
      <View className="bg-slate-200 rounded-lg p-4 mb-4">
        <View className="flex-row justify-between items-center">
          <View>
            <Text className="font-bold text-lg text-slate-800">{item.name_english}</Text>
            <Text className="text-sm font-medium text-slate-500">{item.name_nepali}</Text>
          </View>
          <Text 
            style={{ color: stockColor }} 
            className="font-extrabold text-xl"
          >
            {item.quantity} {item.unit}
          </Text>
        </View>
        
        <View className="flex-row justify-between mt-3 border-t border-slate-300 pt-2">
          <Text className="text-sm text-slate-600 font-semibold">
             Cost: Rs {item.cost_price}
          </Text>
          <Text className="text-sm text-slate-600 font-semibold">
             Sell: Rs {item.selling_price}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-[#fff] mt-14 px-4"
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      {/* Header */}
      <View className="mt-4">
        <Text className="font-inter text-3xl font-bold uppercase text-slate-900">
          Inventory
        </Text>
      </View>

      {/* Search Bar */}
      <TextInput
        value={search}
        onChangeText={handleSearch}
        placeholder="Search By Name (English or Nepali)"
        className="bg-slate-100 border border-slate-300 rounded-xl px-4 py-4 my-6 text-base"
      />

      {/* List Header */}
      <View className="flex-row justify-between items-center mb-4">
        <Text className="font-semibold text-lg text-slate-600">
          Items List ({filteredProducts.length})
        </Text>
        <Pressable 
          onPress={fetchProducts}
          className="rounded-full bg-purple-100 px-4 py-1"
        >
          <Text className="text-purple-700 font-bold text-xs">Refresh</Text>
        </Pressable>
      </View>

      {/* Dynamic List */}
      {loading ? (
        <View className="flex-1 justify-center items-center">
          <ActivityIndicator size="large" color="#7E22CE" />
          <Text className="mt-2 text-slate-400">Loading Inventory...</Text>
        </View>
      ) : (
        <FlatList
          data={filteredProducts}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderItem}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingBottom: 100 }}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchProducts(); }} />
          }
          ListEmptyComponent={
            <Text className="text-center text-slate-400 mt-10">No items found.</Text>
          }
        />
      )}
    </KeyboardAvoidingView>
  );
}