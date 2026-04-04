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
import { API_URL, FETCH_TIMEOUT_MS } from "../../constants/Config";

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
      Alert.alert("Fix details", validationError);
      return;
    }

    setIsSubmitting(true);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    try {
      // Step 1: Register
      const res = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: fullName.trim(),
          email: email.toLowerCase().trim(),
          password,
        }),
        signal: controller.signal,
      });

      clearTimeout(timer);
      const data = await res.json();

      if (!res.ok) {
        Alert.alert("Signup Failed", data.detail || "Something went wrong.");
        return;
      }

      // Step 2: Auto-login so the user gets a valid token
      const loginController = new AbortController();
      const loginTimer = setTimeout(() => loginController.abort(), FETCH_TIMEOUT_MS);

      const loginRes = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.toLowerCase().trim(),
          password,
        }),
        signal: loginController.signal,
      });

      clearTimeout(loginTimer);
      const loginData = await loginRes.json();

      if (loginRes.ok && loginData.access_token) {
        await AsyncStorage.setItem("access_token", loginData.access_token);
        router.replace("/(tabs)");
      } else {
        // Registered but auto-login failed — send to login screen
        Alert.alert("Account Created", "Please log in with your new credentials.");
        router.replace("/(auth)/login");
      }
    } catch (error: any) {
      clearTimeout(timer);
      const msg = error?.name === "AbortError"
        ? "Server took too long to respond."
        : "Could not connect to the server.";
      Alert.alert("Network Error", msg);
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
            Sign Up
          </Text>

          <Text className="mt-6 text-sm font-semibold text-slate-600 dark:text-slate-300">Full Name</Text>
          <TextInput
            value={fullName}
            onChangeText={setFullName}
            placeholder="e.g. Ram Bahadur"
            autoCapitalize="words"
            autoCorrect={false}
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">Email</Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="e.g. ram@gmail.com"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">Password</Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="Min. 6 characters"
            secureTextEntry
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">Confirm Password</Text>
          <TextInput
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            placeholder="••••••"
            secureTextEntry
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

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
              {isSubmitting ? "Creating account..." : "Sign up"}
            </Text>
          </Pressable>

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
