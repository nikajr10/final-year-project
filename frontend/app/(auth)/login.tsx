import { useRouter } from "expo-router";
import React, { useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

// 🚨 REPLACE WITH YOUR COMPUTER'S LOCAL IP ADDRESS
// Find it by running `ipconfig` (Windows) or `ipconfig getifaddr en0` (Mac)
const API_URL = "http://192.168.1.95:8000"; // your local backend IP


export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password) {
      Alert.alert("Missing info", "Enter your email and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      console.log(`🔌 Attempting login to: ${API_URL}/api/auth/login`);

      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.toLowerCase().trim(), // Ensure email format is clean
          password: password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // ✅ Login Success
        console.log("✅ Login Successful:", data);
        
        // FIX: Save the secure JWT Token instead of user_id
        await AsyncStorage.setItem("access_token", data.access_token);
        
        // FIX: Generic welcome message since backend doesn't send the name here
        Alert.alert("Welcome back!", "You have logged in successfully.");
        
        // Navigate to Home
        router.replace("/(tabs)"); 
      } else {
        // ❌ Login Failed (Wrong password, etc.)
        Alert.alert("Login Failed", data.detail || "Invalid credentials.");
      }
    } catch (error) {
      console.error("❌ Network Error:", error);
      Alert.alert(
        "Connection Error",
        "Could not connect to the server. Check your Wi-Fi and IP address."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.select({ ios: "padding", android: undefined })}
    >
      <View className="flex-1 items-center justify-center bg-white px-4 dark:bg-zinc-950">
        <View className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
          <Text className="text-center text-lg font-semibold tracking-wide text-black-600 dark:text-zinc-400">
            Speech Enabled
          </Text>
          <Text className="mt-2 text-center text-3xl font-extrabold leading-9 text-purple-700 dark:text-purple-300">
            Inventory Management{`\n`}System
          </Text>

          {/* Email Input */}
          <Text className="mt-8 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Email
          </Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="e.g. admin@test.com"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          {/* Password Input */}
          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Password
          </Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="••••••"
            secureTextEntry
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          {/* Login Button */}
          <Pressable
            accessibilityRole="button"
            onPress={handleLogin}
            disabled={isSubmitting}
            className="mt-5 items-center rounded-xl bg-purple-700 py-3"
            style={({ pressed }) => [
              pressed && { opacity: 0.9 },
              isSubmitting && { opacity: 0.6 },
            ]}
          >
            <Text className="text-base font-bold text-white">
              {isSubmitting ? "Logging in..." : "Log in"}
            </Text>
          </Pressable>

          {/* Links */}
          <Pressable
            onPress={() => router.push("/(auth)/signup")}
            className="mt-3 items-center py-2"
          >
            <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
              Don’t have an account? Sign up
            </Text>
          </Pressable>

          <Pressable
            onPress={() => router.push("/(auth)/forgot-password")}
            className="items-center py-2"
          >
            <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
              Forgot password?
            </Text>
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}