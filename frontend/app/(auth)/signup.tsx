"use client";

import { useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
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

// ✅ Use your working local IP
const API_URL = "http://192.168.1.95:8000";

export default function SignupScreen() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validationError = useMemo(() => {
    if (!fullName.trim()) return "Full name is required.";
    if (!email.trim()) return "Email is required.";
    if (!email.includes("@")) return "Enter a valid email.";
    if (password.length < 6) return "Password must be at least 6 characters.";
    if (confirmPassword !== password) return "Passwords do not match.";
    return null;
  }, [fullName, email, password, confirmPassword]);

  const handleSignup = async () => {
    if (validationError) {
      Alert.alert("Fix signup details", validationError);
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: fullName.trim(),
          email: email.toLowerCase().trim(),
          password: password,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        // Optionally save user info immediately
        await AsyncStorage.setItem("user_name", data.name || fullName.trim());
        await AsyncStorage.setItem("user_token", data.token || "");
        await AsyncStorage.setItem("user_id", data.id?.toString() || "0");

        Alert.alert("✅ Signup Successful", "You are now logged in!");
        router.replace("/profile");
      } else {
        Alert.alert("❌ Signup Failed", data.detail || "Something went wrong.");
      }
    } catch (error) {
      console.error(error);
      Alert.alert("❌ Network Error", "Could not reach the server.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View className="flex-1 items-center justify-center bg-white px-4 dark:bg-zinc-950">
        <View className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
          <Text className="text-center text-sm font-semibold tracking-wide text-zinc-600 dark:text-zinc-400">
            Inventory Management
          </Text>
          <Text className="mt-2 text-center text-3xl font-extrabold text-purple-700 dark:text-purple-300">
            Signup
          </Text>

          {/* Full Name */}
          <Text className="mt-6 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Full Name
          </Text>
          <TextInput
            value={fullName}
            onChangeText={setFullName}
            placeholder="e.g. Ram Bahadur"
            autoCapitalize="words"
            autoCorrect={false}
            textContentType="name"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          {/* Email */}
          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Email
          </Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="e.g. ram@gmail.com"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            textContentType="emailAddress"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          {/* Password */}
          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Password
          </Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="••••••"
            secureTextEntry
            textContentType="newPassword"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          {/* Confirm Password */}
          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Confirm Password
          </Text>
          <TextInput
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            placeholder="••••••"
            secureTextEntry
            textContentType="newPassword"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          {/* Signup Button */}
          <Pressable
            onPress={handleSignup}
            disabled={isSubmitting}
            className="mt-6 items-center rounded-xl bg-purple-700 py-3"
            style={({ pressed }) => [
              pressed && { opacity: 0.9 },
              isSubmitting && { opacity: 0.6 },
            ]}
          >
            <Text className="text-base font-bold text-white">
              {isSubmitting ? "Creating..." : "Sign up"}
            </Text>
          </Pressable>

          {/* Login Redirect */}
          <Pressable
            onPress={() => router.push("/(auth)/login")}
            className="mt-4 items-center py-2"
            style={({ pressed }) => pressed && { opacity: 0.85 }}
          >
            <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
              Already have an account? Log in
            </Text>
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}