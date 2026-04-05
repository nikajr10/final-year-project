import React, { useEffect, useState } from "react";
import { View, Text, Pressable, Alert, KeyboardAvoidingView, Platform } from "react-native";
import { Image } from "expo-image";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useRouter } from "expo-router";

const DummyProfile = require("../../assets/images/Dummy.svg");

export default function Profile() {
  const router = useRouter();
  const [name, setName] = useState("Loading...");

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const storedName = await AsyncStorage.getItem("user_name");
        setName(storedName || "User");
      } catch {
        setName("User");
      }
    };
    loadProfile();
  }, []);

  const handleLogout = async () => {
    try {
      await AsyncStorage.multiRemove([
        "access_token",
        "user_name",
        "user_id",
        "user_token",
        "session_greeting",
      ]);
      router.replace("/(auth)/login");
    } catch (error) {
      Alert.alert("Error", "Logout failed. Try again.");
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      className="flex-1 bg-gray-100 px-6"
    >
      <View className="mt-20">
              <Text className="font-inter text-3xl font-bold uppercase text-slate-900">
                Profile
              </Text>
            </View>

      <View className="mt-20 items-center">
        <Image
          source={DummyProfile}
          style={{ width: 140, height: 140, borderRadius: 70 }}
          contentFit="cover"
        />
        <Text className="text-2xl font-semibold mt-4">{name}</Text>
        <Text className="text-gray-500 mt-1">Logged in user</Text>
      </View>

      <Pressable
        onPress={handleLogout}
        className="bg-red-500 py-4 rounded-2xl mt-10"
      >
        <Text className="text-white text-center font-semibold text-lg">
          Logout
        </Text>
      </Pressable>
    </KeyboardAvoidingView>
  );
}
