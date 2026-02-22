import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  View,
  Alert,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

const DummyProfile = require("../../assets/images/Dummy.png");

export default function Profile() {
  const router = useRouter();
  const [name, setName] = useState("Loading...");

  // 🔹 Load user name when screen opens
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const storedName = await AsyncStorage.getItem("user_name");

        if (storedName) {
          setName(storedName);
        } else {
          setName("User");
        }
      } catch (error) {
        console.log("Error loading profile:", error);
        setName("User");
      }
    };

    loadProfile();
  }, []);

  // 🔹 Logout function
  const handleLogout = async () => {
    try {
      // Remove only necessary keys
      await AsyncStorage.removeItem("user_token");
      await AsyncStorage.removeItem("user_name");
      await AsyncStorage.removeItem("user_id");

      // Navigate to login screen
      router.replace("/login");
    } catch (error) {
      Alert.alert("Error", "Logout failed. Try again.");
    }
  };

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white mt-14 p-4"
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      {/* Title */}
      <View>
        <Text className="text-2xl font-bold mb-4 text-black">
          PROFILE
        </Text>
      </View>

      {/* Profile Section */}
      <View className="flex-col items-center justify-center mt-10 gap-4">
        <Image
          source={DummyProfile}
          style={{ width: 160, height: 160, borderRadius: 80 }}
          resizeMode="cover"
        />

        <Text className="text-2xl my-10 font-semibold text-zinc-800">
          {name}
        </Text>
      </View>

      {/* Logout Button */}
      <View>
        <Pressable onPress={handleLogout}>
          <Text className="text-center bg-[#FEE2E2] text-[#B91C1C] font-bold text-lg py-4 rounded-xl mt-10 active:opacity-90">
            Logout
          </Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}
