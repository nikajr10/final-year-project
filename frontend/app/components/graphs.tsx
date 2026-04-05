import React, { useMemo, useState } from "react";
import {
  NativeScrollEvent,
  NativeSyntheticEvent,
  ScrollView,
  View,
  useWindowDimensions,
} from "react-native";
import Dougnut from "./dougnut";
import ProductGraph from "./productgraph";
import ProfitGraph from "./profitgraph";

export default function Graphs() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [containerWidth, setContainerWidth] = useState(0);
  const { width: windowWidth } = useWindowDimensions();
  const pageWidth = containerWidth || Math.max(windowWidth - 32, 0);

  const pages = useMemo(
    () => [
      { key: "profit", element: <ProfitGraph /> },
      { key: "product", element: <ProductGraph /> },
    ],
    [],
  );

  const handleMomentumEnd = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    const nextPageWidth = pageWidth || event.nativeEvent.layoutMeasurement.width;
    if (!nextPageWidth) return;

    const nextIndex = Math.round(event.nativeEvent.contentOffset.x / nextPageWidth);
    setActiveIndex(nextIndex);
  };

  return (
    <View
      className="pt-0"
      onLayout={(event) => setContainerWidth(event.nativeEvent.layout.width)}
    >
      <ScrollView
        horizontal
        pagingEnabled
        bounces={false}
        decelerationRate="fast"
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={handleMomentumEnd}
        scrollEventThrottle={16}
      >
        {pages.map((page) => (
          <View
            key={page.key}
            style={{ width: pageWidth }}
            className="overflow-hidden"
          >
            {page.element}
          </View>
        ))}
      </ScrollView>

      <View className="-mt-10 flex-row items-center justify-center gap-2">
        {pages.map((page, index) => (
          <View
            key={page.key}
            className={`h-2 w-2 rounded-full ${
              activeIndex === index ? "bg-[#0F766E]" : "bg-[#A8B7CF]"
            }`}
          />
        ))}
      </View>
    </View>
  );
}
