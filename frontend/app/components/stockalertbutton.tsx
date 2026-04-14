import { TriangleAlert } from "lucide-react-native";
import React from "react";
import { Pressable, Text, View } from "react-native";

type StockAlertButtonProps = {
  count?: number;
  onPress?: () => void;
};

export default function StockAlertButton({
  count = 0,
  onPress,
}: StockAlertButtonProps) {
  const showBadge = count > 0;
  const badgeLabel = count > 99 ? "99+" : String(count);

  return (
    <Pressable
      accessibilityLabel={showBadge ? `${count} stock alerts` : "Stock alerts"}
      accessibilityRole="button"
      className="relative h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#FADDDD]"
      hitSlop={8}
      onPress={onPress}
      style={({ pressed }) => (pressed ? { opacity: 0.84 } : null)}
    >
      <TriangleAlert color="#D2342A" size={22} strokeWidth={2.15} />

      {showBadge && (
        <View className="absolute -right-2 -top-3 min-h-[24px] min-w-[24px] items-center justify-center rounded-full bg-[#C9261C] px-1.5">
          <Text className="text-base font-bold text-white">{badgeLabel}</Text>
        </View>
      )}
    </Pressable>
  );
}
