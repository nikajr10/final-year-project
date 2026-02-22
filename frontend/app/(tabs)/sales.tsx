import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Text,
  View,
  StyleSheet,
  Pressable,
} from "react-native";

export default function SalesScreen() {
  const [selectedIndex, setSelectedIndex] = useState(0);

  const tabs = ["First", "Second"];

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      {/* Title */}
      <Text className="font-inter text-3xl font-bold uppercase text-slate-900">Sales</Text>

      {/* Custom Segmented Control */}
      <View style={styles.segmentContainer} className="my-6">
        {tabs.map((tab, index) => (
          <Pressable
            key={index}
            onPress={() => setSelectedIndex(index)}
            style={[
              styles.segmentButton,
              selectedIndex === index && styles.activeSegment,
            ]}
          >
            <Text
              style={[
                styles.segmentText,
                selectedIndex === index && styles.activeText,
              ]}
            >
              {tab}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Selected Content */}
      <View style={styles.contentContainer}>
        <Text style={styles.selectedText}>
          Selected: {tabs[selectedIndex]}
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#fff",
    marginTop: 50,
    paddingHorizontal: 20,
  },
  segmentContainer: {
    flexDirection: "row",
    backgroundColor: "#E2E8F0",
    borderRadius: 10,
    padding: 8,
  },
  segmentButton: {
    flex: 1,
    paddingVertical: 8,
    alignItems: "center",
    borderRadius: 8,
  },
  activeSegment: {
    backgroundColor: "#fff",
  },
  segmentText: {
    fontSize: 16,
    color: "#000",
  },
  activeText: {
    color: "#7E22CE",
    fontWeight: "bold",
  },
  contentContainer: {
    alignItems: "center",
  },
  selectedText: {
    fontSize: 18,
    fontWeight: "600",
  },
});
