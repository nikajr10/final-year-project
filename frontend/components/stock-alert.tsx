import React from "react";
import { Image, Text, View } from "react-native";

interface StockItem {
  name: string;
  stock: number;
}

const StockAlertCard = ({ item }: { item: StockItem }) => {
  return (
    <View className="bg-red-100 rounded-xl mb-3">
      <View className="flex-row items-center p-4 gap-4">
        {/* Icon */}
        <Image
          source={require("../assets/alert.png")}
          style={{ width: 24, height: 24 }}
        />

        {/* Product Info */}
        <View>
          <Text className="text-base font-semibold">{item.name}</Text>

          <Text className="text-xs font-bold text-red-700">
            ONLY {item.stock} LEFT IN STOCK
          </Text>
        </View>
      </View>
    </View>
  );
};

export default StockAlertCard;
