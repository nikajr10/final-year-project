import React, { useState } from "react";
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
import { useFocusEffect } from "expo-router"; 
import AsyncStorage from "@react-native-async-storage/async-storage";

const API_URL = "http://192.168.1.95:8000";

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

  const fetchProducts = async () => {
    try {
      const token = await AsyncStorage.getItem("access_token");
      if (!token) return;

      // FIX 1: Exact /stock endpoint
      const response = await fetch(`${API_URL}/stock`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        }
      });
      
      const data = await response.json();
      
      if (response.ok && data.status === "success") {
        // FIX 2: Extract data.inventory
        const inventoryList = data.inventory;
        setProducts(inventoryList);
        setFilteredProducts(inventoryList); 
      } else {
        console.error("Failed to fetch inventory:", data);
      }
    } catch (error) {
      console.error("Error fetching inventory:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    React.useCallback(() => {
      fetchProducts();
    }, [])
  );

  const handleSearch = (text: string) => {
    setSearch(text);
    if (text) {
      const newData = products.filter((p) => {
        // FIX 3: Search using the correct keys
        const itemData = p.item ? p.item.toUpperCase() : "";
        const itemDataNepali = p.item_nepali ? p.item_nepali : "";
        const textData = text.toUpperCase();
        
        return itemData.indexOf(textData) > -1 || itemDataNepali.indexOf(textData) > -1;
      });
      setFilteredProducts(newData);
    } else {
      setFilteredProducts(products);
    }
  };

  const renderItem = ({ item }: { item: Product }) => {
    const isLowStock = item.current_stock < 10;
    const stockColor = isLowStock ? "#B91C1C" : "#15803D"; 

    return (
      <View className="bg-slate-200 rounded-lg p-4 mb-4">
        <View className="flex-row justify-between items-center">
          <View>
            {/* FIX 3: Render the correct keys */}
            <Text className="font-bold text-lg text-slate-800">{item.item}</Text>
            <Text className="text-sm font-medium text-slate-500">{item.item_nepali}</Text>
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
        placeholder="Search By Name (English or Nepali)"
        className="bg-slate-100 border border-slate-300 rounded-xl px-4 py-4 my-6 text-base"
      />

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

      {loading ? (
        <View className="flex-1 justify-center items-center">
          <ActivityIndicator size="large" color="#7E22CE" />
          <Text className="mt-2 text-slate-400">Loading Inventory...</Text>
        </View>
      ) : (
        <FlatList
          data={filteredProducts}
          keyExtractor={(item, index) => index.toString()}
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